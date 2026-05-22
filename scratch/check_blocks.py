import ezdxf
import sys
from collections import Counter

dxf_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-TREE PLANTING.dxf"

doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

block_names_by_layer = {}
for entity in msp:
    if entity.dxftype() == "INSERT":
        layer = entity.dxf.layer
        block_name = entity.dxf.name
        
        if layer not in block_names_by_layer:
            block_names_by_layer[layer] = Counter()
        block_names_by_layer[layer][block_name] += 1

print("Block names per layer:")
for layer, blocks in sorted(block_names_by_layer.items()):
    if "LA-" in layer:
        print(f"Layer '{layer}':")
        for block_name, count in blocks.most_common():
            print(f"  - {block_name}: {count}")
