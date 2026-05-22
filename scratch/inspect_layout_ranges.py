import pandas as pd
df = pd.read_csv("scratch/gkb_inserts_raw.csv")

# Filter out the extreme outlier
median_x = df["x"].median()
median_y = df["y"].median()
df_clean = df[(df["x"] - median_x).abs() < 100000].copy()

legend_handles = ["78BCAD", "78BCAE", "78BCAF", "78BCB0", "78BCB1", "78BCC0", "78BCC1"]
df_layout = df_clean[~df_clean["handle"].isin(legend_handles)].copy()

print("--- Layout Inserts (Excluding Legend Handles) ---")
print(f"Total inserts in layout: {len(df_layout)}")

for name, group in df_layout.groupby("name"):
    print(f"\nSpecies: {name}")
    print(f"  Count: {len(group)}")
    print(f"  X Range: [{group['x'].min():.2f}, {group['x'].max():.2f}] (diff: {group['x'].max() - group['x'].min():.2f})")
    print(f"  Y Range: [{group['y'].min():.2f}, {group['y'].max():.2f}] (diff: {group['y'].max() - group['y'].min():.2f})")
    print(f"  Centroid: ({group['x'].mean():.2f}, {group['y'].mean():.2f})")
