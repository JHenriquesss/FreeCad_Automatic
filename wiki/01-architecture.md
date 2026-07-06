# Architecture

## Repo Shape

- Wrapper repo: `D:/dev/FreeCad_Automatic`.
- Vendored upstream: `freecad-addon-robust-mcp-server/`.
- Installer: `install.ps1`.
- User docs: `README.md`, `UPSTREAM.md`.
- CAD and standards assets: `libraries/`.
- AI skill: `skills/build-warehouse/`.
- Project workspace template: `projects/_template/`.
- First concrete project workspace: `projects/galpao/`.
- Project isolation contract: each project folder carries `AGENT_SCOPE.md` and
  project-local `context/` files.
- Local-only research/logs: `pesquisa/`, `sessions/`, `*.log` ignored by Git.

## Installer Architecture

- Installs global `freecad-mcp` via `uv tool install`.
- Registers MCP clients:
  - Claude Desktop JSON config.
  - Claude Code CLI when available.
  - Codex TOML config.
  - OpenCode JSON config.
  - Antigravity VS Code-style MCP JSON.
- Writes default env:
  - `FREECAD_MODE=xmlrpc`
  - `FREECAD_SOCKET_HOST=localhost`
  - `FREECAD_XMLRPC_PORT=9875`
  - `FREECAD_SOCKET_PORT=9876`
  - `FREECAD_TIMEOUT_MS=30000`
  - `PYTHONIOENCODING=utf-8`
- Copies workbench into both classic and namespace layouts, for base and
  versioned FreeCAD profile folders:
  - `%APPDATA%\FreeCAD\Mod\RobustMCPBridge`
  - `%APPDATA%\FreeCAD\Mod\freecad\RobustMCPBridge`
  - `%APPDATA%\FreeCAD\v1-1\Mod\RobustMCPBridge`
  - `%APPDATA%\FreeCAD\v1-1\Mod\freecad\RobustMCPBridge`

## FreeCAD Bridge Local Patch

- Upstream folder had lowercase `init_gui.py` and package `__init__.py`.
- Local wrappers added:
  - `freecad-addon-robust-mcp-server/freecad/RobustMCPBridge/Init.py`
  - `freecad-addon-robust-mcp-server/freecad/RobustMCPBridge/InitGui.py`
- Reason: FreeCAD workbench discovery executes classic `Init.py`/`InitGui.py`.
- GUI startup rule:
  - `Init.py` must not start the bridge.
  - `InitGui.py` owns GUI auto-start after `FreeCAD.GuiUp` is true.
  - Starting from `Init.py` can classify GUI startup as headless and make
    XML-RPC `execute` calls hang in the queue processor.
- Headless robustness patches:
  - `__init__.py`: use `getattr(FreeCAD, "GuiUp", False)` and treat missing
    `GuiUp` as headless.
  - `freecad_mcp_bridge/server.py`: avoid direct `FreeCAD.GuiUp` accesses.
- Auto-start patch:
  - `preferences.py`: `DEFAULT_AUTO_START = True` (upstream `False`).
  - Makes a fresh-PC install auto-start the bridge ~3s after FreeCAD launch via
    `InitGui.py` `QTimer.singleShot`, with no manual workbench selection.
  - Machines with `RobustMCPBridge/AutoStart` already in `user.cfg` keep their
    stored value; the default only governs first run on a new profile.
- Verified with `freecadcmd.exe`: bridge auto-start logs showed XML-RPC 9875
  and socket 9876.
- Verified with FreeCAD GUI after process restart: MCP health check succeeded.

## Library Architecture

- CAD blocks under `libraries/cad-blocks/steel-warehouse/`.
- Standards/reference data under `libraries/standards/`.
- FreeCAD-library assets:
  - HEA/HEB FCStd profiles.
  - Steel roof sheets FCStd/STEP.
  - Glass-skin opening modules FCStd/STEP.
- Gerdau assets:
  - Official AutoCAD ZIPs preserved.
  - DWG extracted under `profiles/gerdau/autocad/dwg/`.
  - Technical PDF under `libraries/standards/gerdau/`.
- Manifests are source-of-truth for attribution and engineering caveats.

## Skill Architecture

- Main skill: `skills/build-warehouse/SKILL.md`.
- Progressive references:
  - `references/gates.md`: the 10-gate staged workflow (start here).
  - `references/calc-modules.md`: gate->module map + orchestrator (calc toolkit).
  - `QUICKSTART.md`: env pre-flight + how a from-scratch run is conducted.
  - `references/block-map.md`: locate assets.
  - `references/project-inputs.md`: required project inputs.
  - `references/steel-warehouse-engineering-map.md`: systems and sequence.
  - `references/connections-bases-durability.md`: connection/base/durability.
  - `references/engineering-review-questions.md`: engineer validation prompts.
  - `references/deliverables.md`: output folders and checks.
  - `references/constructability-detailing.md`, `references/geometry-conventions.md`,
    `references/modeling-workflow-freecad.md`, `references/cbca-galpao-project-sequence.md`.
- Rule: model geometry and placeholders only until engineer approves design
  assumptions, member sizes, connections, bases, and deliverables.
- Project-scoped agents may read shared repo knowledge but write only in the
  active `projects/<project-slug>/` folder.

## Calc Toolkit Architecture

- Location: `projects/galpao/calc/` (17 modules) + `work/build_galpao.py` (model).
- Grounding: formulas extracted from norm PDFs in `pesquisa/aco/` (git-ignored):
  NBR 8800, NBR 6123, NBR 14762; AISC DG1 for base plates. **Rule: verify a method
  against the norm PDF, never from memory (zero-method-error).**
- Each module: PT outputs, a `_selftest()` (or `__main__`), and a markdown twin
  (code + run result) in `notes/scripts-md/`. All senior-reviewed.
- Modules: `terreno` (land feasibility FIRST: KML/coord → lot area, buildable
  rectangle, TO/CA/TP caps, fit check), `frame2d` (solver, `reactions()`),
  `vento_nbr6123`, `galpao_portico`, `estabilidade_b1b2` (MAES 2nd order),
  `check_nbr8800`, `mao_francesa` (flange-brace spacing by inverting the 5.5.1.2
  interaction → viga Lb), `tercas_nbr14762`, `distorcional_fsm`, `base_chumbador`,
  `ligacoes`, `secundarios_nbr8800` (wall girt U biaxial + eave strut/ridge +
  gable post I beam-column), `contraventamento` (tension rods: bracing/sag/
  flange-brace, 5.2 + slenderness + 2% brace force), `ponte_rolante` (crane action
  NBR 8800/8400: wheel loads + impact/surge/braking, runway beam, console reaction;
  integrated into the portico via `PONTE` config), `perfis`, `redimensionamento`.
- Orchestrator: `calc/rodar_galpao.py` — one params dict configures every module,
  runs Gates 5-9, EXTRACTS base/knee efforts from the portico (not hardcoded),
  emits one memorial per module + `MEMORIAL-CONSOLIDADO.txt`. `PARAMS_REF` is the
  validated 20x10 reference and reproduces it exactly.
- Parametric geometry: `gp.configurar(span,eave,ridge,bay,base_fixed,sections,
  loads)`, `est.sincronizar()` (called in `analyse()`), `ti.configurar(...)`,
  `build_galpao.configurar(length,span,eave_h,slope,bay,export_dir,doc_name)`.
  Defaults = the 20x10 reference; any dimension runs.
- Dependency: **numpy < 2** (pycufsm 0.2.0 has numpy-2 incompatibilities, one in
  compiled Cython) — pinned to 1.26.4; only `distorcional_fsm` needs it. See
  `calc/REQUISITOS.txt`.
- Model builder uses real profile sweeps: `i_member` (HEA), `u_member` (UPE),
  `ue_member` (cold-formed lipped channel). Runs `checa_interferencia` +
  `estrutura_em_aberturas` (real clash checks) and a volume-based takeoff.

## Skill-Computes-Engineer-Reviews Model

- The `build-warehouse` skill RUNS the toolkit at Gates 5-8 and emits PT
  memoriais; the responsible ENGINEER reviews and signs off (ART). Nothing is
  "verified" before that. Every engineering-critical module input is a gate
  question (Ask, Do Not Invent) or a recorded pending assumption.
- Entry docs: `SKILL.md` -> `references/gates.md` (10 gates) ->
  `references/calc-modules.md` (gate->module map + orchestrator) -> `QUICKSTART.md`
  (env pre-flight: numpy<2, pycufsm, MCP bridge). The skill is READ-AND-FOLLOW
  (not a slash-command).

## Project Isolation Architecture

- New project starts by copying `projects/_template/`.
- `projects/galpao/` is the first real project fixture, initialized from the
  template with project-local context, notes, inputs, work, and exports folders.
- Agent working directory should be the specific project folder, not repo root.
- `AGENT_SCOPE.md` defines write boundary and startup order.
- `context/chat.md`, `context/decisions.md`, `context/pending.md` store
  project-specific memory.
- Shared assets remain read-only for project work: `wiki/`, `skills/`,
  `libraries/`, `pesquisa/`.

## Runtime Assumptions

- Windows target.
- FreeCAD installed separately.
- `uv` installed or bootstrapped by installer.
- MCP server connects to FreeCAD bridge over XML-RPC; embedded mode is not used
  on Windows.
