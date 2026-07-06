# Open Threads

## Calc Toolkit Backlog (2026-07-05)

- **CRANE MODULE (ponte rolante) — BUILT 2026-07-05.** `calc/ponte_rolante.py`
  (grounded in the "Dimensionamento" book cap.4 + NBR 8800/8400): wheel loads
  (impact φ), surge (transversal), braking (longitudinal); runway beam (absolute
  moving-load moment of 2 wheels + lateral bending + ELS L/600…L/1000 + fatigue
  flag) and packages the console reaction (R_vert, M_ecc, H_transv, H_long). φ and
  the surge/braking fractions are manufacturer/NBR-8400 data → flagged A CONFIRMAR
  (the book itself says these usually come from the supplier). Ref (100 kN crane):
  runway VS500 interaction 0.34, reaction R_vert=132.9 kN. INTEGRATED INTO THE
  PORTICO 2026-07-05: `gp.configurar(ponte=)` injects the reaction as a load case
  (R_vert + eccentric moment at the console node + surge) and adds combos C4
  (crane-principal G+1.5·Crane+1.4·0.6·Wind) and C5 (wind-principal, crane ψ0=0.7).
  It flows through 1st order, the MAES 2nd order (`estabilidade_b1b2`), the member
  check, and the base/knee extraction — all guarded by `PONTE=None` so the craneless
  reference is byte-identical (0.67/0.93, B2 1.036). `rodar_galpao.py --ponte` runs
  a 100 kN example (doesn't govern: uplift 0.67); a 250 kN crane governs (column
  1.8 → resize). REMAINING: senior re-review (touched the approved gp + estabilidade).
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
  rule-timing tags (when each constructability rule becomes geometry) not added.
  RESOLVED 2026-07-05: (a) flange-brace no longer a heuristic
  (`calc/mao_francesa.py` inverts 5.5.1.2 → viga Lb, `build_galpao.MF_STRIDE`);
  (b) BATCH-DEFAULTS mode — secondary decisions go on one editable sheet at Gate
  4b (`references/batch-defaults.md` + `_template/notes/planilha-defaults.md`),
  not a button each; critical decisions stay individual gates.
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
