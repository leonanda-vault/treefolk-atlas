import pandas as pd
import numpy as np
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
GWDD_PATH = ROOT_DIR / "references" / "gwdd_v2.2.csv"
SEED_PATH = ROOT_DIR / "data" / "seed_species.csv"

def main():
    if not GWDD_PATH.exists() or not SEED_PATH.exists():
        logging.error("Missing GWDD or seed CSV files.")
        return

    logging.info(f"Loading GWDD from {GWDD_PATH}...")
    # Load GWDD. Some columns have mixed types, we only care about 'species' and 'wsg'
    gwdd_df = pd.read_csv(GWDD_PATH, usecols=["species", "wsg"], low_memory=False)
    
    # Calculate mean wood specific gravity (wsg) per species
    gwdd_df['species'] = gwdd_df['species'].str.strip().str.lower()
    # Drop rows with NaN wsg
    gwdd_df = gwdd_df.dropna(subset=['wsg'])
    wsg_means = gwdd_df.groupby('species')['wsg'].mean().to_dict()

    logging.info(f"Loaded {len(wsg_means)} species from GWDD with valid wsg.")

    logging.info(f"Loading seed_species.csv from {SEED_PATH}...")
    seed_df = pd.read_csv(SEED_PATH, sep=",")
    
    # Rename 'source;;;' to 'source' if needed
    seed_df.columns = [col.replace(';', '') for col in seed_df.columns]
    
    updated_count = 0
    missing_count = 0

    for idx, row in seed_df.iterrows():
        sci_name = str(row['scientific_name']).strip().lower()
        if sci_name in wsg_means:
            mean_wsg = wsg_means[sci_name]
            seed_df.at[idx, 'wood_density'] = round(mean_wsg, 3)
            # Update source note if we are overwriting
            source_note = str(row['source'])
            if 'GWDD' not in source_note:
                seed_df.at[idx, 'source'] = f"{source_note}; GWDD v2.2".strip(';')
            updated_count += 1
        else:
            missing_count += 1
            logging.debug(f"Species not found in GWDD: {sci_name}")

    logging.info(f"Updated {updated_count} species with GWDD wood density.")
    logging.info(f"{missing_count} species were not found in GWDD.")

    # Save back to CSV
    seed_df.to_csv(SEED_PATH, index=False)
    logging.info("Saved updated seed_species.csv")

if __name__ == "__main__":
    main()
