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
  - `references/block-map.md`: locate assets.
  - `references/project-inputs.md`: required project inputs.
  - `references/steel-warehouse-engineering-map.md`: systems and sequence.
  - `references/connections-bases-durability.md`: connection/base/durability.
  - `references/engineering-review-questions.md`: engineer validation prompts.
  - `references/deliverables.md`: output folders and checks.
- Rule: model geometry and placeholders only until engineer approves design
  assumptions, member sizes, connections, bases, and deliverables.
- Project-scoped agents may read shared repo knowledge but write only in the
  active `projects/<project-slug>/` folder.

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
