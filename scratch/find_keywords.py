with open("itree_sea/dashboard.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

keywords = ["map", "mapbox", "folium", "pydeck", "plotly", "scatter", "px."]
for i, line in enumerate(lines):
    for kw in keywords:
        if kw in line.lower():
            print(f"Line {i+1}: {kw:10s} | {line.strip()[:100]}")
            break
