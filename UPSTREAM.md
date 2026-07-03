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
