"""
simulation.py — Helper module for manual simulation and CAD georeferencing
========================================================================

Implements coordinate scaling, offset adjustments, center-anchoring projection,
and delta calculation logic for manual tree additions and removals.
"""

from __future__ import annotations

import math
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd

from itree_sea.database import get_coefficients, lookup_species
from itree_sea.engine import calculate_biomass, forecast_growth, ForecastRow
from itree_sea.config import DEFAULT_LAI, ANNUAL_RAIN_EVENTS, CONDITION_MULTIPLIERS

def project_coordinates(
    df: pd.DataFrame,
    anchor_lat: float = -6.2088,
    anchor_lon: float = 106.8456,
    scale_factor: float = 1.0,
    easting_offset: float = 0.0,
    northing_offset: float = 0.0,
    anchor_mode: str = "Center of Trees",
    projection_system: str = "Flat Earth Center Anchor (Manual)",
) -> pd.DataFrame:
    """Project local X/Y coordinates to Lat/Lon degrees.

    Applies drawing scale factor, aligns coordinates based on anchor mode,
    adds manual offsets, and projects using a first-order flat Earth model or UTM.
    """
    if df.empty or "x" not in df.columns or "y" not in df.columns:
        return df

    projected = df.copy()
    
    # Ensure coordinates are numeric
    projected["x"] = pd.to_numeric(projected["x"], errors="coerce").fillna(0.0)
    projected["y"] = pd.to_numeric(projected["y"], errors="coerce").fillna(0.0)

    # Filter spatial outliers (e.g. random CAD blocks placed far away)
    if len(projected) > 5:
        med_x = projected["x"].median()
        med_y = projected["y"].median()
        is_val_geo = projected["x"].between(-180, 180).all() and projected["y"].between(-90, 90).all()
        if is_val_geo:
            good_mask = (projected["x"] - med_x).abs().lt(1.0) & (projected["y"] - med_y).abs().lt(1.0)
        else:
            threshold = 100000.0 / scale_factor if scale_factor > 0 else 100000.0
            good_mask = (projected["x"] - med_x).abs().lt(threshold) & (projected["y"] - med_y).abs().lt(threshold)
        projected = projected[good_mask]

    # If coordinate system is a UTM zone, use pyproj for direct mapping
    if "UTM" in projection_system:
        epsg = 32748
        if "49S" in projection_system:
            epsg = 32749
        try:
            from pyproj import Transformer
            transformer = Transformer.from_crs(f"epsg:{epsg}", "epsg:4326", always_xy=True)
            # Apply scaling and shifts in UTM space (typically meters)
            x_m = projected["x"] * scale_factor + easting_offset
            y_m = projected["y"] * scale_factor + northing_offset
            lons, lats = transformer.transform(x_m.values, y_m.values)
            projected["lat"] = lats
            projected["lon"] = lons
            return projected
        except Exception:
            # Fallback to local flat earth projection if pyproj encounters error
            pass

    # Step 1: Apply scale factor (converts units to meters)
    projected["x_m"] = projected["x"] * scale_factor
    projected["y_m"] = projected["y"] * scale_factor

    # Step 2: Handle coordinate translation based on anchoring mode
    if anchor_mode == "Center of Trees" and len(projected) > 0:
        # Anchor the average of tree positions to the lat/lon coordinate
        mean_x = projected["x_m"].mean()
        mean_y = projected["y_m"].mean()
        dx = projected["x_m"] - mean_x
        dy = projected["y_m"] - mean_y
    else:
        # Anchor the CAD origin (0,0) to the lat/lon coordinate
        dx = projected["x_m"]
        dy = projected["y_m"]

    # Step 3: Apply fine-tuning translation offsets (meters)
    dx += easting_offset
    dy += northing_offset

    # Step 4: Convert meters offset to lat/lon degrees
    # 1 degree latitude ~= 111,132.95 meters
    # 1 degree longitude ~= 111,132.95 * cos(latitude) meters
    lat_per_meter = 1.0 / 111132.95
    r_lat = math.radians(anchor_lat)
    lon_per_meter = 1.0 / (111132.95 * math.cos(r_lat))

    projected["lat"] = anchor_lat + (dy * lat_per_meter)
    projected["lon"] = anchor_lon + (dx * lon_per_meter)

    return projected


def calculate_single_tree_schedule(
    species: str,
    dbh_cm: float,
    height_m: Optional[float],
    forecast_years: int = 25,
    condition: str = "good",
    lai: float = DEFAULT_LAI,
    rain_events: int = ANNUAL_RAIN_EVENTS,
    pollution_multiplier: float = 1.0,
    db_path: Optional[str] = None,
    true_growth_rate_cm: Optional[float] = None,
    palm_height_growth_m: Optional[float] = None,
    crown_modifier: Optional[float] = None,
    species_lai: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Calculate the multi-year forecast schedule for a single simulated tree."""
    # Resolve species details
    sp_record = lookup_species(scientific_name=species, db_path=db_path)
    is_palm = sp_record.is_palm if sp_record else False
    growth_rate = sp_record.growth_rate if sp_record else "moderate"

    # Resolve coefficients
    genus = species.split()[0] if species else ""
    coeffs = get_coefficients(scientific_name=species, genus=genus, db_path=db_path)

    # Apply morphology overrides if provided
    if true_growth_rate_cm is not None:
        coeffs.true_growth_rate_cm = true_growth_rate_cm
    if palm_height_growth_m is not None:
        coeffs.palm_height_growth_m = palm_height_growth_m
    if crown_modifier is not None:
        coeffs.crown_modifier = crown_modifier
    if species_lai is not None:
        coeffs.species_lai = species_lai

    # 2. Multi-year Forecast
    forecast = forecast_growth(
        initial_dbh_cm=dbh_cm,
        coefficients=coeffs,
        growth_rate=growth_rate,
        years=forecast_years,
        initial_height_m=height_m,
        is_palm=is_palm,
        lai=lai,
        rain_events=rain_events,
        pollution_multiplier=pollution_multiplier,
    )

    # Condition reduces benefits proportionally
    cond_mult = CONDITION_MULTIPLIERS.get(condition.lower().strip(), 0.80)

    # Format yearly schedule rows
    schedule_rows = []
    for f in forecast:
        schedule_rows.append({
            "year": f.year,
            "dbh_cm": f.dbh_cm,
            "height_m": f.height_m,
            "carbon_storage_kg": f.carbon_storage_kg * cond_mult,
            "carbon_seq_kg": f.carbon_sequestration_kg * cond_mult,
            "co2_storage_kg": f.co2_storage_kg * cond_mult,
            "co2_seq_kg": f.co2_sequestration_kg * cond_mult,
            "o2_production_kg_yr": f.o2_production_kg_yr * cond_mult,
            "epa_gasoline_liters_yr": f.epa_gasoline_liters_yr * cond_mult,
            "epa_km_driven_yr": f.epa_km_driven_yr * cond_mult,
            "stormwater_l": f.stormwater_litres * cond_mult,
            "pm25_removed_g": f.pm25_removed_g * cond_mult,
            "no2_removed_g": f.no2_removed_g * cond_mult,
            "o3_removed_g": f.o3_removed_g * cond_mult,
            "so2_removed_g": f.so2_removed_g * cond_mult,
        })

    return schedule_rows


def compute_simulation(
    baseline_schedule: pd.DataFrame,
    manual_plantings: List[Dict[str, Any]],
    removed_tree_ids: List[int],
    moved_trees: Optional[Dict[int, Tuple[float, float]]] = None,
    forecast_years: int = 25,
    lai: float = 5.0,
    rain_events: int = 180,
    pollution_multiplier: float = 1.0,
    db_path: Optional[str] = None,
) -> pd.DataFrame:
    """Compute the simulated schedule DataFrame by applying removals and manual additions.

    Returns the new schedule DataFrame.
    """
    # Create copies or empty DataFrames
    if baseline_schedule is not None and not baseline_schedule.empty:
        sim_schedule = baseline_schedule.copy()
    else:
        sim_schedule = pd.DataFrame(columns=[
            "tree_id", "block_name", "species", "x", "y", "layer",
            "year", "dbh_cm", "height_m", "carbon_storage_kg", "carbon_seq_kg",
            "co2_storage_kg", "co2_seq_kg", "o2_production_kg_yr", "epa_gasoline_liters_yr",
            "epa_km_driven_yr", "stormwater_l", "pm25_removed_g",
            "no2_removed_g", "o3_removed_g", "so2_removed_g", "match_level"
        ])

    # Step 1: Handle removed trees (zero out their benefits)
    if removed_tree_ids and not sim_schedule.empty:
        sched_removed_mask = sim_schedule["tree_id"].isin(removed_tree_ids)
        sched_metric_cols = [
            "carbon_storage_kg", "carbon_seq_kg", "co2_storage_kg",
            "co2_seq_kg", "o2_production_kg_yr", "epa_gasoline_liters_yr",
            "epa_km_driven_yr", "stormwater_l", "pm25_removed_g",
            "no2_removed_g", "o3_removed_g", "so2_removed_g"
        ]
        for col in sched_metric_cols:
            if col in sim_schedule.columns:
                sim_schedule.loc[sched_removed_mask, col] = 0.0
        if "layer" in sim_schedule.columns:
            sim_schedule.loc[sched_removed_mask, "layer"] = "L-PLNT-TREE-RMVL"

    # Step 1.5: Apply moved tree coordinate overrides
    if moved_trees and not sim_schedule.empty:
        for tid, coords in moved_trees.items():
            try:
                tid_int = int(tid)
                nx, ny = coords
                mask = sim_schedule["tree_id"] == tid_int
                if mask.any():
                    sim_schedule.loc[mask, "x"] = float(nx)
                    sim_schedule.loc[mask, "y"] = float(ny)
            except Exception:
                pass

    # Step 2: Handle manual plantings
    for p in manual_plantings:
        # Calculate yearly forecast rows
        sched_rows = calculate_single_tree_schedule(
            species=p["species"],
            dbh_cm=p["dbh_cm"],
            height_m=p["height_m"],
            forecast_years=forecast_years,
            condition=p.get("condition", "good"),
            lai=lai,
            rain_events=rain_events,
            pollution_multiplier=pollution_multiplier,
            db_path=db_path,
            true_growth_rate_cm=p.get("true_growth_rate_cm"),
            palm_height_growth_m=p.get("palm_height_growth_m"),
            crown_modifier=p.get("crown_modifier"),
            species_lai=p.get("species_lai"),
        )
        
        # Add spatial coordinates and identifiers to yearly rows
        for r in sched_rows:
            r["tree_id"] = p["tree_id"]
            r["block_name"] = "MANUAL_PLANTED"
            r["species"] = p["species"]
            r["x"] = p["x"]
            r["y"] = p["y"]
            r["layer"] = "L-PLNT-TREE-PROP"
            r["match_level"] = "species"
            
        sim_schedule = pd.concat([sim_schedule, pd.DataFrame(sched_rows)], ignore_index=True)

    # Ensure all numeric columns are float/numeric
    numeric_cols = [
        "tree_id", "year", "dbh_cm", "height_m", "x", "y",
        "carbon_storage_kg", "carbon_seq_kg", "co2_storage_kg", "co2_seq_kg",
        "o2_production_kg_yr", "epa_gasoline_liters_yr", "epa_km_driven_yr",
        "stormwater_l", "pm25_removed_g", "no2_removed_g", "o3_removed_g", "so2_removed_g"
    ]
    for col in numeric_cols:
        if col in sim_schedule.columns:
            sim_schedule[col] = pd.to_numeric(sim_schedule[col], errors="coerce").fillna(0.0)

    return sim_schedule
