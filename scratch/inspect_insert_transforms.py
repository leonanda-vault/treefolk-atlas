import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from itree_sea.cad_bridge import parse_dxf

dxf_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf"

doc = parse_dxf(dxf_path)
msp = doc.modelspace()

transforms = []
for entity in msp:
    if entity.dxftype() == "INSERT":
        insert = entity
        transforms.append({
            "name": insert.dxf.name,
            "xscale": insert.dxf.xscale,
            "yscale": insert.dxf.yscale,
            "zscale": insert.dxf.zscale,
            "rotation": insert.dxf.rotation,
            "x": insert.dxf.insert.x,
            "y": insert.dxf.insert.y,
        })

df = pd.DataFrame(transforms)
print(df.groupby("name").first())
