# Decisions

## 2026-07-03 - Use freecad-addon-robust-mcp-server

Decision:
- Use `spkane/freecad-addon-robust-mcp-server` as vendored MCP server/bridge.

Why:
- Mature repo, supports Python execution, document access, XML-RPC/socket modes,
  and broad MCP tool surface.

Alternatives rejected:
- Smaller or less maintained FreeCAD MCP repos.
- Embedded FreeCAD mode on Windows.

## 2026-07-03 - Portable Wrapper Repo

Decision:
- Keep a wrapper repo with installer, vendored upstream, docs, libraries, skills,
  and project templates.

Why:
- User wants GitHub ZIP -> quick install on any PC.

Alternatives rejected:
- Manual per-client setup.
- Relying only on global machine state.

## 2026-07-03 - Global MCP Registration

Decision:
- Install global `freecad-mcp.exe` and register `freecad` MCP for Codex,
  Claude Desktop, Claude Code, OpenCode, and Antigravity.

Why:
- Same FreeCAD tool should be available across user agent surfaces.

Alternatives rejected:
- Project-only MCP config.
- Client-specific one-off commands.

## 2026-07-03 - Keep Research Raw Files Out Of Git

Decision:
- Ignore `pesquisa/` and convert findings into concise skill references.

Why:
- Raw PDFs can be large, licensed, or from unclear sources; skills should carry
  operational knowledge, not copyrighted corpora.

Alternatives rejected:
- Commit all PDFs.
- Require engineer to manually summarize everything before skill evolution.

## 2026-07-03 - Gerdau Assets Stored As Source ZIP + Working DWG

Decision:
- Preserve official Gerdau ZIPs and extract DWG working files.

Why:
- Source provenance remains intact; agents can find CAD blocks quickly.

Alternatives rejected:
- Re-download on every machine.
- Store only extracted files without source package.

## 2026-07-04 - FreeCAD Bridge Installed In Multiple Mod Layouts

Decision:
- Copy RobustMCPBridge to classic direct and namespace paths in base and versioned
  FreeCAD user profiles.

Why:
- FreeCAD 1.1 uses `v1-1`; upstream metadata references namespace layout; classic
  workbench discovery still expects direct addon folder with `Init.py`/`InitGui.py`.

Alternatives rejected:
- Only `%APPDATA%\FreeCAD\Mod\RobustMCPBridge`.
- Only `%APPDATA%\FreeCAD\v1-1\Mod\freecad\RobustMCPBridge`.

## 2026-07-04 - Patch Vendored Bridge For FreeCAD 1.1 Discovery

Decision:
- Add local `Init.py`/`InitGui.py` wrappers and make `GuiUp` access defensive.

Why:
- FreeCAD 1.1 did not load lowercase `init_gui.py` through classic discovery.
- `freecadcmd` lacks `FreeCAD.GuiUp`, causing startup exceptions before patch.

Alternatives rejected:
- Wait for upstream release.
- Tell user to start bridge manually every time.

## 2026-07-04 - Isolate Each Galpao Project Folder

Decision:
- Each project under `projects/<project-slug>/` gets `AGENT_SCOPE.md` and
  project-local `context/`.

Why:
- Agents need read access to shared wiki, skills, libraries, and research while
  being prevented from modifying sibling projects or shared configuration.

Alternatives rejected:
- Open all agents at repo root for project work.
- Duplicate shared libraries and research inside every project.
