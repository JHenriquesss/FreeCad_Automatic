# Open Threads

## Needs Real Galpao Example

- First project fixture exists: `projects/galpao/`.
- Open project agents in `projects/galpao/`, not repo root.
- Minimum input: span, length, eave height, roof slope, bay spacing, use,
  cladding, openings, profile preferences, bracing constraints.
- Goal: exercise `build-warehouse` skill on a concrete case.

## FreeCAD MCP Execute Verification (RESOLVED 2026-07-04)

- Verified working: health check + XML-RPC `execute` (Part::Box) succeed, no hang.
- Operational rule: if `execute`/`ping` hang while port 9875 listens, the running
  FreeCAD holds a stale in-memory bridge (started before its files were patched, or
  before `GuiUp`). Fix = fully close FreeCAD and reopen; do NOT just retry the client.
- Diagnostic sequence that found it:
  - `Get-NetTCPConnection -LocalPort 9875,9876` (port owned by freecad.exe pid).
  - Compare FreeCAD `StartTime` vs Mod `Init.py`/`InitGui.py` `LastWriteTime`;
    if process older than files, it loaded pre-patch code.
  - Guard health check / `execute` with a hard timeout so a hang is visible.
- If a hang ever survives a clean restart, inspect queue processor timer/thread
  selection in `freecad_mcp_bridge/server.py`.

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
