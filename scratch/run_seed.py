import sys
import os

sys.path.insert(0, r"D:\Leonanda's Professional Vault\Projects\itree-sea")

from itree_sea.database import seed_from_csv

try:
    print("Seeding database from CSV...")
    inserted = seed_from_csv()
    print(f"Successfully seeded {inserted} species into the database.")
except Exception as e:
    print(f"Error seeding database: {e}")
