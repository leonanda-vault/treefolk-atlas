import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent))
from itree_sea.cad_bridge import parse_dxf

dxf_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf"

doc = parse_dxf(dxf_path)
msp = doc.modelspace()

inserts = []
for entity in msp:
    if entity.dxftype() == "INSERT":
        insert = entity
        pt = insert.dxf.insert
        inserts.append({
            "handle": insert.dxf.handle,
            "name": insert.dxf.name,
            "layer": insert.dxf.layer,
            "x": pt.x,
            "y": pt.y,
        })

df = pd.DataFrame(inserts)
print(f"Total INSERT entities in modelspace: {len(df)}")
print("\nUnique block names and their counts:")
print(df["name"].value_counts().head(30))

print("\nLayer counts for INSERTs:")
print(df["layer"].value_counts())

# Group by name and show min/max coords
print("\nCoordinate ranges by block name:")
grouped = df.groupby("name").agg(
    count=("x", "count"),
    min_x=("x", "min"),
    max_x=("x", "max"),
    min_y=("y", "min"),
    max_y=("y", "max")
)
print(grouped.to_string())

# Save to CSV for detailed analysis
df.to_csv("scratch/gkb_inserts_raw.csv", index=False)
print("\nSaved raw inserts to scratch/gkb_inserts_raw.csv")
