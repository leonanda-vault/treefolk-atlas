"""Check existing species in the database."""
import sqlite3, os

db_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\itree_sea\data\itree_sea.db"
if not os.path.exists(db_path):
    # Try alternate paths
    for alt in [
        r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\itree_sea.db",
        r"D:\Leonanda's Professional Vault\Projects\itree-sea\itree_sea\itree_sea.db",
    ]:
        if os.path.exists(alt):
            db_path = alt
            break

print(f"DB path: {db_path}")
print(f"Exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # List tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(f"\nTables: {[r[0] for r in cur.fetchall()]}")
    
    # Count species
    cur.execute("SELECT COUNT(*) FROM species_lookup")
    print(f"Species count: {cur.fetchone()[0]}")
    
    # List all species
    cur.execute("SELECT scientific_name, common_name, genus FROM species_lookup ORDER BY scientific_name")
    print("\nAll species:")
    for row in cur.fetchall():
        print(f"  {row[0]} ({row[1]}) — genus: {row[2]}")
    
    conn.close()
