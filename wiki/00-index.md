# FreeCAD Automatic Wiki

Portable Windows repo for installing FreeCAD Robust MCP, configuring AI clients,
and carrying a steel-warehouse automation workspace. Current focus (2026-07-05):
a validated PARAMETRIC structural-calc toolkit (11 modules + orchestrator, all
senior-reviewed) wired into the `build-warehouse` skill, which now COMPUTES
(loads, analysis, 2nd order, member sizing) and emits PT memoriais for engineer
review. Full gate-loop dry-run (Gates 0-9) validated from scratch.

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

- Last known commit: `1843ccc docs(skill): audit fixes` (2026-07-05).
- Galpao calc toolkit COMPLETE: 11 senior-reviewed modules in
  `projects/galpao/calc/` + orchestrator `rodar_galpao.py`; geometry parametric
  via `configurar()`. See [[01-architecture#calc-toolkit-architecture]].
- `build-warehouse` skill now runs the toolkit at Gates 5-8 and emits PT
  memoriais (engineer reviews). Full from-scratch dry-run (`projects/galpao-ensaio`)
  validated the loop; a heavy-crane pick correctly exposed the missing crane
  module (backlog). See [[06-open-threads#calc-toolkit-backlog-2026-07-05]].
- Requires numpy < 2 (pycufsm/`distorcional_fsm`); rest is numpy-agnostic.
- FreeCAD MCP verified working end-to-end on 2026-07-04: after FreeCAD restart,
  health check and XML-RPC `execute` (Part::Box) both succeed with `GuiUp=1`, no
  hang.
- Root cause of prior hang: a FreeCAD process started before the patch had the
  bridge auto-started from `Init.py` while `FreeCAD.GuiUp` was still false, so the
  queue processor ran headless-style inside the GUI process and blocked all
  `execute`/`ping` calls. Fix = patched `InitGui.py` defers start until `GuiUp`;
  a full FreeCAD restart is required to clear a stale in-memory bridge.

---

last-consolidated: 2026-07-05, sessions: 2 (+ ~40 commits 07-04..07-05 not
session-logged; consolidated from git log + direct session state)
