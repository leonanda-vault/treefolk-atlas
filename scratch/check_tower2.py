"""Check Tower Tree coordinates."""
import sys
sys.path.insert(0, r"D:\Leonanda's Professional Vault\Projects\itree-sea")
import ezdxf

doc = ezdxf.readfile(r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf")
msp = doc.modelspace()

for e in msp:
    if e.dxftype() == "INSERT" and "Tower Tree" in e.dxf.name:
        pt = e.dxf.insert
        is_legend = abs(pt.x) < 10000 or abs(pt.y) < 100000
        print(f"  {e.dxf.name}: ({pt.x:.1f}, {pt.y:.1f}) {'LEGEND' if is_legend else 'OK'}")
