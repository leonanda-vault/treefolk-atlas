"""
test_database.py — Unit tests for the database module
=======================================================

Tests cover schema creation, CSV seeding, species lookup, and
the 3-tier coefficient fallback chain.
"""

from __future__ import annotations

import tempfile
import csv
from pathlib import Path

import pytest

from itree_sea.database import (
    init_db,
    seed_from_csv,
    lookup_species,
    get_coefficients,
    SpeciesRecord,
    AllometricCoefficients,
)


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Create a temporary database."""
    db_path = tmp_path / "test.db"
    init_db(db_path)
    return db_path


@pytest.fixture
def seeded_db(tmp_path: Path) -> Path:
    """Create and seed a temporary database with test species."""
    db_path = tmp_path / "test.db"
    init_db(db_path)

    csv_path = tmp_path / "test_seed.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "nparks_code", "common_name", "scientific_name", "genus",
            "family", "growth_rate", "is_palm", "native_region", "notes",
            "wood_density", "equation_form", "a", "b", "c",
            "height_model_a", "height_model_b", "source",
        ])
        writer.writeheader()
        writer.writerow({
            "nparks_code": "PTCR",
            "common_name": "Angsana",
            "scientific_name": "Pterocarpus indicus",
            "genus": "Pterocarpus",
            "family": "Fabaceae",
            "growth_rate": "moderate",
            "is_palm": "0",
            "native_region": "singapore",
            "notes": "",
            "wood_density": "0.55",
            "equation_form": "chave_2014",
            "a": "0.0673",
            "b": "0.976",
            "c": "",
            "height_model_a": "0.893",
            "height_model_b": "0.760",
            "source": "test",
        })
        writer.writerow({
            "nparks_code": "CNCF",
            "common_name": "Coconut Palm",
            "scientific_name": "Cocos nucifera",
            "genus": "Cocos",
            "family": "Arecaceae",
            "growth_rate": "moderate",
            "is_palm": "1",
            "native_region": "pantropical",
            "notes": "",
            "wood_density": "0.45",
            "equation_form": "chave_2014",
            "a": "0.0673",
            "b": "0.976",
            "c": "",
            "height_model_a": "",
            "height_model_b": "",
            "source": "test",
        })

    seed_from_csv(csv_path, db_path)
    return db_path


# ── Schema creation ──

class TestInitDB:
    def test_creates_database_file(self, tmp_db):
        assert tmp_db.exists()

    def test_idempotent(self, tmp_db):
        # Re-initialising should not raise
        init_db(tmp_db)
        assert tmp_db.exists()


# ── Seeding ──

class TestSeedFromCSV:
    def test_seed_count(self, seeded_db):
        # We seeded 2 species
        sp1 = lookup_species(scientific_name="Pterocarpus indicus", db_path=seeded_db)
        sp2 = lookup_species(scientific_name="Cocos nucifera", db_path=seeded_db)
        assert sp1 is not None
        assert sp2 is not None

    def test_missing_csv_raises(self, tmp_db, tmp_path):
        with pytest.raises(FileNotFoundError):
            seed_from_csv(tmp_path / "nonexistent.csv", tmp_db)


# ── Species lookup ──

class TestLookupSpecies:
    def test_by_scientific_name(self, seeded_db):
        sp = lookup_species(scientific_name="Pterocarpus indicus", db_path=seeded_db)
        assert sp is not None
        assert sp.common_name == "Angsana"
        assert sp.genus == "Pterocarpus"
        assert sp.is_palm is False

    def test_by_nparks_code(self, seeded_db):
        sp = lookup_species(nparks_code="CNCF", db_path=seeded_db)
        assert sp is not None
        assert sp.scientific_name == "Cocos nucifera"
        assert sp.is_palm is True

    def test_by_common_name(self, seeded_db):
        sp = lookup_species(common_name="Angsana", db_path=seeded_db)
        assert sp is not None
        assert sp.scientific_name == "Pterocarpus indicus"

    def test_not_found_returns_none(self, seeded_db):
        sp = lookup_species(scientific_name="Nonexistent species", db_path=seeded_db)
        assert sp is None

    def test_case_insensitive(self, seeded_db):
        sp = lookup_species(scientific_name="pterocarpus indicus", db_path=seeded_db)
        assert sp is not None


# ── Coefficient resolution ──

class TestGetCoefficients:
    def test_species_level_match(self, seeded_db):
        c = get_coefficients(scientific_name="Pterocarpus indicus", db_path=seeded_db)
        assert c.match_level == "species"
        assert c.wood_density == pytest.approx(0.55)

    def test_genus_fallback(self, seeded_db):
        # Unknown species but known genus
        c = get_coefficients(scientific_name="Pterocarpus dalbergioides", db_path=seeded_db)
        assert c.match_level == "genus"
        assert c.wood_density == pytest.approx(0.55)  # same genus

    def test_default_fallback(self, seeded_db):
        c = get_coefficients(scientific_name="Completely unknown tree", db_path=seeded_db)
        assert c.match_level == "default"

    def test_always_returns_coefficients(self, seeded_db):
        # Even with garbage input, should never return None
        c = get_coefficients(db_path=seeded_db)
        assert isinstance(c, AllometricCoefficients)
        assert c.match_level == "default"

    def test_common_name_lookup(self, seeded_db):
        c = get_coefficients(scientific_name="Pterocarpus indicus", db_path=seeded_db)
        assert c.common_name == "Angsana"
