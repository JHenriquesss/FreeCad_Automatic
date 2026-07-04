# Test Tree

## Trunk

End-to-end trunk for this project:

1. Fresh Windows checkout or GitHub ZIP.
2. Run installer.
3. FreeCAD workbench copied to discoverable Mod paths.
4. AI client sees `freecad` MCP entry.
5. FreeCAD bridge listens on `localhost:9875`.
6. `freecad-mcp --check --mode xmlrpc --host localhost --port 9875` succeeds.
7. Agent can call FreeCAD tools and read active document state.

## Current Green Checks

| Check | Command / Evidence | Status |
| --- | --- | --- |
| Installer syntax/help | `powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 -Help` | green |
| Codex MCP registration | `codex mcp list` showed `freecad` enabled | green |
| FreeCAD bridge import | `freecadcmd.exe` loaded `Init.py` and started bridge | green |
| GUI MCP connection | `freecad-mcp --check --mode xmlrpc --host localhost --port 9875` | green |
| Skill validation | `quick_validate.py skills/build-warehouse` via `uv` | green |
| Git remote | pushes through `origin/main` | green |
| Galpao workspace | `projects/galpao/AGENT_SCOPE.md` exists | green |

## Branches

### Installer Branch

- Assert `uv` found or installed.
- Assert `freecad-mcp.exe` exists.
- Assert all selected client configs are written with XML-RPC env.
- Assert FreeCAD workbench copied to classic and namespace paths.
- Missing: automated Pester tests for `install.ps1`.

### MCP Bridge Branch

- Assert `Init.py`/`InitGui.py` wrappers load.
- Assert no hard dependency on `FreeCAD.GuiUp` in headless.
- Assert XML-RPC port 9875 opens after FreeCAD restart.
- Assert GUI `execute` creates a simple `Part::Box` after `Init.py` defers to
  `InitGui.py`.
- Missing: automated GUI startup test from this wrapper repo.

### Warehouse Skill Branch

- Assert skill YAML validates.
- Assert asset references point to existing files.
- Assert no raw research PDFs are committed.
- Missing: real galpao project fixture and FreeCAD model generation test.

### Library Branch

- Assert manifests exist for source/license notes.
- Assert Gerdau DWG inventory exists.
- Missing: checksum manifest and import/convert verification for DWG assets.

## Test Gaps

- No CI pipeline for this wrapper repo.
- No scripted FreeCAD GUI integration test in repo root.
- No verified post-patch `execute` smoke test after restarting FreeCAD.
- No project example proving `build-warehouse` can create first conceptual
  FreeCAD model.
- No automated documentation consistency check for README/wiki/manifests.
