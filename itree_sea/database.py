"""
database.py — SQLite database management and species crosswalk queries
=======================================================================

Responsibilities:
  1. Create / initialise the SQLite database with the schema defined
     in Phase 2 of the specification.
  2. Seed initial species data from a CSV file.
  3. Provide the crosswalk lookup: given a species name, return the
     matching allometric coefficients with a graceful fallback chain
     (species → genus → pantropical default).

Thread safety:
  Each function creates its own connection.  For batch processing
  (e.g., enriching a GeoDataFrame row-by-row), prefer
  ``get_coefficients_batch()`` which opens one connection for the
  entire batch.
"""

from __future__ import annotations

import csv
import sqlite3
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from itree_sea.config import (
    DATABASE_PATH,
    SEED_CSV_PATH,
    DEFAULT_WOOD_DENSITY,
    CHAVE_A,
    CHAVE_B,
    DEFAULT_HEIGHT_A,
    DEFAULT_HEIGHT_B,
    DEFAULT_TRUE_GROWTH_RATE_CM,
    DEFAULT_PALM_HEIGHT_GROWTH_M,
    DEFAULT_CROWN_MODIFIER,
    DEFAULT_SPECIES_LAI,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────

@dataclass
class SpeciesRecord:
    """A row from the species_lookup table."""
    species_id: int
    nparks_code: Optional[str]
    common_name: str
    scientific_name: str
    genus: str
    family: Optional[str]
    growth_rate: str         # 'slow' | 'moderate' | 'fast'
    is_palm: bool
    native_region: Optional[str]
    notes: Optional[str]
    true_growth_rate_cm: float = 0.90
    palm_height_growth_m: float = 0.0
    crown_modifier: float = 0.15
    species_lai: float = 5.0


@dataclass
class AllometricCoefficients:
    """Resolved allometric coefficients ready for the engine.

    Includes metadata about how the match was achieved so the
    caller can report confidence levels.
    """
    wood_density: float
    equation_form: str       # e.g. 'chave_2014'
    a: float                 # multiplicative constant
    b: float                 # exponent
    c: Optional[float]       # optional third constant
    height_model_a: Optional[float]
    height_model_b: Optional[float]
    height_model_c: Optional[float]    # for Weibull 3-param model
    height_model_form: str              # 'power' | 'weibull'
    match_level: str         # 'species' | 'genus' | 'default'
    source: Optional[str]
    true_growth_rate_cm: float = 0.90
    palm_height_growth_m: float = 0.0
    crown_modifier: float = 0.15
    species_lai: float = 5.0
    species: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────
# Schema DDL
# ──────────────────────────────────────────────────────────────────────

_DDL_SPECIES_LOOKUP = """
CREATE TABLE IF NOT EXISTS species_lookup (
    species_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    nparks_code     TEXT UNIQUE,
    common_name     TEXT NOT NULL,
    scientific_name TEXT NOT NULL,
    genus           TEXT NOT NULL,
    family          TEXT,
    growth_rate     TEXT DEFAULT 'moderate'
                    CHECK(growth_rate IN ('slow', 'moderate', 'fast')),
    is_palm         INTEGER DEFAULT 0,
    native_region   TEXT,
    notes           TEXT,
    true_growth_rate_cm REAL DEFAULT 0.90,
    palm_height_growth_m REAL DEFAULT 0.0,
    crown_modifier  REAL DEFAULT 0.15,
    species_lai     REAL DEFAULT 5.0
);
"""

_DDL_ALLOMETRIC_COEFFICIENTS = """
CREATE TABLE IF NOT EXISTS allometric_coefficients (
    coeff_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    genus           TEXT,
    species         TEXT,
    equation_form   TEXT NOT NULL DEFAULT 'chave_2014',
    a               REAL NOT NULL DEFAULT 0.0673,
    b               REAL NOT NULL DEFAULT 0.976,
    c               REAL,
    wood_density    REAL NOT NULL,
    height_model_form TEXT DEFAULT 'power',
    height_model_a  REAL,
    height_model_b  REAL,
    height_model_c  REAL,
    source          TEXT,
    true_growth_rate_cm REAL DEFAULT 0.90,
    palm_height_growth_m REAL DEFAULT 0.0,
    crown_modifier  REAL DEFAULT 0.15,
    species_lai     REAL DEFAULT 5.0,
    UNIQUE(genus, species)
);
"""

_DDL_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_species_scientific ON species_lookup(scientific_name);",
    "CREATE INDEX IF NOT EXISTS idx_species_genus ON species_lookup(genus);",
    "CREATE INDEX IF NOT EXISTS idx_species_nparks ON species_lookup(nparks_code);",
    "CREATE INDEX IF NOT EXISTS idx_coeff_genus ON allometric_coefficients(genus);",
    "CREATE INDEX IF NOT EXISTS idx_coeff_species ON allometric_coefficients(species);",
]


# ──────────────────────────────────────────────────────────────────────
# Database initialisation
# ──────────────────────────────────────────────────────────────────────

def init_db(db_path: Optional[Path] = None) -> Path:
    """Create the SQLite database and all tables.

    Parameters
    ----------
    db_path : Path, optional
        Override the default database location from ``config.py``.

    Returns
    -------
    Path
        The absolute path to the created database file.
    """
    db_path = db_path or DATABASE_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        cur = conn.cursor()
        cur.execute(_DDL_SPECIES_LOOKUP)
        cur.execute(_DDL_ALLOMETRIC_COEFFICIENTS)
        for idx_sql in _DDL_INDEXES:
            cur.execute(idx_sql)
        conn.commit()
        logger.info("Database initialised at %s", db_path)
    finally:
        conn.close()

    return db_path


def seed_from_csv(
    csv_path: Optional[Path] = None,
    db_path: Optional[Path] = None,
) -> int:
    """Populate species_lookup and allometric_coefficients from a CSV.

    The CSV must have the following columns (order-independent):
        nparks_code, common_name, scientific_name, genus, family,
        growth_rate, is_palm, native_region, notes,
        wood_density, equation_form, a, b, c,
        height_model_a, height_model_b, source

    Parameters
    ----------
    csv_path : Path, optional
        Path to the seed CSV.  Defaults to ``config.SEED_CSV_PATH``.
    db_path : Path, optional
        Override database location.

    Returns
    -------
    int
        Number of species rows inserted.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    """
    csv_path = csv_path or SEED_CSV_PATH
    db_path = db_path or DATABASE_PATH

    if not csv_path.exists():
        raise FileNotFoundError(f"Seed CSV not found: {csv_path}")

    conn = sqlite3.connect(str(db_path))
    inserted = 0

    try:
        cur = conn.cursor()
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Parse morphology fields with fallbacks
                true_growth = float(row["true_growth_rate_cm"]) if row.get("true_growth_rate_cm") else DEFAULT_TRUE_GROWTH_RATE_CM
                palm_h_growth = float(row["palm_height_growth_m"]) if row.get("palm_height_growth_m") else DEFAULT_PALM_HEIGHT_GROWTH_M
                cr_mod = float(row["crown_modifier"]) if row.get("crown_modifier") else DEFAULT_CROWN_MODIFIER
                sp_lai = float(row["species_lai"]) if row.get("species_lai") else DEFAULT_SPECIES_LAI

                # ── Insert into species_lookup ──
                cur.execute(
                    """
                    INSERT OR IGNORE INTO species_lookup
                        (nparks_code, common_name, scientific_name, genus,
                         family, growth_rate, is_palm, native_region, notes,
                         true_growth_rate_cm, palm_height_growth_m, crown_modifier, species_lai)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("nparks_code", "").strip() or None,
                        row["common_name"].strip(),
                        row["scientific_name"].strip(),
                        row["genus"].strip(),
                        row.get("family", "").strip() or None,
                        row.get("growth_rate", "moderate").strip().lower(),
                        int(row.get("is_palm", 0)),
                        row.get("native_region", "").strip() or None,
                        row.get("notes", "").strip() or None,
                        true_growth,
                        palm_h_growth,
                        cr_mod,
                        sp_lai,
                    ),
                )

                # ── Insert into allometric_coefficients ──
                species_name = row["scientific_name"].strip()
                genus_name = row["genus"].strip()

                cur.execute(
                    """
                    INSERT OR IGNORE INTO allometric_coefficients
                        (genus, species, equation_form, a, b, c,
                         wood_density, height_model_form,
                         height_model_a, height_model_b, height_model_c, source,
                         true_growth_rate_cm, palm_height_growth_m, crown_modifier, species_lai)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        genus_name,
                        species_name,
                        row.get("equation_form", "chave_2014").strip(),
                        float(row.get("a", CHAVE_A)),
                        float(row.get("b", CHAVE_B)),
                        float(row["c"]) if row.get("c") else None,
                        float(row.get("wood_density", DEFAULT_WOOD_DENSITY)),
                        row.get("height_model_form", "power").strip(),
                        float(row["height_model_a"]) if row.get("height_model_a") else None,
                        float(row["height_model_b"]) if row.get("height_model_b") else None,
                        float(row["height_model_c"]) if row.get("height_model_c") else None,
                        row.get("source", "").strip() or None,
                        true_growth,
                        palm_h_growth,
                        cr_mod,
                        sp_lai,
                    ),
                )

                inserted += 1

        conn.commit()
        logger.info("Seeded %d species from %s", inserted, csv_path)

    finally:
        conn.close()

    return inserted


# ──────────────────────────────────────────────────────────────────────
# Species lookup queries
# ──────────────────────────────────────────────────────────────────────

def lookup_species(
    scientific_name: Optional[str] = None,
    nparks_code: Optional[str] = None,
    common_name: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Optional[SpeciesRecord]:
    """Find a species record by scientific name, NParks code, or common name.

    Parameters
    ----------
    scientific_name : str, optional
        Full binomial, e.g. "Pterocarpus indicus".
    nparks_code : str, optional
        NParks flora code, e.g. "PTCR".
    common_name : str, optional
        Common name (case-insensitive LIKE search).
    db_path : Path, optional
        Override database location.

    Returns
    -------
    SpeciesRecord or None
        The matched record, or None if not found.
    """
    db_path = db_path or DATABASE_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()

        if scientific_name:
            cur.execute(
                "SELECT * FROM species_lookup WHERE LOWER(scientific_name) = LOWER(?)",
                (scientific_name.strip(),),
            )
        elif nparks_code:
            cur.execute(
                "SELECT * FROM species_lookup WHERE UPPER(nparks_code) = UPPER(?)",
                (nparks_code.strip(),),
            )
        elif common_name:
            cur.execute(
                "SELECT * FROM species_lookup WHERE LOWER(common_name) LIKE LOWER(?)",
                (f"%{common_name.strip()}%",),
            )
        else:
            return None

        row = cur.fetchone()
        if row is None:
            return None

        return SpeciesRecord(
            species_id=row["species_id"],
            nparks_code=row["nparks_code"],
            common_name=row["common_name"],
            scientific_name=row["scientific_name"],
            genus=row["genus"],
            family=row["family"],
            growth_rate=row["growth_rate"],
            is_palm=bool(row["is_palm"]),
            native_region=row["native_region"],
            notes=row["notes"],
            true_growth_rate_cm=row["true_growth_rate_cm"] if "true_growth_rate_cm" in row.keys() else DEFAULT_TRUE_GROWTH_RATE_CM,
            palm_height_growth_m=row["palm_height_growth_m"] if "palm_height_growth_m" in row.keys() else DEFAULT_PALM_HEIGHT_GROWTH_M,
            crown_modifier=row["crown_modifier"] if "crown_modifier" in row.keys() else DEFAULT_CROWN_MODIFIER,
            species_lai=row["species_lai"] if "species_lai" in row.keys() else DEFAULT_SPECIES_LAI,
        )

    finally:
        conn.close()


def get_coefficients(
    scientific_name: Optional[str] = None,
    genus: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> AllometricCoefficients:
    """Resolve allometric coefficients with fallback chain.

    Lookup priority:
      1. Exact species match  →  match_level = 'species'
      2. Genus-level match    →  match_level = 'genus'
      3. Pantropical default  →  match_level = 'default'

    Parameters
    ----------
    scientific_name : str, optional
        Full binomial for species-level lookup.
    genus : str, optional
        Genus name for genus-level lookup.
    db_path : Path, optional
        Override database location.

    Returns
    -------
    AllometricCoefficients
        Always returns a valid object — never None.
    """
    db_path = db_path or DATABASE_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()

        # ── Attempt 1: exact species match ──
        if scientific_name:
            cur.execute(
                """SELECT * FROM allometric_coefficients
                   WHERE LOWER(species) = LOWER(?)""",
                (scientific_name.strip(),),
            )
            row = cur.fetchone()
            if row:
                return _row_to_coefficients(row, match_level="species", conn=conn)

        # ── Attempt 2: genus-level match ──
        genus_query = genus
        if not genus_query and scientific_name:
            # Extract genus from "Genus species"
            genus_query = scientific_name.strip().split()[0]

        if genus_query:
            cur.execute(
                """SELECT * FROM allometric_coefficients
                   WHERE LOWER(genus) = LOWER(?) AND species IS NULL
                   LIMIT 1""",
                (genus_query.strip(),),
            )
            row = cur.fetchone()
            if row:
                return _row_to_coefficients(row, match_level="genus", conn=conn)

            # Try any row for that genus (species-level entry from a relative)
            cur.execute(
                """SELECT * FROM allometric_coefficients
                   WHERE LOWER(genus) = LOWER(?)
                   LIMIT 1""",
                (genus_query.strip(),),
            )
            row = cur.fetchone()
            if row:
                return _row_to_coefficients(row, match_level="genus", conn=conn)

        # ── Attempt 3: pantropical default ──
        logger.warning(
            "No coefficients found for species=%s genus=%s — using pantropical defaults",
            scientific_name, genus,
        )
        return _default_coefficients()

    finally:
        conn.close()


def get_coefficients_batch(
    species_list: List[str],
    db_path: Optional[Path] = None,
) -> Dict[str, AllometricCoefficients]:
    """Resolve coefficients for a list of species names in one connection.

    Parameters
    ----------
    species_list : list of str
        Scientific names (may contain duplicates).
    db_path : Path, optional
        Override database location.

    Returns
    -------
    dict
        Mapping from each input species name to its AllometricCoefficients.
    """
    results: Dict[str, AllometricCoefficients] = {}
    for name in set(species_list):
        results[name] = get_coefficients(scientific_name=name, db_path=db_path)
    return results


# ──────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────

def _resolve_genus_averages(conn: sqlite3.Connection, genus_name: str) -> Dict[str, Optional[float]]:
    """Query and calculate averages for numeric columns of all sibling species under the same genus."""
    averages = {}
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 
                AVG(wood_density) as avg_wd,
                AVG(true_growth_rate_cm) as avg_growth,
                AVG(palm_height_growth_m) as avg_palm_h,
                AVG(crown_modifier) as avg_crown,
                AVG(species_lai) as avg_lai
            FROM allometric_coefficients
            WHERE LOWER(genus) = LOWER(?) AND species IS NOT NULL
            """,
            (genus_name.strip(),)
        )
        row = cur.fetchone()
        if row:
            averages["wood_density"] = row[0]
            averages["true_growth_rate_cm"] = row[1]
            averages["palm_height_growth_m"] = row[2]
            averages["crown_modifier"] = row[3]
            averages["species_lai"] = row[4]
    except Exception as e:
        logger.error("Error calculating genus averages for genus %s: %s", genus_name, e)
    return averages


def _row_to_coefficients(
    row: sqlite3.Row, 
    match_level: str, 
    conn: Optional[sqlite3.Connection] = None
) -> AllometricCoefficients:
    """Convert a database row to an AllometricCoefficients dataclass, checking for null morphology fields."""
    true_growth = row["true_growth_rate_cm"] if "true_growth_rate_cm" in row.keys() else None
    palm_h_growth = row["palm_height_growth_m"] if "palm_height_growth_m" in row.keys() else None
    cr_mod = row["crown_modifier"] if "crown_modifier" in row.keys() else None
    sp_lai = row["species_lai"] if "species_lai" in row.keys() else None

    genus = row["genus"] if "genus" in row.keys() else None

    # Taxonomic Genus fallback: if species-level fields are None or 0.0, average over genus
    if genus and conn and (true_growth is None or true_growth == 0.0 or cr_mod is None or cr_mod == 0.0 or sp_lai is None or sp_lai == 0.0):
        averages = _resolve_genus_averages(conn, genus)
        if true_growth is None or true_growth == 0.0:
            true_growth = averages.get("true_growth_rate_cm")
        if palm_h_growth is None or palm_h_growth == 0.0:
            palm_h_growth = averages.get("palm_height_growth_m")
        if cr_mod is None or cr_mod == 0.0:
            cr_mod = averages.get("crown_modifier")
        if sp_lai is None or sp_lai == 0.0:
            sp_lai = averages.get("species_lai")

    # Final config defaults fallbacks
    if true_growth is None or true_growth == 0.0:
        true_growth = DEFAULT_TRUE_GROWTH_RATE_CM
    if palm_h_growth is None: # palms can have 0.0 height growth if slow, but if None we default it
        palm_h_growth = DEFAULT_PALM_HEIGHT_GROWTH_M
    if cr_mod is None or cr_mod == 0.0:
        cr_mod = DEFAULT_CROWN_MODIFIER
    if sp_lai is None or sp_lai == 0.0:
        sp_lai = DEFAULT_SPECIES_LAI

    return AllometricCoefficients(
        wood_density=row["wood_density"],
        equation_form=row["equation_form"],
        a=row["a"],
        b=row["b"],
        c=row["c"],
        height_model_a=row["height_model_a"],
        height_model_b=row["height_model_b"],
        height_model_c=row["height_model_c"] if "height_model_c" in row.keys() else None,
        height_model_form=row["height_model_form"] if "height_model_form" in row.keys() else "power",
        match_level=match_level,
        source=row["source"],
        true_growth_rate_cm=true_growth,
        palm_height_growth_m=palm_h_growth,
        crown_modifier=cr_mod,
        species_lai=sp_lai,
        species=row["species"] if "species" in row.keys() else None,
    )


def _default_coefficients() -> AllometricCoefficients:
    """Return pantropical default coefficients (Chave 2014 mean)."""
    return AllometricCoefficients(
        wood_density=DEFAULT_WOOD_DENSITY,
        equation_form="chave_2014",
        a=CHAVE_A,
        b=CHAVE_B,
        c=None,
        height_model_a=DEFAULT_HEIGHT_A,
        height_model_b=DEFAULT_HEIGHT_B,
        height_model_c=None,
        height_model_form="power",
        match_level="default",
        source="Chave et al. (2014) pantropical default",
        true_growth_rate_cm=DEFAULT_TRUE_GROWTH_RATE_CM,
        palm_height_growth_m=DEFAULT_PALM_HEIGHT_GROWTH_M,
        crown_modifier=DEFAULT_CROWN_MODIFIER,
        species_lai=DEFAULT_SPECIES_LAI,
        species=None,
    )

