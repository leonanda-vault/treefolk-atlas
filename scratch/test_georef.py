import sys
from pathlib import Path
import pandas as pd

# Add the project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from itree_sea.cad_bridge import parse_dxf, extract_planting_blocks, generate_schedule, BLOCK_NAME_MAP
from itree_sea.simulation import project_coordinates

DXF_FILES = [
    r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-POHON.dxf",
    r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-TREE PLANTING.dxf",
    r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-TREE PLAN 1ST FLOOR.dxf",
    r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf"
]

for dxf_path in DXF_FILES:
    p = Path(dxf_path)
    if not p.exists():
        print(f"Skipping {p.name} (does not exist)")
        continue
    
    print(f"\n--- Testing Georeferencing for: {p.name} ---")
    try:
        doc = parse_dxf(str(p))
        entries = extract_planting_blocks(doc)
        print(f"Extracted {len(entries)} tree entries.")
        
        if not entries:
            continue
            
        df = pd.DataFrame([{
            "x": entry.x,
            "y": entry.y,
            "species": entry.species_name,
            "dbh_cm": entry.dbh_cm,
            "height_m": entry.height_m
        } for entry in entries])
        
        print(f"X bounds: [{df['x'].min():.2f}, {df['x'].max():.2f}]")
        print(f"Y bounds: [{df['y'].min():.2f}, {df['y'].max():.2f}]")
        
        # Test UTM Zone 48S
        df_proj_48 = project_coordinates(
            df,
            projection_system="UTM Zone 48S - WGS 84 (Jakarta, BSD, Banten)",
            scale_factor=1.0
        )
        print(f"UTM 48S projection Lat bounds: [{df_proj_48['lat'].min():.6f}, {df_proj_48['lat'].max():.6f}]")
        print(f"UTM 48S projection Lon bounds: [{df_proj_48['lon'].min():.6f}, {df_proj_48['lon'].max():.6f}]")

        # Test UTM Zone 49S
        df_proj_49 = project_coordinates(
            df,
            projection_system="UTM Zone 49S - WGS 84 (Central/East Java, Yogyakarta, Bali)",
            scale_factor=1.0
        )
        print(f"UTM 49S projection Lat bounds: [{df_proj_49['lat'].min():.6f}, {df_proj_49['lat'].max():.6f}]")
        print(f"UTM 49S projection Lon bounds: [{df_proj_49['lon'].min():.6f}, {df_proj_49['lon'].max():.6f}]")

    except Exception as e:
        print(f"Failed to process {p.name}: {e}")
