# Open Threads

## Needs Real Galpao Example

- Need first project fixture under `projects/<project-slug>/`.
- Start by copying `projects/_template/` and opening the agent in the new
  project folder.
- Minimum input: span, length, eave height, roof slope, bay spacing, use,
  cladding, openings, profile preferences, bracing constraints.
- Goal: exercise `build-warehouse` skill on a concrete case.

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
