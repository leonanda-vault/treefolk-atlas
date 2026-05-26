import pytest
import os
from pathlib import Path
from itree_sea.cad_bridge import (
    parse_dxf,
    extract_planting_blocks,
    _parse_mtext_label,
    BLOCK_NAME_MAP,
)

DXF_DIR = Path(r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN")

def test_parse_mtext_label():
    # Standard format: ID, Elev, Species, DBH
    text = "9\n49.94\nMahoni  \nØ 30 cm"
    tree_id, elev, species, dbh = _parse_mtext_label(text)
    assert tree_id == 9
    assert elev == 49.94
    assert species == "Mahoni"
    assert dbh == 30.0

    # No ID or Elev, just Species and DBH
    text = "Angsana\n%%C 25 cm"
    tree_id, elev, species, dbh = _parse_mtext_label(text)
    assert tree_id is None
    assert elev is None
    assert species == "Angsana"
    assert dbh == 25.0

    # Plain cm format (no symbol)
    text = "208\n51.74\nLamtoro\n35cm"
    tree_id, elev, species, dbh = _parse_mtext_label(text)
    assert tree_id == 208
    assert elev == 51.74
    assert species == "Lamtoro"
    assert dbh == 35.0

    # Species name with diameter on the same line
    text = "144\n52.99\nMahoni Ø 35 cm"
    tree_id, elev, species, dbh = _parse_mtext_label(text)
    assert tree_id == 144
    assert elev == 52.99
    assert species == "Mahoni"
    assert dbh == 35.0

    # Multiline species name, no diameter
    text = "567\nBunga \nKupu-kupu"
    tree_id, elev, species, dbh = _parse_mtext_label(text)
    assert tree_id == 567
    assert elev is None
    assert species == "Bunga Kupu-kupu"
    assert dbh is None


def test_species_translations_added():
    assert "tabebuya" in BLOCK_NAME_MAP
    assert BLOCK_NAME_MAP["tabebuya"] == "Handroanthus impetiginosus"
    assert "akasia" in BLOCK_NAME_MAP
    assert BLOCK_NAME_MAP["akasia"] == "Acacia mangium"


def test_cawang_dxf_extraction():
    cawang_path = DXF_DIR / "Analisis Pohon Cawang.dxf"
    if not cawang_path.exists():
        pytest.skip(f"Test file not found: {cawang_path}")

    doc = parse_dxf(cawang_path)
    entries = extract_planting_blocks(doc)

    # 1. Total trees extracted should be 669
    assert len(entries) == 669

    # 2. Species names should be resolved correctly
    species_counts = {}
    for entry in entries:
        species_counts[entry.species_name] = species_counts.get(entry.species_name, 0) + 1

    # Check key species are parsed
    assert "Swietenia macrophylla" in species_counts
    assert "Leucaena leucocephala" in species_counts
    assert "Tectona grandis" in species_counts
    assert "Pterocarpus indicus" in species_counts

    # Verify that unmapped custom species fallback or map correctly
    # Tabebuya maps to Handroanthus impetiginosus, Akasia to Acacia mangium
    assert "Handroanthus impetiginosus" in species_counts
    assert "Acacia mangium" in species_counts

    # 3. DBH values should match expected distribution
    # Let's inspect a few specific inserts
    mahoni_30 = [e for e in entries if e.species_name == "Swietenia macrophylla" and e.dbh_cm == 30.0]
    assert len(mahoni_30) > 0


def test_no_regression_existing_files():
    # 1. Test LA-TREE PLAN 1ST FLOOR.dxf
    floor_path = DXF_DIR / "LA-TREE PLAN 1ST FLOOR.dxf"
    if floor_path.exists():
        doc1 = parse_dxf(floor_path)
        # Should filter by target layers like in the original test script
        layers1 = ["LA-Phn KAMBOJA PUTIH FOSIL", "LA-Phn PANDAN BALI", "LA-Phn TANJUNG", "LA-Phn KAMBOJA PUTIH"]
        entries1 = extract_planting_blocks(doc1, layers1)
        assert len(entries1) == 30
        
        # Verify species counts
        sp1 = [e.species_name for e in entries1]
        assert sp1.count("Plumeria obtusa") == 14
        assert sp1.count("Mimusops elengi") == 12
        assert sp1.count("Pandanus baptistii") == 4

    # 2. Test LA_PLANTING PLAN TREE GKB...dxf
    gkb_path = DXF_DIR / "LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf"
    if gkb_path.exists():
        doc2 = parse_dxf(gkb_path)
        layers2 = ["LA-POHON"]
        entries2 = extract_planting_blocks(doc2, layers2)
        assert len(entries2) == 289
