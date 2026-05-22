import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
from itree_sea.simulation import project_coordinates

df = pd.read_csv("scratch/gkb_inserts_raw.csv")

# Filter out the extreme outlier
median_x = df["x"].median()
median_y = df["y"].median()
df_clean = df[(df["x"] - median_x).abs() < 100000].copy()

# Project coordinates using UTM Zone 48S
df_proj = project_coordinates(
    df_clean,
    projection_system="UTM Zone 48S - WGS 84 (Jakarta, BSD, Banten)",
    scale_factor=1.0
)

# Print unique species and their projected centroids
for name, group in df_proj.groupby("name"):
    print(f"\nSpecies: {name}")
    print(f"  Count: {len(group)}")
    print(f"  Lat Range: [{group['lat'].min():.6f}, {group['lat'].max():.6f}]")
    print(f"  Lon Range: [{group['lon'].min():.6f}, {group['lon'].max():.6f}]")
    print(f"  Projected Centroid Lat/Lon: ({group['lat'].mean():.6f}, {group['lon'].mean():.6f})")
