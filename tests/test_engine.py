"""
test_engine.py — Unit tests for the core calculation engine
=============================================================

Tests validate biomass, carbon, and sequestration calculations against
hand-computed expected values using known species parameters.
"""

from __future__ import annotations

import math
import pytest

from itree_sea.engine import (
    estimate_height,
    calculate_agb,
    calculate_biomass,
    calculate_carbon_storage,
    calculate_sequestration,
    estimate_crown_width,
    estimate_crown_area,
    estimate_leaf_area,
    estimate_stormwater_interception,
    estimate_pollution_removal,
    forecast_growth,
)
from itree_sea.database import AllometricCoefficients
from itree_sea.config import (
    CHAVE_A,
    CHAVE_B,
    URBAN_ADJUSTMENT,
    ROOT_SHOOT_RATIO,
    CARBON_FRACTION_GENERAL,
    CARBON_FRACTION_PALM,
)


# ── Fixtures ──

@pytest.fixture
def angsana_coefficients() -> AllometricCoefficients:
    """Pterocarpus indicus (Angsana) — moderate growth, ρ=0.55."""
    return AllometricCoefficients(
        wood_density=0.55,
        equation_form="chave_2014",
        a=CHAVE_A,
        b=CHAVE_B,
        c=None,
        height_model_a=0.893,
        height_model_b=0.760,
        height_model_c=None,
        height_model_form="power",
        match_level="species",
        source="test",
    )


@pytest.fixture
def coconut_coefficients() -> AllometricCoefficients:
    """Cocos nucifera (Coconut Palm) — ρ=0.45."""
    return AllometricCoefficients(
        wood_density=0.45,
        equation_form="chave_2014",
        a=CHAVE_A,
        b=CHAVE_B,
        c=None,
        height_model_a=0.893,
        height_model_b=0.760,
        height_model_c=None,
        height_model_form="power",
        match_level="species",
        source="test",
    )


# ── Height estimation ──

class TestEstimateHeight:
    def test_positive_dbh(self):
        h = estimate_height(30.0, 0.893, 0.760)
        assert h > 2.0
        assert h == pytest.approx(0.893 * (30.0 ** 0.760), rel=1e-3)

    def test_zero_dbh_returns_minimum(self):
        assert estimate_height(0.0) == 2.0

    def test_negative_dbh_returns_minimum(self):
        assert estimate_height(-5.0) == 2.0


# ── AGB calculation ──

class TestCalculateAGB:
    def test_with_height(self, angsana_coefficients):
        dbh, h, rho = 30.0, 12.0, 0.55
        expected = CHAVE_A * (rho * dbh**2 * h) ** CHAVE_B * URBAN_ADJUSTMENT
        result = calculate_agb(dbh, h, rho, angsana_coefficients, is_urban=True)
        assert result == pytest.approx(expected, rel=1e-3)

    def test_without_urban_adjustment(self, angsana_coefficients):
        dbh, h, rho = 30.0, 12.0, 0.55
        expected = CHAVE_A * (rho * dbh**2 * h) ** CHAVE_B
        result = calculate_agb(dbh, h, rho, angsana_coefficients, is_urban=False)
        assert result == pytest.approx(expected, rel=1e-3)

    def test_zero_dbh_returns_zero(self, angsana_coefficients):
        assert calculate_agb(0.0, 10.0, 0.55, angsana_coefficients) == 0.0

    def test_negative_density_returns_zero(self, angsana_coefficients):
        assert calculate_agb(30.0, 10.0, -0.5, angsana_coefficients) == 0.0


# ── Full biomass ──

class TestCalculateBiomass:
    def test_carbon_fraction_general(self, angsana_coefficients):
        result = calculate_biomass(30.0, 12.0, angsana_coefficients, is_palm=False)
        # Carbon should be ~50% of total biomass
        assert result.carbon_storage_kg == pytest.approx(
            result.total_biomass_kg * CARBON_FRACTION_GENERAL, rel=1e-3
        )

    def test_carbon_fraction_palm(self, coconut_coefficients):
        result = calculate_biomass(25.0, 15.0, coconut_coefficients, is_palm=True)
        assert result.carbon_storage_kg == pytest.approx(
            result.total_biomass_kg * CARBON_FRACTION_PALM, rel=1e-3
        )

    def test_bgb_is_ratio_of_agb(self, angsana_coefficients):
        result = calculate_biomass(30.0, 12.0, angsana_coefficients)
        assert result.bgb_kg == pytest.approx(
            result.agb_kg * ROOT_SHOOT_RATIO, rel=1e-3
        )

    def test_dead_tree_zero_carbon(self, angsana_coefficients):
        result = calculate_biomass(30.0, 12.0, angsana_coefficients, condition="dead")
        assert result.carbon_storage_kg == 0.0

    def test_epa_equivalencies_metric(self, angsana_coefficients):
        result = calculate_biomass(30.0, 12.0, angsana_coefficients, is_palm=False)
        co2_seq = result.co2_sequestration_kg
        expected_liters = (co2_seq / 1000.0) * 112.18 * 3.78541
        expected_km = (co2_seq / 1000.0) * 2564.0 * 1.60934
        assert result.epa_gasoline_liters_yr == pytest.approx(expected_liters, abs=1e-1)
        assert result.epa_km_driven_yr == pytest.approx(expected_km, abs=1e-1)


# ── Sequestration ──

class TestSequestration:
    def test_positive_sequestration(self, angsana_coefficients):
        result = calculate_sequestration(
            30.0, 12.0, angsana_coefficients, growth_rate="moderate"
        )
        assert result.annual_sequestration_kg > 0.0
        assert result.dbh_end_cm > result.dbh_start_cm

    def test_sequestration_not_negative(self, angsana_coefficients):
        result = calculate_sequestration(
            5.0, 3.0, angsana_coefficients, growth_rate="slow"
        )
        assert result.annual_sequestration_kg >= 0.0


# ── Stormwater ──

class TestStormwater:
    def test_positive_interception(self):
        litres = estimate_stormwater_interception(30.0)
        assert litres > 0.0

    def test_zero_dbh(self):
        litres = estimate_stormwater_interception(0.0)
        # Minimum crown width is 0.6 m, so still some interception
        assert litres > 0.0

    def test_crown_width_cap(self):
        cw = estimate_crown_width(200.0)
        assert cw == 20.0  # capped


# ── Pollution ──

class TestPollution:
    def test_all_pollutants_positive(self):
        result = estimate_pollution_removal(30.0)
        assert result.pm25_g > 0.0
        assert result.no2_g > 0.0
        assert result.o3_g > 0.0
        assert result.so2_g > 0.0
        assert result.total_g == pytest.approx(
            result.pm25_g + result.no2_g + result.o3_g + result.so2_g, rel=1e-3
        )


# ── Forecast ──

class TestForecast:
    def test_forecast_length(self, angsana_coefficients):
        rows = forecast_growth(5.0, angsana_coefficients, years=10)
        assert len(rows) == 11  # year 0 through 10

    def test_dbh_increases(self, angsana_coefficients):
        rows = forecast_growth(5.0, angsana_coefficients, years=5)
        for i in range(1, len(rows)):
            assert rows[i].dbh_cm > rows[i - 1].dbh_cm

    def test_carbon_increases(self, angsana_coefficients):
        rows = forecast_growth(5.0, angsana_coefficients, years=5)
        for i in range(1, len(rows)):
            assert rows[i].carbon_storage_kg >= rows[i - 1].carbon_storage_kg

    def test_first_year_zero_sequestration(self, angsana_coefficients):
        rows = forecast_growth(5.0, angsana_coefficients, years=3)
        assert rows[0].carbon_sequestration_kg == 0.0
