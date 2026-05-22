# Mathematical Specification — i-Tree SEA

> This document formalises all equations used by the i-Tree SEA engine.  
> Every constant is traceable to a peer-reviewed source.

---

## 1. Aboveground Biomass (AGB)

### 1.1 Primary Equation (with height)

Source: **Chave et al. (2014)** — pantropical allometric model, calibrated on 4,004 trees.

```
AGB = 0.0673 × (ρ × D² × H)^0.976
```

| Symbol | Unit   | Description                              |
|--------|--------|------------------------------------------|
| AGB    | kg     | Oven-dry aboveground biomass             |
| ρ      | g/cm³  | Basic wood specific gravity              |
| D      | cm     | Diameter at breast height (1.3 m above ground) |
| H      | m      | Total tree height                        |

### 1.2 Alternative Equation (height unavailable)

When H is not measured, height is replaced by a bioclimatic stress variable E:

```
ln(AGB) = −1.803 − 0.976·E + 0.976·ln(ρ) + 2.673·ln(D) − 0.0299·[ln(D)]²
```

For **Singapore/Indonesia equatorial lowland**: E ≈ **−0.070**  
(low temperature seasonality, high precipitation, minimal drought)

---

## 2. Height Estimation (when field data is unavailable)

Source: **Feldpausch et al. (2012)** — SE Asian tropical moist forest regional model.

```
H = a × D^b
```

Default: a = 0.893, b = 0.760

---

## 3. Belowground Biomass

Source: **Cairns et al. (1997)** — root-to-shoot ratio meta-analysis.

```
BGB = AGB × 0.26
Total Biomass = AGB × 1.26
```

---

## 4. Urban Open-Grown Adjustment

Source: **Nowak (1994)**, applied in i-Tree Eco v6.

```
AGB_urban = AGB_forest × 0.80
```

Rationale: Open-canopy urban trees have less wood volume per unit DBH than forest-grown counterparts.

---

## 5. Carbon Storage

Source: **IPCC (2006)** default; used by i-Tree Eco.

```
C_storage = Total Biomass × 0.50    (general trees)
C_storage = Total Biomass × 0.41    (palms — lower lignin content)
```

---

## 6. Annual Carbon Sequestration

Source: **i-Tree Eco v6** — delta-storage method.

```
C_seq = C_storage(DBH + ΔD) − C_storage(DBH)
```

Where ΔD is the annual DBH growth increment:

| Growth Rate | ΔD (cm/yr) | Example genera                     |
|-------------|------------|------------------------------------|
| Slow        | 0.50       | Diospyros, Fagraea, Mimusops       |
| Moderate    | 1.00       | Pterocarpus, Terminalia, Syzygium   |
| Fast        | 1.75       | Falcataria, Ficus, Samanea          |

### Cap Rule (large trees)

When C_storage ≥ 7,500 kg:

```
C_seq_max = 40 kg/cm × ΔD
```

---

## 7. Stormwater Interception (Simplified Proxy)

Bypasses hourly weather processing by using annual area-based constants.

```
Annual Interception (L) = Crown Area (m²) × LAI × S_L × N_events × 1000
```

| Parameter   | Value   | Source                                       |
|-------------|---------|----------------------------------------------|
| S_L         | 0.0002 m| Specific leaf storage (i-Tree Hydro)         |
| LAI         | 5.0     | Asner et al. (2003) tropical broadleaf       |
| N_events    | 180     | Singapore Met Service (~180 rain days/yr)    |

### Crown Width from DBH

```
CW (m) = 0.6 + 0.15 × DBH (cm)     [capped at 20 m]
Crown Area = π × (CW / 2)²
```

---

## 8. Air Pollution Removal (Simplified Proxy)

Bypasses hourly meteorological/concentration data with annual area-based deposition rates.

```
Pollutant Removed (g/yr) = Leaf Area (m²) × Rate (g/m²/yr)
Leaf Area = Crown Area × LAI
```

| Pollutant | Rate (g/m²/yr) | Source                              |
|-----------|----------------|-------------------------------------|
| PM2.5     | 0.50           | Chen et al. (2017) tropical analog  |
| NO₂       | 0.90           | Nowak et al. (2006) i-Tree default  |
| O₃        | 1.40           | Nowak et al. (2006) i-Tree default  |
| SO₂       | 0.35           | Nowak et al. (2006) i-Tree default  |

---

## 9. Condition Adjustment

Source: **i-Tree Eco** — condition classes.

| Condition  | Multiplier | Description                         |
|------------|------------|-------------------------------------|
| Excellent  | 1.00       | Full canopy, no defects             |
| Good       | 0.95       | Minor issues                        |
| Fair       | 0.80       | Moderate dieback                    |
| Poor       | 0.55       | Significant decline                 |
| Critical   | 0.30       | Near dead                           |
| Dead       | 0.00       | Standing dead (carbon stock only)   |

---

## References

1. Chave, J., et al. (2014). Improved allometric models to estimate the aboveground biomass of tropical trees. *Global Change Biology*, 20(10), 3177–3190.
2. Cairns, M. A., et al. (1997). Root biomass allocation in the world's upland forests. *Oecologia*, 111, 1–11.
3. Feldpausch, T. R., et al. (2012). Tree height integrated into pantropical forest biomass estimates. *Biogeosciences*, 9, 3381–3403.
4. Nowak, D. J. (1994). Atmospheric carbon dioxide reduction by Chicago's urban forest. *USDA Forest Service Gen. Tech. Rep.* NE-186.
5. Nowak, D. J., Crane, D. E., & Stevens, J. C. (2006). Air pollution removal by urban trees and shrubs in the United States. *Urban Forestry & Urban Greening*, 4(3–4), 115–123.
6. Wang, J., Endreny, T. A., & Nowak, D. J. (2008). Mechanistic simulation of tree effects in an urban water balance model. *JAWRA*, 44(1), 75–85.
7. Asner, G. P., Scurlock, J. M. O., & Hicke, J. A. (2003). Global synthesis of leaf area index observations. *Global Ecology and Biogeography*, 12(3), 191–205.
8. IPCC (2006). 2006 IPCC Guidelines for National Greenhouse Gas Inventories. Volume 4: Agriculture, Forestry and Other Land Use.
