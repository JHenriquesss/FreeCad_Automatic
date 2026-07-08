# Phases

## Phase 1-9 (historical)

Installer → Steel library → Gerdau assets → Research skill → MCP reliability → Project isolation → Execute verification → Calc toolkit → Skill integration. See git log `1843ccc` and prior.

## Phase 10 — Framework Completion (2026-07-08)

**Scope:** Close all gaps identified after Phase 9: new structural modules, multi-span, foundations, fire, complement systems, pipeline integration, 3D model.

### Modules Added

| # | Module | Lines | Norm |
|---|---|---|---|
| 18 | `galpao_portico` (multi-span) | estendido | NBR 8800 + 6123 Tab.7 |
| 19 | `sapata_divisa` | 170 | NBR 6122 / Velloso&Lopes |
| 20 | `fogo_nbr14323` | 140 | NBR 14323 / ISO 834 |
| 21 | `calhas` | 100 | NBR 10844 / Manning |
| 22 | `plataforma` | 102 | NBR 8800 / NBR 6120 |
| 23 | `escada` | 110 | NBR 8800 / NR-18 |
| 24 | `neve` | 75 | EN 1991-1-3 |
| 25 | `alma_variavel` | 60 | NBR 8800 |
| 26 | `tesoura` | 105 | NBR 8800 |
| 27 | `estabilidade_b1b2` (multi-span) | estendido | NBR 8800 An.D |
| 28 | `redimensionamento` (greedy) | reescrito | — |

**Integrações:** `rodar_galpao` ganhou gates 8 (fogo, escada, plataforma). `projeto_spec` e `rodar_projeto` atualizados. Total: **23 gates**.

### Correções Aplicadas Durante Revisões

- Ponte rolante: reação aplicada em 2 colunas (max+min), não 1.
- Escada: `int()` → `ceil()`, `n_pisos = n_espelhos - 1`, Blondel, patamar >3.2m.
- Calhas: borda livre 25%, Bellei rule, geometria prática 200×80mm.
- Tesoura: parábola verdadeira, nós defasados (Warren), isostática.
- T-stub: Q corrigida `(F·m − 2·Mpl)/n`.
- Neve: retorno em tuplas `(esq, dir)`, deslizamento impedido.
- Sapata divisa: loop falso removido, `V = ΔP` não `R`.

### Outcome

- 35 módulos, todos com selftest PASSED.
- Pipeline completo testado: galpão 24×12m → 20 gates → FreeCAD 669 obj, 0 interferências, 20.156 kg aço.
- MCP bridge verificado: XML-RPC 9875, GuiUp=1, execute OK.

## Current Phase — Homologado

Todos os 35 módulos revisados por parecer sênior (NotebookLM) e integrados. Framework pronto para uso.
