# Phases

## Phase 1 - Portable MCP Installer

Scope:
- Make repo downloadable as ZIP.
- Install global FreeCAD MCP server.
- Copy FreeCAD bridge workbench.
- Register MCP clients.

Outcome:
- `install.ps1`, `README.md`, `UPSTREAM.md`, `.gitignore`.
- Vendored upstream `freecad-addon-robust-mcp-server/`.
- Pushed as `5583316 chore: add portable FreeCAD MCP installer`.

## Phase 2 - Steel Warehouse Base Library

Scope:
- Add initial CAD assets and project structure.
- Create `build-warehouse` skill.

Outcome:
- `libraries/cad-blocks/steel-warehouse/`.
- `libraries/standards/`.
- `skills/build-warehouse/`.
- `projects/_template/`.
- Pushed as `25e929b feat: add steel warehouse block library`.

## Phase 3 - Gerdau Supplier Assets

Scope:
- Add commonly used Gerdau steel profile CAD/BIM assets.

Outcome:
- Downloaded official AutoCAD ZIPs and extracted DWGs.
- Added Gerdau technical PDF.
- Updated manifests and block map.
- Pushed as `879fe0f feat: add Gerdau steel profile blocks`.

## Phase 4 - Research-Derived Warehouse Skill

Scope:
- Analyze local `pesquisa/aco` material without committing raw PDFs.
- Convert useful structure into concise skill references.

Outcome:
- Added engineering map, connection/base/durability checklist, review questions.
- Expanded project input requirements.
- Pushed as `3886a66 feat: enrich steel warehouse skill research`.

## Phase 5 - FreeCAD MCP Reliability Fixes

Scope:
- Diagnose why FreeCAD MCP failed to load/connect.

Outcome:
- Documented explicit XML-RPC health check.
- Installed workbench in namespace and classic paths.
- Added `Init.py`/`InitGui.py` wrappers.
- Patched `FreeCAD.GuiUp` assumptions for headless.
- Verified after real FreeCAD restart.
- Pushed through `64a9228 fix: make FreeCAD bridge load in 1.1 profile`.

## Phase 6 - Project Workspace Isolation

Scope:
- Add isolated per-project workspaces for agents.
- Prevent project agents from modifying sibling projects or shared config.

Outcome:
- Added `projects/_template/` with `AGENT_SCOPE.md` and local context folders.
- Updated `skills/build-warehouse` to respect project write boundaries.
- Created first fixture `projects/galpao/`.
- Pushed through `ad7c258 chore: create galpao project workspace`.

## Phase 7 - FreeCAD MCP Execute Verification

Scope:
- Ensure GUI bridge startup happens only after `FreeCAD.GuiUp`.
- Verify `execute` can create simple geometry without hanging.

Outcome (verified 2026-07-04):
- Diagnosed live hang: FreeCAD process predating the patch held stale bridge code
  auto-started from `Init.py` before `GuiUp`; `ping`/`execute` timed out on 9875
  though the port listened.
- Confirmed all 4 installed Mod copies of `Init.py`/`InitGui.py` match patched repo.
- Restarted FreeCAD; new pid loaded patched `InitGui.py`.
- `freecad-mcp --check --mode xmlrpc --host localhost --port 9875` -> success,
  FreeCAD 1.1.1, GUI available.
- XML-RPC `execute` created `Part::Box` (vol 6000, `GuiUp=1`) with no hang.
- Fix committed as `1b33707 fix(freecad): defer GUI bridge startup`.

## Phase 8 - Galpao Structural Calc Toolkit (2026-07-04..05)

Scope:
- Build a parametric, norm-grounded structural-calc toolkit so the skill can
  size a galpao (user is an engineer; a senior only reviews).
- Formulas extracted from the actual norm PDFs (`pesquisa/aco/`), one self-test
  per module, PT outputs, one markdown per script (code + result) under
  `projects/galpao/notes/scripts-md/`.

Outcome (11 modules in `projects/galpao/calc/`, all senior-reviewed):
- `frame2d` (direct-stiffness 2D solver + `reactions()`); `vento_nbr6123`
  (NBR 6123 wind); `galpao_portico` (transverse frame); `estabilidade_b1b2`
  (NBR 8800 Anexo D MAES: nt/lt split, B1/B2, 80% stiffness for media
  deslocabilidade, notional force); `check_nbr8800` (member check Anexos F/G);
  `tercas_nbr14762` (cold-formed Ue purlin, MSE + Anexo F suction);
  `distorcional_fsm` (Mdist via pycufsm FSM); `base_chumbador` (base plate +
  anchors, NBR 8800 6.3/6.6 + AISC DG1); `ligacoes` (bolts/welds + 45 kN min);
  `perfis` (profile library); `redimensionamento` (sizing driver).
- Iterated through many senior-review rounds (wind incidence alpha=90, ELU combos,
  reduced stiffness, terca load-split/Ief/distortional, base plate unit bug +
  plastified bearing + two-interface plate). Commits `bc40619`..`ded22d1`,
  `2417bbb`.

## Phase 9 - Skill Integration, Parametrization, Dry-Run (2026-07-05)

Scope:
- Wire the toolkit into `build-warehouse` (skill computes, engineer reviews).
- Run the current galpao through Gates 6-9 with the toolkit.
- Bulletproof: parametrize geometry and validate a full from-scratch loop.

Outcome:
- Skill rewired: `references/calc-modules.md` maps each gate to its module;
  SKILL.md/gates.md say "skill computes, engineer reviews" (was handoff). Commit
  `eafc410`.
- Galpao 20x10 through Gates 6-9: FIXED base adopted (pinned failed, drift
  179 mm); HEA200/HEA180, Ue 200x75x25x2.65 purlins, base 450x550x40 + 4 d20
  A307, knee 4 M24 A325; verified sections in the FreeCAD model (0 clashes);
  consolidated PT memorial. Commits `cf21f8e`..`595cfa4`.
- Parametrized geometry (`gp.configurar`, `est.sincronizar`,
  `build_galpao.configurar`) + canonical orchestrator `rodar_galpao.py` that
  extracts base/knee efforts from the portico. Default reproduces the reference
  exactly; a 24x12 run executes cleanly. Commit `8dd3525`.
- Full gate-loop dry-run from scratch in `projects/galpao-ensaio` (Gates 0-9,
  live gate questions). A heavy-crane pick at Gate 0 correctly stopped the flow
  (no crane module) -> crane backlogged. Commits `0b2809a`, `1843ccc`.
