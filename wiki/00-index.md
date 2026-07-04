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

- Last known commit: `1b33707 fix(freecad): defer GUI bridge startup`.
- FreeCAD MCP verified working end-to-end on 2026-07-04: after FreeCAD restart,
  health check and XML-RPC `execute` (Part::Box) both succeed with `GuiUp=1`, no
  hang.
- Root cause of prior hang: a FreeCAD process started before the patch had the
  bridge auto-started from `Init.py` while `FreeCAD.GuiUp` was still false, so the
  queue processor ran headless-style inside the GUI process and blocked all
  `execute`/`ping` calls. Fix = patched `InitGui.py` defers start until `GuiUp`;
  a full FreeCAD restart is required to clear a stale in-memory bridge.

---

last-consolidated: 2026-07-04, sessions: 2
