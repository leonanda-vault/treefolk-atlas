import pandas as pd
import numpy as np

df = pd.read_csv("scratch/gkb_inserts_raw.csv")

# Filter out the extreme outlier
median_x = df["x"].median()
median_y = df["y"].median()
df_clean = df[(df["x"] - median_x).abs() < 100000].copy()

print("--- Cleaned Inserts Summary ---")
print(f"Total inserts after filtering: {len(df_clean)}")

for name, group in df_clean.groupby("name"):
    print(f"\nSpecies: {name}")
    print(f"  Count: {len(group)}")
    print(f"  X Range: [{group['x'].min():.2f}, {group['x'].max():.2f}] (diff: {group['x'].max() - group['x'].min():.2f})")
    print(f"  Y Range: [{group['y'].min():.2f}, {group['y'].max():.2f}] (diff: {group['y'].max() - group['y'].min():.2f})")
    print(f"  Centroid: ({group['x'].mean():.2f}, {group['y'].mean():.2f})")
    print(f"  Std Dev: X={group['x'].std():.2f}, Y={group['y'].std():.2f}")
