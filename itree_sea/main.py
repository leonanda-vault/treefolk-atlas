"""
main.py — CLI entry point for Treefolk Atlas
==========================================

Provides three subcommands:

  init-db    Create/reset the SQLite database and seed species data.
  gis        Run the GIS pipeline (GeoJSON/Shapefile → enriched GeoJSON).
  cad        Run the CAD pipeline (DXF → planting schedule CSV).

Usage examples:

  # Initialise the database
  python -m itree_sea init-db

  # Initialise and seed from a custom CSV
  python -m itree_sea init-db --seed data/my_species.csv

  # Process a GIS tree inventory
  python -m itree_sea gis --input survey.geojson --output enriched.geojson

  # Process a CAD planting plan with 30-year forecast
  python -m itree_sea cad --input planting.dxf --years 30

  # Restrict DXF parsing to specific layers
  python -m itree_sea cad --input planting.dxf --layers "L-PLNT-TREE" "L-PLNT-SHRUB"
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from itree_sea import __version__
from itree_sea.config import DATABASE_PATH, SEED_CSV_PATH, DEFAULT_FORECAST_YEARS


def _setup_logging(verbose: bool) -> None:
    """Configure root logger with a human-readable format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


# ──────────────────────────────────────────────────────────────────────
# Subcommand handlers
# ──────────────────────────────────────────────────────────────────────

def _cmd_init_db(args: argparse.Namespace) -> int:
    """Handle the ``init-db`` subcommand."""
    from itree_sea.database import init_db, seed_from_csv

    db_path = Path(args.db) if args.db else DATABASE_PATH
    logger = logging.getLogger("init-db")

    # Create tables
    created = init_db(db_path)
    logger.info("Database ready: %s", created)

    # Seed if CSV exists
    seed_csv = Path(args.seed) if args.seed else SEED_CSV_PATH
    if seed_csv.exists():
        count = seed_from_csv(seed_csv, db_path)
        logger.info("Seeded %d species from %s", count, seed_csv)
    else:
        logger.warning(
            "Seed CSV not found at %s — database created but empty.  "
            "Provide a seed CSV with --seed or place it at %s",
            seed_csv, SEED_CSV_PATH,
        )

    return 0


def _cmd_gis(args: argparse.Namespace) -> int:
    """Handle the ``gis`` subcommand."""
    from itree_sea.gis_bridge import run_gis_pipeline

    logger = logging.getLogger("gis")

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        return 1

    output_path = Path(args.output) if args.output else None
    db_path = Path(args.db) if args.db else None

    try:
        result = run_gis_pipeline(
            input_path=input_path,
            output_path=output_path,
            db_path=db_path,
            lai=args.lai,
        )
        logger.info("✓ GIS pipeline complete → %s", result)
        return 0

    except Exception as exc:
        logger.error("GIS pipeline failed: %s", exc, exc_info=True)
        return 1


def _cmd_cad(args: argparse.Namespace) -> int:
    """Handle the ``cad`` subcommand."""
    from itree_sea.cad_bridge import run_cad_pipeline

    logger = logging.getLogger("cad")

    dxf_path = Path(args.input)
    if not dxf_path.exists():
        logger.error("DXF file not found: %s", dxf_path)
        return 1

    output_csv = Path(args.output) if args.output else None
    summary_csv = Path(args.summary) if args.summary else None
    db_path = Path(args.db) if args.db else None
    layers = args.layers if args.layers else None

    try:
        sched_path, summ_path = run_cad_pipeline(
            dxf_path=dxf_path,
            output_csv=output_csv,
            summary_csv=summary_csv,
            forecast_years=args.years,
            target_layers=layers,
            db_path=db_path,
            lai=args.lai,
        )
        logger.info("✓ CAD pipeline complete")
        logger.info("  Schedule → %s", sched_path)
        logger.info("  Summary  → %s", summ_path)
        return 0

    except Exception as exc:
        logger.error("CAD pipeline failed: %s", exc, exc_info=True)
        return 1


# ──────────────────────────────────────────────────────────────────────
# Argument parser
# ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with subcommands."""

    parser = argparse.ArgumentParser(
        prog="itree-sea",
        description=(
            "Treefolk Atlas — Southeast Asian Urban Forest Carbon Calculator.  "
            "Calculates biomass, carbon storage, sequestration, stormwater "
            "interception, and air pollution removal for tropical trees."
        ),
        epilog="Documentation: https://github.com/your-username/itree-sea",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable debug-level logging.",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── init-db ──
    p_init = subparsers.add_parser(
        "init-db",
        help="Create the SQLite database and seed species data.",
    )
    p_init.add_argument(
        "--db", type=str, default=None,
        help=f"Database path (default: {DATABASE_PATH})",
    )
    p_init.add_argument(
        "--seed", type=str, default=None,
        help=f"Path to seed CSV (default: {SEED_CSV_PATH})",
    )

    # ── gis ──
    p_gis = subparsers.add_parser(
        "gis",
        help="Process a GIS tree inventory (GeoJSON/Shapefile).",
    )
    p_gis.add_argument(
        "-i", "--input", type=str, required=True,
        help="Input GeoJSON or Shapefile path.",
    )
    p_gis.add_argument(
        "-o", "--output", type=str, default=None,
        help="Output enriched GeoJSON path.",
    )
    p_gis.add_argument(
        "--db", type=str, default=None,
        help="Database path override.",
    )
    p_gis.add_argument(
        "--lai", type=float, default=5.0,
        help="Leaf Area Index (default: 5.0).",
    )

    # ── cad ──
    p_cad = subparsers.add_parser(
        "cad",
        help="Process a DXF planting plan.",
    )
    p_cad.add_argument(
        "-i", "--input", type=str, required=True,
        help="Input DXF file path.",
    )
    p_cad.add_argument(
        "-o", "--output", type=str, default=None,
        help="Output schedule CSV path.",
    )
    p_cad.add_argument(
        "--summary", type=str, default=None,
        help="Output summary CSV path.",
    )
    p_cad.add_argument(
        "--years", type=int, default=DEFAULT_FORECAST_YEARS,
        help=f"Forecast horizon in years (default: {DEFAULT_FORECAST_YEARS}).",
    )
    p_cad.add_argument(
        "--layers", type=str, nargs="+", default=None,
        help="DXF layer names to filter (default: all layers).",
    )
    p_cad.add_argument(
        "--db", type=str, default=None,
        help="Database path override.",
    )
    p_cad.add_argument(
        "--lai", type=float, default=5.0,
        help="Leaf Area Index (default: 5.0).",
    )

    return parser


# ──────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────

def main() -> int:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    _setup_logging(args.verbose)

    if args.command is None:
        parser.print_help()
        return 0

    handlers = {
        "init-db": _cmd_init_db,
        "gis": _cmd_gis,
        "cad": _cmd_cad,
    }

    handler = handlers.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
