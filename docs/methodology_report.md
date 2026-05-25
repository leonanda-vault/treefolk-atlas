# Scientific Methodology & Workflow Integration Report
## Treefolk Atlas (i-Tree SEA) Adaptations for Tropical Southeast Asia

> **Document Reference:** ATLAS-METHODOLOGY-v0.5  
> **Date:** May 2026  
> **Target Audience:** Landscape Architects, Urban Foresters, Surveyors, and Environmental Consultants  
> **Repository Documentation:** [methodology.md](file:///d:/Leonanda's%20Professional%20Vault/Projects/itree-sea/docs/methodology.md)

---

## 1. Executive Summary

The **Treefolk Atlas (i-Tree SEA)** is a specialized, open-source urban forestry evaluation platform. It adapts and extends the USDA Forest Service i-Tree Eco methodology to suit the unique climatic, taxonomic, and structural conditions of equatorial Southeast Asia (Köppen *Af* and *Am* zones). 

By integrating species-specific wood densities, tropical height-diameter models (Weibull regressions), dedicated monocot (palm) equations, and morphology-driven canopy modifiers, the tool provides landscape architects and surveyors with a highly localized engine to quantify the ecological benefits of urban green infrastructure. It translates physical inventory or CAD/GIS layouts into audited environmental metrics, including carbon storage, gross sequestration, oxygen production, pollution dry-deposition, and stormwater runoff reduction.

---

## 2. Core Scientific Methodology & Mathematical Foundations

Unlike temperate climate engines that rely on simplified hardwood/conifer categorizations, Treefolk Atlas utilizes localized parameters and biological formulas.

### 2.1 Aboveground Biomass (AGB) Calculations

#### For Dicotyledonous Trees (Standard Broadleaf & Needle Species)
The engine implements the pantropical allometric model by **Chave et al. (2014)** as the baseline for aboveground biomass:

$$\text{AGB}_{\text{base}} = 0.0673 \times (\rho \times D^2 \times H)^{0.976}$$

Where:
*   $\text{AGB}_{\text{base}}$ is the dry-weight aboveground biomass (kg).
*   $\rho$ is the species-specific basic wood specific gravity (g/cm³), sourced from the **Global Wood Density Database (Chave 2009, Zanne 2009)**.
*   $D$ is the Diameter at Breast Height (DBH, cm) measured at 1.3 m above ground.
*   $H$ is the total height of the tree (m).

To account for architectural differences in urban open-grown trees, the engine splits biomass into woody and foliage components:

1.  **Woody Component Extraction:**
    $$\text{Woody}_{\text{base}} = \text{AGB}_{\text{base}} \times (1 - \text{DEFAULT\_FOLIAGE\_FRACTION})$$
    *(where $\text{DEFAULT\_FOLIAGE\_FRACTION} = 0.05$ or $5\%$)*

2.  **Morphological Corrections for Structure:**
    $$\text{Woody}_{\text{adjusted}} = \text{Woody}_{\text{base}} \times f_{\text{trunk}} \times f_{\text{crown}}$$
    *   **Trunk Taper Multiplier ($f_{\text{trunk}}$):** Standard single-stem taper (`1.0`), Buttressed base (e.g., *Ficus*, *Samanea* = `1.15`), and Multi-stemmed structure (e.g., *Dypsis lutescens* cluster = `0.85`).
    *   **Crown Shape Multiplier ($f_{\text{crown}}$):** Columnar (`0.80`), Conical (`0.90`), Spherical (`1.00`), Spreading (`1.15`).

3.  **Foliage Component Calculation:**
    Instead of calculating foliage as a static fraction, the engine models foliage biomass dynamically from leaf geometry and density:
    $$\text{Foliage} = \text{Crown Area} \times \text{LAI}_{\text{species}} \times \text{SLW}$$
    *   **Crown Area (m²):** Derived from Crown Width ($CW$), where $CW = 0.6 + (k_{cw} \times DBH)$ capped at 20 m.
    *   **Crown Modifier ($k_{cw}$):** Specific canopy architectural factors (Columnar/Fastigiate = `0.08`, Standard/Oval = `0.15`, Spreading/Umbrella = `0.25 - 0.30`).
    *   **Leaf Area Index ($\text{LAI}_{\text{species}}$):** Species-specific foliage density multiplier (default = `5.0`).
    *   **Specific Leaf Weight (SLW, kg/m²):** Scaled by leaf morphology class (Simple leaves = `0.12`, Compound leaves = `0.09`, Needles = `0.22`, Palm Fans = `0.32`).

$$\text{AGB}_{\text{final}} = \text{Woody}_{\text{adjusted}} + \text{Foliage}$$

To account for open-grown tree architecture in urban environments, the engine applies a dynamic urban adjustment factor:
$$\text{AGB}_{\text{final\_urban}} = \text{AGB}_{\text{final}} \times f_{\text{urban}}$$
Where $f_{\text{urban}}$ is calculated based on Crown Light Exposure (CLE, 0 to 5):
$$f_{\text{urban}} = \max\left(0.80, \min\left(1.00, 0.80 + 0.04 \times (5 - CLE)\right)\right)$$

#### For Monocotyledonous Trees (Palms)
Standard dicot allometric models overestimate palm biomass due to distinct structural mechanics (non-tapering cylindrical trunks, absence of secondary lateral cambial growth, and high water-to-dry-mass ratios). Treefolk Atlas applies a dedicated **Cylindrical Stem Model**:

$$\text{AGB}_{\text{palm}} = 0.07854 \times \rho \times D^2 \times H$$

*   *Derivation:* The volume of a cylinder is $V = \frac{\pi}{4} \times (\frac{D}{100})^2 \times H = \frac{\pi}{40000} \times D^2 \times H$ (m³). Converting volume to dry mass using dry wood specific density ($\rho \times 1000$ kg/m³) yields:
    $$\text{AGB}_{\text{palm}} = \left(\frac{\pi}{40000} \times 1000\right) \times \rho \times D^2 \times H \approx 0.07854 \times \rho \times D^2 \times H$$
*   *Taxonomic Calibration:* Basic carbon fraction is adjusted downward to **0.41** (compared to 0.50 for dicots) to reflect the lower lignin content of monocot vascular bundles (IPCC 2006).

---

### 2.2 Hydrological Stormwater Model: Daily Canopy Water Balance

Rather than using simplified annual event-based proxies, the engine implements a daily wet-canopy water balance model driven by Penman-Monteith potential leaf evaporation to reduce prediction errors:

1. **Evaporation Rate ($E$, mm/day):** Estimated from temperature, wind speed, and relative humidity using the Penman equation:
   $$E = \frac{\Delta \cdot R_n + \gamma \cdot f(u) \cdot (e_s - e_a)}{\Delta + \gamma}$$
   Where:
   *   $\Delta$ is the slope of the saturation vapor pressure curve.
   *   $\gamma$ is the psychrometric constant ($0.066$).
   *   $R_n$ is the net solar radiation ($2.5\text{ MJ/m}^2/\text{day}$).
   *   $f(u)$ is the wind function: $f(u) = 2.626 \cdot (1.0 + 0.54 \cdot u)$, where $u$ is wind speed ($m/s$).
   *   $e_s - e_a$ is the vapor pressure deficit.

2. **Canopy Storage Tracking:** For each day $t$:
   *   **Interception ($I_t$, mm):** Water captured by empty canopy capacity:
       $$I_t = \min(P_t, C_{\max} - S_{t-1})$$
       Where $P_t$ is rainfall on day $t$, $S_{t-1}$ is existing storage, and $C_{\max}$ is the maximum canopy capacity ($LAI \times 0.2\text{ mm}$).
   *   **Evaporation ($E_{\text{act}}$, mm):** Evaporative water loss from wet leaves:
       $$E_{\text{act}} = \min(E_t, S_{t-1} + I_t)$$
   *   **Updated Storage ($S_t$, mm):**
       $$S_t = S_{t-1} + I_t - E_{\text{act}}$$
       *(where $S_t \ge 0$)*
   *   **Total Interception (L):** Computed as $\sum E_{\text{act}} \times \text{Crown Area} \times 1000$.

By default, the engine runs this daily water balance using a 365-day Southeast Asian weather profile. For advanced projects, users can upload custom hourly precipitation files (processed using a 6-hour dry reset threshold).

---

### 2.3 Air Pollution Removal

Dry deposition of particulate and gaseous air pollutants ($\text{PM}_{2.5}$, $\text{NO}_2$, $\text{O}_3$, $\text{SO}_2$) is modeled using the **resistance-in-series dry deposition model** (Baldocchi et al. 1987) to calculate the daily deposition velocity ($V_d$, m/s):

$$V_d = \frac{1}{R_a + R_b + R_c}$$

Where:
*   **Aerodynamic Resistance ($R_a$, s/m):** Derived from wind speed $u$ (m/s) and canopy height $h$ (m):
    $$R_a = \frac{\ln(10.0 + 20.0 / h)}{0.16 \cdot u}$$
*   **Quasi-Laminar Boundary Layer Resistance ($R_b$, s/m):** Models leaf boundary layer:
    $$R_b = \frac{84.0}{\sqrt{u}}$$
*   **Canopy Resistance ($R_c$, s/m):**
    *   **For PM2.5:** Modeled using default canopy resistance $R_c = 200.0\text{ s/m}$.
    *   **For Gaseous Pollutants:** Combines stomatal resistance ($R_s$), mesophyll resistance ($R_m = 10.0\text{ s/m}$), cuticular resistance ($R_{\text{cut}} = 2000.0\text{ s/m}$), and ground resistance ($R_g = 1000.0\text{ s/m}$) in parallel:
        $$\frac{1}{R_c} = \frac{1}{R_s + R_m} + \frac{1}{R_{\text{cut}}} + \frac{1}{R_g}$$
        *Stomata closure* is modeled dynamically by setting daytime stomatal resistance $R_s = 100.0\text{ s/m}$ and nighttime stomatal resistance $R_s = 10000.0\text{ s/m}$ (reducing nighttime gaseous deposition to near-zero). The daily $V_d$ is the average of daytime and nighttime velocities.

The daily removal of each pollutant is calculated as:
$$\text{Removal}_t = \text{Leaf Area} \times V_d \times \text{Concentration} \times 86400$$

Where baseline ambient concentrations are $\text{PM}_{2.5} = 12.0\ \mu\text{g/m}^3$, $\text{NO}_2 = 40.0\ \mu\text{g/m}^3$, $\text{O}_3 = 100.0\ \mu\text{g/m}^3$, and $\text{SO}_2 = 40.0\ \mu\text{g/m}^3$. These are scaled by the site profile's `pollution_multiplier`.

---

## 3. Workflow Integration for Landscape Architects & Surveyors

The Treefolk Atlas bridges the gap between field data collection, schematic landscape design, and environmental impact reporting.

```mermaid
flowchart TD
    subgraph Field Survey & Data Prep
        A1[Surveyor: Field Inventory GPS/Total Station] -->|Export GeoJSON/SHP/CSV| B1[Standardized Tree Assets]
        A2[CAD Designer: Schematic Layouts] -->|Drafting Layers standard| B2[DXF AutoCAD Drawing File]
    end

    subgraph Treefolk Atlas Parsing & Engine
        B1 --> C[i-Tree SEA Core Parser]
        B2 --> C
        C --> D{Taxonomic Engine Lookup}
        D -->|1. Exact match| E[Species Database]
        D -->|2. Genus fallback| F[Average Genus ρ & Growth]
        D -->|3. Family fallback| G[Pantropical Defaults]
    end

    subgraph Simulation & Scenario Sandbox
        E & F & G --> H[Ecosystem Service Core calculations]
        H --> I[Interactive Dashboard & Map Sandbox]
        I -->|What-If clearings/plantings| J[Nudge Species, Modify Shape, Override LAI]
    end

    subgraph Project Delivery & Reporting
        J --> K1[ESG Reports & Carbon Offset Certificates]
        J --> K2[Green Mark / Greenship Credit Verification]
        J --> K3[EIA Compliance Documentation]
    end
    
    style B1 fill:#f9f,stroke:#333,stroke-width:2px
    style B2 fill:#bbf,stroke:#333,stroke-width:2px
    style I fill:#f96,stroke:#333,stroke-width:2px
    style K2 fill:#8f8,stroke:#333,stroke-width:2px
```

### 3.1 For Surveyors (Existing Canopy Asset Auditing)
1.  **Field Inventory Collection:** Surveyors record GPS coordinates, species names (scientific or common), DBH (cm), and tree condition (Excellent to Dead).
2.  **Height-Diameter (H-D) Optimization:** In tropical surveys, measuring the height of every tree is time-consuming and often obstructed by dense multi-tiered canopies. The surveyor only needs to capture DBH. The engine automatically runs the **Feldpausch et al. (2012) 3-parameter Weibull model** to project the asymptotic height curve:
    $$H = a \times (1 - e^{-b \times D^c})$$
    *(using regional Southeast Asian parameters: $a=57.122, b=0.0332, c=0.8468$ unless species overrides exist)*
3.  **GIS Pipeline Upload:** Surveyors export inventories directly as GeoJSON or Shapefiles and run them through the CLI. The engine automatically resolves taxonomic wood densities and computes current environmental baselines.

### 3.2 For Landscape Architects (Schematic Design & Proposed Planning)
1.  **Standardized CAD Layering:** Landscape architects draft planting layouts using standardized layer conventions in AutoCAD/Vectorworks:
    *   `L-PLNT-TREE-PROP` (Proposed new trees)
    *   `L-PLNT-TREE-EXST` (Existing trees to be retained)
    *   `L-PLNT-TREE-RMVL` (Trees targeted for removal/clearing)
2.  **DXF Direct Parsing:** The architect uploads the `.dxf` file directly. The platform reads coordinate blocks, counts symbols, matches block attributes to database species, and resolves planting densities.
3.  **Interactive Scenario Planning (Sandbox):** In the dashboard's manual planting sandbox, the designer can:
    *   **Test Species Alternatives:** Swap a slow-growing hardwood like *Fagraea fragrans* (Tembusu, $\rho=0.82$, $\Delta D=0.5\text{ cm/yr}$) with a fast-growing carbon sink like *Samanea saman* (Rain Tree, $\rho=0.45$, $\Delta D=1.75\text{ cm/yr}$) to optimize carbon capture targets.
    *   **Simulate Canopy Spacing:** Adjust the crown modifier $k_{cw}$ (e.g., set to Columnar `0.08` for tight alignments or Spreading `0.28` for shade canopies) to evaluate the spatial layout and check for crown overlaps.
    *   **Assess Impact of Clearances:** View the immediate loss in stormwater retention and air filtration if mature trees in `L-PLNT-TREE-RMVL` are cut down.

---

## 4. Scientific Accuracy, Error Margins & Calibration

To ensure engineering-grade data, the platform uses peer-reviewed tropical forestry regressions rather than temperate equivalents.

| Calculation Component | Scientific Baseline Model | Expected Error Margin | Calibration Factors & Constraints |
| :--- | :--- | :--- | :--- |
| **Dicot Biomass (AGB)** | Chave et al. (2014) Pantropical Regressions | $\pm 5\% - 10\%$ (Stand level)<br>$\pm 10\% - 15\%$ (Single tree) | Directly incorporates wood density ($\rho$) and height. Adjusts for urban open-grown forms using dynamic CLE-based factor: $f_{\text{urban}} = 0.8 + 0.04 \times (5 - CLE)$. |
| **Palm Biomass (AGB)** | Frangi & Lugo (1985); Cylindrical | $\pm 10\% - 15\%$ | Dedicated cylindrical volume formula ($0.07854 \times \rho \times D^2 \times H$). Eliminates the $200\% - 300\%$ overestimation errors of dicot models. |
| **Stormwater Interception** | Penman-Monteith Daily Wet-Canopy Evaporation | $\pm 10\% - 15\%$ | Driven by daily temperature, wind speed, relative humidity, and precipitation. Tracks canopy saturation and throughfall dynamically. |
| **Air Pollution Removal** | Baldocchi Resistance-in-Series Model | $\pm 15\% - 20\%$ | Calculates daily dry deposition velocity ($V_d = 1 / [R_a + R_b + R_c]$). Models stomatal closure dynamically (nighttime $R_s \to 10000$ s/m). |
| **Growth Forecast** | Chapman-Richards Sigmoidal Model | $\pm 5\%$ | Replaces linear growth increments with asymptotic sigmoidal curves: $\Delta D = k \cdot DBH \cdot ((DBH_{\max}/DBH)^{1/3} - 1)$. |

---

## 5. Feature Comparison: i-Tree Eco vs. Treefolk Atlas (i-Tree SEA)

| Evaluation Parameter | Standard USDA i-Tree Eco v6 | Treefolk Atlas (i-Tree SEA) | Local Impact & Rationale |
| :--- | :--- | :--- | :--- |
| **Climatic Baseline** | Temperate Northern Hemisphere (US/Europe) | Tropical Lowland Southeast Asia (Af/Am zones) | Eliminates temperature-based growth limits and frost adjustments that do not apply to tropical regions. |
| **Growth Forecasting** | US Forest Service growth tables | Chapman-Richards Sigmoidal curves | Avoids mature tree runaway biomass; models species-specific asymptotic growth limits ($DBH_{\max}$). |
| **Palm (Monocot) Modeling** | Standard dicot allometric equations (severe overestimation) | Dedicated Cylindrical Stem volume model | Accurately calculates palm biomass; critical for tropical urban sites where palms make up 20%–40% of plantings. |
| **Wood Density Mapping** | Post-hoc WD ratio weight adjustment | Direct inclusion of $\rho$ in biomass equations | Ensures taxonomic accuracy by utilizing species-level basic specific gravities from local databases. |
| **Tree Height Input** | Mandatory field measurement | Weibull H-D projection (Feldpausch 2012) | Speeds up field surveys; height is projected using regional tropical parameters when omitted. |
| **CAD/GIS Design Integration** | Not supported | Native DXF parsing and shapefile georeferencing | Connects directly to the tools used by landscape architects and surveyors (AutoCAD, QGIS, ArcGIS). |
| **Stormwater Method** | Hourly water balance | Daily wet-canopy water balance (Penman-driven) | Enables highly accurate seasonal interception tracking without requiring full weather station files. |
| **Pollution Method** | Hourly dry deposition model | Daily dry deposition resistance-in-series (Baldocchi) | Accounts for boundary layer resistances and diurnal stomatal closure (nighttime closure) for high accuracy. |
| **Evaluation Stage** | Post-facto forest management & inventory | Concept planning, schematic design, and impact modeling | Enables architects to optimize designs *before* construction begins. |

---

## 6. Primary Use Cases & Application Areas

### 6.1 Green Building Certifications (BCA Green Mark, Greenship)
Under green building rating frameworks (such as Singapore's **BCA Green Mark 2021** under the *Health and Well-being (Hw)* section, or Indonesia's **GBCI Greenship** under the *Appropriate Site Development (ASD)* section), projects receive credits for preserving existing mature trees and expanding canopy coverage. 
*   **Application:** Designers generate reports showing the total carbon stored and annual stormwater intercepted by the site. The tool's output serves as audit-ready compliance documentation to secure credits for biophilic design and urban greenery.

### 6.2 ESG Corporate Reporting & Carbon Offsetting
Organizations must demonstrate tangible carbon reduction strategies to meet Environmental, Social, and Governance (ESG) criteria.
*   **Application:** Real estate developers model the long-term (e.g., 30-year) carbon storage and sequestration potential of their developments. The generated PDF outputs provide verifiable data on the lifetime carbon offset of the site, translating ecological benefits into equivalents like gasoline saved or kilometers driven.

### 6.3 Environmental Impact Assessments (EIA) & Tree Preservation Orders (TPO)
Municipal authorities often enforce strict tree preservation guidelines. Developers must justify the removal of mature trees and outline mitigation plans.
*   **Application:** Surveyors map existing trees on layer `L-PLNT-TREE-RMVL`. The engine quantifies the lost ecological value. The landscape architect can then design a compensatory planting plan on layer `L-PLNT-TREE-PROP` and demonstrate that the proposed canopy will reach ecological parity with the cleared vegetation within a specific timeframe.

### 6.4 Urban Hydrology & Sustainable Drainage Systems (SuDS)
Rapid urbanization in Southeast Asia increases the risk of flash flooding.
*   **Application:** Civil engineers and landscape architects use the stormwater interception sandbox to evaluate species layouts. They can compare a columnar layout (such as *Polyalthia longifolia*, $k_{cw}=0.08$) with a wide, spreading canopy layout (such as *Samanea saman*, $k_{cw}=0.28$) to maximize rainfall interception, which helps reduce peak stormwater runoff in flood-prone developments.
