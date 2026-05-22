# i-Tree SEA — CAD Plugin

## Overview

The CAD plugin provides two integration modes for landscape architects:

### Mode 1: Standalone DXF Processor (Any CAD Software)
Works with any software that exports DXF files — AutoCAD, BricsCAD, QCAD, DraftSight, etc.

```bash
# Process a DXF planting plan
python itree_sea_cad.py process --input planting.dxf --years 25

# Extract tree blocks only (no calculations)
python itree_sea_cad.py extract --input planting.dxf
```

### Mode 2: Live BricsCAD Integration
Connects to a running BricsCAD session via COM/ActiveX:

```bash
python itree_sea_cad.py bricscad --years 25
```

### Mode 3: AutoCAD/BricsCAD Command (via AutoLISP)
Load `itree_sea.lsp` into your CAD application:

```
(load "itree_sea.lsp")
ITREESEA          ; Run carbon calculation on current drawing
ITREESEA_OPEN     ; Open the results CSV
```

## Setup

1. Install the core package:
   ```bash
   pip install -e /path/to/itree-sea[cad]
   ```

2. Initialise the species database:
   ```bash
   python -m itree_sea init-db
   ```

3. Update the path in `itree_sea.lsp` to point to your installation.

## Files

| File | Purpose |
|------|---------|
| `itree_sea_cad.py` | Python CAD plugin (standalone + BricsCAD COM) |
| `itree_sea.lsp` | AutoLISP wrapper for AutoCAD/BricsCAD |

## Requirements

- Python 3.10+
- `ezdxf` (standalone mode)
- `comtypes` (BricsCAD live mode only, Windows)
