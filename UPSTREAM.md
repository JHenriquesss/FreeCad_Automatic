# Upstream

This installer vendors the FreeCAD Robust MCP project:

```text
https://github.com/spkane/freecad-addon-robust-mcp-server
```

The vendored code is kept under:

```text
freecad-addon-robust-mcp-server/
```

Before publishing a ZIP release, update the vendored folder from upstream and
run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -Help
powershell -ExecutionPolicy Bypass -File .\install.ps1 -WhatIf
```

Keep upstream license files in the vendored directory.

## Local Patch Notes

This wrapper currently carries local changes inside the vendored workbench to
make FreeCAD 1.1 load the bridge reliably on Windows:

- `freecad/RobustMCPBridge/Init.py`
- `freecad/RobustMCPBridge/InitGui.py`
- defensive `FreeCAD.GuiUp` handling in:
  - `freecad/RobustMCPBridge/__init__.py`
  - `freecad/RobustMCPBridge/freecad_mcp_bridge/server.py`
- `freecad/RobustMCPBridge/preferences.py`: `DEFAULT_AUTO_START = True`
  (upstream default is `False`). This makes a fresh-PC install work with no
  manual steps: the bridge auto-starts on FreeCAD launch instead of requiring
  the user to select the workbench and click Start. A machine that already has
  the `RobustMCPBridge/AutoStart` param stored in `user.cfg` keeps its own
  value; the default only affects first run on a new profile.

When refreshing from upstream, preserve these changes or verify upstream has
equivalent fixes before replacing the vendored folder.
