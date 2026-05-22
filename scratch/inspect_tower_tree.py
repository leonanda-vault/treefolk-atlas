import pandas as pd
df = pd.read_csv("scratch/gkb_inserts_raw.csv")
tower_trees = df[df["name"] == "LA_Tower Tree_2M"]
print(tower_trees.to_string())
