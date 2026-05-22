"""
i-Tree SEA — QGIS Plugin Entry Point
======================================

This file is loaded by QGIS when the plugin is activated.
It must contain a ``classFactory()`` function that returns
an instance of the main plugin class.
"""


def classFactory(iface):  # noqa: N802 — QGIS naming convention
    """QGIS calls this to instantiate the plugin.

    Parameters
    ----------
    iface : QgisInterface
        The QGIS application interface object.

    Returns
    -------
    ITreeSEAPlugin
        The plugin instance.
    """
    from .plugin import ITreeSEAPlugin
    return ITreeSEAPlugin(iface)
