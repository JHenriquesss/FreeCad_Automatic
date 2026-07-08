# Architecture

## Repo Shape

- Wrapper repo: `D:/dev/FreeCad_Automatic`.
- Framework: `framework/galpao_fw/` — 35 Python modules.
- AI skill: `skills/build-warehouse/`.
- Projects: `projects/<slug>/` (isolated per AGENT_SCOPE.md).
- Wiki: `wiki/` (LLM-oriented).
- CAD assets: `libraries/cad-blocks/steel-warehouse/`.
- Norm PDFs (gitignored): `pesquisa/aco/`.

## Framework Architecture

### Module Layers

| Layer | Modules | Responsibility |
|---|---|---|
| **Solver** | `frame2d` | Direct-stiffness 2D frame solver |
| **Actions** | `vento_nbr6123`, `sismo_nbr15421`, `ponte_rolante`, `fogo_nbr14323`, `neve` | Wind (incl. multi-span Tab.7), seismic (NBR 15421), crane (NBR 8400), fire (ISO 834), snow (EN 1991-1-3) |
| **Analysis** | `galpao_portico`, `estabilidade_b1b2`, `tesoura`, `alma_variavel` | Portal frame (1+N spans), MAES B1/B2 2nd order, truss, tapered member |
| **Sizing** | `redimensionamento`, `check_nbr8800`, `perfis` | Auto-sizing (greedy per-column), member check (NBR 8800 An.F/G), profile database |
| **Secondary** | `tercas_iteracao`, `secundarios_nbr8800`, `mao_francesa`, `contraventamento`, `telha_cobertura` | Purlins (NBR 14762+FSM), girts/eave struts/gable posts, flange braces, bracing rods, roof sheeting |
| **Connections** | `ligacoes`, `base_chumbador` | Bolted/welded joints (NBR 8800), T-stub prying (EN 1993-1-8), base plates + anchors (ACI 318) |
| **Foundations** | `fundacao_sapata`, `viga_baldrame`, `estaca_profunda`, `sapata_divisa` | Spread footing (NBR 6118), tie beam, deep pile (3 methods), eccentric footing |
| **Complement** | `junta_dilatacao`, `calhas`, `plataforma`, `escada` | Expansion joints, gutters (Manning-Strickler), platforms, stairs |
| **Orchestration** | `rodar_galpao`, `rodar_projeto`, `projeto_spec`, `framework` | 23-gate pipeline, spec validation, project runner |
| **Output** | `build_galpao`, `dxf_vistas` | FreeCAD 3D model (669 obj), DXF views (portico+planta+elevacao), material takeoff |

### Data Flow

```
spec (projeto_spec)  →  validar()  →  rodar_projeto.calcular()
                                       ↓
  Gates 5-9: vento → sismo → ponte → portico → MAES → redim →
  terças → telha → secundarios → contraventamento → base →
  sapata → baldrame → estaca → ligações → fogo → escada → plataforma
                                       ↓
  MEMORIAL-CONSOLIDADO.txt  +  res dict (perfis, bases, resultados)
                                       ↓
  rodar_projeto.gerar_dxf()  →  .dxf
  rodar_projeto.montar_modelo()  →  FreeCAD .FCStd + .step
```

### Multi-Span Support

- `SPANS` replaces `SPAN` in all modules (list of floats).
- `N_VAOS = len(SPANS)` → N+1 columns, N ridges, 2N rafters.
- B1/B2 sums all column reactions (N+1 bases, N+1 eaves).
- Redim uses per-column profile list `cols[i]`.
- Wind: `cpe_telhado_multiplo()` implements NBR 6123 Table 7 (per-span Cpe).

## FreeCAD Bridge

- Vendored: `freecad-addon-robust-mcp-server/`.
- Connection: XML-RPC port 9875 (GuiUp=1 verified).
- Patched `InitGui.py` defers server start until `FreeCAD.GuiUp`.
- Model built via `build_galpao.run()` (669 obj, 0 interferences in test).
