"""
cad_bridge.py — DXF planting plan parser and benefit schedule generator
========================================================================

This module is the Landscape CAD designer's entry point.  It parses a
DXF file produced by AutoCAD/BricsCAD, extracts tree blocks, and runs
multi-year growth forecasts for each tree.

Supports TWO extraction modes:
  1. **Attribute-based** (standard): blocks with SPECIES/CALIPER ATTDEFs.
  2. **Block-name-based** (Indonesian): blocks named by common name
     (e.g. "Mahoni", "Flamboyan") with optional MTEXT diameter labels.

The block-name mode uses a built-in Indonesian common name → scientific
name mapping table, and parses nearby MTEXT entities for %%C diameter
values.

Dependencies:
  • ezdxf (for DXF parsing)
"""

from __future__ import annotations

import csv
import logging
import math
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Union, Dict

try:
    import ezdxf
    from ezdxf.entities import Insert, MText
    HAS_EZDXF = True
except ImportError:
    HAS_EZDXF = False

import pandas as pd

from itree_sea.config import (
    DXF_SPECIES_TAG,
    DXF_DBH_TAG,
    DXF_HEIGHT_TAG,
    DXF_CALIPER_TAG,
    DEFAULT_PLANTING_DBH,
    DEFAULT_FORECAST_YEARS,
    OUTPUT_DIR,
    DEFAULT_LAI,
)
from itree_sea.database import (
    get_coefficients,
    lookup_species,
    AllometricCoefficients,
    SpeciesRecord,
)
from itree_sea.engine import (
    forecast_growth,
    ForecastRow,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Indonesian block name → scientific name mapping
# ──────────────────────────────────────────────────────────────────────

BLOCK_NAME_MAP: Dict[str, str] = {
    # Exact block names from LA-POHON.dxf → scientific names
    "mahoni":              "Swietenia macrophylla",
    "mahoni xtg":          "Swietenia macrophylla",
    "lamtoro":             "Leucaena leucocephala",
    "lamtoro xtg":         "Leucaena leucocephala",
    "jati":                "Tectona grandis",
    "jati xtg":            "Tectona grandis",
    "angsana":             "Pterocarpus indicus",
    "angsana xtg":         "Pterocarpus indicus",
    "beringin":            "Ficus benjamina",
    "beringin xtg":        "Ficus benjamina",
    "tanjung":             "Mimusops elengi",
    "tanjung xtg":         "Mimusops elengi",
    "trembesi":            "Samanea saman",
    "akranji":             "Dialium indum",
    "asam kranji":         "Dialium indum",
    "asam kranji xtg":     "Dialium indum",
    "bintaro":             "Cerbera manghas",
    "kemiri":              "Aleurites moluccanus",
    "kemiri xtg":          "Aleurites moluccanus",
    "leda":                "Eucalyptus deglupta",
    "leda xtg":            "Eucalyptus deglupta",
    "ketpg laut":          "Terminalia catappa",
    "ketapang laut":       "Terminalia catappa",
    "ketapang laut xtg":   "Terminalia catappa",
    "ketapang kencana":    "Terminalia mantaly",
    "kersen":              "Muntingia calabura",
    "mangga":              "Mangifera indica",
    "kapuk":               "Ceiba pentandra",
    "nangka":              "Artocarpus heterophyllus",
    "asam jawa":           "Tamarindus indica",
    "glodokan tiang":      "Polyalthia longifolia",
    "glodokan":            "Polyalthia longifolia",
    "flamboyan":           "Delonix regia",
    "tabekuning":          "Tabebuia aurea",
    "tabe kuning":         "Tabebuia aurea",
    "spathodea":           "Spathodea campanulata",
    "palem raja":          "Roystonea regia",
    "kupu":                "Bauhinia purpurea",
    "xtg kelapa":          "Cocos nucifera",
    "kelapa":              "Cocos nucifera",
    # New Sample Trees
    "lohansung":           "Podocarpus macrophyllus",
    "balibong":            "Palaquium obovatum",
    "bambu petung":        "Dendrocalamus asper",
    "cemara angin":        "Casuarina equisetifolia",
    "pinus":               "Agathis dammara",
    "damar":               "Agathis dammara",
    "jambu mawar":         "Syzygium jambos",
    "kayu putih":          "Melaleuca cajuputi",
    "kelor africa":        "Moringa oleifera",
    "ketapang mini":       "Terminalia mantaly",
    "yangliu":             "Salix babylonica",
    "liang liu":           "Salix babylonica",
    "pakis brazil":        "Schizolobium parahyba",
    "tebebuia":            "Handroanthus impetiginosus",
    "tabebuia pink":       "Handroanthus impetiginosus",
    # LA-TREE PLAN 1ST FLOOR.dxf — Phn prefix blocks
    "kamboja putih":       "Plumeria obtusa",
    "kamboja putih fosil": "Plumeria obtusa",
    "kamboja fossil":      "Plumeria obtusa",
    "pandan bali":         "Pandanus baptistii",
    # LA_PLANTING PLAN TREE GKB — height-encoded blocks
    "sikat botol":         "Callistemon viminalis",
    "tower tree":          "Schizolobium parahyba",
    "baobab":              "Adansonia digitata",
    "pulai":               "Alstonia scholaris",
    "pulai hias":          "Alstonia scholaris",
    # Common aliases
    "pohon eksisting":     None,  # skip generic markers
    "luar":                None,  # skip outer boundary
    "batas area":          None,  # skip boundary markers
    "randu":               "Ceiba pentandra",
    "cendana":             "Santalum album",
    "meranti":             "Shorea leprosula",
    "sawo duren":          "Chrysophyllum cainito",
    "tabebuya":            "Handroanthus impetiginosus",
    "akasia":              "Acacia mangium",
}


# ──────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────

@dataclass
class PlantingEntry:
    """A single proposed tree extracted from a DXF block INSERT."""
    block_name: str
    species_name: str
    dbh_cm: float
    height_m: Optional[float]
    x: float
    y: float
    layer: str
    handle: str                    # DXF entity handle (for traceability)


@dataclass
class ScheduleRow:
    """One row of the output planting benefit schedule."""
    tree_id: int
    block_name: str
    species: str
    common_name: Optional[str]
    x: float
    y: float
    layer: str
    year: int
    dbh_cm: float
    height_m: float
    carbon_storage_kg: float
    carbon_sequestration_kg: float
    co2_storage_kg: float
    co2_sequestration_kg: float
    o2_production_kg_yr: float
    epa_gasoline_liters_yr: float
    epa_km_driven_yr: float
    stormwater_litres: float
    pm25_removed_g: float
    no2_removed_g: float
    o3_removed_g: float
    so2_removed_g: float
    match_level: str


@dataclass
class ParsedTextLabel:
    """A parsed text or MTEXT label from the CAD drawing."""
    x: float
    y: float
    tree_id: Optional[int]
    elevation: Optional[float]
    species: Optional[str]
    dbh: Optional[float]
    layer: str


# ──────────────────────────────────────────────────────────────────────
# MTEXT diameter parser and label parser
# ──────────────────────────────────────────────────────────────────────

# Pattern: %%C followed by digits (the %%C is AutoCAD's ⌀ symbol)
_DIAMETER_PATTERN = re.compile(r"%%[Cc]\s*(\d+(?:\.\d+)?)\s*cm", re.IGNORECASE)
# Also try plain "D XX" or "Ø XX" patterns
_DIAMETER_ALT = re.compile(r"[ØøDd]\s*[:=]?\s*(\d+(?:\.\d+)?)\s*cm", re.IGNORECASE)


def _parse_mtext_label(text: str) -> Tuple[Optional[int], Optional[float], Optional[str], Optional[float]]:
    """Parse MTEXT plaintext to extract tree details.

    Returns: (tree_id, elevation_or_height, species_name, dbh_cm)
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    tree_id = None
    elevation = None
    dbh = None
    species_parts = []

    # Diameter regex patterns
    # Pattern 1: with symbol (Ø, %C, D)
    symbol_pat = re.compile(r"(?:%%[Cc]|Ø|ø|[Dd]\s*[:=]?)\s*(\d+(?:\.\d+)?)\s*(?:cm|mm)?", re.IGNORECASE)
    # Pattern 2: just number + cm
    plain_cm_pat = re.compile(r"\b(\d+(?:\.\d+)?)\s*cm\b", re.IGNORECASE)

    for line in lines:
        # Check for diameter first
        match = symbol_pat.search(line)
        if not match:
            match = plain_cm_pat.search(line)

        if match:
            try:
                dbh = float(match.group(1))
            except (ValueError, TypeError):
                pass
            # Remove diameter part from line to see if there is species text on the same line
            cleaned_line = line.replace(match.group(0), "").strip()
            if cleaned_line:
                species_parts.append(cleaned_line)
            continue

        # Check if it's a pure integer (ID)
        if re.match(r'^\d+$', line):
            try:
                tree_id = int(line)
            except (ValueError, TypeError):
                pass
            continue

        # Check if it's a float (Elevation/Height)
        cleaned_float = line.replace(" ", "")
        if re.match(r'^\d+\.\d+$', cleaned_float):
            try:
                elevation = float(cleaned_float)
            except (ValueError, TypeError):
                pass
            continue

        # Otherwise, it's a species name part
        species_parts.append(line)

    species_name = " ".join(species_parts).strip()
    species_name = re.sub(r'\s+', ' ', species_name)
    if not species_name:
        species_name = None

    return tree_id, elevation, species_name, dbh


def _extract_text_labels(doc) -> List[ParsedTextLabel]:
    """Extract and parse all MTEXT and TEXT entities from the document."""
    if not HAS_EZDXF:
        return []

    msp = doc.modelspace()
    labels = []

    for entity in msp:
        if entity.dxftype() not in ("MTEXT", "TEXT"):
            continue

        # Get plaintext content
        if entity.dxftype() == "MTEXT":
            try:
                text = entity.plain_text()
            except Exception:
                try:
                    text = entity.text
                except Exception:
                    text = getattr(entity.dxf, 'text', '')
        else: # TEXT
            text = getattr(entity, 'text', None) or getattr(entity.dxf, 'text', '')

        if not text:
            continue

        tree_id, elevation, species, dbh = _parse_mtext_label(text)

        try:
            pt = entity.dxf.insert
            labels.append(ParsedTextLabel(
                x=pt.x,
                y=pt.y,
                tree_id=tree_id,
                elevation=elevation,
                species=species,
                dbh=dbh,
                layer=entity.dxf.layer,
            ))
        except Exception:
            continue

    logger.info("Extracted and parsed %d MTEXT/TEXT labels", len(labels))
    return labels


def _find_nearest_label(
    x: float, y: float,
    labels: List[ParsedTextLabel],
    max_distance: float = 5.0,
) -> Optional[ParsedTextLabel]:
    """Find the nearest parsed MTEXT/TEXT label to a given point."""
    best_dist = max_distance
    best_label = None

    for label in labels:
        dist = math.sqrt((x - label.x) ** 2 + (y - label.y) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_label = label

    return best_label


def _extract_mtext_diameters(doc) -> Dict[str, float]:
    """Parse MTEXT entities near tree blocks to extract diameter values.

    Returns a dict of { "x,y" proximity key : diameter_cm }.
    We'll match these to the nearest INSERT later.
    """
    if not HAS_EZDXF:
        return {}

    msp = doc.modelspace()
    diameters: List[Tuple[float, float, float]] = []  # (x, y, diameter_cm)

    for entity in msp:
        if entity.dxftype() != "MTEXT":
            continue

        # Get the raw text content
        try:
            text = entity.text
        except Exception:
            try:
                text = entity.dxf.text
            except Exception:
                continue

        if not text:
            continue

        # Try to find diameter pattern
        match = _DIAMETER_PATTERN.search(text)
        if not match:
            match = _DIAMETER_ALT.search(text)
        if not match:
            continue

        diameter_cm = float(match.group(1))

        # Get MTEXT insertion point
        try:
            pt = entity.dxf.insert
            diameters.append((pt.x, pt.y, diameter_cm))
        except Exception:
            continue

    logger.info("Found %d diameter labels in MTEXT entities", len(diameters))
    return diameters


def _find_nearest_diameter(
    x: float, y: float,
    diameter_list: List[Tuple[float, float, float]],
    max_distance: float = 30.0,
) -> Optional[float]:
    """Find the nearest MTEXT diameter label to a given block position.

    Parameters
    ----------
    x, y : float
        Block insertion point.
    diameter_list : list of (x, y, diameter_cm)
        Parsed MTEXT diameter labels.
    max_distance : float
        Maximum search radius in drawing units (metres for UTM).

    Returns
    -------
    float or None
        The diameter in cm, or None if no label is close enough.
    """
    best_dist = max_distance
    best_diam = None

    for dx, dy, diam in diameter_list:
        dist = math.sqrt((x - dx) ** 2 + (y - dy) ** 2)
        if dist < best_dist:
            best_dist = dist
            best_diam = diam

    return best_diam


# ──────────────────────────────────────────────────────────────────────
# Height-from-block-name pattern:  _3M, _4M, _6M, etc.
# ──────────────────────────────────────────────────────────────────────
_HEIGHT_SUFFIX_PATTERN = re.compile(r"_(\d+(?:\.\d+)?)M$", re.IGNORECASE)


# ──────────────────────────────────────────────────────────────────────
# Block name resolver
# ──────────────────────────────────────────────────────────────────────

def _resolve_block_name(block_name: str) -> Optional[Tuple[str, Optional[float]]]:
    """Map an Indonesian block name to a scientific name.

    Handles multiple CAD naming conventions:
      - Direct names: "Mahoni", "Flamboyan"
      - Phn prefix + _Raz suffix: "Phn TANJUNG_Raz"
      - LA_ prefix + height suffix: "LA_Ketapang Laut_3M"
      - XREF prefix: "LA_TREE PLANTING$0$LA_Damar_4M"
      - _Warna suffix: colored display variants

    Returns
    -------
    tuple of (scientific_name, embedded_height_m) or None
        embedded_height_m is extracted from _NM suffix when present.
    """
    raw = block_name.strip()
    key = raw.lower()

    # ── Phase 0: Try direct lookup first ──
    if key in BLOCK_NAME_MAP:
        return (BLOCK_NAME_MAP[key], None) if BLOCK_NAME_MAP[key] is not None else None

    # ── Phase 1: Normalize the block name ──
    normalized = raw

    # Strip XREF prefix:  "LA_TREE PLANTING$0$LA_Damar_4M" → "LA_Damar_4M"
    if "$0$" in normalized:
        normalized = normalized.split("$0$")[-1]

    # Strip "Phn " prefix: "Phn TANJUNG_Raz" → "TANJUNG_Raz"
    if normalized.upper().startswith("PHN "):
        normalized = normalized[4:]

    # Strip "LA_" prefix: "LA_Ketapang Laut_3M" → "Ketapang Laut_3M"
    if normalized.startswith("LA_") or normalized.startswith("la_"):
        normalized = normalized[3:]

    # Extract embedded height from _NM suffix
    embedded_height = None
    height_match = _HEIGHT_SUFFIX_PATTERN.search(normalized)
    if height_match:
        embedded_height = float(height_match.group(1))
        normalized = normalized[:height_match.start()]

    # Strip _Raz, _Raz_Warna, _Warna suffixes
    for sfx in ("_raz_warna", "_raz", "_warna"):
        if normalized.lower().endswith(sfx):
            normalized = normalized[:-len(sfx)]
            break

    # Final cleanup
    normalized = normalized.strip().strip("_").strip()
    key = normalized.lower()

    # ── Phase 2: Try lookup with normalized name ──
    if key in BLOCK_NAME_MAP:
        sci = BLOCK_NAME_MAP[key]
        return (sci, embedded_height) if sci is not None else None

    # Strip common suffixes (xtg, pindah, baru, eksisting)
    for suffix in (" xtg", " pindah", " baru", " eksisting"):
        if key.endswith(suffix):
            stripped = key[: -len(suffix)].strip()
            if stripped in BLOCK_NAME_MAP:
                sci = BLOCK_NAME_MAP[stripped]
                return (sci, embedded_height) if sci is not None else None

    # Partial match (block name contains a known key, or vice versa)
    for map_key, sci_name in BLOCK_NAME_MAP.items():
        if map_key in key or key in map_key:
            return (sci_name, embedded_height) if sci_name is not None else None

    return None


# ──────────────────────────────────────────────────────────────────────
# DXF parsing
# ──────────────────────────────────────────────────────────────────────

def parse_dxf(dxf_path: Union[str, Path]) -> "ezdxf.document.Drawing":
    """Open and return an ezdxf Drawing object."""
    if not HAS_EZDXF:
        raise ImportError(
            "ezdxf is required for CAD bridge functionality.  "
            "Install it with:  pip install ezdxf"
        )

    dxf_path = Path(dxf_path)
    if not dxf_path.exists():
        raise FileNotFoundError(f"DXF file not found: {dxf_path}")

    logger.info("Parsing DXF: %s", dxf_path)
    doc = ezdxf.readfile(str(dxf_path))
    return doc


def _is_explicit_skip(block_name: str) -> bool:
    """Check if the normalized block name maps to None in BLOCK_NAME_MAP."""
    norm = block_name.strip().lower()
    if "$0$" in norm:
        norm = norm.split("$0$")[-1]
    if norm.startswith("phn "):
        norm = norm[4:]
    if norm.startswith("la_"):
        norm = norm[3:]
    norm = _HEIGHT_SUFFIX_PATTERN.sub("", norm)
    for sfx in ("_raz_warna", "_raz", "_warna"):
        if norm.endswith(sfx):
            norm = norm[:-len(sfx)]
            break
    norm = norm.strip().strip("_").strip()

    skips = {"pohon eksisting", "luar", "batas area"}
    if norm in skips:
        return True
    for suffix in (" xtg", " pindah", " baru", " eksisting"):
        if norm.endswith(suffix):
            stripped = norm[:-len(suffix)].strip()
            if stripped in skips:
                return True
    return False


def extract_planting_blocks(
    doc: "ezdxf.document.Drawing",
    target_layers: Optional[List[str]] = None,
) -> List[PlantingEntry]:
    """Extract tree planting entries from DXF INSERT entities.

    Supports three extraction modes:
      1. Standard: INSERTs with SPECIES/CALIPER ATTRIB tags.
      2. Block-name: INSERTs where the block name maps to a species
         via BLOCK_NAME_MAP. Diameter is sourced from nearby MTEXT.
      3. Proximity-based MTEXT/TEXT: INSERTs with generic block names
         where details (species, diameter) are parsed from a nearby
         MTEXT or TEXT entity.

    Parameters
    ----------
    doc : ezdxf.document.Drawing
        The parsed DXF document.
    target_layers : list of str, optional
        If provided, only INSERTs on these layers are extracted.

    Returns
    -------
    list of PlantingEntry
    """
    if not HAS_EZDXF:
        raise ImportError("ezdxf is required")

    msp = doc.modelspace()
    entries: List[PlantingEntry] = []

    # Pre-parse MTEXT diameter labels
    diameter_labels = _extract_mtext_diameters(doc)
    # Pre-parse all MTEXT/TEXT labels for proximity matching
    text_labels = _extract_text_labels(doc)

    attrib_found = 0
    blockname_found = 0
    mtext_found = 0

    # Pre-compute block geometry offsets relative to their base points
    block_offsets = {}
    for block in doc.blocks:
        if block.name.startswith("*") or block.name.startswith("Paper_Space") or block.name.startswith("Model_Space"):
            continue
        circle_pts = []
        other_pts = []
        for entity in block:
            if entity.dxftype() == "CIRCLE":
                circle_pts.append((entity.dxf.center.x, entity.dxf.center.y))
            elif entity.dxftype() == "LWPOLYLINE":
                for vertex in entity.vertices():
                    other_pts.append((vertex[0], vertex[1]))
            elif entity.dxftype() == "LINE":
                other_pts.append((entity.dxf.start.x, entity.dxf.start.y))
                other_pts.append((entity.dxf.end.x, entity.dxf.end.y))
        if circle_pts:
            dx = sum(p[0] for p in circle_pts) / len(circle_pts)
            dy = sum(p[1] for p in circle_pts) / len(circle_pts)
        elif other_pts:
            dx = sum(p[0] for p in other_pts) / len(other_pts)
            dy = sum(p[1] for p in other_pts) / len(other_pts)
        else:
            dx, dy = 0.0, 0.0
        block_offsets[block.name] = (dx, dy)

    # Auto-detect if drawing uses georeferenced UTM coordinates.
    # UTM coordinates in Indonesia (Zone 48S / 49S) have large values:
    # Easting (X) in [100000, 900000] and Northing (Y) in [8000000, 10000000]
    large_coords_count = 0
    total_inserts = 0
    for entity in msp:
        if entity.dxftype() == "INSERT":
            total_inserts += 1
            pt = entity.dxf.insert
            name = entity.dxf.name
            dx, dy = block_offsets.get(name, (0.0, 0.0))
            xscale = entity.dxf.xscale if hasattr(entity.dxf, "xscale") else 1.0
            yscale = entity.dxf.yscale if hasattr(entity.dxf, "yscale") else 1.0
            x_vis = pt.x + dx * xscale
            y_vis = pt.y + dy * yscale
            if (100000 <= abs(x_vis) <= 900000) and (8000000 <= abs(y_vis) <= 10000000):
                large_coords_count += 1

    is_utm_drawing = (large_coords_count > 0.5 * total_inserts) if total_inserts > 0 else False
    if is_utm_drawing:
        logger.info("Auto-detected UTM coordinate system in CAD drawing.")

    ignored_legend_count = 0

    for entity in msp:
        if entity.dxftype() != "INSERT":
            continue

        insert = entity
        layer = insert.dxf.layer
        block_name = insert.dxf.name

        # Layer filter
        if target_layers and layer not in target_layers:
            continue

        # Position (exact visual center calculation using block geometry offset and scales)
        insertion_point = insert.dxf.insert
        xscale = insert.dxf.xscale if hasattr(insert.dxf, "xscale") else 1.0
        yscale = insert.dxf.yscale if hasattr(insert.dxf, "yscale") else 1.0
        dx, dy = block_offsets.get(block_name, (0.0, 0.0))
        x = round(insertion_point.x + dx * xscale, 3)
        y = round(insertion_point.y + dy * yscale, 3)

        # Exclude legend/border blocks near the origin in a UTM drawing
        if is_utm_drawing and (abs(x) < 10000 or abs(y) < 100000):
            ignored_legend_count += 1
            continue

        # ── MODE 1: Attribute-based extraction ──
        attribs = {}
        if insert.attribs:
            attribs = {
                attrib.dxf.tag.upper().strip(): attrib.dxf.text.strip()
                for attrib in insert.attribs
            }

        species = (
            attribs.get(DXF_SPECIES_TAG.upper())
            or attribs.get("TREE_SPECIES")
            or attribs.get("SP")
            or attribs.get("NAMA")
            or attribs.get("BOTANICAL")
        )

        if species:
            # Standard attrib-based block
            dbh_str = attribs.get(DXF_DBH_TAG.upper()) or attribs.get(DXF_CALIPER_TAG.upper())
            dbh = _parse_numeric(dbh_str, DEFAULT_PLANTING_DBH)
            height_str = attribs.get(DXF_HEIGHT_TAG.upper())
            height = _parse_numeric(height_str, None)

            entries.append(PlantingEntry(
                block_name=block_name,
                species_name=species,
                dbh_cm=dbh,
                height_m=height,
                x=x, y=y,
                layer=layer,
                handle=insert.dxf.handle,
            ))
            attrib_found += 1
            continue

        # ── MODE 2: Block-name-based extraction ──
        resolved = _resolve_block_name(block_name)
        if resolved is not None:
            species_name, embedded_height = resolved

            # Find diameter from nearby MTEXT
            dbh = DEFAULT_PLANTING_DBH
            if diameter_labels:
                mtext_diam = _find_nearest_diameter(x, y, diameter_labels)
                if mtext_diam is not None:
                    dbh = mtext_diam

            entries.append(PlantingEntry(
                block_name=block_name,
                species_name=species_name,
                dbh_cm=dbh,
                height_m=embedded_height,
                x=x, y=y,
                layer=layer,
                handle=insert.dxf.handle,
            ))
            blockname_found += 1
            continue

        # If block name is an explicit skip (e.g. "pohon eksisting"), skip it
        if _is_explicit_skip(block_name):
            continue

        # ── MODE 3: MTEXT/TEXT proximity-based extraction ──
        nearest_label = _find_nearest_label(x, y, text_labels, max_distance=5.0)
        if nearest_label and nearest_label.species:
            resolved = _resolve_block_name(nearest_label.species)
            if resolved:
                species_name = resolved[0]
            else:
                species_name = nearest_label.species

            dbh = nearest_label.dbh if nearest_label.dbh is not None else DEFAULT_PLANTING_DBH

            entries.append(PlantingEntry(
                block_name=block_name,
                species_name=species_name,
                dbh_cm=dbh,
                height_m=None,  # Elevation in label is ground level elevation, not tree height
                x=x, y=y,
                layer=layer,
                handle=insert.dxf.handle,
            ))
            mtext_found += 1

    logger.info(
        "Extracted %d planting entries from DXF "
        "(%d from attribs, %d from block names, %d from MTEXT proximity). Ignored %d legend blocks.",
        len(entries), attrib_found, blockname_found, mtext_found, ignored_legend_count,
    )
    return entries


# ──────────────────────────────────────────────────────────────────────
# Schedule generation
# ──────────────────────────────────────────────────────────────────────

def generate_schedule(
    entries: List[PlantingEntry],
    forecast_years: int = DEFAULT_FORECAST_YEARS,
    db_path: Optional[Path] = None,
    lai: float = DEFAULT_LAI,
    rain_events: int = 180,
    pollution_multiplier: float = 1.0,
    cle: float = 5.0,
) -> pd.DataFrame:
    """Generate a multi-year planting benefit schedule.

    For each PlantingEntry, resolves species coefficients and runs
    ``engine.forecast_growth()`` over the specified horizon.

    Parameters
    ----------
    entries : list of PlantingEntry
        Extracted tree planting data from DXF.
    forecast_years : int
        Number of years to project.
    db_path : Path, optional
        Database location override.
    lai : float
        Leaf Area Index.
    rain_events : int
        Number of rain events per year (from site profile).
    pollution_multiplier : float
        Site-specific pollution removal scalar (from site profile).
    cle : float
        Crown Light Exposure (0 to 5).

    Returns
    -------
    pd.DataFrame
        A schedule with one row per tree per year, suitable for CSV export.
    """
    all_rows: List[dict] = []

    for tree_id, entry in enumerate(entries, start=1):
        # Resolve species
        sp_record = lookup_species(scientific_name=entry.species_name, db_path=db_path)
        is_palm = sp_record.is_palm if sp_record else False
        growth_rate = sp_record.growth_rate if sp_record else "moderate"

        # Resolve coefficients
        genus = entry.species_name.split()[0] if entry.species_name else None
        coeffs = get_coefficients(
            scientific_name=entry.species_name,
            genus=genus,
            db_path=db_path,
        )

        # Run forecast
        forecast = forecast_growth(
            initial_dbh_cm=entry.dbh_cm,
            coefficients=coeffs,
            growth_rate=growth_rate,
            years=forecast_years,
            initial_height_m=entry.height_m,
            is_palm=is_palm,
            lai=lai,
            rain_events=rain_events,
            pollution_multiplier=pollution_multiplier,
            cle=cle,
        )

        # Convert forecast rows to schedule rows
        for frow in forecast:
            all_rows.append({
                "tree_id": tree_id,
                "block_name": entry.block_name,
                "species": entry.species_name,
                "common_name": coeffs.common_name if coeffs.common_name else (sp_record.common_name if sp_record else None),
                "x": entry.x,
                "y": entry.y,
                "layer": entry.layer,
                "year": frow.year,
                "dbh_cm": frow.dbh_cm,
                "height_m": frow.height_m,
                "carbon_storage_kg": frow.carbon_storage_kg,
                "carbon_seq_kg": frow.carbon_sequestration_kg,
                "co2_storage_kg": frow.co2_storage_kg,
                "co2_seq_kg": frow.co2_sequestration_kg,
                "o2_production_kg_yr": frow.o2_production_kg_yr,
                "epa_gasoline_liters_yr": frow.epa_gasoline_liters_yr,
                "epa_km_driven_yr": frow.epa_km_driven_yr,
                "stormwater_l": frow.stormwater_litres,
                "pm25_removed_g": frow.pm25_removed_g,
                "no2_removed_g": frow.no2_removed_g,
                "o3_removed_g": frow.o3_removed_g,
                "so2_removed_g": frow.so2_removed_g,
                "match_level": coeffs.match_level,
            })

        logger.info(
            "Tree %d: %s (%s) — %d-year forecast complete (match: %s)",
            tree_id, entry.species_name, entry.block_name,
            forecast_years, coeffs.match_level,
        )

    df = pd.DataFrame(all_rows)
    logger.info("Generated schedule: %d rows (%d trees × %d years)",
                len(df), len(entries), forecast_years + 1)
    return df


# ──────────────────────────────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────────────────────────────

def export_schedule_csv(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Write the planting schedule DataFrame to CSV."""
    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "planting_schedule.csv"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(str(output_path), index=False, encoding="utf-8")
    logger.info("Exported planting schedule to %s (%d rows)", output_path, len(df))
    return output_path


def export_summary_csv(
    df: pd.DataFrame,
    output_path: Optional[Union[str, Path]] = None,
) -> Path:
    """Export an aggregated summary (totals per tree at final year)."""
    if output_path is None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / "planting_summary.csv"
    else:
        output_path = Path(output_path)

    if df.empty:
        logger.warning("Empty schedule — writing empty summary")
        pd.DataFrame().to_csv(str(output_path), index=False)
        return output_path

    max_year = df["year"].max()
    final = df[df["year"] == max_year].copy()

    cumulative_seq = (
        df.groupby("tree_id")["carbon_seq_kg"]
        .sum()
        .reset_index()
        .rename(columns={"carbon_seq_kg": "cumulative_seq_kg"})
    )

    summary = final.merge(cumulative_seq, on="tree_id", how="left")
    summary.to_csv(str(output_path), index=False, encoding="utf-8")
    logger.info("Exported planting summary to %s (%d trees)", output_path, len(summary))
    return output_path


# ──────────────────────────────────────────────────────────────────────
# Full pipeline (convenience)
# ──────────────────────────────────────────────────────────────────────

def run_cad_pipeline(
    dxf_path: Union[str, Path],
    output_csv: Optional[Union[str, Path]] = None,
    summary_csv: Optional[Union[str, Path]] = None,
    forecast_years: int = DEFAULT_FORECAST_YEARS,
    target_layers: Optional[List[str]] = None,
    db_path: Optional[Path] = None,
    lai: float = DEFAULT_LAI,
) -> Tuple[Path, Path]:
    """End-to-end CAD pipeline: parse DXF → forecast → export CSV."""
    doc = parse_dxf(dxf_path)
    entries = extract_planting_blocks(doc, target_layers)

    if not entries:
        logger.warning("No planting entries found in DXF — check layer/tag names")
        empty_df = pd.DataFrame()
        p1 = export_schedule_csv(empty_df, output_csv)
        p2 = export_summary_csv(empty_df, summary_csv)
        return p1, p2

    schedule_df = generate_schedule(entries, forecast_years, db_path, lai)

    p1 = export_schedule_csv(schedule_df, output_csv)
    p2 = export_summary_csv(schedule_df, summary_csv)

    return p1, p2


# ──────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────

def _parse_numeric(value: Optional[str], default: Optional[float]) -> Optional[float]:
    """Safely parse a numeric string from a DXF ATTRIB value."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.debug("Could not parse numeric value: '%s' — using default %s", value, default)
        return default
