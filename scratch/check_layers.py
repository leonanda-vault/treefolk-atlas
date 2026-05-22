import ezdxf
import sys

dxf_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-TREE PLANTING.dxf"

doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

layer_entities = {}
for entity in msp:
    layer = entity.dxf.layer
    etype = entity.dxftype()
    
    if layer not in layer_entities:
        layer_entities[layer] = {}
    
    if etype not in layer_entities[layer]:
        layer_entities[layer][etype] = 0
    layer_entities[layer][etype] += 1

print("Entities per layer:")
for layer, counts in sorted(layer_entities.items()):
    if "LA-" in layer:
        print(f"Layer '{layer}': {counts}")
