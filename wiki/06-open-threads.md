# Open Threads

## Needs Real Galpao Example

- First project fixture exists: `projects/galpao/`.
- Open project agents in `projects/galpao/`, not repo root.
- Minimum input: span, length, eave height, roof slope, bay spacing, use,
  cladding, openings, profile preferences, bracing constraints.
- Goal: exercise `build-warehouse` skill on a concrete case.

## FreeCAD MCP Execute Verification

- `Init.py` was patched to defer GUI startup to `InitGui.py`.
- Current FreeCAD process may still have old bridge code loaded.
- Required next check after FreeCAD restart:
  - `freecad-mcp --check --mode xmlrpc --host localhost --port 9875`
  - XML-RPC `execute` creates `Part::Box` without timeout.
- If `execute` still hangs, inspect queue processor timer/thread selection in
  `freecad_mcp_bridge/server.py`.

## Installer Test Coverage

- Add Pester or PowerShell tests for:
  - `New-McpEnv`
  - JSON/TOML config writes.
  - FreeCAD Mod target path generation.
  - `-WhatIf` behavior.

## FreeCAD Bridge Upstream Sync

- Local patches exist in vendored upstream:
  - `Init.py`
  - `InitGui.py`
  - defensive `GuiUp` handling.
- `Init.py` intentionally does not start the GUI bridge; preserve this behavior.
- Before replacing vendored upstream, reapply or upstream these patches.

## DWG Import Workflow

- Gerdau blocks are DWG.
- FreeCAD may need DWG converter/importer.
- Need documented DXF conversion path and test import for representative Gerdau
  W/HP, U, I, cantoneira files.

## Documentation Consistency

- README and wiki now describe current state.
- Need future rule: after installer or bridge path changes, update
  `README.md`, `UPSTREAM.md`, and wiki.

## Research Material Governance

- `pesquisa/` stays ignored.
- Derived skill refs are allowed.
- Do not copy large copyrighted snippets/tables/figures into repo.
