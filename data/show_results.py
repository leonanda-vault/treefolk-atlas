"""Show results from the LA-POHON pipeline run."""
import pandas as pd

summary = pd.read_csv(r"D:\Leonanda's Professional Vault\Projects\itree-sea\output\la_pohon_summary.csv")
schedule = pd.read_csv(r"D:\Leonanda's Professional Vault\Projects\itree-sea\output\la_pohon_schedule.csv")

print(f"=== LA-POHON.dxf Results ===")
print(f"Total trees processed:    {len(summary)}")
print(f"Schedule rows:            {len(schedule)}")

print(f"\n=== By Layer ===")
print(summary.groupby("layer").size().to_string())

print(f"\n=== By Species ===")
print(summary.groupby("species").size().sort_values(ascending=False).to_string())

print(f"\n=== Match Levels ===")
print(summary.groupby("match_level").size().to_string())

print(f"\n=== Totals at Year 25 ===")
print(f"Carbon stored:          {summary['carbon_storage_kg'].sum():,.1f} kg  ({summary['carbon_storage_kg'].sum()/1000:,.2f} tonnes)")
print(f"Annual sequestration:   {summary['carbon_seq_kg'].sum():,.1f} kg/yr")
print(f"Stormwater intercepted: {summary['stormwater_l'].sum():,.0f} L/yr")
print(f"Cumulative seq (25yr):  {summary['cumulative_seq_kg'].sum():,.1f} kg  ({summary['cumulative_seq_kg'].sum()/1000:,.2f} tonnes)")

print(f"\n=== Top 5 Carbon Contributors (at Year 25) ===")
top5 = summary.nlargest(5, "carbon_storage_kg")[["tree_id", "block_name", "species", "dbh_cm", "carbon_storage_kg"]]
print(top5.to_string(index=False))

print(f"\n=== Carbon by Species (sorted) ===")
sp_carbon = summary.groupby("species")["carbon_storage_kg"].agg(["sum", "count", "mean"]).sort_values("sum", ascending=False)
sp_carbon.columns = ["total_kg", "count", "avg_kg"]
print(sp_carbon.to_string())
