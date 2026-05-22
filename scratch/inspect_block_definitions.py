import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from itree_sea.cad_bridge import parse_dxf

dxf_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf"

doc = parse_dxf(dxf_path)

print("--- Inspecting Block Definitions ---")
for block in doc.blocks:
    # Skip anonymous blocks or layouts if they don't look like tree blocks
    if block.name.startswith("*") or block.name.startswith("Paper_Space") or block.name.startswith("Model_Space"):
        continue
        
    print(f"\nBlock Name: {block.name}")
    print(f"  Base Point: {block.base_point}")
    
    # Calculate bounding box of entities inside the block
    x_coords = []
    y_coords = []
    entity_types = []
    
    for entity in block:
        entity_types.append(entity.dxftype())
        # Try to get coordinates from common entity types
        if entity.dxftype() == "CIRCLE":
            x_coords.append(entity.dxf.center.x)
            y_coords.append(entity.dxf.center.y)
        elif entity.dxftype() in ("LINE", "POLYLINE", "LWPOLYLINE"):
            # For simplicity, if it's a lightweight polyline
            if entity.dxftype() == "LWPOLYLINE":
                for vertex in entity.vertices():
                    x_coords.append(vertex[0])
                    y_coords.append(vertex[1])
            elif entity.dxftype() == "LINE":
                x_coords.append(entity.dxf.start.x)
                x_coords.append(entity.dxf.end.x)
                y_coords.append(entity.dxf.start.y)
                y_coords.append(entity.dxf.end.y)
                
    if x_coords:
        min_x = min(x_coords)
        max_x = max(x_coords)
        min_y = min(y_coords)
        max_y = max(y_coords)
        mean_x = sum(x_coords) / len(x_coords)
        mean_y = sum(y_coords) / len(y_coords)
        print(f"  Entities: {dict(pd.Series(entity_types).value_counts())}")
        print(f"  Geometry Bounds relative to Base Point:")
        print(f"    X: [{min_x:.2f}, {max_x:.2f}] (mean: {mean_x:.2f})")
        print(f"    Y: [{min_y:.2f}, {max_y:.2f}] (mean: {mean_y:.2f})")
    else:
        print("  No circle or polyline geometry found in block.")
