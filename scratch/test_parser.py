"""Test parser against both new DXF files."""
import sys, logging
sys.path.insert(0, r"D:\Leonanda's Professional Vault\Projects\itree-sea")

logging.basicConfig(level=logging.INFO)

from itree_sea.cad_bridge import parse_dxf, extract_planting_blocks

files = [
    (r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-TREE PLAN 1ST FLOOR.dxf",
     ["LA-Phn KAMBOJA PUTIH FOSIL", "LA-Phn PANDAN BALI", "LA-Phn TANJUNG", "LA-Phn KAMBOJA PUTIH"]),
    (r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf",
     ["LA-POHON"]),
]

for path, layers in files:
    print("=" * 70)
    print(f"FILE: {path.split(chr(92))[-1]}")
    print("=" * 70)
    
    doc = parse_dxf(path)
    entries = extract_planting_blocks(doc, layers)
    
    print(f"Extracted {len(entries)} trees")
    
    # Summary by species
    species_count = {}
    for e in entries:
        species_count[e.species_name] = species_count.get(e.species_name, 0) + 1
    
    print("\nSpecies breakdown:")
    for sp, cnt in sorted(species_count.items(), key=lambda x: -x[1]):
        print(f"  {sp}: {cnt}")
    
    # Show a few entries with height
    print("\nSample entries (first 5):")
    for e in entries[:5]:
        print(f"  {e.block_name} -> {e.species_name} | DBH: {e.dbh_cm}cm | H: {e.height_m}m | ({e.x:.1f}, {e.y:.1f}) [{e.layer}]")
    
    # Check coordinate ranges
    xs = [e.x for e in entries]
    ys = [e.y for e in entries]
    if xs:
        print(f"\nCoord ranges: X=[{min(xs):.1f}, {max(xs):.1f}], Y=[{min(ys):.1f}, {max(ys):.1f}]")
    print()
