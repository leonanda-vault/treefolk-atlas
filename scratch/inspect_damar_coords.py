import pandas as pd
df = pd.read_csv("scratch/gkb_inserts_raw.csv")
damar = df[df["name"] == "LA_TREE PLANTING$0$LA_Damar_4M"]
print(damar.to_string())
