"""
itree_sea_cad.py — CAD Plugin Script for i-Tree SEA
=====================================================

This script works in two modes:

  1. **BricsCAD Plugin** — Load via BIMPYTHON or PYLOAD command.
     It connects to the running BricsCAD session via COM/ActiveX,
     scans the drawing for tree block references, and runs the
     i-Tree SEA forecast pipeline.

  2. **Standalone DXF Processor** — Run from the command line.
     It uses ezdxf to parse a DXF file (no running CAD needed)
     and generates the planting benefit schedule.

Usage:
  # Standalone mode (any CAD software that exports DXF)
  python itree_sea_cad.py process --input planting.dxf --years 25

  # BricsCAD mode (run from within BricsCAD Python console)
  python itree_sea_cad.py bricscad --years 25

  # Extract only — dump block attributes to CSV without calculations
  python itree_sea_cad.py extract --input planting.dxf

AutoCAD Integration:
  AutoCAD does not natively support Python plugins, but this script
  can be called from an AutoLISP wrapper:

    (defun c:ITREESEA ()
      (command "._SHELL"
        (strcat "python \\"" (findfile "itree_sea_cad.py") "\\" process "
                "--input \\"" (getvar "DWGNAME") ".dxf\\""))
    )

  Or via the AutoCAD Python Shell (if available).
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger("itree_sea_cad")


# ──────────────────────────────────────────────────────────────────────
# Block attribute extraction (BricsCAD COM mode)
# ──────────────────────────────────────────────────────────────────────

def extract_from_bricscad(
    target_layers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Extract tree block attributes from a running BricsCAD session.

    Uses the COM/ActiveX API to connect to BricsCAD, iterate through
    modelspace, and collect block reference attributes.

    Parameters
    ----------
    target_layers : list of str, optional
        Only process blocks on these layers.

    Returns
    -------
    list of dict
        Each dict has keys: block_name, species, dbh_cm, height_m,
        x, y, layer, handle.
    """
    try:
        import comtypes.client
    except ImportError:
        raise ImportError(
            "comtypes is required for BricsCAD integration.\n"
            "Install it with:  pip install comtypes"
        )

    # Connect to BricsCAD
    try:
        app = comtypes.client.GetActiveObject("BricscadApp.AcadApplication")
    except Exception:
        try:
            app = comtypes.client.GetActiveObject("AutoCAD.Application")
        except Exception:
            raise ConnectionError(
                "Could not connect to BricsCAD or AutoCAD.\n"
                "Ensure the application is running."
            )

    doc = app.ActiveDocument
    model = doc.ModelSpace
    entries = []

    for i in range(model.Count):
        entity = model.Item(i)

        if entity.ObjectName != "AcDbBlockReference":
            continue

        layer = entity.Layer
        if target_layers and layer not in target_layers:
            continue

        if not entity.HasAttributes:
            continue

        # Extract attributes
        attribs = {}
        for attr in entity.GetAttributes():
            attribs[attr.TagString.upper().strip()] = attr.TextString.strip()

        # Must have SPECIES
        species = (
            attribs.get("SPECIES")
            or attribs.get("TREE_SPECIES")
            or attribs.get("SP")
            or attribs.get("BOTANICAL")
            or attribs.get("NAMA")
        )
        if not species:
            continue

        # Parse numeric values
        dbh = _parse_float(
            attribs.get("DBH") or attribs.get("CALIPER"),
            5.0
        )
        height = _parse_float(attribs.get("HEIGHT"), None)

        insertion = entity.InsertionPoint
        entries.append({
            "block_name": entity.Name,
            "species": species,
            "dbh_cm": dbh,
            "height_m": height,
            "x": round(insertion[0], 3),
            "y": round(insertion[1], 3),
            "layer": layer,
            "handle": entity.Handle,
        })

    logger.info("Extracted %d tree blocks from BricsCAD", len(entries))
    return entries


# ──────────────────────────────────────────────────────────────────────
# Block attribute extraction (ezdxf standalone mode)
# ──────────────────────────────────────────────────────────────────────

def extract_from_dxf(
    dxf_path: Path,
    target_layers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Extract tree block attributes from a DXF file using ezdxf.

    Parameters
    ----------
    dxf_path : Path
        Path to the DXF file.
    target_layers : list of str, optional
        Layer filter.

    Returns
    -------
    list of dict
    """
    try:
        import ezdxf
    except ImportError:
        raise ImportError(
            "ezdxf is required for standalone DXF processing.\n"
            "Install it with:  pip install ezdxf"
        )

    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    entries = []

    for entity in msp:
        if entity.dxftype() != "INSERT":
            continue

        layer = entity.dxf.layer
        if target_layers and layer not in target_layers:
            continue

        if not entity.attribs:
            continue

        attribs = {
            a.dxf.tag.upper().strip(): a.dxf.text.strip()
            for a in entity.attribs
        }

        species = (
            attribs.get("SPECIES")
            or attribs.get("TREE_SPECIES")
            or attribs.get("SP")
            or attribs.get("BOTANICAL")
            or attribs.get("NAMA")
        )
        if not species:
            continue

        dbh = _parse_float(
            attribs.get("DBH") or attribs.get("CALIPER"),
            5.0,
        )
        height = _parse_float(attribs.get("HEIGHT"), None)

        pt = entity.dxf.insert
        entries.append({
            "block_name": entity.dxf.name,
            "species": species,
            "dbh_cm": dbh,
            "height_m": height,
            "x": round(pt.x, 3),
            "y": round(pt.y, 3),
            "layer": layer,
            "handle": entity.dxf.handle,
        })

    logger.info("Extracted %d tree blocks from DXF", len(entries))
    return entries


# ──────────────────────────────────────────────────────────────────────
# Calculation pipeline
# ──────────────────────────────────────────────────────────────────────

def run_forecast_pipeline(
    entries: List[Dict[str, Any]],
    forecast_years: int = 25,
    output_dir: Optional[Path] = None,
    db_path: Optional[Path] = None,
    lai: float = 5.0,
) -> tuple:
    """Run the i-Tree SEA forecast on extracted tree entries.

    Parameters
    ----------
    entries : list of dict
        Tree data from extract_from_bricscad() or extract_from_dxf().
    forecast_years : int
        Years to project.
    output_dir : Path, optional
        Output directory for CSV files.
    db_path : Path, optional
        Species database override.
    lai : float
        Leaf Area Index.

    Returns
    -------
    tuple of (Path, Path)
        Paths to the schedule and summary CSV files.
    """
    from itree_sea.database import get_coefficients, lookup_species
    from itree_sea.engine import forecast_growth

    if output_dir is None:
        output_dir = Path.cwd() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    schedule_path = output_dir / "planting_schedule.csv"
    summary_path = output_dir / "planting_summary.csv"

    schedule_headers = [
        "tree_id", "block_name", "species", "x", "y", "layer",
        "year", "dbh_cm", "height_m", "carbon_storage_kg",
        "carbon_seq_kg", "stormwater_l", "pm25_g", "no2_g",
        "o3_g", "so2_g", "match_level",
    ]
    summary_headers = [
        "tree_id", "block_name", "species", "x", "y", "layer",
        "final_dbh_cm", "final_height_m", "final_carbon_kg",
        "cumulative_seq_kg", "final_stormwater_l", "match_level",
    ]

    with open(schedule_path, "w", newline="", encoding="utf-8") as sf, \
         open(summary_path, "w", newline="", encoding="utf-8") as sumf:

        sched_writer = csv.writer(sf)
        sched_writer.writerow(schedule_headers)

        summ_writer = csv.writer(sumf)
        summ_writer.writerow(summary_headers)

        for tree_id, entry in enumerate(entries, start=1):
            species_name = entry["species"]

            sp_record = lookup_species(scientific_name=species_name, db_path=db_path)
            is_palm = sp_record.is_palm if sp_record else False
            growth_rate = sp_record.growth_rate if sp_record else "moderate"
            genus = species_name.split()[0] if species_name else None

            coeffs = get_coefficients(
                scientific_name=species_name,
                genus=genus,
                db_path=db_path,
            )

            rows = forecast_growth(
                initial_dbh_cm=entry["dbh_cm"],
                coefficients=coeffs,
                growth_rate=growth_rate,
                years=forecast_years,
                initial_height_m=entry["height_m"],
                is_palm=is_palm,
                lai=lai,
            )

            cumulative_seq = 0.0
            for r in rows:
                cumulative_seq += r.carbon_sequestration_kg
                sched_writer.writerow([
                    tree_id, entry["block_name"], species_name,
                    entry["x"], entry["y"], entry["layer"],
                    r.year, r.dbh_cm, r.height_m,
                    r.carbon_storage_kg, r.carbon_sequestration_kg,
                    r.stormwater_litres, r.pm25_removed_g,
                    r.no2_removed_g, r.o3_removed_g,
                    r.so2_removed_g, coeffs.match_level,
                ])

            final = rows[-1]
            summ_writer.writerow([
                tree_id, entry["block_name"], species_name,
                entry["x"], entry["y"], entry["layer"],
                final.dbh_cm, final.height_m,
                final.carbon_storage_kg, round(cumulative_seq, 3),
                final.stormwater_litres, coeffs.match_level,
            ])

    logger.info("Schedule: %s", schedule_path)
    logger.info("Summary: %s", summary_path)
    return schedule_path, summary_path


# ──────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="itree-sea-cad",
        description="i-Tree SEA — CAD Plugin for tree carbon calculations",
    )
    sub = parser.add_subparsers(dest="command")

    # -- process --
    p_proc = sub.add_parser("process", help="Process a DXF file (standalone)")
    p_proc.add_argument("-i", "--input", required=True, help="DXF file path")
    p_proc.add_argument("-o", "--output", default=None, help="Output directory")
    p_proc.add_argument("--years", type=int, default=25, help="Forecast years")
    p_proc.add_argument("--layers", nargs="+", default=None, help="DXF layers to filter")
    p_proc.add_argument("--db", default=None, help="Database path")
    p_proc.add_argument("--lai", type=float, default=5.0, help="LAI")

    # -- bricscad --
    p_brics = sub.add_parser("bricscad", help="Process current BricsCAD drawing")
    p_brics.add_argument("-o", "--output", default=None, help="Output directory")
    p_brics.add_argument("--years", type=int, default=25, help="Forecast years")
    p_brics.add_argument("--layers", nargs="+", default=None, help="Layers to filter")
    p_brics.add_argument("--db", default=None, help="Database path")
    p_brics.add_argument("--lai", type=float, default=5.0, help="LAI")

    # -- extract --
    p_ext = sub.add_parser("extract", help="Extract block attributes to CSV only")
    p_ext.add_argument("-i", "--input", required=True, help="DXF file path")
    p_ext.add_argument("-o", "--output", default="extracted_trees.csv", help="Output CSV")
    p_ext.add_argument("--layers", nargs="+", default=None, help="Layers to filter")

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.command == "process":
        entries = extract_from_dxf(Path(args.input), args.layers)
        if not entries:
            logger.warning("No tree blocks found in DXF")
            return
        out_dir = Path(args.output) if args.output else None
        db = Path(args.db) if args.db else None
        run_forecast_pipeline(entries, args.years, out_dir, db, args.lai)

    elif args.command == "bricscad":
        entries = extract_from_bricscad(args.layers)
        if not entries:
            logger.warning("No tree blocks found in drawing")
            return
        out_dir = Path(args.output) if args.output else None
        db = Path(args.db) if args.db else None
        run_forecast_pipeline(entries, args.years, out_dir, db, args.lai)

    elif args.command == "extract":
        entries = extract_from_dxf(Path(args.input), args.layers)
        with open(args.output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "block_name", "species", "dbh_cm", "height_m",
                "x", "y", "layer", "handle",
            ])
            writer.writeheader()
            writer.writerows(entries)
        logger.info("Extracted %d trees → %s", len(entries), args.output)

    else:
        parser.print_help()


# ──────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────

def _parse_float(value: Optional[str], default: Optional[float]) -> Optional[float]:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


if __name__ == "__main__":
    main()
