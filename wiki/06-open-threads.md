# Open Threads

## Calc Toolkit Backlog (2026-07-05)

- **CRANE MODULE (ponte rolante) — high priority.** Toolkit does NOT size for
  overhead cranes (no load case, runway beam, corbel, surge/braking, fatigue).
  Surfaced at Gate 0 of the dry-run when a heavy crane was picked; the flow
  correctly stopped rather than fake it. Build after validation, grounded in
  NBR 8800 (impact/fatigue) + NBR 8400 (classes) + CBCA example. Tracked in
  `projects/galpao-ensaio/notes/backlog.md`.
- **Secondary member verification (RESOLVED 2026-07-05).** All secondary members
  now checked: wall girt (UPE100 biaxial, `secundarios_nbr8800`), eave strut/ridge
  + gable post (HEA160 beam-column, same module), bracing/sag/flange-brace rods
  (`contraventamento`, tension 5.2 + slenderness + 2% brace force), door lintel
  (reuses the girt check). LONGITUDINAL wind (α=0) in `vento.compute_longitudinal`
  feeds the strut axial and the diagonal forces (Fa=59 kN / 29.5 per side).
  Reference utilizations: girt 0.99 (needs 2 sag-rod lines), strut 0.07, gable
  post 0.43, rods u_max 0.66, lintel 0.04 — all OK. Remaining are INPUT refinements
  flagged A CONFIRMAR (Ca from Figura 4; sag-rod axial; catalog J/Cw) and the
  model must add 2 wall sag-rod lines.
- **Delegated (flagged, not errors):** concrete anchor breakout/pull-out cone
  (NBR 6118/ACI — foundation scope, `base_chumbador` flags); block shear / plate
  limit states beyond bearing (`ligacoes`); moment end-plate thickness + prying;
  rigorous purlin Ief/Wefy (catalog input, conservative fallback used).
- **Skill improvement backlog** (from `projects/galpao/notes/skill-audit.md`):
  no formal "batch defaults" mode (asking every secondary decision as buttons is
  impractical); rule-timing tags (when each constructability rule becomes
  geometry) not added. RESOLVED 2026-07-05: flange-brace (mao-francesa) is no
  longer a heuristic — `calc/mao_francesa.py` derives the brace spacing by
  inverting the 5.5.1.2 interaction (feeds the viga Lb; `build_galpao.MF_STRIDE`).
- Purlin/terca profile properties come from the mid-line (`prop2`) or catalog
  and are flagged "A CONFIRMAR" against the supplier catalog.

## Needs Real Galpao Example (RESOLVED 2026-07-05)

- `projects/galpao` taken through Gates 0-9; `projects/galpao-ensaio` is a
  from-scratch full-loop dry-run. Both use the toolkit + orchestrator.

## Needs Real Galpao Example (historical)

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
