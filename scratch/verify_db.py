"""Verify new species in DB."""
import sqlite3
db = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\itree_sea.db"
conn = sqlite3.connect(db)
cur = conn.cursor()
for sp in ["Plumeria obtusa", "Pandanus baptistii", "Callistemon viminalis", "Adansonia digitata"]:
    cur.execute("SELECT scientific_name, common_name FROM species_lookup WHERE scientific_name = ?", (sp,))
    row = cur.fetchone()
    print(f"  {'OK' if row else 'MISSING'}: {sp} -> {row}")
cur.execute("SELECT COUNT(*) FROM species_lookup")
print(f"Total species: {cur.fetchone()[0]}")
conn.close()
