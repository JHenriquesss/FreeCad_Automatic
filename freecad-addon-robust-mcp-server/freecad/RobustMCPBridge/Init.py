"""FreeCAD startup wrapper for Robust MCP Bridge."""

from __future__ import annotations

import os
import runpy
import sys

try:
    _ADDON_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    import FreeCAD

    _base_dir = FreeCAD.getUserAppDataDir()
    _candidates = [
        os.path.join(_base_dir, "Mod", "RobustMCPBridge"),
        os.path.join(_base_dir, "Mod", "freecad", "RobustMCPBridge"),
    ]
    _ADDON_DIR = next(path for path in _candidates if os.path.isdir(path))

if _ADDON_DIR not in sys.path:
    sys.path.insert(0, _ADDON_DIR)

runpy.run_path(os.path.join(_ADDON_DIR, "__init__.py"), run_name="__robust_mcp_init__")
