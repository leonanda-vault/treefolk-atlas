# QGIS Plugin — i-Tree SEA

## Installation

### Step 1: Install the core package
In the QGIS Python Console (`Plugins → Python Console`):

```python
import subprocess, sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-e', r'D:\path\to\itree-sea[gis]'])
```

Replace the path with your actual `itree-sea` project directory.

### Step 2: Copy the plugin
Copy the `itree_sea_qgis/` folder to your QGIS plugins directory:

**Windows:**
```
%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\itree_sea_qgis\
```

**Or use this script** (run in QGIS Python Console):
```python
import shutil, os
src = r"D:\path\to\itree-sea\qgis_plugin\itree_sea_qgis"
dst = os.path.join(os.environ['APPDATA'], 'QGIS', 'QGIS3', 'profiles', 'default', 'python', 'plugins', 'itree_sea_qgis')
shutil.copytree(src, dst, dirs_exist_ok=True)
print(f"Installed to: {dst}")
```

### Step 3: Enable the plugin
1. Go to `Plugins → Manage and Install Plugins`
2. Find "i-Tree SEA" in the list
3. Check the box to enable it

### Step 4: Initialise the database
In QGIS Python Console:
```python
from itree_sea.database import init_db, seed_from_csv
init_db()
seed_from_csv()
```

## Usage

After installation, the algorithms appear in the **Processing Toolbox**:

```
Processing Toolbox
└── i-Tree SEA
    ├── Enrich Tree Inventory Layer
    └── Forecast Planting Benefits
```

### Enrich Tree Inventory Layer
- **Input**: Point layer with `species` and `dbh_cm` fields
- **Output**: New layer with 13 ecosystem benefit columns added

### Forecast Planting Benefits
- **Input**: Point layer with `species` field (proposed planting plan)
- **Output**: Two CSV files (schedule + summary)

## Plugin Structure

```
itree_sea_qgis/
├── __init__.py          # classFactory entry point
├── metadata.txt         # Plugin metadata
├── plugin.py            # Provider registration
└── processing/
    ├── __init__.py
    ├── provider.py               # Processing provider
    ├── enrich_tree_layer.py      # Algorithm: Enrich existing trees
    └── forecast_planting.py      # Algorithm: Forecast proposed trees
```
