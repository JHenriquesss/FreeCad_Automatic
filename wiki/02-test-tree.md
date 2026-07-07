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
| GUI `execute` smoke | XML-RPC `execute` created Part::Box (vol 6000, GuiUp=1) post-restart 2026-07-04 | green |
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

### Calc Toolkit Branch (2026-07-05)

- Assert each `calc/*.py` module `_selftest()` passes (frame2d closed-form,
  tercas kl/Wef, base anchor/bearing/uplift, ligacoes bolt/weld/45kN,
  distorcional_fsm local-buckling sanity vs plate k=23.9). All green.
- Assert `rodar_galpao.py` with `PARAMS_REF` reproduces the reference: column
  interaction 0.67, rafter 0.93 (Lb=3.35 m from `mao_francesa`, 2 braces/frame),
  B2 1.036. Green.
- Assert a different geometry (24x12) runs the whole chain without error
  (interactions >1 as expected -> would trigger resizing). Green.
- Assert `build_galpao.configurar(...)` builds via MCP: 248 elements, 0
  interferences, 0 structure-in-openings, verified sections in takeoff. Green.
- Assert full gate-loop dry-run (`projects/galpao-ensaio`, Gates 0-9) runs and a
  heavy-crane pick is correctly caught as unsupported. Green.
- Each module was senior-reviewed (external engineer) across multiple rounds.
- Assert `secundarios_nbr8800._selftest()`: UPE100 girt fails with 1 wall sag rod,
  passes with 2 (0.99); HEA160 strut beam-column OK. Green.
- Missing: automated (CI) regression on the reference numbers; longitudinal wind
  (α=0) for the strut axial; crane load path.

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
