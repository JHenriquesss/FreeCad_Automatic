"""FreeCAD startup wrapper for Robust MCP Bridge.

Do not start the bridge from Init.py. In FreeCAD GUI startup this file can run
before FreeCAD.GuiUp is true, which starts the queue processor in headless mode
and makes XML-RPC execute requests hang. InitGui.py owns GUI auto-start.
"""

from __future__ import annotations

import os
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

try:
    import FreeCAD

    FreeCAD.Console.PrintMessage(
        "Robust MCP Bridge: Init.py loaded; startup deferred to InitGui.py\n"
    )
except Exception:
    pass
