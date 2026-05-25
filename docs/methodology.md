# i-Tree SEA — Methodology Documentation

> **Version:** 0.3.0-alpha · **Last updated:** May 2026
> **Engine reference:** i-Tree Eco v6.0.22+ methods, adapted for Southeast Asian tropical urban forestry

---

## 1. Overview

i-Tree SEA is an open-source adaptation of the [USDA Forest Service i-Tree](https://www.itreetools.org) methodology, specifically calibrated for tropical urban forestry in Southeast Asia. It estimates ecosystem services provided by individual trees using allometric equations, growth models, and environmental proxy calculations.

### Ecosystem services quantified

| Service | Unit | Method |
| Carbon storage | kg C | Allometric biomass → carbon conversion |
| Carbon sequestration | kg C/yr | Annual delta-storage |
| CO₂ Equivalent | kg CO₂ | IPCC stoichiometric ratio (3.6663) |
| Oxygen production | kg O₂/yr | Photosynthetic stoichiometry (2.6667) |
| EPA Equivalencies | liters/km | US EPA GHG Equivalencies Calculator |
| Stormwater interception | L/yr | Canopy storage proxy |
| Air pollution removal (PM2.5, NO₂, O₃, SO₂) | g/yr | Leaf-area deposition proxy |

### Scope & limitations

- **Design-phase tool:** intended for landscape architects evaluating planting plans, not for post-hoc forest inventory
- **Individual-tree resolution:** no stand-level competition or mortality modelling
- **Tropical focus:** constants calibrated for equatorial lowland SE Asia (Köppen Af/Am)
- Does **not** include energy savings, property value, or UV shading benefits

---

## 2. Carbon Storage

### 2.1 Aboveground Biomass (AGB)

We implement two equation forms from the i-Tree Eco methodology:

#### Primary: Chave et al. (2014) pantropical model

When tree height is available:

```
AGB = 0.0673 × (ρ × D² × H)^0.976
```

| Symbol | Meaning | Unit |
|--------|---------|------|
| AGB | Aboveground dry-weight biomass | kg |
| ρ | Wood specific gravity | g/cm³ |
| D | Diameter at breast height | cm |
| H | Total tree height | m |

> **Source:** Chave, J., et al. (2014). "Improved allometric models to estimate the aboveground biomass of tropical trees." *Global Change Biology*, 20(10), 3177–3190.

#### Alternative: no-height equation

When height is unmeasured (typical for design-phase planting plans):

```
ln(AGB) = -1.803 + (-0.976)·E + 0.976·ln(ρ) + 2.673·ln(D) + (-0.0299)·[ln(D)]²
```

| Symbol | Value | Source |
|--------|-------|--------|
| E | -0.070 | Bioclimatic stress for equatorial SE Asia (Chave 2014, Table S3) |

#### Secondary: Ketterings et al. (2001) secondary forest model

For specific species adapted to or regenerating in secondary forests in Indonesia (e.g., *Trema orientalis*, *Macaranga* spp.), the power-law equation derived by Ketterings et al. is used:

```
AGB = a × ρ × D^b
```

| Symbol | Default Value | Source |
|--------|-------|--------|
| a | 0.11 | Ketterings et al. (2001) |
| b | 2.62 | Ketterings et al. (2001) |

> **Source:** Ketterings, Q.M., et al. (2001). "Reducing uncertainty in the use of allometric biomass equations for predicting above-ground tree biomass in mixed secondary forests." *Forest Ecology and Management*, 146(1-3), 199-209.

#### Palm cylindrical stem model (monocots)

For palm species (monocots where `is_palm = 1`), standard dicot allometric equations (like Chave 2014) are biologically inappropriate because palm trunks are cylindrical, do not experience secondary lateral growth (DBH expansion) after establishment, and do not taper like standard dicots.

Aboveground dry-weight biomass (AGB) is calculated using a cylindrical stem volume formula:

$$AGB_{\text{palm}} = 0.07854 \times \rho \times D^2 \times H$$

Where:
- $AGB$: Aboveground dry-weight biomass (kg)
- $\rho$: Wood specific gravity / specific gravity (g/cm³)
- $D$: Diameter at breast height (cm)
- $H$: Tree height (m)

*Derivation:*
The volume of a cylinder is $V = \pi \times (\frac{D}{200})^2 \times H = \frac{\pi}{40000} \times D^2 \times H$ (m³). Converting volume to dry weight using density $\rho \times 1000$ (kg/m³) gives:
$$AGB = \frac{\pi}{40000} \times 1000 \times \rho \times D^2 \times H \approx 0.07854 \times \rho \times D^2 \times H$$

> **Sources:**
> - Frangi, J. L., & Lugo, A. E. (1985). "Ecosystem dynamics of a subtropical floodplain forest." *Ecological Monographs*, 55(3), 351-369.
> - Goodman, R. C., et al. (2013). "Amazon palm biomass templates." *Forest Ecology and Management*, 291, 230-237.
> - Nowak, D. J. (2020). "i-Tree Eco Palm Biomass Estimation." USDA Forest Service.

#### Morphology-driven Woody & Foliage model (dicots)

For standard dicot trees, aboveground biomass is refined by separating woody biomass and foliage biomass components based on morphological properties:

$$\text{AGB} = \text{Woody}_{\text{adjusted}} + \text{Foliage}$$

Where:
1. **Woody component:** Separated from standard Chave baseline biomass using the standard foliage fraction:
   $$\text{Woody}_{\text{base}} = \text{AGB}_{\text{Chave\_Base}} \times (1 - \text{DEFAULT\_FOLIAGE\_FRACTION})$$
   $$\text{Woody}_{\text{adjusted}} = \text{Woody}_{\text{base}} \times f_{\text{trunk}} \times f_{\text{crown}}$$
   - $f_{\text{trunk}}$: Trunk type multiplier (e.g. Standard = `1.0`, Buttressed = `1.15`, Multi-stemmed = `0.85`).
   - $f_{\text{crown}}$: Crown shape multiplier based on the crown modifier $k_{cw}$ (Columnar = `0.80`, Conical = `0.90`, Spherical = `1.00`, Spreading = `1.15`).

2. **Foliage component:** Explicitly computed based on species-specific Leaf Area Index (LAI) and leaf shape Specific Leaf Weight (SLW):
   $$\text{Foliage} = \text{Crown\_Area} \times \text{LAI}_{\text{species}} \times \text{SLW}$$
   - $\text{Crown\_Area} = \pi \times \left(\frac{CW}{2}\right)^2$ (m²)
   - $CW = 0.6 + k_{cw} \times DBH$ (m)
   - $\text{LAI}_{\text{species}}$: Leaf Area Index of the species (default = `5.0`).
   - $\text{SLW}$: Specific Leaf Weight (kg/m²), determined by leaf shape (Simple = `0.12`, Compound = `0.09`, Needle = `0.22`, Palm Fan = `0.32`).

> **Sources:**
> - Nowak, D. J. (1996). "Estimating leaf area and leaf biomass of individual open-grown deciduous trees." *Forest Science*, 42(3), 270-275.
> - Peper, P. J., & McPherson, E. G. (2003). "Evaluation of four methods for estimating leaf area of isolated trees." *Urban Forestry & Urban Greening*, 2(1), 19-29.
> - Asner, G. P., et al. (2003). "Global synthesis of leaf area index observations." *Global Ecology and Biogeography*, 12(3), 191-205.

#### Tropical climate-specific equations (Chave et al. 2005)

i-Tree Eco v6.0.22 introduced climate-specific tropical equations based on Chave et al. (2005). Three variants exist:

| Climate | Precip. | Equation |
|---------|---------|----------|
| **Moist** (default for SEA) | 1500–3500 mm/yr | `AGB = ρ × exp(-1.499 + 2.148·ln(D) + 0.207·[ln(D)]² - 0.0281·[ln(D)]³)` |
| Wet | >3500 mm/yr | `AGB = ρ × exp(-1.239 + 1.980·ln(D) + 0.207·[ln(D)]² - 0.0281·[ln(D)]³)` |
| Dry | <1500 mm/yr | `AGB = ρ × exp(-0.667 + 1.784·ln(D) + 0.207·[ln(D)]² - 0.0281·[ln(D)]³)` |

> **Current implementation:** i-Tree SEA uses the Chave 2014 pantropical model as default, which supersedes and generalises the 2005 climate-split approach. The 2014 model incorporates the bioclimatic stress variable *E* to account for climate without requiring manual zone classification.
>
> **Status:** ✅ Aligned with i-Tree Eco v6.0.22 methodology.

### 2.2 Wood Density Weighting (i-Tree 2021 update)

i-Tree Eco v6.0.22 introduced a wood density weighting process when using cross-species equations:

```
C_est = C_eq × (WD_spp / WD_eq)
```

| Symbol | Meaning |
|--------|---------|
| C_est | Adjusted carbon estimate |
| C_eq | Carbon from equation (generic or genus-level) |
| WD_spp | Wood density of the actual species being measured |
| WD_eq | Average wood density from the species the equation was built on |

> **Current implementation:** i-Tree SEA uses species-specific wood densities from the Global Wood Density Database (Chave 2009, Zanne 2009) stored in `seed_species.csv`. Since we apply species-specific ρ directly into the Chave 2014 equation, the WD ratio adjustment is **implicitly handled** — the equation already takes ρ as a direct input.
>
> **Status:** ✅ Functionally equivalent. The Chave 2014 primary form directly uses species ρ, achieving the same outcome as i-Tree's post-hoc WD weighting.

### 2.3 Belowground Biomass (BGB)

```
BGB = AGB × 0.26
```

> **Source:** Cairns, M.A., et al. (1997). "Root biomass allocation in the world's upland forests." *Oecologia*, 111, 1–11.
>
> **Status:** ✅ Matches i-Tree Eco.

### 2.4 Carbon Conversion

```
Carbon (kg) = Total Biomass × Carbon Fraction
```

| Tree type | Carbon fraction | Source |
|-----------|----------------|--------|
| General (dicots) | 0.50 | IPCC 2006; i-Tree Eco |
| Palms (monocots) | 0.41 | i-Tree Eco palm override |

### 2.5 Urban Adjustment

```
AGB_urban = AGB_forest × 0.80
```

Open-grown urban trees have different architecture than forest-grown trees of the same DBH. i-Tree Eco applies a 0.80 reduction factor (Nowak 1994).

> **Implementation note:** This is applied unconditionally in design-phase estimates. i-Tree Eco applies it conditionally based on crown light exposure (CLE ≥ 4), which requires field measurement.
>
> **Status:** ⚠️ Simplified — we apply 0.80 to all trees. i-Tree Eco's CLE-conditional approach is more precise but requires field data unavailable at design phase.

### 2.6 Condition Adjustment

Tree condition reduces effective biomass:

| Condition | Multiplier |
|-----------|-----------|
| Excellent | 1.00 |
| Good | 0.95 |
| Fair | 0.80 |
| Poor | 0.55 |
| Critical | 0.30 |
| Dead | 0.00 |

> **Source:** i-Tree Eco condition classes.
> **Status:** ✅ Matches i-Tree Eco.

---

## 3. Carbon Sequestration

### 3.1 Delta-storage method

Annual gross sequestration is calculated as the change in carbon storage over one year of growth:

```
Sequestration = C_storage(DBH + ΔD) − C_storage(DBH)
```

Where ΔD is the annual DBH increment:

| Growth rate | ΔD (cm/yr) | Source |
|-------------|-----------|--------|
| Slow | 0.50 | Adapted from i-Tree Eco; NParks growth data |
| Moderate | 1.00 | i-Tree Eco default |
| Fast | 1.75 | Adapted for tropical fast-growers |

> **Note:** i-Tree Eco uses field-measured growth rates when available. Our design-phase proxy assigns rates by species growth class from the database.

### 3.2 Large-tree cap

When carbon storage exceeds **7,500 kg**, the sequestration rate is capped at **40 kg per cm of DBH growth**. This prevents unrealistic estimates for very large trees.

> **Source:** i-Tree Eco internal rule.
> **Status:** ✅ Implemented.

### 3.3 Net sequestration (not implemented)

i-Tree Eco calculates **net** sequestration by subtracting estimated carbon release from tree mortality and decomposition. This requires:
- Plot-based mortality rate estimates
- Decomposition time constants

> **Status:** ❌ Not implemented. i-Tree SEA reports **gross** sequestration only. For design-phase planting plans, mortality is typically excluded since trees are newly planted and assumed healthy.

---

## 4. Carbon Dioxide (CO₂) and Oxygen (O₂)

### 4.1 CO₂ Equivalent
To convert elemental carbon storage or sequestration into carbon dioxide equivalent (CO₂e), we use the standard IPCC stoichiometric ratio based on atomic weights (CO₂ = 44, C = 12, ratio = 44/12 ≈ 3.6663).

```
CO₂ Equivalent (kg) = Carbon (kg) × 3.6663
```

> **Source:** IPCC Guidelines for National Greenhouse Gas Inventories.
> **Status:** ✅ Implemented.

### 4.2 Oxygen Production
Oxygen production is directly tied to carbon sequestration through the process of photosynthesis: 
`6CO₂ + 6H₂O → C₆H₁₂O₆ + 6O₂`. 
For every molecule of carbon fixed into biomass, a proportional mass of oxygen is released. The stoichiometric ratio is the atomic weight of O₂ (32) divided by C (12) ≈ 2.6667.

```
Annual Oxygen Production (kg/yr) = Net Carbon Sequestration (kg/yr) × 2.6667
```

> **Source:** Nowak, D.J., et al. (2007). "Oxygen production by urban trees in the United States." *Arboriculture & Urban Forestry*.
> **Status:** ✅ Implemented.

---

## 5. Environmental Equivalencies (Metric Conversions)

To make carbon sequestration metrics more understandable to non-technical stakeholders, the tool converts annual CO₂ sequestration into tangible equivalencies using the US EPA Greenhouse Gas Equivalencies Calculator, converted to metric units, and supplementary local factors.

```
Liters of Gasoline Saved = (Annual CO₂ Sequestration in Metric Tons) × 112.18 × 3.78541 ≈ (Annual CO₂ Sequestration in Metric Tons) × 424.65
Kilometers Driven Avoided = (Annual CO₂ Sequestration in Metric Tons) × 2564.0 × 1.60934 ≈ (Annual CO₂ Sequestration in Metric Tons) × 4126.36
Kilometers of Motorcycle Travel Avoided = (Annual CO₂ Sequestration in kg) × 20.0
Smartphones Charged = (Annual CO₂ Sequestration in kg) × 80.645
```

- **Motorcycle factor (20.0 km/kg CO₂)** is based on average emissions of 0.05 kg CO₂/km for small-displacement motorcycles common in Southeast Asia.
- **Smartphones Charged factor (80.645 charges/kg CO₂)** matches the US EPA factor of 80,645 charges per metric ton of CO₂ (approx. 0.0124 kg CO₂ per charge).

> **Source:** US Environmental Protection Agency (EPA) GHG Equivalencies Calculator and regional transport emission databases.
> **Status:** ✅ Implemented (converted to metric: 1 gallon ≈ 3.78541 L; 1 mile ≈ 1.60934 km; added regional specific proxies).

---

## 6. Height Estimation

When height is not measured (common for planting plans), we estimate height from DBH using a power-law model:

```
H = a × D^b
```

| Parameter | Default value | Source |
|-----------|--------------|--------|
| a | 0.893 | Feldpausch et al. (2012) — SE Asian tropical moist |
| b | 0.760 | Feldpausch et al. (2012) |

Species-specific height parameters are stored in the database and override these defaults when available.

> **Status:** ✅ Appropriate for design-phase. i-Tree Eco measures height directly; we estimate it.

---

## 7. Stormwater Interception

### 5.1 Model approach

i-Tree Eco uses a full hydrological water-balance model (Wang et al. 2008, Hirabayashi 2013) requiring hourly precipitation data and comparing tree-present vs tree-absent runoff scenarios.

i-Tree SEA uses a **simplified proxy** that estimates annual canopy interception volume:

```
Annual Interception (L) = Crown Area × LAI × S_L × N_events × 1000
```

| Parameter | Value | Source |
|-----------|-------|--------|
| Crown Area | `π × (CW/2)²` where `CW = 0.6 + 0.15 × DBH` (max 20m) | Peper et al. (2001), adapted |
| LAI | 5.0 | Asner et al. (2003), tropical broadleaf |
| S_L (specific leaf storage) | 0.0002 m (0.2 mm) | i-Tree Hydro (Wang et al. 2008) |
| N_events | 180 rain events/yr | Singapore Met Service |

### 5.2 Comparison to i-Tree Eco

| Aspect | i-Tree Eco | i-Tree SEA |
|--------|-----------|-----------|
| Temporal resolution | Hourly | Annual proxy |
| Rainfall data | Hourly gauge data | Average event count |
| Ground surface | Pervious/impervious split | Not modelled |
| Throughfall | Modelled | Not modelled |
| Depression storage | Modelled | Not modelled |

> **Status:** ⚠️ Simplified proxy. Suitable for comparative ranking between planting options, not for absolute hydrological modelling. For detailed stormwater analysis, use i-Tree Hydro+ or a dedicated model.

### 5.3 Site Profiles

Rather than exposing raw environmental parameters to users, i-Tree SEA bundles rainfall, pollution concentration, and LAI into **Site Profiles** — pre-configured environmental contexts based on land use type. This makes the tool accessible to landscape architects who may not have meteorological data.

| Profile | Rain Events/yr | Pollution Multiplier | LAI | Rationale |
|---------|---------------|---------------------|-----|-----------|
| **Urban Dense (CBD / Roadside)** | 180 | 1.50× | 4.0 | High ambient pollution near traffic; reduced canopy density |
| **Urban Park / Campus** | 180 | 1.00× (baseline) | 5.0 | Literature-standard tropical broadleaf defaults |
| **Suburban / Residential** | 180 | 0.75× | 5.0 | Lower ambient pollution in residential areas |
| **Industrial / Port Area** | 170 | 2.00× | 3.5 | Very high pollution; sparse canopy; fewer rain events |
| **Coastal / Waterfront** | 170 | 0.60× | 4.5 | Clean marine air; wind-pruned canopy |
| **Peri-Urban / Rural Edge** | 190 | 0.40× | 6.0 | Low pollution; dense canopy potential; more rain events |

The **pollution multiplier** scales the base removal rates (Nowak et al. 2006) to reflect ambient pollutant concentrations. Higher concentrations mean more pollutant available for dry deposition, up to the deposition velocity limit. Values are calibrated against WHO and IQAir city air quality data for Southeast Asian urban areas.

> **Note:** Users select one site profile in the dashboard sidebar before running calculations. The selected profile applies uniformly to all trees in the analysis.

### 5.4 Custom / Advanced Mode

For projects with site-specific environmental data, i-Tree SEA offers a **Custom / Advanced** profile that replaces the preset values with user-supplied measurements:

#### Hourly Rainfall Upload

Users can upload a CSV of hourly rainfall data (mm). The engine:
1. Identifies discrete rain events (contiguous wet hours separated by ≥6 dry hours, following WMO conventions).
2. For each event, caps canopy interception at the tree's maximum storage capacity (`Crown Area × LAI × S_L`).
3. Light events are fully intercepted; heavy events overflow — this is more accurate than the simple proxy.

**CSV format:** Single column, one value per row, no header required (or header `rain_mm`). 8760 rows = 1 year of hourly data. Data sources include national meteorological services (BMKG for Indonesia, MSS for Singapore) or ECMWF ERA5 reanalysis.

#### Ambient Pollution Concentrations

Users enter measured annual mean ambient concentrations for PM2.5, NO₂, O₃, and SO₂ in µg/m³. The engine derives a weighted pollution multiplier:

```
multiplier = Σ(measured_i / baseline_i × weight_i) / Σ(weight_i)
```

Where baselines are the concentrations assumed by Nowak et al. (2006), and weights are the base removal rates. This ensures that pollutants with higher removal potential contribute proportionally more to the aggregate multiplier.

| Pollutant | Baseline (µg/m³) | Source |
|-----------|-----------------|--------|
| PM2.5 | 12.0 | US EPA NAAQS annual standard |
| NO₂ | 40.0 | WHO guideline annual mean |
| O₃ | 100.0 | WHO guideline 8-hr mean |
| SO₂ | 40.0 | WHO guideline 24-hr |

#### Custom LAI

Users can adjust the Leaf Area Index to match site-specific canopy conditions (e.g., 3.0–4.0 for coastal wind-pruned trees, 6.0–8.0 for dense secondary forest).

---

## 8. Air Pollution Removal

### 6.1 Model approach

i-Tree Eco uses an hourly dry deposition model that combines:
- Local air pollution concentration data
- Deposition velocity (species-dependent)
- Leaf area
- Meteorological conditions (wind, boundary layer height)

i-Tree SEA uses **annual proxy rates** (g/m² leaf area/yr):

| Pollutant | Rate (g/m²/yr) | Source |
|-----------|---------------|--------|
| PM2.5 | 0.50 | Chen et al. (2017), tropical analog |
| NO₂ | 0.90 | Nowak et al. (2006), i-Tree Eco default |
| O₃ | 1.40 | Nowak et al. (2006), i-Tree Eco default |
| SO₂ | 0.35 | Nowak et al. (2006), i-Tree Eco default |

```
Pollutant removed (g/yr) = Leaf Area (m²) × Rate (g/m²/yr)
```

> **Status:** ⚠️ Simplified proxy. Uses literature-median removal rates instead of hourly deposition modelling. Provides order-of-magnitude estimates for design comparison.

---

## 9. Species Database

### 7.1 Data sources

| Source | Data used | Count |
|--------|----------|-------|
| Global Wood Density Database (Chave 2009, Zanne 2009) | Wood density (ρ) | All species |
| ICRAF World Agroforestry wood density | Tropical species ρ | Supplementary |
| NParks Singapore tree database | Species list, growth rates | 15 species |
| McPherson et al. (2016) Urban Tree Database | Allometric validation | Reference |
| GlobAllomeTree (2017) | Additional equation forms | Reference |

### 7.2 Species resolution fallback

When looking up allometric coefficients, the engine follows a 3-tier fallback:

```
1. Species-level match  →  exact scientific name
2. Genus-level match    →  same genus, averaged coefficients
3. Pantropical default  →  Chave 2014 with default ρ = 0.58 g/cm³
```

> **Status:** ✅ Matches i-Tree Eco's resolution strategy (species → genus → family → hardwood/conifer default).

### 7.3 Current species count

**85 species** in the database, covering:
- NParks Singapore common urban trees
- Indonesian landscape species (Dinas Pertamanan)
- SE Asian fruit trees, palms, and native species
- Common pantropical ornamentals

---

## 10. Multi-Year Growth Forecast

### 8.1 Method

Users can customize the forecast horizon from **1 to 100 years**, allowing for both short-term tracking and long-term ecosystem service modeling. The engine tracks the absolute growth (ΔDBH and ΔHeight) alongside the derived benefits.

Starting from a baseline DBH and height, growth projections are split by tree type:

**For Dicot Trees (Standard Deciduous/Evergreen):**
```
For each year 1..N:
    DBH(t) = DBH(t-1) + true_growth_rate_cm
    Height(t) = Height(0) * [DBH(t) / DBH(0)]^0.5
    Biomass(t) = calculate_biomass(DBH(t), Height(t), coefficients, is_palm=False)
```

**For Monocot Trees (Palms):**
```
For each year 1..N:
    DBH(t) = DBH(0)   (constant stem thickness)
    Height(t) = Height(t-1) + palm_height_growth_m
    Biomass(t) = calculate_biomass(DBH(t), Height(t), coefficients, is_palm=True)
```

For all trees, ecosystem services are computed dynamically at each time step `t` using:
```
    Sequestration(t) = Carbon(t) - Carbon(t-1)
    Stormwater(t) = estimate_stormwater_interception(DBH(t), resolved_lai, rain_events, crown_modifier)
    Pollution(t) = estimate_pollution_removal(DBH(t), resolved_lai, pollution_multiplier, crown_modifier)
```

### 8.2 Height estimation and growth model

If tree height is not provided in the CAD or field data, i-Tree SEA estimates it from DBH using the **Feldpausch et al. (2012)** pantropical models. The engine supports two equation forms:

1. **Power-law (fallback):** $H = a \times D^b$
2. **Weibull (preferred):** $H = a \times (1 - e^{-b \times D^c})$

The Weibull model is more accurate for mature trees because it captures the biological height asymptote (maximum height). By default, the system uses the Feldpausch 3-parameter Weibull regional coefficients for Southeast Asia ($a=57.122, b=0.0332, c=0.8468$). Users can override this with species-specific coefficients via `seed_species.csv`.

Over time, height grows as a function of the forecasted DBH, recalculating the height estimate dynamically as the tree expands.

> **Status:** ✅ High fidelity. i-Tree Eco uses species-specific height growth curves. The integration of the Feldpausch Weibull model provides comparable accuracy for tropical contexts where regional curves are unavailable.

---

## 11. Differences from i-Tree Eco

### Summary comparison table

| Feature | i-Tree Eco | i-Tree SEA | Impact |
|---------|-----------|-----------|--------|
| AGB equation | Species-specific + Chave 2014 | Chave 2014 pantropical & Ketterings 2001 | Low — Adds regional specificity for Indonesia |
| Wood density weighting | Post-hoc WD ratio | Direct ρ in equation | None — functionally equivalent |
| Height | Field-measured | Weibull estimation (Feldpausch 2012) | Low — Weibull model accurately captures tropical height asymptotes |
| Growth rate | Field/regional tables | Categorical (slow/mod/fast) | Low — appropriate for forecasting |
| Urban adjustment | CLE-conditional (0.80) | Always 0.80 | Low — conservative |
| Stormwater | Hourly water balance | Annual proxy + site profiles / hourly upload | Low — Advanced mode runs hourly event interception capping |
| Pollution | Hourly deposition model | Annual proxy × site / hourly concentration multiplier | Low — Advanced mode scales removal rates using measured concentrations |
| Mortality | Yes (net sequestration) | No (gross only) | Moderate — gross is standard for planting plans |
| Energy savings | Yes | No | Not in scope |
| CO₂ & O₂ equivalents | Yes | Yes (IPCC & Nowak 2007) | None — identical stoichiometric method |
| EPA Equivalencies | No (US specific reports only) | Yes (Gasoline, Kilometers Driven) | High — improves public communication |

---

## 12. References

### Primary allometric models

1. **Chave, J., et al. (2014).** "Improved allometric models to estimate the aboveground biomass of tropical trees." *Global Change Biology*, 20(10), 3177–3190. — Primary AGB equation.
2. **Chave, J., et al. (2005).** "Tree allometry and improved estimation of carbon stocks and balance in tropical forests." *Oecologia*, 145, 87–99. — Climate-specific tropical equations (i-Tree Eco v6.0.22).
3. **Cairns, M.A., et al. (1997).** "Root biomass allocation in the world's upland forests." *Oecologia*, 111, 1–11. — Root-to-shoot ratio.
4. **Feldpausch, T.R., et al. (2012).** "Tree height integrated into pantropical forest biomass estimates." *Biogeosciences*, 9, 3381–3403. — Height estimation.

### i-Tree methods

5. **Nowak, D.J. (2023).** "Understanding i-Tree: 2023 Summary of Programs and Methods." USDA Forest Service. — [PDF](https://www.itreetools.org/documents/1099/UnderstandingiTree2023.pdf)
6. **i-Tree (2021).** "New Carbon Equations and Methods." — [Webpage](https://www.itreetools.org/support/resources-overview/i-tree-methods-and-files/new-carbon-equations-and-methods-2020)
7. **i-Tree (2021).** "Tropical Carbon Equations." — [Webpage](https://www.itreetools.org/support/resources-overview/i-tree-methods-and-files/i-tree-eco-tropical-carbon-equations)
8. **i-Tree (2016).** "Pollutant Removal, Biogenic Emissions and Hydrologic Processes." — [PDF](http://www.itreetools.org/landscape/resources/Air_Pollutant_Removals_Biogenic_Emissions_and_Hydrologic_Estimates_for_iTree_v6_Applications.pdf)

### Wood density & species data

9. **Chave, J., et al. (2009).** "Towards a worldwide wood economics spectrum." *Ecology Letters*, 12(4), 351–366.
10. **Zanne, A.E., et al. (2009).** "Global Wood Density Database." *Dryad Digital Repository*.
11. **McPherson, E.G., et al. (2016).** "Urban Tree Database and Allometric Equations." Gen. Tech. Rep. PSW-GTR-235, USDA FS.

### Hydrology & pollution

12. **Wang, J., et al. (2008).** "A Numerical Model for Flow and Pollution Transport in a 2D Urban Stormwater Drainage System." — i-Tree Hydro foundation.
13. **Hirabayashi, S. (2013).** "i-Tree Eco Precipitation Interception Model." — Updated hydrology model.
14. **Nowak, D.J., et al. (2006).** "Air pollution removal by urban trees and shrubs in the United States." *Urban Forestry & Urban Greening*, 4(3–4), 115–123.

### Growth & urban forestry

15. **Nowak, D.J. (1994).** "Atmospheric Carbon Dioxide Reduction by Chicago's Urban Forest." — Urban adjustment factor.
16. **Pretzsch, H. (2009).** "Forest Dynamics, Growth and Yield." Springer. — Growth rate calibration.
17. **Asner, G.P., et al. (2003).** "Global synthesis of leaf area index observations." *Global Ecology and Biogeography*, 12, 191–205. — LAI defaults.
18. **Peper, P.J., et al. (2001).** "Tree size facts." Center for Urban Forest Research, USDA FS. — Crown width estimation.
19. **Ketterings, Q.M., et al. (2001).** "Reducing uncertainty in the use of allometric biomass equations for predicting above-ground tree biomass in mixed secondary forests." *Forest Ecology and Management*, 146(1-3), 199-209.
20. **Nowak, D.J., et al. (2007).** "Oxygen production by urban trees in the United States." *Arboriculture & Urban Forestry*.
21. **US Environmental Protection Agency (EPA).** "Greenhouse Gas Equivalencies Calculator."

---

## Appendix A: Constants Reference

| Constant | Value | Unit | Source |
|----------|-------|------|--------|
| CHAVE_A | 0.0673 | — | Chave 2014 |
| CHAVE_B | 0.976 | — | Chave 2014 |
| BIOCLIMATIC_E | -0.070 | — | Chave 2014, Table S3 |
| ROOT_SHOOT_RATIO | 0.26 | — | Cairns 1997 |
| URBAN_ADJUSTMENT | 0.80 | — | Nowak 1994 |
| CARBON_FRACTION | 0.50 / 0.41 (palm) | — | IPCC 2006 |
| CARBON_STORAGE_CAP | 7,500 | kg C | i-Tree Eco |
| SEQUESTRATION_RATE_CAP | 40 | kg C/cm | i-Tree Eco |
| DEFAULT_WOOD_DENSITY | 0.58 | g/cm³ | Chave 2009 |
| DEFAULT_LAI | 5.0 | m²/m² | Asner 2003 |
| SPECIFIC_LEAF_STORAGE | 0.0002 | m | Wang 2008 |
| ANNUAL_RAIN_EVENTS | 180 | events/yr | Singapore Met |
| CW_INTERCEPT | 0.6 | m | Peper 2001 |
| CW_SLOPE | 0.15 | m/cm | Peper 2001 |
| CW_MAX | 20.0 | m | Capped |
| HEIGHT_A | 0.893 | — | Feldpausch 2012 |
| HEIGHT_B | 0.760 | — | Feldpausch 2012 |
