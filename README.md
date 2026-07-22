# FreeCAD Automatic — Steel Warehouse Design Framework

**53 Python modules** for parametric structural design of steel warehouses (galpões).
End-to-end: site data → wind/seismic/crane loads → 2D portal analysis (1 or N spans,
prismatic / web-tapered / truss) → MAES 2nd order → member check NBR 8800 (+ Annex G/H,
§5.7 localized forces, DG25 cross-check) → connections → foundations (shallow/deep/
eccentric) → fire → stairs → platforms → **FreeCAD 3D model** → **2D executive drawings
(TechDraw, AWS A2.4 weld symbols)** → DXF → PT memorials.

**Status:** REVISAO items 1–49 senior-homologated · pytest 245 passed · smoke 7/7.

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
       — Alma variável/tesoura: DG25 FLT + envelope FLB/TFY, zona de painel, mísula
       — Forças localizadas §5.7 + enrijecedor de apoio + alma esbelta (Anexo H)
       — Secundários + Contraventamento + Verga
       — Base + Chumbadores + Sapata + Baldrame + Estaca + Divisa (viga de equilíbrio) + Ligações/Gusset
Gate 8 — Fogo (NBR 14323) + Escada + Plataforma
Gate 9 — Memorial Consolidado (PDF) + Pranchas executivas 2D (TechDraw headless)
```

## Module Catalog

| Category | Modules |
|---|---|
| Análise/verificação | `frame2d`, `galpao_portico`, `estabilidade_b1b2`, `check_nbr8800`, `perfis`, `redimensionamento` |
| Perfis avançados | `alma_variavel`, `tesoura`, `props_I_mono` (I monossimétrico), `dg25_ltb` (DG25 FLT+envelope), `alma_esbelta` (Anexo H), `enrijecedor_painel` (§5.4.3), `zona_painel`, `flt_misula`, `cortante_tapered`, `tensao_ponto`, `forcas_localizadas` (§5.7 + enrijecedor de apoio) |
| Cargas | `vento_nbr6123`, `sismo_nbr15421`, `ponte_rolante`, `nbr8400`, `neve` (stub, não wired) |
| Secundários | `tercas_iteracao`, `secundarios_nbr8800`, `mao_francesa`, `contraventamento`, `telha_cobertura`, `calhas`, `junta_dilatacao` |
| Ligações/base | `ligacoes`, `gusset_ligacao`, `console_ponte`, `base_chumbador` |
| Fundações | `fundacao_sapata`, `viga_baldrame`, `estaca_profunda`, `sapata_divisa`, `viga_equilibrio` (divisa sobre estacas) |
| Fogo/acessórios | `fogo_nbr14323`, `plataforma`, `escada` |
| Geometria/saída | `build_galpao`, `dxf_vistas`, `techdraw_exec` (pranchas 2D + glyph solda AWS), `relatorio_calculo` (memorial PDF), `terreno` |
| Orquestração | `projeto_spec`, `rodar_galpao`, `rodar_projeto`, `framework`, `build_final` |

## Key Features

- **Multi-span**: N vãos (N≥1), colunas independentes no redim, vento Tab.7.
- **Portal types**: prismático, alma variável (web-tapered, DG25), tesoura (truss).
- **Foundations**: sapata (NBR 6118), baldrame, estaca (3 métodos), divisa rasa
  (`sapata_divisa`) e profunda (`viga_equilibrio` — viga de equilíbrio sobre estacas).
- **Fire**: ISO 834, ky/kE tabelados, proteção intumescente/spray.
- **3D Model**: FreeCAD headless (`freecadcmd`) + MCP, auditoria de interferências.
- **2D Executive drawings**: TechDraw headless (`freecad.exe`) — pranchas A1, cortes
  seccionados hachurados, símbolos de solda AWS A2.4 (arrow/other/both-side).
- **Zero-erro-de-método**: todo valor de norma lido verbatim do PDF em `pesquisa/`
  (nunca de memória); tabelas/equações ambíguas lidas por imagem de página.
- **Review**: 48 REVISAO-*.md para parecer sênior — **itens 1–49 homologados**
  (correções de bug/omissão acolhidas e refutações provadas com PDF, item a item).

## Requirements

- Windows, FreeCAD ≥ 1.1, Python 3.12, `uv`.
- `numpy < 2` (pycufsm dependency).
- MCP: `freecad-mcp` (installed by `install.ps1`).

## Docs

- `wiki/` — LLM-oriented wiki (architecture, phases, decisions).
- `framework/galpao_fw/wiki/revisoes/REVISAO-*.md` — per-module senior review docs.
- `skills/build-warehouse/` — AI skill with 10-gate workflow.

