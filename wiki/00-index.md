# FreeCAD Automatic Wiki

Portable Windows repo for installing FreeCAD Robust MCP, configuring AI clients,
and carrying a steel-warehouse automation workspace. Current focus:
FreeCAD MCP reliability, reusable CAD/standards library, isolated project
workspaces, first `projects/galpao` fixture, and `build-warehouse` skill for
galpao metalico workflows.

## Contents

- [[01-architecture#architecture]]: repo shape, installer, MCP bridge, skill/library layout.
- [[02-test-tree#test-tree]]: current verification paths and missing tests.
- [[03-phases#phases]]: completed work and current phase.
- [[04-decisions#decisions]]: durable decisions and rejected alternatives.
- [[05-glossary#glossary]]: project/domain terms.
- [[06-open-threads#open-threads]]: known gaps and next work.

## Load Order For Fresh Agents

1. Read this file.
2. Read [[01-architecture#architecture]] and [[06-open-threads#open-threads]].
3. For galpao modeling, read `skills/build-warehouse/SKILL.md`.
4. For installer work, read `README.md`, `install.ps1`, and `UPSTREAM.md`.

## Current Head

- Last known commit: `ad7c258 chore: create galpao project workspace`.
- Local uncommitted MCP patch: `RobustMCPBridge/Init.py` now defers GUI startup
  to `InitGui.py`; restart FreeCAD before verifying `execute`.
- FreeCAD MCP health checks can pass while `execute` still hangs if the bridge
  starts before `FreeCAD.GuiUp`; see [[06-open-threads#freecad-mcp-execute-verification]].

---

last-consolidated: 2026-07-04, sessions: 2
