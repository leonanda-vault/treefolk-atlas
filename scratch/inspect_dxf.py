import ezdxf
from collections import Counter

dxf_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\SAMPLE FOR I TREE SEA DEVELOPMENT\PLANTING PLAN\LA-TREE PLANTING.dxf"

try:
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()
    
    blocks = []
    texts = []
    
    for entity in msp:
        if entity.dxftype() == 'INSERT':
            blocks.append(entity.dxf.name)
        elif entity.dxftype() in ['TEXT', 'MTEXT']:
            texts.append(entity.text)
            
    block_counts = Counter(blocks)
    
    print("--- BLOCK COUNTS ---")
    for b, c in block_counts.most_common():
        print(f"{b}: {c}")
        
    print("\n--- SAMPLE TEXTS ---")
    for t in texts[:20]:
        print(t)
        
except Exception as e:
    print(f"Error parsing DXF: {e}")
