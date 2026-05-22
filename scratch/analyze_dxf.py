"""Analyze the two new DXF files to understand their structure."""
import ezdxf
import os

files = [
    r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-TREE PLAN 1ST FLOOR.dxf",
    r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA_PLANTING PLAN TREE GKB_WARNA SOLID TREE_Update.dxf",
]

for filepath in files:
    print("=" * 80)
    print(f"FILE: {os.path.basename(filepath)}")
    print("=" * 80)
    
    if not os.path.exists(filepath):
        print(f"  FILE NOT FOUND: {filepath}")
        continue
    
    doc = ezdxf.readfile(filepath)
    
    # Layers
    print("\nLayers:")
    for layer in doc.layers:
        if not layer.dxf.name.startswith("*"):
            print(f"  {layer.dxf.name}")
    
    msp = doc.modelspace()
    
    # Entity type counts
    entity_types = {}
    for e in msp:
        t = e.dxftype()
        entity_types[t] = entity_types.get(t, 0) + 1
    print(f"\nEntity types: {entity_types}")
    
    # INSERT entities (blocks)
    inserts = [e for e in msp if e.dxftype() == "INSERT"]
    print(f"\nTotal INSERTs: {len(inserts)}")
    
    block_names = {}
    for ins in inserts:
        name = ins.dxf.name
        layer = ins.dxf.layer
        key = (name, layer)
        block_names[key] = block_names.get(key, 0) + 1
    
    print("\nBlock names + layers (top 40):")
    for (name, layer), count in sorted(block_names.items(), key=lambda x: -x[1])[:40]:
        print(f"  {name} [layer: {layer}]: {count}")
    
    # Check for tree-related blocks
    tree_keywords = ["TREE", "POHON", "PHN", "PLNT", "PLANT", "TAMAN", "PALM", "PALEM"]
    print("\nTree-related blocks:")
    for (name, layer), count in sorted(block_names.items(), key=lambda x: -x[1]):
        if any(kw in name.upper() for kw in tree_keywords) or any(kw in layer.upper() for kw in tree_keywords):
            print(f"  {name} [layer: {layer}]: {count}")
    
    # Sample attributes from all inserts
    print("\nSample block attributes (first 20 with attributes):")
    attr_count = 0
    for ins in inserts:
        attrs = {a.dxf.tag: a.dxf.text for a in ins.attribs}
        if attrs:
            print(f"  Block '{ins.dxf.name}' [layer: {ins.dxf.layer}]: {attrs}")
            attr_count += 1
            if attr_count >= 20:
                break
    
    if attr_count == 0:
        print("  (No blocks with attributes found)")
    
    # Check MTEXT entities for tree names / caliper info
    mtexts = [e for e in msp if e.dxftype() == "MTEXT"]
    texts = [e for e in msp if e.dxftype() == "TEXT"]
    print(f"\nMTEXT count: {len(mtexts)}, TEXT count: {len(texts)}")
    
    # Sample MTEXT
    print("\nSample MTEXT (first 30):")
    for mt in mtexts[:30]:
        raw = mt.dxf.text if hasattr(mt.dxf, 'text') else mt.text
        print(f"  [{mt.dxf.layer}] ({mt.dxf.insert.x:.1f}, {mt.dxf.insert.y:.1f}): {repr(raw[:100])}")
    
    # Sample TEXT
    print("\nSample TEXT (first 30):")
    for tx in texts[:30]:
        raw = tx.dxf.text
        print(f"  [{tx.dxf.layer}] ({tx.dxf.insert.x:.1f}, {tx.dxf.insert.y:.1f}): {repr(raw[:100])}")
    
    # Coordinate ranges
    xs = [ins.dxf.insert.x for ins in inserts]
    ys = [ins.dxf.insert.y for ins in inserts]
    if xs:
        print(f"\nCoordinate ranges: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}]")
    
    print()
