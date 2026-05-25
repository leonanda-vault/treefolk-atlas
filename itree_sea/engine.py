"""
engine.py — Core ecosystem benefit calculators
================================================

Implements the mathematical models from Phase 1 of the specification:

  • Aboveground biomass via Chave et al. (2014) pantropical allometry
  • Belowground biomass via root-to-shoot ratio (Cairns et al. 1997)
  • Carbon storage (biomass × 0.5)
  • Annual carbon sequestration (delta-storage method)
  • Multi-year growth forecast with annual benefit schedule
  • Simplified stormwater interception proxy
  • Simplified air pollution removal proxy

Every function is stateless — it depends only on its arguments and
constants from ``config.py``.  No database access occurs here; the
caller is responsible for resolving coefficients first.

Units convention:
  • DBH in cm
  • Height in m
  • Biomass in kg
  • Carbon in kg
  • Stormwater in litres
  • Pollution in grams
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from itree_sea.config import (
    CHAVE_A,
    CHAVE_B,
    CHAVE_NOHGT_B0,
    CHAVE_NOHGT_B1,
    CHAVE_NOHGT_B2,
    CHAVE_NOHGT_B3,
    CHAVE_NOHGT_B4,
    BIOCLIMATIC_E,
    ROOT_SHOOT_RATIO,
    URBAN_ADJUSTMENT,
    CARBON_FRACTION_GENERAL,
    CARBON_FRACTION_PALM,
    CARBON_STORAGE_CAP,
    SEQUESTRATION_RATE_CAP,
    GROWTH_RATE_MAP,
    SPECIFIC_LEAF_STORAGE_M,
    DEFAULT_LAI,
    ANNUAL_RAIN_EVENTS,
    CW_INTERCEPT,
    CW_SLOPE,
    CW_MAX_M,
    POLLUTION_RATES,
    DEFAULT_HEIGHT_A,
    DEFAULT_HEIGHT_B,
    CONDITION_MULTIPLIERS,
    DEFAULT_TRUE_GROWTH_RATE_CM,
    DEFAULT_PALM_HEIGHT_GROWTH_M,
    DEFAULT_CROWN_MODIFIER,
    DEFAULT_SPECIES_LAI,
    DEFAULT_FOLIAGE_FRACTION,
)
from itree_sea.database import AllometricCoefficients

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Result containers
# ──────────────────────────────────────────────────────────────────────

@dataclass
class BiomassResult:
    """Complete biomass + carbon result for a single tree."""
    dbh_cm: float
    height_m: Optional[float]
    wood_density: float
    agb_kg: float                  # aboveground biomass
    bgb_kg: float                  # belowground biomass
    total_biomass_kg: float
    carbon_storage_kg: float
    carbon_sequestration_kg: float
    co2_storage_kg: float
    co2_sequestration_kg: float
    o2_production_kg_yr: float
    epa_gasoline_liters_yr: float
    epa_km_driven_yr: float
    
    # Optional extended metrics for backwards compatibility
    stormwater_litres: float = 0.0
    pm25_removed_g: float = 0.0
    no2_removed_g: float = 0.0
    o3_removed_g: float = 0.0
    so2_removed_g: float = 0.0
    
    match_level: str = ""          # how coefficients were resolved
    equation_used: str = ""        # which equation form


@dataclass
class SequestrationResult:
    """Annual carbon sequestration for one growth step."""
    dbh_start_cm: float
    dbh_end_cm: float
    carbon_start_kg: float
    carbon_end_kg: float
    annual_sequestration_kg: float
    was_capped: bool               # True if the 7500 kg cap was applied


@dataclass
class ForecastRow:
    """One year in a multi-year growth forecast."""
    year: int
    dbh_cm: float
    height_m: float
    agb_kg: float
    total_biomass_kg: float
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


# ──────────────────────────────────────────────────────────────────────
# 1. HEIGHT ESTIMATION
# ──────────────────────────────────────────────────────────────────────

def estimate_height(
    dbh_cm: float,
    height_model_a: Optional[float] = None,
    height_model_b: Optional[float] = None,
    height_model_c: Optional[float] = None,
    height_model_form: str = "power",
) -> float:
    """Estimate total tree height from DBH when field measurement is missing.

    Supports two model forms:

    **Power-law** (default):  H = a × DBH^b
        Source: Feldpausch et al. (2012), generic tropical.

    **Weibull** (3-param):  H = a × (1 − exp(−b × DBH^c))
        Source: Feldpausch et al. (2012), regional SE Asian coefficients
        (a=57.122, b=0.0332, c=0.8468).
        More accurate — captures the biological height asymptote.

    Parameters
    ----------
    dbh_cm : float
        Diameter at breast height in centimetres.
    height_model_a, height_model_b, height_model_c : float, optional
        Species/genus-specific or regional coefficients.
    height_model_form : str
        'power' or 'weibull'.

    Returns
    -------
    float
        Estimated height in metres (minimum 2.0 m).
    """
    if dbh_cm <= 0:
        return 2.0

    if height_model_form == "weibull":
        # Weibull: H = a * (1 - exp(-b * D^c))
        a = height_model_a if height_model_a is not None else 57.122
        b = height_model_b if height_model_b is not None else 0.0332
        c = height_model_c if height_model_c is not None else 0.8468
        height = a * (1.0 - math.exp(-b * (dbh_cm ** c)))
    else:
        # Power-law: H = a * D^b
        a = height_model_a if height_model_a is not None else DEFAULT_HEIGHT_A
        b = height_model_b if height_model_b is not None else DEFAULT_HEIGHT_B
        height = a * (dbh_cm ** b)

    return max(height, 2.0)


# ──────────────────────────────────────────────────────────────────────
# 2. ABOVEGROUND BIOMASS (AGB)
# ──────────────────────────────────────────────────────────────────────

def get_trunk_multiplier(scientific_name: Optional[str]) -> float:
    """Determine trunk type multiplier based on species name."""
    if not scientific_name:
        return 1.0
    name = scientific_name.lower().strip()
    # Buttressed species
    if any(k in name for k in ["samanea saman", "ficus", "dialium", "adansonia", "trembesi", "beringin", "asam kranji", "baobab"]):
        return 1.15
    # Multi-stemmed species
    if any(k in name for k in ["plumeria", "callistemon", "frangipani", "sikat botol"]):
        return 0.85
    return 1.0


def get_crown_shape_multiplier(crown_modifier: float) -> float:
    """Determine crown shape multiplier based on crown modifier value."""
    if crown_modifier <= 0.10:
        return 0.80  # columnar
    elif crown_modifier <= 0.13:
        return 0.90  # conical
    elif crown_modifier <= 0.20:
        return 1.00  # spherical
    else:
        return 1.15  # spreading


def get_leaf_shape_slw(scientific_name: Optional[str], is_palm: bool) -> float:
    """Determine Specific Leaf Weight (SLW, kg/m2) based on leaf shape/species."""
    if is_palm:
        return 0.32  # palm_fan
    if not scientific_name:
        return 0.12  # broadleaf_simple
    name = scientific_name.lower().strip()
    # Conifers/needles
    if any(k in name for k in ["casuarina", "araucaria", "podocarpus", "agathis", "conifer", "cemara", "damar"]):
        return 0.22  # needle
    # Compound leaf genera
    compound_genera = [
        "pterocarpus", "swietenia", "delonix", "samanea", "erythrina", 
        "khaya", "senna", "leucaena", "dialium", "tamarindus", 
        "schizolobium", "moringa", "angsana", "mahoni", "trembesi", "flamboyan",
        "mindi", "lamtoro", "asam"
    ]
    if any(name.startswith(g) or g in name for g in compound_genera):
        return 0.09  # broadleaf_compound
    return 0.12  # broadleaf_simple


def calculate_agb(
    dbh_cm: float,
    height_m: Optional[float],
    wood_density: float,
    coefficients: Optional[AllometricCoefficients] = None,
    is_urban: bool = True,
    is_palm: bool = False,
) -> float:
    """Calculate aboveground dry-weight biomass (kg).

    When height is available and it is a palm, uses a cylindrical palm model:
        AGB = 0.07854 × ρ × D² × H

    When it is not a palm, uses the morphology-driven woody + foliage model:
        Woody = Chave_AGB_Base × 0.97 × trunk_multiplier × crown_shape_multiplier
        Foliage = Crown_Area × LAI × SLW
        AGB = Woody + Foliage

    When height is unavailable, uses the no-height alternative with default/species fallbacks.
    """
    if dbh_cm <= 0 or wood_density <= 0:
        logger.warning("Invalid input: DBH=%.2f, density=%.4f → AGB=0", dbh_cm, wood_density)
        return 0.0

    sci_name = coefficients.species if coefficients else None

    # ── Palms (Monocots) Cylindrical Model ──
    if is_palm:
        if height_m is None or height_m <= 0:
            # Estimate height first using palm-specific/fallback models
            h_a = coefficients.height_model_a if coefficients else None
            h_b = coefficients.height_model_b if coefficients else None
            h_c = coefficients.height_model_c if coefficients else None
            h_form = coefficients.height_model_form if coefficients else "power"
            height_m = estimate_height(dbh_cm, h_a, h_b, h_c, h_form)

        # Cylindrical biomass formula for palm (no taper)
        # Volume = (pi * D^2 / 40000) * H m3
        # Biomass = Volume * wood_density * 1000 kg = 0.07854 * wood_density * D^2 * H kg
        agb = 0.07854 * wood_density * (dbh_cm ** 2) * height_m
        if is_urban:
            agb *= URBAN_ADJUSTMENT
        return max(agb, 0.0)

    # ── Non-palms (Dicots) ──
    a = coefficients.a if coefficients else CHAVE_A
    b = coefficients.b if coefficients else CHAVE_B

    # Resolve height
    if height_m is None or height_m <= 0:
        h_a = coefficients.height_model_a if coefficients else None
        h_b = coefficients.height_model_b if coefficients else None
        h_c = coefficients.height_model_c if coefficients else None
        h_form = coefficients.height_model_form if coefficients else "power"

        if h_a is not None and h_b is not None:
            height_m = estimate_height(dbh_cm, h_a, h_b, h_c, h_form)
            # Having resolved height, use primary equation
            if coefficients and coefficients.equation_form == "ketterings_2001":
                agb_base = a * wood_density * (dbh_cm ** b)
            else:
                combined = wood_density * (dbh_cm ** 2) * height_m
                agb_base = a * (combined ** b)
        else:
            # Use no-height equation
            ln_dbh = math.log(dbh_cm)
            ln_agb = (
                CHAVE_NOHGT_B0
                + CHAVE_NOHGT_B1 * BIOCLIMATIC_E
                + CHAVE_NOHGT_B2 * math.log(wood_density)
                + CHAVE_NOHGT_B3 * ln_dbh
                + CHAVE_NOHGT_B4 * (ln_dbh ** 2)
            )
            agb_base = math.exp(ln_agb)
    else:
        # Primary equation with height
        if coefficients and coefficients.equation_form == "ketterings_2001":
            agb_base = a * wood_density * (dbh_cm ** b)
        else:
            combined = wood_density * (dbh_cm ** 2) * height_m
            agb_base = a * (combined ** b)

    # Separate Woody and Foliage components from baseline AGB
    woody_base = agb_base * (1.0 - DEFAULT_FOLIAGE_FRACTION)

    # Resolve morphology properties
    crown_modifier = coefficients.crown_modifier if coefficients else DEFAULT_CROWN_MODIFIER
    species_lai = coefficients.species_lai if coefficients else DEFAULT_SPECIES_LAI

    trunk_mult = get_trunk_multiplier(sci_name)
    crown_shape_mult = get_crown_shape_multiplier(crown_modifier)

    # Adjust woody component
    woody_adjusted = woody_base * trunk_mult * crown_shape_mult

    # Explicitly calculate foliage biomass based on morphology
    # 1. Crown width CW = 0.6 + crown_modifier * DBH
    # 2. Crown area CA = pi * (CW/2)^2
    # 3. Leaf area LA = CA * LAI (species_lai)
    # 4. Foliage biomass = LA * SLW
    cw = 0.6 + crown_modifier * dbh_cm
    cw = min(cw, CW_MAX_M)
    ca = math.pi * (cw / 2.0) ** 2
    la = ca * species_lai
    slw = get_leaf_shape_slw(sci_name, is_palm=False)
    foliage_biomass = la * slw

    # Recombine components
    agb = woody_adjusted + foliage_biomass

    if is_urban:
        agb *= URBAN_ADJUSTMENT

    return max(agb, 0.0)



# ──────────────────────────────────────────────────────────────────────
# 3. TOTAL BIOMASS & CARBON STORAGE
# ──────────────────────────────────────────────────────────────────────

def calculate_biomass(
    dbh_cm: float,
    height_m: Optional[float],
    coefficients: AllometricCoefficients,
    is_urban: bool = True,
    condition: str = "good",
    is_palm: bool = False,
    lai: float = DEFAULT_LAI,
    rain_events: int = ANNUAL_RAIN_EVENTS,
    pollution_multiplier: float = 1.0,
) -> BiomassResult:
    """Calculate full biomass and carbon storage for one tree.

    This is the primary entry point for single-tree calculations.
    It wraps ``calculate_agb()`` and adds belowground biomass,
    condition adjustment, and carbon conversion.
    """
    # Condition multiplier
    cond_mult = CONDITION_MULTIPLIERS.get(condition.lower().strip(), 0.80)

    # Aboveground biomass
    agb = calculate_agb(
        dbh_cm=dbh_cm,
        height_m=height_m,
        wood_density=coefficients.wood_density,
        coefficients=coefficients,
        is_urban=is_urban,
        is_palm=is_palm,
    )
    agb *= cond_mult

    # Belowground biomass
    bgb = agb * ROOT_SHOOT_RATIO

    # Total biomass
    total = agb + bgb

    # Carbon storage
    carbon_frac = CARBON_FRACTION_PALM if is_palm else CARBON_FRACTION_GENERAL
    carbon = total * carbon_frac

    # CO2 Equivalent Conversion (IPCC 3.6663)
    CO2_RATIO = 3.6663
    co2_storage = carbon * CO2_RATIO

    # Resolve displayed height (needed for next year height estimation)
    display_height = height_m
    if display_height is None or display_height <= 0:
        display_height = estimate_height(
            dbh_cm,
            coefficients.height_model_a,
            coefficients.height_model_b,
            coefficients.height_model_c,
            coefficients.height_model_form,
        )

    # Annual Sequestration/Oxygen/Equivalencies proxy (using annual increment)
    if is_palm:
        delta_d = 0.0
        palm_h_growth = coefficients.palm_height_growth_m if hasattr(coefficients, "palm_height_growth_m") else DEFAULT_PALM_HEIGHT_GROWTH_M
        height_next = display_height + palm_h_growth
    else:
        delta_d = coefficients.true_growth_rate_cm if hasattr(coefficients, "true_growth_rate_cm") else DEFAULT_TRUE_GROWTH_RATE_CM
        height_next = None
        if display_height is not None and display_height > 0:
            height_next = display_height * ((dbh_cm + delta_d) / dbh_cm) ** 0.5

    c_next = calculate_carbon_storage(dbh_cm + delta_d, height_next, coefficients, is_urban, is_palm)
    seq = max(c_next - carbon, 0.0)
    
    co2_seq = seq * CO2_RATIO
    o2_prod = seq * 2.6667
    epa_liters = (co2_seq / 1000.0) * 112.18 * 3.78541
    epa_km = (co2_seq / 1000.0) * 2564.0 * 1.60934

    # Resolve LAI scaled by site profile selection
    site_lai_factor = lai / DEFAULT_LAI
    spec_lai = coefficients.species_lai if hasattr(coefficients, "species_lai") else DEFAULT_SPECIES_LAI
    resolved_lai = spec_lai * site_lai_factor
    
    crown_modifier = coefficients.crown_modifier if hasattr(coefficients, "crown_modifier") else DEFAULT_CROWN_MODIFIER

    # Pollution/Stormwater
    pollution = estimate_pollution_removal(dbh_cm, resolved_lai, pollution_multiplier, crown_modifier)
    sw = estimate_stormwater_interception(dbh_cm, resolved_lai, rain_events, crown_modifier)

    # Determine equation used
    if height_m is not None and height_m > 0:
        eq_used = f"{coefficients.equation_form}_with_height"
    else:
        eq_used = f"{coefficients.equation_form}_no_height"

    return BiomassResult(
        dbh_cm=dbh_cm,
        height_m=display_height,
        wood_density=coefficients.wood_density,
        match_level=coefficients.match_level,
        equation_used=eq_used,
        agb_kg=round(agb, 2),
        bgb_kg=round(bgb, 2),
        total_biomass_kg=round(total, 2),
        carbon_storage_kg=round(carbon, 2),
        carbon_sequestration_kg=round(seq, 2),
        co2_storage_kg=round(co2_storage, 2),
        co2_sequestration_kg=round(co2_seq, 2),
        o2_production_kg_yr=round(o2_prod, 2),
        epa_gasoline_liters_yr=round(epa_liters, 2),
        epa_km_driven_yr=round(epa_km, 2),
        stormwater_litres=round(sw, 2),
        pm25_removed_g=pollution.pm25_g,
        no2_removed_g=pollution.no2_g,
        o3_removed_g=pollution.o3_g,
        so2_removed_g=pollution.so2_g,
    )


# ──────────────────────────────────────────────────────────────────────
# 4. CARBON SEQUESTRATION
# ──────────────────────────────────────────────────────────────────────

def calculate_carbon_storage(
    dbh_cm: float,
    height_m: Optional[float],
    coefficients: AllometricCoefficients,
    is_urban: bool = True,
    is_palm: bool = False,
) -> float:
    """Shorthand: return only the carbon storage (kg) for a given DBH.

    Used internally by the sequestration calculator.
    """
    # This simplified version uses the carbon fraction directly
    agb = calculate_agb(dbh_cm, height_m, coefficients.wood_density, coefficients, is_urban)
    total = agb * (1.0 + ROOT_SHOOT_RATIO)
    carbon_frac = CARBON_FRACTION_PALM if is_palm else CARBON_FRACTION_GENERAL
    return total * carbon_frac


def calculate_sequestration(
    dbh_cm: float,
    height_m: Optional[float],
    coefficients: AllometricCoefficients,
    growth_rate: str = "moderate",
    is_urban: bool = True,
    is_palm: bool = False,
) -> SequestrationResult:
    """Calculate annual gross carbon sequestration (delta-storage method).

    Sequestration = C_storage(DBH + ΔD) − C_storage(DBH)

    When C_storage exceeds 7,500 kg, the sequestration rate is capped
    at 40 kg per cm of DBH growth (i-Tree Eco rule).

    Parameters
    ----------
    dbh_cm : float
        Current DBH in cm.
    height_m : float or None
        Current total height (or None).
    coefficients : AllometricCoefficients
        Resolved coefficients.
    growth_rate : str
        Growth rate category ('slow', 'moderate', 'fast').
    is_urban : bool
        Apply urban adjustment.
    is_palm : bool
        Use palm carbon fraction.

    Returns
    -------
    SequestrationResult
    """
    delta_d = GROWTH_RATE_MAP.get(growth_rate.lower().strip(), GROWTH_RATE_MAP["moderate"])

    c_now = calculate_carbon_storage(dbh_cm, height_m, coefficients, is_urban, is_palm)

    dbh_next = dbh_cm + delta_d
    # Estimate next year's height if we know current height
    height_next = None
    if height_m is not None and height_m > 0:
        # Simple proportional height growth
        height_next = height_m * (dbh_next / dbh_cm) ** 0.5

    c_next = calculate_carbon_storage(dbh_next, height_next, coefficients, is_urban, is_palm)

    sequestration = c_next - c_now
    was_capped = False

    # Apply cap for very large trees
    if c_now >= CARBON_STORAGE_CAP:
        max_seq = SEQUESTRATION_RATE_CAP * delta_d
        if sequestration > max_seq:
            sequestration = max_seq
            was_capped = True

    return SequestrationResult(
        dbh_start_cm=round(dbh_cm, 2),
        dbh_end_cm=round(dbh_next, 2),
        carbon_start_kg=round(c_now, 3),
        carbon_end_kg=round(c_next, 3),
        annual_sequestration_kg=round(max(sequestration, 0.0), 3),
        was_capped=was_capped,
    )


# ──────────────────────────────────────────────────────────────────────
# 5. STORMWATER INTERCEPTION
# ──────────────────────────────────────────────────────────────────────

def estimate_crown_width(dbh_cm: float, crown_modifier: Optional[float] = None) -> float:
    """Estimate crown width (m) from DBH using a tropical urban proxy.

    CW = CW_INTERCEPT + crown_modifier × DBH, capped at CW_MAX.
    """
    cw_slope = crown_modifier if crown_modifier is not None else CW_SLOPE
    cw = CW_INTERCEPT + cw_slope * max(dbh_cm, 0.0)
    return min(cw, CW_MAX_M)


def estimate_crown_area(dbh_cm: float, crown_modifier: Optional[float] = None) -> float:
    """Estimate crown projection area (m²) from DBH."""
    cw = estimate_crown_width(dbh_cm, crown_modifier)
    return math.pi * (cw / 2.0) ** 2


def estimate_leaf_area(dbh_cm: float, lai: float = DEFAULT_LAI, crown_modifier: Optional[float] = None) -> float:
    """Estimate total one-sided leaf area (m²).

    Leaf Area = Crown Area × LAI
    """
    return estimate_crown_area(dbh_cm, crown_modifier) * lai


def estimate_stormwater_interception(
    dbh_cm: float,
    lai: float = DEFAULT_LAI,
    rain_events: int = ANNUAL_RAIN_EVENTS,
    crown_modifier: Optional[float] = None,
) -> float:
    """Estimate annual avoided stormwater runoff (litres).

    Uses the simplified canopy storage proxy:
        Annual Interception = Crown Area × LAI × S_L × N_events × 1000
    """
    crown_area = estimate_crown_area(dbh_cm, crown_modifier)
    # Max canopy storage depth per event (m)
    storage_depth = lai * SPECIFIC_LEAF_STORAGE_M
    # Annual volume in m³
    annual_m3 = crown_area * storage_depth * rain_events
    # Convert to litres
    return round(annual_m3 * 1000.0, 1)


def estimate_stormwater_from_hourly(
    dbh_cm: float,
    hourly_rain_mm: List[float],
    lai: float = DEFAULT_LAI,
    min_event_mm: float = 1.0,
    crown_modifier: Optional[float] = None,
) -> float:
    """Estimate annual stormwater interception from hourly rainfall data.

    This is the **advanced mode** stormwater model.  Instead of using a
    fixed number of rain events, it processes each event individually,
    capping interception at the canopy storage capacity.

    Events are defined as contiguous hours with rainfall >= min_event_mm,
    separated by at least 6 dry hours (allowing canopy to dry).
    """
    crown_area = estimate_crown_area(dbh_cm, crown_modifier)
    # Max canopy storage capacity per event (m³)
    max_storage_m3 = crown_area * lai * SPECIFIC_LEAF_STORAGE_M

    total_intercepted_m3 = 0.0
    event_depth_mm = 0.0
    dry_hours = 0
    DRY_RESET_HOURS = 6  # hours of no rain before canopy is considered "dry"

    for mm in hourly_rain_mm:
        if mm >= min_event_mm:
            event_depth_mm += mm
            dry_hours = 0
        else:
            dry_hours += 1
            if dry_hours >= DRY_RESET_HOURS and event_depth_mm > 0:
                # End of event — compute interception
                event_depth_m = event_depth_mm / 1000.0
                event_supply_m3 = crown_area * event_depth_m
                intercepted = min(event_supply_m3, max_storage_m3)
                total_intercepted_m3 += intercepted
                event_depth_mm = 0.0

    # Handle trailing event at end of data
    if event_depth_mm > 0:
        event_depth_m = event_depth_mm / 1000.0
        event_supply_m3 = crown_area * event_depth_m
        intercepted = min(event_supply_m3, max_storage_m3)
        total_intercepted_m3 += intercepted

    return round(total_intercepted_m3 * 1000.0, 1)  # m³ → litres


def derive_rain_events(hourly_rain_mm: List[float], min_event_mm: float = 1.0) -> int:
    """Count the number of distinct rain events from hourly data.

    An event is a contiguous period of rainfall >= min_event_mm,
    separated by at least 6 dry hours.

    Parameters
    ----------
    hourly_rain_mm : list of float
        Hourly precipitation in mm.
    min_event_mm : float
        Minimum threshold to count as wet.

    Returns
    -------
    int
        Number of rain events.
    """
    events = 0
    in_event = False
    dry_hours = 0

    for mm in hourly_rain_mm:
        if mm >= min_event_mm:
            if not in_event:
                events += 1
                in_event = True
            dry_hours = 0
        else:
            dry_hours += 1
            if dry_hours >= 6:
                in_event = False

    return events


def derive_pollution_multiplier(
    pm25_ugm3: float = 12.0,
    no2_ugm3: float = 40.0,
    o3_ugm3: float = 100.0,
    so2_ugm3: float = 40.0,
) -> float:
    """Derive an aggregate pollution multiplier from measured concentrations.

    Computes the ratio of each measured concentration to the baseline
    (literature default) and returns the weighted mean.  Weights are
    proportional to the base removal rates.

    Parameters
    ----------
    pm25_ugm3, no2_ugm3, o3_ugm3, so2_ugm3 : float
        Measured annual mean ambient concentrations in µg/m³.

    Returns
    -------
    float
        Aggregate pollution multiplier (1.0 = baseline).
    """
    from itree_sea.config import BASELINE_CONCENTRATIONS, POLLUTION_RATES

    # Individual ratios
    r_pm25 = pm25_ugm3 / BASELINE_CONCENTRATIONS.pm25
    r_no2 = no2_ugm3 / BASELINE_CONCENTRATIONS.no2
    r_o3 = o3_ugm3 / BASELINE_CONCENTRATIONS.o3
    r_so2 = so2_ugm3 / BASELINE_CONCENTRATIONS.so2

    # Weight by base removal rate (more important pollutants weigh more)
    w = [POLLUTION_RATES.pm25, POLLUTION_RATES.no2,
         POLLUTION_RATES.o3, POLLUTION_RATES.so2]
    ratios = [r_pm25, r_no2, r_o3, r_so2]

    weighted_sum = sum(r * wt for r, wt in zip(ratios, w))
    total_weight = sum(w)

    return round(weighted_sum / total_weight, 3)


# ──────────────────────────────────────────────────────────────────────
# 6. AIR POLLUTION REMOVAL
# ──────────────────────────────────────────────────────────────────────

@dataclass
class PollutionResult:
    """Annual pollution removal for one tree."""
    pm25_g: float
    no2_g: float
    o3_g: float
    so2_g: float
    total_g: float
    leaf_area_m2: float


def estimate_pollution_removal(
    dbh_cm: float,
    lai: float = DEFAULT_LAI,
    pollution_multiplier: float = 1.0,
    crown_modifier: Optional[float] = None,
) -> PollutionResult:
    """Estimate annual air pollution removal (grams) using area-based proxy.

    Pollutant removed = Leaf Area (m²) × removal rate (g/m²/yr) × multiplier
    """
    la = estimate_leaf_area(dbh_cm, lai, crown_modifier)

    pm25 = la * POLLUTION_RATES.pm25 * pollution_multiplier
    no2 = la * POLLUTION_RATES.no2 * pollution_multiplier
    o3 = la * POLLUTION_RATES.o3 * pollution_multiplier
    so2 = la * POLLUTION_RATES.so2 * pollution_multiplier

    return PollutionResult(
        pm25_g=round(pm25, 2),
        no2_g=round(no2, 2),
        o3_g=round(o3, 2),
        so2_g=round(so2, 2),
        total_g=round(pm25 + no2 + o3 + so2, 2),
        leaf_area_m2=round(la, 2),
    )


# ──────────────────────────────────────────────────────────────────────
# 7. MULTI-YEAR GROWTH FORECAST
# ──────────────────────────────────────────────────────────────────────

def forecast_growth(
    initial_dbh_cm: float,
    coefficients: AllometricCoefficients,
    growth_rate: str = "moderate",
    years: int = 25,
    initial_height_m: Optional[float] = None,
    is_urban: bool = True,
    is_palm: bool = False,
    lai: float = DEFAULT_LAI,
    rain_events: int = ANNUAL_RAIN_EVENTS,
    pollution_multiplier: float = 1.0,
) -> List[ForecastRow]:
    """Project tree growth and ecosystem benefits over multiple years.

    Starting from ``initial_dbh_cm``, the function increments DBH by
    the annual growth rate each year, recalculates all benefits, and
    returns a list of ``ForecastRow`` objects suitable for export to CSV.

    Parameters
    ----------
    initial_dbh_cm : float
        Planting DBH or current DBH in cm.
    coefficients : AllometricCoefficients
        Resolved species coefficients.
    growth_rate : str
        Growth rate category.
    years : int
        Number of years to forecast.
    initial_height_m : float, optional
        Starting height; estimated if None.
    is_urban : bool
        Apply urban adjustment.
    is_palm : bool
        Use palm carbon fraction.
    lai : float
        Leaf Area Index.

    Returns
    -------
    list of ForecastRow
    """
    if is_palm:
        delta_d = 0.0
        delta_h = coefficients.palm_height_growth_m if hasattr(coefficients, "palm_height_growth_m") else DEFAULT_PALM_HEIGHT_GROWTH_M
    else:
        delta_d = coefficients.true_growth_rate_cm if hasattr(coefficients, "true_growth_rate_cm") else DEFAULT_TRUE_GROWTH_RATE_CM
        delta_h = 0.0

    # Resolve starting height
    if initial_height_m is None or initial_height_m <= 0:
        initial_height_m = estimate_height(
            initial_dbh_cm,
            coefficients.height_model_a,
            coefficients.height_model_b,
            coefficients.height_model_c,
            coefficients.height_model_form,
        )

    rows: List[ForecastRow] = []
    prev_carbon = 0.0

    # Resolve LAI scaled by site profile selection
    site_lai_factor = lai / DEFAULT_LAI
    spec_lai = coefficients.species_lai if hasattr(coefficients, "species_lai") else DEFAULT_SPECIES_LAI
    resolved_lai = spec_lai * site_lai_factor
    
    crown_modifier = coefficients.crown_modifier if hasattr(coefficients, "crown_modifier") else DEFAULT_CROWN_MODIFIER

    for yr in range(years + 1):
        if is_palm:
            dbh = initial_dbh_cm
            height = initial_height_m + delta_h * yr
        else:
            dbh = initial_dbh_cm + delta_d * yr
            # Height grows proportionally (power 0.5 — decelerating)
            if initial_dbh_cm > 0:
                height = initial_height_m * (dbh / initial_dbh_cm) ** 0.5
            else:
                height = estimate_height(
                    dbh,
                    coefficients.height_model_a,
                    coefficients.height_model_b,
                    coefficients.height_model_c,
                    coefficients.height_model_form,
                )

        # Biomass and carbon
        bio = calculate_biomass(
            dbh_cm=dbh,
            height_m=height,
            coefficients=coefficients,
            is_urban=is_urban,
            is_palm=is_palm,
            lai=lai,
            rain_events=rain_events,
            pollution_multiplier=pollution_multiplier,
        )

        # Sequestration (delta from previous year)
        seq = bio.carbon_storage_kg - prev_carbon if yr > 0 else 0.0

        # Cap check
        if prev_carbon >= CARBON_STORAGE_CAP:
            step_size = delta_h if is_palm else delta_d
            max_seq = SEQUESTRATION_RATE_CAP * (step_size if step_size > 0 else 1.0)
            seq = min(seq, max_seq)

        seq = max(seq, 0.0)
        prev_carbon = bio.carbon_storage_kg

        # Stormwater
        stormwater = estimate_stormwater_interception(dbh, resolved_lai, rain_events, crown_modifier)

        # Pollution
        pollution = estimate_pollution_removal(dbh, resolved_lai, pollution_multiplier, crown_modifier)

        # Convert seq back to CO2, O2, EPA
        co2_seq = seq * 3.6663
        o2_prod = seq * 2.6667
        epa_liters = (co2_seq / 1000.0) * 112.18 * 3.78541
        epa_km = (co2_seq / 1000.0) * 2564.0 * 1.60934

        rows.append(ForecastRow(
            year=yr,
            dbh_cm=round(dbh, 2),
            height_m=round(height, 2),
            agb_kg=bio.agb_kg,
            total_biomass_kg=bio.total_biomass_kg,
            carbon_storage_kg=bio.carbon_storage_kg,
            carbon_sequestration_kg=round(seq, 3),
            co2_storage_kg=bio.co2_storage_kg,
            co2_sequestration_kg=round(co2_seq, 2),
            o2_production_kg_yr=round(o2_prod, 2),
            epa_gasoline_liters_yr=round(epa_liters, 2),
            epa_km_driven_yr=round(epa_km, 2),
            stormwater_litres=stormwater,
            pm25_removed_g=pollution.pm25_g,
            no2_removed_g=pollution.no2_g,
            o3_removed_g=pollution.o3_g,
            so2_removed_g=pollution.so2_g,
        ))

    return rows
