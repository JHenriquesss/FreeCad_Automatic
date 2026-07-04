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
