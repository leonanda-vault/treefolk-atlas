"""
provider.py — QGIS Processing Provider for i-Tree SEA
=======================================================

Groups all i-Tree SEA algorithms under a single provider entry
in the Processing Toolbox.
"""

from __future__ import annotations

from qgis.core import QgsProcessingProvider

from .enrich_tree_layer import EnrichTreeLayerAlgorithm
from .forecast_planting import ForecastPlantingAlgorithm
from .convert_points_to_trees import ConvertPointsToTreesAlgorithm


class ITreeSEAProvider(QgsProcessingProvider):
    """Processing provider that registers all i-Tree SEA algorithms."""

    def loadAlgorithms(self, *args, **kwargs):
        """Register algorithms when the provider is loaded."""
        self.addAlgorithm(EnrichTreeLayerAlgorithm())
        self.addAlgorithm(ForecastPlantingAlgorithm())
        self.addAlgorithm(ConvertPointsToTreesAlgorithm())

    def id(self) -> str:
        return "itree_sea"

    def name(self) -> str:
        return "i-Tree SEA"

    def longName(self) -> str:
        return "i-Tree SEA — Tropical Urban Forest Calculator"

    def icon(self):
        """Return the provider icon (optional)."""
        return QgsProcessingProvider.icon(self)
