# FreeCAD Automatic Wiki

Portable Windows repo for installing FreeCAD Robust MCP, configuring AI clients,
and carrying a steel-warehouse automation workspace. Current focus:
FreeCAD MCP reliability, reusable CAD/standards library, and `build-warehouse`
skill for galpao metalico workflows.

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

- Last known commit: `64a9228 fix: make FreeCAD bridge load in 1.1 profile`.
- FreeCAD MCP verified locally after real FreeCAD restart:
  `freecad-mcp --check --mode xmlrpc --host localhost --port 9875` succeeded
  against FreeCAD `1.1.1` with GUI available.

---

last-consolidated: 2026-07-04, sessions: 1
