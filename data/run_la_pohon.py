"""Run i-Tree SEA on the real LA-POHON.dxf planting plan."""
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s  %(message)s")

from itree_sea.cad_bridge import run_cad_pipeline

DXF = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-POHON.dxf"
OUT = r"D:\Leonanda's Professional Vault\Projects\itree-sea\output\la_pohon_schedule.csv"
SUM = r"D:\Leonanda's Professional Vault\Projects\itree-sea\output\la_pohon_summary.csv"

schedule_path, summary_path = run_cad_pipeline(
    dxf_path=DXF,
    output_csv=OUT,
    summary_csv=SUM,
    forecast_years=25,
)

print(f"\n✓ Schedule: {schedule_path}")
print(f"✓ Summary:  {summary_path}")

# Quick stats
import pandas as pd
summary = pd.read_csv(str(summary_path))
schedule = pd.read_csv(str(schedule_path))

print(f"\n=== Results ===")
print(f"Total trees processed:    {len(summary)}")
print(f"Schedule rows:            {len(schedule)}")
print(f"\n=== By Layer ===")
print(summary.groupby("layer").size().to_string())
print(f"\n=== By Species ===")
print(summary.groupby("species").size().sort_values(ascending=False).to_string())
print(f"\n=== Match Levels ===")
print(summary.groupby("match_level").size().to_string())
print(f"\n=== Totals at Year 25 ===")
print(f"Carbon stored:         {summary['carbon_storage_kg'].sum():,.1f} kg")
print(f"Annual sequestration:  {summary['carbon_seq_kg'].sum():,.1f} kg/yr")
print(f"Stormwater intercepted:{summary['stormwater_l'].sum():,.0f} L/yr")
print(f"Cumulative seq (25yr): {summary['cumulative_seq_kg'].sum():,.1f} kg")
