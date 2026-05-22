import pandas as pd
df = pd.read_csv("scratch/gkb_inserts_raw.csv")

# Filter out the extreme outlier
median_x = df["x"].median()
median_y = df["y"].median()
df_clean = df[(df["x"] - median_x).abs() < 100000].copy()

# Print blocks on the far east side or far south side
east_south = df_clean[(df_clean["x"] > 716900) | (df_clean["y"] < 9309100)]
print(east_south.to_string())
