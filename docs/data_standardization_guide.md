# Data Standardization Guide — i-Tree SEA
## CAD Block Standards & GIS Attribute Schema for Tree Inventories

> This guide defines the standard data formats that make tree data
> flow seamlessly from **field surveyors** through **GIS** and
> **CAD planting plans** into the i-Tree SEA carbon calculator.

---

## Table of Contents

1. [CAD Block Standards (for Landscape Designers)](#1-cad-block-standards)
2. [GIS Attribute Schema (for Surveyors)](#2-gis-attribute-schema)
3. [Reformatting Surveyor Data](#3-reformatting-surveyor-data)
4. [Species Naming & Coding Convention](#4-species-naming--coding)
5. [Layer & File Naming Conventions](#5-layer--file-naming)
6. [Sample Templates](#6-sample-templates)

---

## 1. CAD Block Standards

### 1.1 Tree Block Structure

Every tree symbol in a CAD drawing must be a **Block Reference (INSERT)** with attached **ATTDEFs** (Attribute Definitions). The block insertion point must be at the **center of the trunk**.

```
┌──────────────────────────────────┐
│          TREE BLOCK              │
│                                  │
│   Insertion Point: Trunk center  │
│   Canopy Circle: Mature spread   │
│                                  │
│   ATTDEF Tags:                   │
│     SPECIES  ← required         │
│     CALIPER  ← required         │
│     HEIGHT   ← optional         │
│     TAG      ← recommended      │
│     COMMON   ← optional         │
│                                  │
└──────────────────────────────────┘
```

### 1.2 Required ATTDEF Tags

| Tag | Type | Example Value | Description |
|-----|------|---------------|-------------|
| **`SPECIES`** | Text | `Pterocarpus indicus` | Full botanical name (Genus species). **This is the primary key** for looking up allometric coefficients. |
| **`CALIPER`** | Number | `5` | Planting caliper in **cm** (nursery stock diameter, measured 15 cm above soil for trees ≤10 cm). For existing trees, use DBH. |

### 1.3 Recommended ATTDEF Tags

| Tag | Type | Example Value | Description |
|-----|------|---------------|-------------|
| `TAG` | Text | `PT-01` | Unique tree identifier linking to plant schedule. Format: `XX-##` where XX = species abbreviation. |
| `HEIGHT` | Number | `4.0` | Planting height in **metres**. If omitted, i-Tree SEA estimates height from DBH. |
| `COMMON` | Text | `Angsana` | Common name (for drawing annotations). |
| `QTY` | Integer | `1` | Quantity (always 1 for individually placed blocks; only used for grouped schedules). |
| `NPARKS` | Text | `PTCR` | NParks flora code (optional, for Singapore projects). |

### 1.4 Alternative Tag Names (Auto-detected)

i-Tree SEA automatically recognizes these alternative tag names:

| Standard Tag | Also Accepted |
|--------------|---------------|
| `SPECIES` | `TREE_SPECIES`, `SP`, `BOTANICAL`, `NAMA` |
| `CALIPER` | `DBH`, `DIAMETER` |
| `HEIGHT` | `HT`, `TINGGI` |

### 1.5 Block Naming Convention

Name tree blocks systematically for easy filtering:

```
TREE_{canopy_diameter}m_{form}

Examples:
  TREE_6m_OVAL       ← 6m mature canopy, oval crown
  TREE_10m_SPREAD    ← 10m mature canopy, spreading crown
  TREE_4m_COLUMNAR   ← 4m mature canopy, columnar form
  PALM_8m            ← 8m palm crown
  SHRUB_2m           ← 2m shrub (not processed by i-Tree SEA)
```

### 1.6 Example Block Creation (AutoCAD / BricsCAD)

```
Command: ATTDEF
  Tag:       SPECIES
  Prompt:    Botanical name (Genus species):
  Default:   Pterocarpus indicus
  Mode:      Preset, Invisible (or Verify)
  Height:    0.3

Command: ATTDEF
  Tag:       CALIPER
  Prompt:    Planting caliper (cm):
  Default:   5
  Mode:      Preset, Invisible

Command: ATTDEF
  Tag:       TAG
  Prompt:    Plant tag (XX-##):
  Default:   PT-01
  Mode:      Visible
  Height:    0.25

Command: BLOCK
  Name:      TREE_8m_SPREAD
  Base Point: 0,0 (trunk center)
  Objects:   [canopy circle + trunk + all ATTDEFs]
```

---

## 2. GIS Attribute Schema

### 2.1 Required Fields

For **surveyed existing trees** (GIS surveyors delivering GeoJSON/Shapefile):

| Field Name | Type | Units | Example | Description |
|-----------|------|-------|---------|-------------|
| **`tree_id`** | String | — | `JKT-2024-0001` | Unique permanent identifier. Never reuse after removal. |
| **`species`** | String | — | `Pterocarpus indicus` | Full scientific name. **Primary key** for calculations. |
| **`dbh_cm`** | Float | cm | `45.2` | Diameter at Breast Height (1.3 m above ground). |

### 2.2 Recommended Fields

| Field Name | Type | Units | Example | Description |
|-----------|------|-------|---------|-------------|
| `height_m` | Float | m | `15.0` | Total tree height (to apex). |
| `condition` | String | — | `good` | Tree health: `excellent`, `good`, `fair`, `poor`, `critical`, `dead` |
| `common_name` | String | — | `Angsana` | Local/common name |
| `crown_w_m` | Float | m | `12.0` | Crown width (widest spread). If provided, used instead of DBH-based estimate. |
| `stems` | Integer | — | `1` | Number of stems. Multi-stem trees: measure each, record largest as DBH. |
| `land_use` | String | — | `street` | Where the tree grows: `street`, `park`, `private`, `forest`, `median` |
| `survey_date` | Date | ISO 8601 | `2024-11-15` | Date of field measurement |
| `surveyor` | String | — | `PT Geodata` | Survey company / person |
| `notes` | String | — | `Leaning 15° NW` | Free-text field observations |

### 2.3 Optional Extended Fields

| Field Name | Type | Units | Description |
|-----------|------|-------|-------------|
| `nparks_code` | String | — | NParks flora code (Singapore projects) |
| `crown_ht_m` | Float | m | Height to crown base (for live crown ratio) |
| `dieback_pct` | Float | % | Crown dieback percentage (0–100) |
| `lat` | Float | dd | Latitude (if geometry is separate) |
| `lon` | Float | dd | Longitude (if geometry is separate) |

### 2.4 Geometry

| Property | Standard |
|----------|----------|
| Geometry type | **Point** (trunk base location) |
| CRS | **EPSG:4326** (WGS 84) for exchange; project-local CRS acceptable |
| Precision | ≥ 6 decimal places for WGS 84 |

---

## 3. Reformatting Surveyor Data

### 3.1 Common Surveyor Formats → i-Tree SEA

Indonesian and Singaporean surveyors often deliver data in non-standard formats. Here's how to reformat:

#### Problem: DBH in millimetres

```
Input field:  "DBH_MM" = 452
Output field: "dbh_cm" = 45.2
```

**QGIS Field Calculator:**
```
"DBH_MM" / 10.0
```

#### Problem: DBH in inches

```
Input field:  "DBH_IN" = 17.8
Output field: "dbh_cm" = 45.2
```

**Formula:** `dbh_cm = dbh_in × 2.54`

#### Problem: Species as common name only

If surveyors record common names, you need a lookup table. Create a CSV:

```csv
common_name,species
Angsana,Pterocarpus indicus
Ketapang,Terminalia catappa
Beringin,Ficus benjamina
Trembesi,Samanea saman
...
```

**QGIS:** Use the "Join attributes by field value" tool to merge.

#### Problem: Condition as numeric (1–5)

```
Surveyor: 1=Dead, 2=Poor, 3=Fair, 4=Good, 5=Excellent
i-Tree SEA: 'dead', 'poor', 'fair', 'good', 'excellent'
```

**QGIS Field Calculator:**
```python
CASE
  WHEN "kondisi" = 5 THEN 'excellent'
  WHEN "kondisi" = 4 THEN 'good'
  WHEN "kondisi" = 3 THEN 'fair'
  WHEN "kondisi" = 2 THEN 'poor'
  WHEN "kondisi" = 1 THEN 'dead'
  ELSE 'fair'
END
```

#### Problem: Coordinates in UTM (Zone 48S) instead of WGS 84

**QGIS:** Right-click layer → Export → Save Features As → CRS: EPSG:4326

#### Problem: Mixed multi-stem DBH (e.g., "20/15/10")

For multi-stem trees, calculate equivalent single-stem DBH:

```
DBH_equiv = √(d₁² + d₂² + d₃² + ...)
Example:  √(20² + 15² + 10²) = √(400 + 225 + 100) = √725 = 26.9 cm
```

### 3.2 Quick Reference: Field Name Aliases

i-Tree SEA automatically recognizes these column name variations during import:

| Standard | Accepted Aliases |
|----------|-----------------|
| `species` | `species_name`, `scientific_name`, `tree_species`, `sp`, `nama` |
| `dbh_cm` | `dbh`, `dbh_mm` (auto-converts ÷10), `dbh_in` (auto-converts ×2.54) |
| `height_m` | `height`, `tinggi` |
| `condition` | `kondisi`, `tree_condition`, `health` |

---

## 4. Species Naming & Coding

### 4.1 Naming Rules

1. Always use **full binomial** (Genus species): `Pterocarpus indicus`
2. Capitalise genus, lowercase species: `Syzygium grande` ✓, `syzygium Grande` ✗
3. No authority names: `Pterocarpus indicus` ✓, `Pterocarpus indicus Willd.` ✗
4. For subspecies/cultivars, omit the cultivar in the species field and note it in `notes`
5. If species is unknown, use genus only: `Ficus` → will match genus-level coefficients

### 4.2 NParks Code Format

For Singapore projects, use the 4-character NParks flora code:

| Code | Species | Common Name |
|------|---------|-------------|
| `PTCR` | Pterocarpus indicus | Angsana |
| `SMNR` | Samanea saman | Rain Tree |
| `TRCT` | Cyrtophyllum fragrans | Tembusu |
| `FCBN` | Ficus benjamina | Weeping Fig |
| `CNCF` | Cocos nucifera | Coconut Palm |

### 4.3 Species Code for Indonesia

For Indonesian projects without NParks codes, use a 6-character code:

```
Format: GGGSS#
  GGG = First 3 letters of Genus
  SS  = First 2 letters of Species
  #   = Disambiguator (if needed)

Examples:
  PTEIN  = Pterocarpus indicus
  SAMSA  = Samanea saman
  FICBE  = Ficus benjamina
  TECGR  = Tectona grandis
```

---

## 5. Layer & File Naming Conventions

### 5.1 CAD Layers (NCS-Based)

Follow the National CAD Standard (NCS) adapted for landscape:

| Layer | Description | Content |
|-------|-------------|---------|
| `L-PLNT-TREE-PROP` | Proposed trees | New planting block INSERTs |
| `L-PLNT-TREE-EXST` | Existing trees | Survey data / topo trees |
| `L-PLNT-TREE-RMVL` | Trees to remove | Marked for removal |
| `L-PLNT-TREE-PROT` | Protected trees | Heritage / conservation |
| `L-PLNT-SHRB-PROP` | Proposed shrubs | Not processed by i-Tree SEA |
| `L-PLNT-GRND-PROP` | Groundcover | Not processed |
| `L-PLNT-NOTE` | Planting notes | Text annotations |
| `L-PLNT-SCHD` | Plant schedule | Table / data |

### 5.2 GIS File Naming

```
{project_code}_{content}_{date}.{ext}

Examples:
  JKT001_tree_survey_20241115.geojson
  JKT001_tree_survey_20241115_enriched.geojson
  SGP_nparks_planting_20240801.shp
```

### 5.3 Output File Naming

i-Tree SEA default outputs:

```
output/
  enriched_trees.geojson          ← GIS pipeline
  planting_schedule.csv           ← CAD pipeline (year-by-year)
  planting_summary.csv            ← CAD pipeline (final totals)
```

---

## 6. Sample Templates

### 6.1 Sample GeoJSON (Surveyed Trees)

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [106.8456, -6.2088]
      },
      "properties": {
        "tree_id": "JKT-2024-0001",
        "species": "Pterocarpus indicus",
        "dbh_cm": 45.2,
        "height_m": 15.0,
        "condition": "good",
        "common_name": "Angsana",
        "crown_w_m": 12.0,
        "land_use": "street",
        "survey_date": "2024-11-15",
        "surveyor": "PT Geodata",
        "notes": ""
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [106.8461, -6.2091]
      },
      "properties": {
        "tree_id": "JKT-2024-0002",
        "species": "Samanea saman",
        "dbh_cm": 78.5,
        "height_m": 22.0,
        "condition": "excellent",
        "common_name": "Rain Tree",
        "crown_w_m": 25.0,
        "land_use": "park",
        "survey_date": "2024-11-15",
        "surveyor": "PT Geodata",
        "notes": "Heritage tree candidate"
      }
    },
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [106.8470, -6.2085]
      },
      "properties": {
        "tree_id": "JKT-2024-0003",
        "species": "Cocos nucifera",
        "dbh_cm": 25.0,
        "height_m": 18.0,
        "condition": "fair",
        "common_name": "Coconut Palm",
        "crown_w_m": 6.0,
        "land_use": "median",
        "survey_date": "2024-11-15",
        "surveyor": "PT Geodata",
        "notes": "Leaning 10° SE"
      }
    }
  ]
}
```

### 6.2 Sample Surveyor CSV (Before Reformatting)

This is what a typical Indonesian surveyor might deliver:

```csv
NO,NAMA_POHON,DBH_MM,TINGGI,KONDISI,LAT,LON,CATATAN
1,Angsana,452,15.0,4,-6.2088,106.8456,
2,Trembesi,785,22.0,5,-6.2091,106.8461,Pohon heritage
3,Kelapa,250,18.0,3,-6.2085,106.8470,Miring 10° SE
```

After reformatting with the rules in Section 3:

```csv
tree_id,species,dbh_cm,height_m,condition,lat,lon,notes
JKT-2024-0001,Pterocarpus indicus,45.2,15.0,good,-6.2088,106.8456,
JKT-2024-0002,Samanea saman,78.5,22.0,excellent,-6.2091,106.8461,Pohon heritage
JKT-2024-0003,Cocos nucifera,25.0,18.0,fair,-6.2085,106.8470,Miring 10° SE
```

### 6.3 Sample Plant Schedule Output (from CAD Pipeline)

```csv
tree_id,block_name,species,x,y,layer,year,dbh_cm,height_m,carbon_storage_kg,carbon_seq_kg,stormwater_l,pm25_g,no2_g,o3_g,so2_g,match_level
1,TREE_8m_SPREAD,Pterocarpus indicus,150.0,200.0,L-PLNT-TREE-PROP,0,5.0,3.42,0.526,0.526,27.8,3.51,6.33,9.84,2.46,species
1,TREE_8m_SPREAD,Pterocarpus indicus,150.0,200.0,L-PLNT-TREE-PROP,1,6.0,3.75,0.844,0.318,37.9,4.79,8.63,13.42,3.36,species
1,TREE_8m_SPREAD,Pterocarpus indicus,150.0,200.0,L-PLNT-TREE-PROP,5,10.0,4.84,3.267,0.667,87.4,11.04,19.88,30.92,7.73,species
1,TREE_8m_SPREAD,Pterocarpus indicus,150.0,200.0,L-PLNT-TREE-PROP,10,15.0,5.93,9.387,1.004,172.2,21.77,39.18,60.95,15.24,species
1,TREE_8m_SPREAD,Pterocarpus indicus,150.0,200.0,L-PLNT-TREE-PROP,25,30.0,8.38,52.914,2.568,533.4,67.43,121.37,188.80,47.20,species
```

---

> [!TIP]
> **For Indonesian surveyors**: Create a simple reformatting script using the
> `gis_bridge.py` module — it auto-detects `DBH_MM`, `tinggi`, `kondisi`,
> and `nama` columns and remaps them.

> [!IMPORTANT]
> **The species field is the most critical**. If a surveyor delivers only
> common names, you **must** translate to scientific binomials before
> running i-Tree SEA. Genus-only entries (e.g., `Ficus`) will still work
> but with reduced accuracy (genus-level fallback).
