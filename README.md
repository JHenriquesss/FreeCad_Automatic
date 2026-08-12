# FreeCAD Automatic — Steel Warehouse Design Framework

**135 Python modules** for parametric structural design of steel warehouses (galpões).
End-to-end: site data → wind/seismic/crane loads → 2D portal analysis (1 or N spans,
prismatic / web-tapered / truss) → MAES 2nd order → member check NBR 8800 (+ Annex G/H,
§5.7 localized forces, DG25 cross-check) → connections → foundations (shallow/deep/
eccentric) → fire → stairs → platforms → **FreeCAD 3D model** → **2D executive drawings
(TechDraw, AWS A2.4 weld symbols)** → DXF → PT memorials.

**Status:** REVISAO itens 1–49: 47 HOMOLOGADO + 2 PARECER (46, 49) · pytest 1393
coletados / 1357 passed / 0 failed / 14 skipped / 22 deselecionados (2026-08-11,
pós-instalação do PyMuPDF) · smoke 7/7.

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
RP.montar_modelo(s, 'exports', 'meu_galpao')          # modelo 3D (FCStd)
RP.rodar_executivo(s, 'exports', 'exports/freecad/meu_galpao.FCStd')  # pranchas 2D + DXF
"
```

## Pipeline (40 gates)

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
| Cargas | `vento_nbr6123`, `sismo_nbr15421`, `ponte_rolante`, `nbr8400`, `neve` (wired desde D51, 2026-07-16) |
| Secundários | `tercas_iteracao`, `secundarios_nbr8800`, `mao_francesa`, `contraventamento`, `telha_cobertura`, `calhas`, `junta_dilatacao` |
| Ligações/base | `ligacoes`, `gusset_ligacao`, `console_ponte`, `base_chumbador` |
| Fundações | `fundacao_sapata`, `viga_baldrame`, `estaca_profunda`, `sapata_divisa`, `viga_equilibrio` (divisa sobre estacas) |
| Fogo/acessórios | `fogo_nbr14323`, `plataforma`, `escada` |
| Geometria/saída | `build_galpao`, `techdraw_exec` (pranchas 2D + glyph solda AWS, desde 2026-07-09), `relatorio_calculo` (memorial PDF), `terreno` |
| Orquestração | `projeto_spec`, `rodar_galpao`, `rodar_projeto`, `framework`, `build_final` |

## Key Features

- **Multi-span**: N vãos (N≥1), colunas independentes no redim, vento Tab.7.
- **Portal types**: prismático, alma variável (web-tapered, DG25), tesoura (truss).
- **Foundations**: sapata (NBR 6118), baldrame, estaca (1 método: Aoki-Velloso), divisa rasa
  (`sapata_divisa`) e profunda (`viga_equilibrio` — viga de equilíbrio sobre estacas).
- **Fire**: ISO 834, ky/kE tabelados, proteção intumescente/spray.
- **3D Model**: FreeCAD headless (`freecadcmd`) + MCP, auditoria de interferências.
- **2D Executive drawings**: TechDraw headless (`freecad.exe`) — pranchas A1, cortes
  seccionados hachurados, símbolos de solda AWS A2.4 (arrow/other/both-side).
- **Zero-erro-de-método**: todo valor de norma lido verbatim dos PDFs das normas
  (nunca de memória; PDFs no repo: `Framework_Galpao_Modulos.pdf` na raiz,
  `libraries/standards/gerdau/`); tabelas/equações ambíguas lidas por imagem de página.
- **Review**: 48 REVISAO-*.md para parecer sênior (49 arquivos com o índice) —
  **itens 1–49 vereditados: 47 HOMOLOGADO + 2 PARECER (46 e 49)**
  (correções de bug/omissão acolhidas e refutações provadas com PDF, item a item).

## Requirements

- Windows, FreeCAD ≥ 1.1, Python 3.12, `uv`.
- `numpy < 2` (pycufsm dependency).
- MCP: `freecad-mcp` (installed by `install.ps1`).

## Docs

- `framework/galpao_fw/wiki/` — LLM-oriented wiki (architecture, phases, decisions).
- `framework/galpao_fw/REVISAO-*.md` — per-module senior review docs.

