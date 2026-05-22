"""Add missing columns to DB and re-seed."""
import sqlite3, sys
sys.path.insert(0, r"D:\Leonanda's Professional Vault\Projects\itree-sea")
from itree_sea.config import DATABASE_PATH, SEED_CSV_PATH

db = str(DATABASE_PATH)
conn = sqlite3.connect(db)
cur = conn.cursor()

# Check existing columns
cur.execute("PRAGMA table_info(allometric_coefficients)")
cols = [r[1] for r in cur.fetchall()]
print(f"Existing columns: {cols}")

# Add missing columns
for col_name, col_type, col_default in [
    ("height_model_form", "TEXT", "'power'"),
    ("height_model_c", "REAL", "NULL"),
]:
    if col_name not in cols:
        sql = f"ALTER TABLE allometric_coefficients ADD COLUMN {col_name} {col_type} DEFAULT {col_default}"
        print(f"Adding column: {col_name}")
        cur.execute(sql)

conn.commit()
conn.close()

# Now re-seed
from itree_sea.database import seed_from_csv
count = seed_from_csv()
print(f"Seeded {count} species rows")

# Verify
conn = sqlite3.connect(db)
cur = conn.cursor()
for sp in ["Plumeria obtusa", "Pandanus baptistii", "Callistemon viminalis", "Adansonia digitata"]:
    cur.execute("SELECT scientific_name, common_name FROM species_lookup WHERE scientific_name = ?", (sp,))
    row = cur.fetchone()
    if row:
        print(f"  ✅ {row[0]} ({row[1]})")
    else:
        print(f"  ❌ {sp} NOT FOUND")

cur.execute("SELECT COUNT(*) FROM species_lookup")
print(f"\nTotal species in DB: {cur.fetchone()[0]}")
conn.close()
