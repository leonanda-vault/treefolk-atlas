import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.append(str(Path(__file__).parent.parent))
from itree_sea.cad_bridge import parse_dxf

dxf_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf"

doc = parse_dxf(dxf_path)
msp = doc.modelspace()

# Step 1: Pre-calculate block centroids
block_offsets = {}
for block in doc.blocks:
    if block.name.startswith("*") or block.name.startswith("Paper_Space") or block.name.startswith("Model_Space"):
        continue
    
    # Collect circle centers
    circle_pts = []
    other_pts = []
    
    for entity in block:
        if entity.dxftype() == "CIRCLE":
            circle_pts.append((entity.dxf.center.x, entity.dxf.center.y))
        elif entity.dxftype() == "LWPOLYLINE":
            for vertex in entity.vertices():
                other_pts.append((vertex[0], vertex[1]))
        elif entity.dxftype() == "LINE":
            other_pts.append((entity.dxf.start.x, entity.dxf.start.y))
            other_pts.append((entity.dxf.end.x, entity.dxf.end.y))
            
    # Use circle center if available, otherwise fallback to other geometry
    if circle_pts:
        dx = np.mean([p[0] for p in circle_pts])
        dy = np.mean([p[1] for p in circle_pts])
    elif other_pts:
        dx = np.mean([p[0] for p in other_pts])
        dy = np.mean([p[1] for p in other_pts])
    else:
        dx, dy = 0.0, 0.0
        
    block_offsets[block.name] = (dx, dy)
    print(f"Block: {block.name:35s} | Offset: ({dx:10.2f}, {dy:10.2f})")

# Step 2: Compute visual coordinates for inserts
inserts = []
for entity in msp:
    if entity.dxftype() == "INSERT":
        insert = entity
        name = insert.dxf.name
        pt = insert.dxf.insert
        xscale = insert.dxf.xscale
        yscale = insert.dxf.yscale
        
        dx, dy = block_offsets.get(name, (0.0, 0.0))
        
        # Apply transformation: insertion point + scaled geometry offset
        x_vis = pt.x + dx * xscale
        y_vis = pt.y + dy * yscale
        
        inserts.append({
            "handle": insert.dxf.handle,
            "name": name,
            "layer": insert.dxf.layer,
            "x_ins": pt.x,
            "y_ins": pt.y,
            "x_vis": x_vis,
            "y_vis": y_vis
        })

df = pd.DataFrame(inserts)

# Filter out the legend handles we identified earlier
legend_handles = ["78BCAD", "78BCAE", "78BCAF", "78BCB0", "78BCB1", "78BCC0", "78BCC1"]
df_layout = df[~df["handle"].isin(legend_handles)].copy()

# Also filter out the extreme outlier at 10 million (it was a Tower Tree legend/block far away)
df_layout = df_layout[df_layout["x_vis"] < 1000000]

print("\n--- Visual Coordinate Ranges by Species (Excluding Legend & Outliers) ---")
for name, group in df_layout.groupby("name"):
    print(f"\nSpecies: {name}")
    print(f"  Count: {len(group)}")
    print(f"  Visual X Range: [{group['x_vis'].min():.2f}, {group['x_vis'].max():.2f}] (diff: {group['x_vis'].max() - group['x_vis'].min():.2f})")
    print(f"  Visual Y Range: [{group['y_vis'].min():.2f}, {group['y_vis'].max():.2f}] (diff: {group['y_vis'].max() - group['y_vis'].min():.2f})")
    print(f"  Visual Centroid: ({group['x_vis'].mean():.2f}, {group['y_vis'].mean():.2f})")

print("\n--- Overall Visual Bounds of Site Layout ---")
print(f"Visual X Bounds: [{df_layout['x_vis'].min():.2f}, {df_layout['x_vis'].max():.2f}] (diff: {df_layout['x_vis'].max() - df_layout['x_vis'].min():.2f})")
print(f"Visual Y Bounds: [{df_layout['y_vis'].min():.2f}, {df_layout['y_vis'].max():.2f}] (diff: {df_layout['y_vis'].max() - df_layout['y_vis'].min():.2f})")
