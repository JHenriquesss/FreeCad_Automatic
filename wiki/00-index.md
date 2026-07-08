# FreeCAD Automatic Wiki

Portable Windows repo for automated steel warehouse (galpao) structural design.
Current: **35 modules, 23-gate pipeline** from wind/seismic loads → 3D FreeCAD
model → DXF → PT memorials. All modules senior-reviewed via NotebookLM.
Last consolidated: 2026-07-08.

## Contents

- [[01-architecture]]: repo shape, module architecture, data flow.
- [[02-test-tree]]: selftest coverage per module.
- [[03-phases]]: completed phases + current state.
- [[04-decisions]]: durable decisions (D0-D32).
- [[05-glossary]]: domain terms.
- [[06-open-threads]]: known gaps.

## Load Order For Fresh Agents

1. `wiki/00-index.md` → `01-architecture.md` → `03-phases.md`
2. `framework/galpao_fw/REVISAO-INDICE.md` (full module table)
3. `framework/galpao_fw/rodar_projeto.py` (pipeline entry point)
4. `framework/galpao_fw/projeto_spec.py` (data contract)

## Current Head

- 35 modules in `framework/galpao_fw/`, all importable and selftest-passing.
- 23 gates: vento → sismo → portico → estabilidade → redimensionamento →
  terças → telha → secundarios → contraventamento → base → sapata →
  baldrame → estaca → ligacoes → **fogo → escada → plataforma** → consolidado.
- Pipeline entry: `rodar_projeto.calcular(spec, out_dir)`.
- FreeCAD MCP connected (xmlrpc port 9875, GuiUp=1).
- Full end-to-end test: galpao 24×12m → 20.156 kg aco, 669 obj FreeCAD, 0 interferencias.

last-consolidated: 2026-07-08, sessions: 1 (sprint completa)
