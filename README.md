# FreeCAD Automatic — Steel Warehouse Design Framework

**35 Python modules** for parametric structural design of steel warehouses (galpões).
End-to-end: site data → wind/seismic/crane loads → 2D portal analysis (1 or N spans) →
MAES 2nd order → member check NBR 8800 → connections → foundations (shallow/deep/eccentric) →
fire → stairs → platforms → **FreeCAD 3D model** → DXF → PT memorials.

## Quick Start

```powershell
# Setup (one time)
.\install.bat

# Create and run a project
cd framework\galpao_fw
python -c "
import projeto_spec as PS, rodar_projeto as RP
s = PS.novo()
# ... preencher s com dados do projeto ...
RP.calcular(s, 'exports/memoria')
RP.gerar_dxf(s, 'exports/dxf', 'meu_galpao')
"
```

## Pipeline (23 gates)

```
Gate 5 — Vento (NBR 6123 transversal + longitudinal + Tab.7 multi-span)
       — Sismo (NBR 15421)
       — Ponte rolante (NBR 8800/8400)
Gate 6 — Pórtico 2D (1 ou N vãos)
       — 2ª ordem MAES (B1/B2)
Gate 7 — Redimensionamento (guloso, perfis por coluna)
       — Verificação NBR 8800 + Mão-francesa + Terças + Telha
       — Secundários + Contraventamento + Verga
       — Base + Chumbadores + Sapata + Baldrame + Estaca + Ligações
Gate 8 — Fogo (NBR 14323) + Escada + Plataforma
Gate 9 — Memorial Consolidado
```

## Module Catalog

| Count | Category | Modules |
|---|---|---|
| 35 | All | `frame2d`, `galpao_portico`, `estabilidade_b1b2`, `check_nbr8800`, `perfis`, `redimensionamento`, `vento_nbr6123`, `tercas_iteracao`, `secundarios_nbr8800`, `mao_francesa`, `contraventamento`, `base_chumbador`, `ligacoes`, `fundacao_sapata`, `viga_baldrame`, `estaca_profunda`, `sapata_divisa`, `telha_cobertura`, `junta_dilatacao`, `sismo_nbr15421`, `ponte_rolante`, `fogo_nbr14323`, `calhas`, `plataforma`, `escada`, `neve`, `alma_variavel`, `tesoura`, `dxf_vistas`, `build_galpao`, `projeto_spec`, `rodar_galpao`, `rodar_projeto`, `framework` |

## Key Features

- **Multi-span**: N vãos (N≥1), colunas independentes no redim, vento Tab.7.
- **Foundations**: sapata (NBR 6118), baldrame, estaca (3 métodos), divisa.
- **Fire**: ISO 834, ky/kE tabelados, proteção intumescente/spray.
- **3D Model**: FreeCAD via MCP (669 obj, 0 interferências testado).
- **Review**: 27 REVISAO-*.md para parecer sênior, todos homologados.

## Requirements

- Windows, FreeCAD ≥ 1.1, Python 3.12, `uv`.
- `numpy < 2` (pycufsm dependency).
- MCP: `freecad-mcp` (installed by `install.ps1`).

## Docs

- `wiki/` — LLM-oriented wiki (architecture, phases, decisions).
- `framework/galpao_fw/REVISAO-*.md` — per-module senior review docs.
- `skills/build-warehouse/` — AI skill with 10-gate workflow.
