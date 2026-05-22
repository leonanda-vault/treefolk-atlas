"""
plugin.py — Main QGIS plugin class
====================================

Registers the i-Tree SEA Processing provider so that the algorithms
appear in the QGIS Processing Toolbox under "i-Tree SEA".

Installation:
  Copy the ``itree_sea_qgis/`` folder into your QGIS plugins directory:
    Windows:  %APPDATA%/QGIS/QGIS3/profiles/default/python/plugins/
    Linux:    ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
    macOS:    ~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/

  Then enable "i-Tree SEA" in the Plugin Manager.

Dependencies:
  The ``itree_sea`` core package must be importable.  Install it with:
    pip install -e /path/to/itree-sea[gis]
  using the Python interpreter that QGIS uses (check via QGIS Python console).
"""

from __future__ import annotations

from qgis.core import QgsApplication

from .processing.provider import ITreeSEAProvider


class ITreeSEAPlugin:
    """Main plugin class — lifecycle management only.

    All actual computation lives in the Processing algorithms.
    This class only registers and unregisters the provider.
    """

    def __init__(self, iface):
        """
        Parameters
        ----------
        iface : QgisInterface
            QGIS application interface (provides access to the
            main window, map canvas, menus, etc.).
        """
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        """Create and register the Processing provider."""
        self.provider = ITreeSEAProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        """Called when the plugin is activated in the Plugin Manager."""
        self.initProcessing()

    def unload(self):
        """Called when the plugin is deactivated."""
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
