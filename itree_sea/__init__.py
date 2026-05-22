"""
Treefolk Atlas — Southeast Asian Urban Forest Carbon Calculator
============================================================

An open-source Python bridge replicating core i-Tree Eco carbon
calculations, tailored for tropical species in Singapore and Indonesia.

Provides two pipelines:
  • GIS Bridge  — GeoJSON/Shapefile → enriched ecosystem benefit layers
  • CAD Bridge  — DXF planting plans → CSV planting benefit schedules

Mathematical foundation:
  Chave et al. (2014) pantropical allometric model,
  USFS i-Tree Eco carbon storage / sequestration methodology,
  simplified proxy models for stormwater interception and air
  pollution removal using area-based constants.
"""

__version__ = "0.1.0"
__author__ = "Leonanda"
__license__ = "MIT"
