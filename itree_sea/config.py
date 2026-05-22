"""
config.py — Global constants, file paths, and default climate parameters
=========================================================================

All numeric constants used across the i-Tree SEA engine are centralised
here.  Values are sourced from:

  • Chave et al. (2014) — pantropical allometric model
  • USFS i-Tree Eco v6 methodology documents
  • Singapore Meteorological Service — climate normals
  • Published tropical urban forestry literature

Design note:
  Every constant carries an inline citation so a reviewer can trace
  the number back to a peer-reviewed source.  Where a constant has
  been *adapted* for tropical conditions (rather than used verbatim),
  the adaptation rationale is documented.
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict


# ──────────────────────────────────────────────────────────────────────
# 1. FILE PATHS
# ──────────────────────────────────────────────────────────────────────

# Root of the project (one level above this package)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

# Default SQLite database location
DATABASE_PATH: Path = PROJECT_ROOT / "data" / "itree_sea.db"

# CSV seed file for initial species + coefficient data
SEED_CSV_PATH: Path = PROJECT_ROOT / "data" / "seed_species.csv"

# Default output directory for enriched exports
OUTPUT_DIR: Path = PROJECT_ROOT / "output"


# ──────────────────────────────────────────────────────────────────────
# 2. ALLOMETRIC EQUATION CONSTANTS  (Chave et al. 2014)
# ──────────────────────────────────────────────────────────────────────

# Primary pantropical equation:  AGB = a × (ρ × D² × H)^b
CHAVE_A: float = 0.0673       # multiplicative constant
CHAVE_B: float = 0.976        # exponent

# Alternative (no-height) equation coefficients:
# ln(AGB) = β₀ + β₁·E + β₂·ln(ρ) + β₃·ln(D) + β₄·[ln(D)]²
CHAVE_NOHGT_B0: float = -1.803
CHAVE_NOHGT_B1: float = -0.976   # coefficient on bioclimatic stress E
CHAVE_NOHGT_B2: float = 0.976    # coefficient on ln(wood density)
CHAVE_NOHGT_B3: float = 2.673    # coefficient on ln(DBH)
CHAVE_NOHGT_B4: float = -0.0299  # coefficient on [ln(DBH)]²

# Bioclimatic stress variable E for equatorial lowland SE Asia
# (low temperature seasonality, high rainfall, minimal drought)
# Source: Chave et al. 2014, Table S3 — Singapore/W. Java region
BIOCLIMATIC_E: float = -0.070


# ──────────────────────────────────────────────────────────────────────
# 3. BIOMASS → CARBON CONVERSION  (i-Tree Eco v6)
# ──────────────────────────────────────────────────────────────────────

# Root-to-shoot ratio for belowground biomass estimation
# Source: Cairns et al. (1997)
ROOT_SHOOT_RATIO: float = 0.26

# Urban open-grown adjustment factor
# Forest-grown allometry overestimates open-canopy urban trees
# Source: Nowak (1994), applied in i-Tree Eco
URBAN_ADJUSTMENT: float = 0.80

# Dry biomass to carbon conversion
# Source: IPCC (2006) default; i-Tree Eco standard
CARBON_FRACTION_GENERAL: float = 0.50
CARBON_FRACTION_PALM: float = 0.41

# Maximum carbon storage before sequestration is capped (kg C)
CARBON_STORAGE_CAP: float = 7500.0

# Maximum sequestration rate once cap is reached (kg C per cm DBH growth)
SEQUESTRATION_RATE_CAP: float = 40.0


# ──────────────────────────────────────────────────────────────────────
# 4. GROWTH RATE DEFAULTS  (annual DBH increment, cm/yr)
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GrowthRates:
    """Annual DBH increment (cm/yr) by growth rate category.

    Tropical values are higher than USFS temperate defaults.
    Source: i-Tree Eco growth tables, adapted for SE Asian tropical
    species using NParks growth monitoring data and Pretzsch (2009).
    """
    slow: float = 0.50
    moderate: float = 1.00
    fast: float = 1.75

GROWTH_RATES: GrowthRates = GrowthRates()

# Mapping from string category to numeric value for easy lookup
GROWTH_RATE_MAP: Dict[str, float] = {
    "slow": GROWTH_RATES.slow,
    "moderate": GROWTH_RATES.moderate,
    "fast": GROWTH_RATES.fast,
}


# ──────────────────────────────────────────────────────────────────────
# 5. STORMWATER INTERCEPTION PROXY CONSTANTS
# ──────────────────────────────────────────────────────────────────────

# Specific leaf storage capacity (m of water depth per unit LAI)
# Source: i-Tree Hydro (Wang et al. 2008)
SPECIFIC_LEAF_STORAGE_M: float = 0.0002   # 0.2 mm

# Default Leaf Area Index for tropical broadleaf evergreen
# Source: Asner et al. (2003) — global LAI dataset
DEFAULT_LAI: float = 5.0

# Number of rain events per year (Singapore / W. Indonesia)
# Source: Singapore Met Service — ~180 rain days per year
ANNUAL_RAIN_EVENTS: int = 180

# Crown width estimation from DBH (tropical urban approximation)
# CW(m) = CW_INTERCEPT + CW_SLOPE × DBH(cm), capped at CW_MAX
# Source: Adapted from Peper et al. (2001), recalibrated for tropical species
CW_INTERCEPT: float = 0.6
CW_SLOPE: float = 0.15
CW_MAX_M: float = 20.0


# ──────────────────────────────────────────────────────────────────────
# 6. AIR POLLUTION REMOVAL PROXY CONSTANTS  (g/m² leaf area/yr)
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PollutionRemovalRates:
    """Annual dry deposition removal rates per unit leaf area.

    Values represent literature medians for tropical broadleaf urban
    canopies.  They bypass the need for hourly meteorological data by
    pre-integrating seasonal deposition velocity × concentration.

    Sources:
      PM2.5  — Chen et al. (2017), Shanghai tropical analog study
      NO2    — Nowak et al. (2006), i-Tree Eco default
      O3     — Nowak et al. (2006), i-Tree Eco default
      SO2    — Nowak et al. (2006), i-Tree Eco default
    """
    pm25: float = 0.50    # g/m²/yr
    no2: float = 0.90     # g/m²/yr
    o3: float = 1.40      # g/m²/yr
    so2: float = 0.35     # g/m²/yr

POLLUTION_RATES: PollutionRemovalRates = PollutionRemovalRates()


# ──────────────────────────────────────────────────────────────────────
# 7. DEFAULT WOOD DENSITY FALLBACKS  (g/cm³)
# ──────────────────────────────────────────────────────────────────────

# Used when neither species nor genus is found in the database
# Source: Chave et al. (2009) — pantropical mean
DEFAULT_WOOD_DENSITY: float = 0.58

# Height estimation defaults (H = a × D^b) when height is missing
# Source: Feldpausch et al. (2012) — SE Asian tropical moist forest
DEFAULT_HEIGHT_A: float = 0.893
DEFAULT_HEIGHT_B: float = 0.760


# ──────────────────────────────────────────────────────────────────────
# 8. DXF / CAD CONVENTIONS
# ──────────────────────────────────────────────────────────────────────

# Expected DXF block attribute tags that identify tree planting symbols
# These are the ATTDEF tag strings landscape architects typically use
DXF_SPECIES_TAG: str = "SPECIES"
DXF_DBH_TAG: str = "DBH"
DXF_HEIGHT_TAG: str = "HEIGHT"
DXF_CALIPER_TAG: str = "CALIPER"   # alternative for DBH at planting

# Default newly-planted DBH if not specified in the CAD block (cm)
DEFAULT_PLANTING_DBH: float = 5.0

# Default forecast horizon for planting schedule (years)
DEFAULT_FORECAST_YEARS: int = 25


# ──────────────────────────────────────────────────────────────────────
# 9. GIS FIELD NAME CONVENTIONS
# ──────────────────────────────────────────────────────────────────────

# Expected attribute column names in GeoJSON / Shapefile
GIS_SPECIES_FIELD: str = "species"
GIS_DBH_FIELD: str = "dbh_cm"
GIS_HEIGHT_FIELD: str = "height_m"
GIS_CONDITION_FIELD: str = "condition"

# Condition multiplier: reduces biomass for trees in poor health
# Source: i-Tree Eco condition classes
CONDITION_MULTIPLIERS: Dict[str, float] = {
    "excellent": 1.00,
    "good": 0.95,
    "fair": 0.80,
    "poor": 0.55,
    "critical": 0.30,
    "dead": 0.00,
}


# ──────────────────────────────────────────────────────────────────────
# 10. SITE PROFILES  (bundled environmental context)
# ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SiteProfile:
    """Pre-configured environmental context for a site type.

    Bundles together the parameters that vary by location and land use,
    so users pick one profile instead of tuning raw numbers.

    Parameters
    ----------
    label : str
        Human-readable name shown in the UI.
    description : str
        Short explanation of when to use this profile.
    rain_events : int
        Number of rain events per year.
        Source: national met services, WorldClim.
    pollution_multiplier : float
        Scalar on the base pollution removal rates (1.0 = literature default).
        Higher ambient concentrations → more removal (up to deposition limit).
        Source: WHO air quality reports, IQAir city rankings.
    lai : float
        Leaf Area Index for the canopy type at this site.
        Source: Asner et al. (2003), tropical LAI dataset.
    """
    label: str
    description: str
    rain_events: int
    pollution_multiplier: float
    lai: float


SITE_PROFILES: Dict[str, SiteProfile] = {
    "urban_dense": SiteProfile(
        label="Urban Dense (CBD / Roadside)",
        description="High-density built environment: arterial roads, commercial districts, "
                    "minimal pervious surface. High pollution, moderate rainfall interception.",
        rain_events=180,
        pollution_multiplier=1.50,
        lai=4.0,
    ),
    "urban_park": SiteProfile(
        label="Urban Park / Campus",
        description="Green spaces within urban areas: city parks, university campuses, "
                    "hospital grounds. Moderate pollution, good canopy coverage.",
        rain_events=180,
        pollution_multiplier=1.00,
        lai=5.0,
    ),
    "suburban": SiteProfile(
        label="Suburban / Residential",
        description="Low-to-medium density residential: housing estates, school grounds, "
                    "neighbourhood streets. Lower pollution, mixed canopy.",
        rain_events=180,
        pollution_multiplier=0.75,
        lai=5.0,
    ),
    "industrial": SiteProfile(
        label="Industrial / Port Area",
        description="Industrial estates, logistics hubs, port areas. Very high pollution "
                    "concentrations, sparse existing canopy.",
        rain_events=170,
        pollution_multiplier=2.00,
        lai=3.5,
    ),
    "coastal": SiteProfile(
        label="Coastal / Waterfront",
        description="Coastal reclamation, waterfront promenades, mangrove buffer zones. "
                    "Salt-spray exposure, moderate pollution, high wind.",
        rain_events=170,
        pollution_multiplier=0.60,
        lai=4.5,
    ),
    "rural_periurban": SiteProfile(
        label="Peri-Urban / Rural Edge",
        description="Rural-urban fringe: agricultural borders, new development areas, "
                    "reforestation sites. Low pollution, dense canopy potential.",
        rain_events=190,
        pollution_multiplier=0.40,
        lai=6.0,
    ),
    "custom_advanced": SiteProfile(
        label="🔬 Custom / Advanced",
        description="Upload your own hourly rainfall CSV and enter measured ambient pollution "
                    "concentrations. The engine will derive rain events and pollution multipliers "
                    "from your data.",
        rain_events=180,           # overridden at runtime
        pollution_multiplier=1.0,  # overridden at runtime
        lai=5.0,                   # overridden at runtime
    ),
}

# Default profile key
DEFAULT_SITE_PROFILE: str = "urban_park"


# ──────────────────────────────────────────────────────────────────────
# 11. ADVANCED MODE — BASELINE POLLUTION CONCENTRATIONS  (µg/m³)
# ──────────────────────────────────────────────────────────────────────
# These are the ambient concentrations assumed when the base removal
# rates (Nowak et al. 2006) were derived.  Used to convert user-supplied
# measured concentrations into a pollution multiplier:
#     multiplier = measured_conc / baseline_conc
#
# Sources:
#   PM2.5  — US EPA NAAQS annual standard: 12 µg/m³
#   NO₂    — WHO guideline annual mean: 40 µg/m³
#   O₃     — WHO guideline 8-hr mean: 100 µg/m³
#   SO₂    — WHO guideline 24-hr: 40 µg/m³

@dataclass(frozen=True)
class BaselinePollutionConcentrations:
    """Ambient concentrations (µg/m³) assumed by the literature removal rates."""
    pm25: float = 12.0
    no2: float = 40.0
    o3: float = 100.0
    so2: float = 40.0

BASELINE_CONCENTRATIONS: BaselinePollutionConcentrations = BaselinePollutionConcentrations()

# Minimum rainfall depth (mm) to count as a "rain event"
# Source: WMO definition of a rain day
MIN_RAIN_EVENT_MM: float = 1.0
