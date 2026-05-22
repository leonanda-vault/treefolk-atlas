import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("scratch/gkb_inserts_raw.csv")

# Filter out the one extreme outlier for the plot
median_x = df["x"].median()
median_y = df["y"].median()
df_clean = df[(df["x"] - median_x).abs() < 100000]

plt.figure(figsize=(10, 8))
colors = {
    "LA_Ketapang Laut_3M": "green",
    "LA_TREE PLANTING$0$LA_Damar_4M": "blue",
    "LA_Sikat Botol_2M": "red",
    "LA_Tower Tree_2M": "cyan",
    "LA_TREE PLANTING$0$LA_Leda_4M": "magenta",
    "LA_TREE PLANTING$0$LA_Pulai_4M": "yellow",
    "LA_TREE PLANTING$0$LA_Flamboyan_6M": "orange",
    "LA_TREE PLANTING$0$LA_Trembesi_6M": "black",
    "LA_Baobab_3M": "purple"
}

for name, group in df_clean.groupby("name"):
    color = colors.get(name, "gray")
    plt.scatter(group["x"], group["y"], label=name, color=color, alpha=0.6, s=15)

plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.title("GKB DXF Raw Coordinate Layout (Cleaned of Outliers)")
plt.xlabel("X")
plt.ylabel("Y")
plt.grid(True)
plt.tight_layout()

# Save the plot
plot_path = "artifacts/raw_coords_plot.png"
plt.savefig(plot_path, dpi=150)
print(f"Saved scatter plot to {plot_path}")
