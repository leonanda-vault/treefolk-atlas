"""Deep analysis of the planting plan DXF — counts by layer and block name."""
import ezdxf
from collections import Counter

dxf_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-POHON.dxf"
doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

# Count inserts by layer
layer_counts = Counter()
# Count inserts by block name
block_counts = Counter()
# Count by (layer, block_name)
combo_counts = Counter()

for e in msp:
    if e.dxftype() == "INSERT":
        layer = e.dxf.layer
        name = e.dxf.name
        layer_counts[layer] += 1
        block_counts[name] += 1
        combo_counts[(layer, name)] += 1

print("=== INSERTS by Layer ===")
for layer, c in layer_counts.most_common():
    print(f"  {layer}: {c}")

print("\n=== INSERTS by Block Name ===")
for name, c in block_counts.most_common():
    print(f"  {name}: {c}")

print("\n=== New planting (LA-POHON BARU layer) ===")
new_trees = Counter()
for e in msp:
    if e.dxftype() == "INSERT" and e.dxf.layer == "LA-POHON BARU":
        new_trees[e.dxf.name] += 1
for name, c in new_trees.most_common():
    print(f"  {name}: {c}")

print("\n=== Existing to retain (X-POHON TETAP) ===")
retain_trees = Counter()
for e in msp:
    if e.dxftype() == "INSERT" and e.dxf.layer == "X-POHON TETAP":
        retain_trees[e.dxf.name] += 1
for name, c in retain_trees.most_common():
    print(f"  {name}: {c}")

print("\n=== To relocate (X-POHON PINDAHAN) ===")
move_trees = Counter()
for e in msp:
    if e.dxftype() == "INSERT" and e.dxf.layer == "X-POHON PINDAHAN":
        move_trees[e.dxf.name] += 1
for name, c in move_trees.most_common():
    print(f"  {name}: {c}")

print("\n=== To remove (X-POHON DIPINDAH) ===")
remove_trees = Counter()
for e in msp:
    if e.dxftype() == "INSERT" and e.dxf.layer == "X-POHON DIPINDAH":
        remove_trees[e.dxf.name] += 1
for name, c in remove_trees.most_common():
    print(f"  {name}: {c}")

# Check MTEXT on labeling layers for species info
print("\n=== Sample MTEXT labels (first 20) ===")
count = 0
for e in msp:
    if e.dxftype() == "MTEXT":
        layer = e.dxf.layer
        text = e.text[:80] if hasattr(e, 'text') else str(e.dxf.text)[:80]
        print(f"  [{layer}] {text}")
        count += 1
        if count >= 20:
            break
