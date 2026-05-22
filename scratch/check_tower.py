"""Check Tower Tree and Sikat Botol blocks."""
import sys
sys.path.insert(0, r"D:\Leonanda's Professional Vault\Projects\itree-sea")
import ezdxf

doc = ezdxf.readfile(r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf")
msp = doc.modelspace()

# Check all inserts on LA-POHON
blocks_on_layer = {}
for e in msp:
    if e.dxftype() == "INSERT" and e.dxf.layer == "LA-POHON":
        name = e.dxf.name
        blocks_on_layer[name] = blocks_on_layer.get(name, 0) + 1

print("All blocks on LA-POHON:")
for name, cnt in sorted(blocks_on_layer.items(), key=lambda x: -x[1]):
    print(f"  {name}: {cnt}")

# Check what Tower Tree resolves to
from itree_sea.cad_bridge import _resolve_block_name
for bn in ["LA_Tower Tree_2M", "LA_Sikat Botol_2M", "LA_Baobab_3M"]:
    r = _resolve_block_name(bn)
    print(f"\n_resolve_block_name('{bn}') -> {r}")
