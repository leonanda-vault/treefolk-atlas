"""
Create a sample DXF planting plan for testing the CAD pipeline.
This script generates a DXF file with tree block inserts on the
L-PLNT-TREE-PROP layer, each with SPECIES and CALIPER attributes.
"""

import ezdxf

doc = ezdxf.new("R2010")
msp = doc.modelspace()

# ── Define tree blocks with ATTDEF tags ──

trees_to_place = [
    {
        "block": "TREE_8m_SPREAD",
        "species": "Pterocarpus indicus",
        "caliper": "5",
        "position": (10.0, 20.0),
    },
    {
        "block": "TREE_8m_SPREAD",
        "species": "Pterocarpus indicus",
        "caliper": "5",
        "position": (25.0, 20.0),
    },
    {
        "block": "TREE_10m_SPREAD",
        "species": "Samanea saman",
        "caliper": "7",
        "position": (40.0, 30.0),
    },
    {
        "block": "TREE_6m_OVAL",
        "species": "Terminalia catappa",
        "caliper": "5",
        "position": (55.0, 25.0),
    },
    {
        "block": "TREE_6m_OVAL",
        "species": "Syzygium grande",
        "caliper": "5",
        "position": (70.0, 25.0),
    },
    {
        "block": "PALM_8m",
        "species": "Cocos nucifera",
        "caliper": "15",
        "position": (85.0, 15.0),
    },
    {
        "block": "PALM_8m",
        "species": "Cocos nucifera",
        "caliper": "15",
        "position": (85.0, 35.0),
    },
    {
        "block": "TREE_10m_SPREAD",
        "species": "Ficus benjamina",
        "caliper": "5",
        "position": (100.0, 20.0),
    },
    {
        "block": "TREE_4m_COLUMNAR",
        "species": "Cassia fistula",
        "caliper": "5",
        "position": (115.0, 20.0),
    },
    {
        "block": "TREE_8m_SPREAD",
        "species": "Cyrtophyllum fragrans",
        "caliper": "5",
        "position": (130.0, 20.0),
    },
    {
        "block": "TREE_8m_SPREAD",
        "species": "Tectona grandis",
        "caliper": "7",
        "position": (15.0, 50.0),
    },
    {
        "block": "TREE_6m_OVAL",
        "species": "Tabebuia rosea",
        "caliper": "5",
        "position": (30.0, 50.0),
    },
]

# ── Create block definitions ──
block_names_created = set()

for tree in trees_to_place:
    bname = tree["block"]
    if bname not in block_names_created:
        blk = doc.blocks.new(name=bname)
        # Simple trunk circle
        blk.add_circle((0, 0), radius=0.3)
        # Canopy circle
        canopy_r = 4.0
        if "4m" in bname:
            canopy_r = 2.0
        elif "6m" in bname:
            canopy_r = 3.0
        elif "8m" in bname:
            canopy_r = 4.0
        elif "10m" in bname:
            canopy_r = 5.0
        blk.add_circle((0, 0), radius=canopy_r)
        # Attribute definitions
        blk.add_attdef("SPECIES", insert=(0, -canopy_r - 0.5), dxfattribs={"height": 0.3})
        blk.add_attdef("CALIPER", insert=(0, -canopy_r - 1.0), dxfattribs={"height": 0.25})
        block_names_created.add(bname)

# ── Create the planting layer ──
doc.layers.add("L-PLNT-TREE-PROP", color=3)  # green

# ── Insert blocks ──
for i, tree in enumerate(trees_to_place, start=1):
    insert = msp.add_blockref(
        tree["block"],
        tree["position"],
        dxfattribs={"layer": "L-PLNT-TREE-PROP"},
    )
    insert.add_auto_attribs({
        "SPECIES": tree["species"],
        "CALIPER": tree["caliper"],
    })

# ── Save ──
output_path = r"d:\Leonanda's Professional Vault\Projects\itree-sea\data\sample_planting.dxf"
doc.saveas(output_path)
print(f"Created sample DXF: {output_path}")
print(f"  {len(trees_to_place)} trees on L-PLNT-TREE-PROP")
