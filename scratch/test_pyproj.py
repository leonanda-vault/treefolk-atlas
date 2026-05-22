try:
    from pyproj import Transformer
    transformer = Transformer.from_crs("epsg:32748", "epsg:4326", always_xy=True)
    lon, lat = transformer.transform(717046.3, 9309189.1)
    print(f"pyproj loaded successfully. Projected coordinates: lon={lon:.6f}, lat={lat:.6f}")
except Exception as e:
    print(f"pyproj import/execution failed: {e}")
