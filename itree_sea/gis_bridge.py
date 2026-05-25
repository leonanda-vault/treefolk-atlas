"""
gis_bridge.py — GeoJSON / Shapefile ingestion and enrichment pipeline
======================================================================

This module is the GIS surveyor's entry point.  It reads a GeoJSON or
Shapefile containing tree inventory points, maps the attribute fields
to the species database, runs the engine calculations row-by-row, and
exports an enriched GeoJSON with ecosystem benefit columns appended.

Workflow:
  1. Ingest geodata (GeoJSON or Shapefile) via GeoPandas.
  2. Validate required columns (species, DBH at minimum).
  3. For each tree row:
       a. Lookup species → allometric coefficients (with fallback).
       b. Calculate biomass, carbon, sequestration, stormwater, pollution.
  4. Append result columns to the GeoDataFrame.
  5. Export as enriched GeoJSON.

Dependencies:
  • geopandas (for spatial data I/O)
  • pandas (bundled with geopandas)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Union

import pandas as pd

try:
    import geopandas as gpd
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False

from itree_sea.config import (
    GIS_SPECIES_FIELD,
    GIS_DBH_FIELD,
    GIS_HEIGHT_FIELD,
    GIS_CONDITION_FIELD,
    OUTPUT_DIR,
    DEFAULT_LAI,
)
from itree_sea.database import (
    get_coefficients,
    lookup_species,
    AllometricCoefficients,
)
from itree_sea.engine import (
    calculate_biomass,
    calculate_sequestration,
    estimate_stormwater_interception,
    estimate_pollution_removal,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Input validation
# ──────────────────────────────────────────────────────────────────────

class GISValidationError(Exception):
    """Raised when the input geodata is missing required columns."""
    pass


def _validate_columns(gdf: "gpd.GeoDataFrame") -> None:
    """Check that the GeoDataFrame has at minimum a species column.

    DBH is strongly recommended but will be filled with a default if
    missing.  Height and condition are optional.

    Raises
    ------
    GISValidationError
        If the species column is completely absent.
    """
    cols_lower = {c.lower(): c for c in gdf.columns}

    if GIS_SPECIES_FIELD.lower() not in cols_lower:
        # Try common alternatives
        alternatives = ["species_name", "scientific_name", "tree_species", "sp", "nama"]
        found = None
        for alt in alternatives:
            if alt in cols_lower:
                found = cols_lower[alt]
                break

        if found:
            gdf.rename(columns={found: GIS_SPECIES_FIELD}, inplace=True)
            logger.info("Mapped column '%s' → '%s'", found, GIS_SPECIES_FIELD)
        else:
            raise GISValidationError(
                f"Missing required column '{GIS_SPECIES_FIELD}'.  "
                f"Available columns: {list(gdf.columns)}"
            )


def _normalise_columns(gdf: "gpd.GeoDataFrame") -> "gpd.GeoDataFrame":
    """Normalise column names to lowercase and apply sensible defaults.

    - If ``dbh_cm`` is missing, attempts to find ``dbh``, ``dbh_mm``, etc.
    - If ``height_m`` is missing, leaves it as NaN (engine will estimate).
    - If ``condition`` is missing, defaults to 'good'.

    Returns the (modified) GeoDataFrame.
    """
    # Lowercase all columns for consistency
    rename_map = {c: c.lower().strip() for c in gdf.columns}
    gdf = gdf.rename(columns=rename_map)

    # DBH normalisation
    if GIS_DBH_FIELD not in gdf.columns:
        if "dbh" in gdf.columns:
            gdf = gdf.rename(columns={"dbh": GIS_DBH_FIELD})
        elif "dbh_mm" in gdf.columns:
            gdf[GIS_DBH_FIELD] = gdf["dbh_mm"] / 10.0
            logger.info("Converted dbh_mm → dbh_cm")
        elif "dbh_in" in gdf.columns:
            gdf[GIS_DBH_FIELD] = gdf["dbh_in"] * 2.54
            logger.info("Converted dbh_in → dbh_cm")
        else:
            logger.warning("No DBH column found — will use default 15 cm for all trees")
            gdf[GIS_DBH_FIELD] = 15.0

    # Height normalisation
    if GIS_HEIGHT_FIELD not in gdf.columns:
        if "height" in gdf.columns:
            gdf = gdf.rename(columns={"height": GIS_HEIGHT_FIELD})
        else:
            gdf[GIS_HEIGHT_FIELD] = None

    # Condition
    if GIS_CONDITION_FIELD not in gdf.columns:
        gdf[GIS_CONDITION_FIELD] = "good"

    return gdf


# ──────────────────────────────────────────────────────────────────────
# Ingestion
# ──────────────────────────────────────────────────────────────────────

def ingest_geodata(
    input_path: Union[str, Path],
) -> "gpd.GeoDataFrame":
    """Read a GeoJSON or Shapefile into a GeoDataFrame.

    Parameters
    ----------
    input_path : str or Path
        Path to a .geojson, .json, or .shp file.

    Returns
    -------
    gpd.GeoDataFrame
        The loaded geodata with columns normalised.

    Raises
    ------
    ImportError
        If geopandas is not installed.
    FileNotFoundError
        If the input file does not exist.
    GISValidationError
        If required columns are missing.
    """
    if not HAS_GEOPANDAS:
        raise ImportError(
            "geopandas is required for GIS bridge functionality.  "
            "Install it with:  pip install geopandas"
        )

    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    logger.info("Reading geodata from %s", input_path)
    gdf = gpd.read_file(str(input_path))
    logger.info("Loaded %d features", len(gdf))

    # Normalise and validate
    gdf = _normalise_columns(gdf)
    _validate_columns(gdf)

    return gdf


# ──────────────────────────────────────────────────────────────────────
# Enrichment
# ──────────────────────────────────────────────────────────────────────

def enrich_geodataframe(
    gdf: "gpd.GeoDataFrame",
    db_path: Optional[Path] = None,
    lai: float = DEFAULT_LAI,
) -> "gpd.GeoDataFrame":
    """Run ecosystem benefit calculations on every tree in the GeoDataFrame.

    For each row, this function:
      1. Resolves allometric coefficients from the species database.
      2. Calculates biomass and carbon storage.
      3. Calculates annual carbon sequestration.
      4. Estimates stormwater interception.
      5. Estimates air pollution removal.

    All results are appended as new columns to the GeoDataFrame.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Tree inventory with at least 'species' and 'dbh_cm' columns.
    db_path : Path, optional
        Override the default database path.
    lai : float
        Leaf Area Index for canopy calculations.

    Returns
    -------
    gpd.GeoDataFrame
        The input GeoDataFrame with new ecosystem benefit columns.
    """
    # Prepare result columns
    result_cols = {
        "agb_kg": [],
        "bgb_kg": [],
        "total_biomass_kg": [],
        "carbon_storage_kg": [],
        "annual_seq_kg": [],
        "co2_storage_kg": [],
        "co2_sequestration_kg": [],
        "o2_production_kg_yr": [],
        "epa_gasoline_liters_yr": [],
        "epa_km_driven_yr": [],
        "stormwater_l": [],
        "pm25_removed_g": [],
        "no2_removed_g": [],
        "o3_removed_g": [],
        "so2_removed_g": [],
        "pollution_total_g": [],
        "match_level": [],
        "equation_used": [],
    }

    total = len(gdf)
    for idx, row in gdf.iterrows():
        species_name = str(row.get(GIS_SPECIES_FIELD, "")).strip()
        dbh = _safe_float(row.get(GIS_DBH_FIELD), default=15.0)
        height = _safe_float(row.get(GIS_HEIGHT_FIELD), default=None)
        condition = str(row.get(GIS_CONDITION_FIELD, "good")).strip()
        cle = _safe_float(row.get("cle"), default=5.0) if "cle" in row else 5.0

        # Resolve species info
        sp_record = lookup_species(scientific_name=species_name, db_path=db_path)
        is_palm = sp_record.is_palm if sp_record else False
        growth_rate = sp_record.growth_rate if sp_record else "moderate"

        # Resolve coefficients
        genus = species_name.split()[0] if species_name else None
        coeffs = get_coefficients(
            scientific_name=species_name if species_name else None,
            genus=genus,
            db_path=db_path,
        )

        # Calculate biomass & carbon
        bio = calculate_biomass(
            dbh_cm=dbh,
            height_m=height,
            coefficients=coeffs,
            condition=condition,
            is_palm=is_palm,
            lai=lai,
            cle=cle,
        )

        # Sequestration
        seq = calculate_sequestration(
            dbh_cm=dbh,
            height_m=height,
            coefficients=coeffs,
            growth_rate=growth_rate,
            is_palm=is_palm,
            lai=lai,
            cle=cle,
        )

        # Resolve LAI and crown modifier for stormwater and pollution
        from itree_sea.config import DEFAULT_LAI
        site_lai_factor = lai / DEFAULT_LAI
        spec_lai = coeffs.species_lai if coeffs else DEFAULT_LAI
        resolved_lai = spec_lai * site_lai_factor
        
        crown_modifier = coeffs.crown_modifier if coeffs else None

        # Stormwater
        stormwater = estimate_stormwater_interception(dbh, resolved_lai, crown_modifier=crown_modifier)

        # Pollution
        pollution = estimate_pollution_removal(dbh, resolved_lai, crown_modifier=crown_modifier, height_m=height)

        # Append
        result_cols["agb_kg"].append(bio.agb_kg)
        result_cols["bgb_kg"].append(bio.bgb_kg)
        result_cols["total_biomass_kg"].append(bio.total_biomass_kg)
        result_cols["carbon_storage_kg"].append(bio.carbon_storage_kg)
        result_cols["annual_seq_kg"].append(bio.carbon_sequestration_kg)
        result_cols["co2_storage_kg"].append(bio.co2_storage_kg)
        result_cols["co2_sequestration_kg"].append(bio.co2_sequestration_kg)
        result_cols["o2_production_kg_yr"].append(bio.o2_production_kg_yr)
        result_cols["epa_gasoline_liters_yr"].append(bio.epa_gasoline_liters_yr)
        result_cols["epa_km_driven_yr"].append(bio.epa_km_driven_yr)
        result_cols["stormwater_l"].append(stormwater)
        result_cols["pm25_removed_g"].append(pollution.pm25_g)
        result_cols["no2_removed_g"].append(pollution.no2_g)
        result_cols["o3_removed_g"].append(pollution.o3_g)
        result_cols["so2_removed_g"].append(pollution.so2_g)
        result_cols["pollution_total_g"].append(pollution.total_g)
        result_cols["match_level"].append(bio.match_level)
        result_cols["equation_used"].append(bio.equation_used)

        if (idx + 1) % 100 == 0 or (idx + 1) == total:
            logger.info("Processed %d / %d trees", idx + 1, total)

    # Attach new columns
    for col_name, col_data in result_cols.items():
        gdf[col_name] = col_data

    return gdf


# ──────────────────────────────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────────────────────────────

def export_geojson(
    gdf: "gpd.GeoDataFrame",
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Write the enriched GeoDataFrame to a GeoJSON file.

    Parameters
    ----------
    gdf : gpd.GeoDataFrame
        Enriched tree data.
    output_path : str or Path, optional
        Destination path.  Defaults to ``output/enriched_trees.geojson``.

    Returns
    -------
    Path
        The path to the written file.
    """
    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "enriched_trees.geojson"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    gdf.to_file(str(output_path), driver="GeoJSON")
    logger.info("Exported enriched GeoJSON to %s (%d features)", output_path, len(gdf))

    return output_path


# ──────────────────────────────────────────────────────────────────────
# Full pipeline (convenience)
# ──────────────────────────────────────────────────────────────────────

def run_gis_pipeline(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    db_path: Optional[Path] = None,
    lai: float = DEFAULT_LAI,
) -> Path:
    """End-to-end GIS pipeline: ingest → enrich → export.

    Parameters
    ----------
    input_path : str or Path
        Input GeoJSON or Shapefile.
    output_path : str or Path, optional
        Output GeoJSON path.
    db_path : Path, optional
        Database location override.
    lai : float
        Leaf Area Index.

    Returns
    -------
    Path
        Path to the exported enriched GeoJSON.
    """
    gdf = ingest_geodata(input_path)
    gdf = enrich_geodataframe(gdf, db_path=db_path, lai=lai)
    return export_geojson(gdf, output_path)


# ──────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────

def _safe_float(value, default: Optional[float] = None) -> Optional[float]:
    """Convert a value to float, returning *default* on failure."""
    if value is None:
        return default
    try:
        result = float(value)
        if pd.isna(result):
            return default
        return result
    except (ValueError, TypeError):
        return default
