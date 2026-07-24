# 01 — Arquitetura

## Princípios
- **ProjetoSpec = fonte única da verdade** (`projeto_spec.py`). `validar()` bloqueia calc/model até todos os gates respondidos. Builder lê só do spec (sem cópia hardcoded).
- **Calcula apenas; CONCEITUAL** — pendente revisão + ART do eng. responsável. Nada é executivo.
- **Ask, Do Not Invent**: σ_solo,adm, μ, coesão, fck, fyk, φ (impacto ponte), frações laterais/long — INPUT do caso; a skill pergunta. Defaults entram flagados.
- **Método extraído das normas** (`pesquisa/aço/*.pdf`), não de memória. Cada módulo cita item da NBR.

## Cadeia de cálculo (por candidato de perfil)
1. `galpao_portico` — pórtico 2D, flecha lateral no beiral (ELS).
2. `estabilidade_b1b2` — 2ª ordem **MAES** (rigidez 0,8 + forças nocionais) → Nsd/Msd/Vsd amplificados. Permite **K=1** (NBR 8800 4.9.6.2).
3. `check_nbr8800` — verificação por peça, K=1, todas as combinações → pior interação (flexo-compressão 5.5.1.2, split 0,2; FLT Anexo G).
4. `redimensionamento` — first-fit: par (coluna,viga) mais leve que passa ELU (interação≤1) **E** ELS (flecha ≤ **H/300**, Tab. C.1). Ver [[04-decisions#D5]].

## Envelope de combinações (por elemento)
`rodar_galpao._casos_base_envelope()` lê a reação do nó de base **direto do solve de 2ª ordem** (`R[3·nBaseL+{0,1,2}]` = V,N,M) por combinação ELU. Alimenta:
- **fundação** `fundacao_sapata.dimensiona_sapata_env` — menor geometria que passa TODAS as combos (bearing=N máx, tombamento=N mín+M).
- **base** `base_chumbador` — placa + chumbadores, caso "Base engastada — M=…".
Mesmo `R` para redim/fundação/base → consistência; M do engaste não é recalculado.

## Módulos
| Grupo | Módulos | Norma |
|---|---|---|
| Análise | `galpao_portico`, `estabilidade_b1b2`, `frame2d` (solver genérico), **`diafragma`** (rigidez de cobertura) | NBR 8800 An. D, NBR 15421 §8.3.2 |
| Verificação | `check_nbr8800`, `perfis` (tabela), **`torcao_nbr8800`**, **`empocamento_nbr8800`** | NBR 8800 §5.5.2 / §9.3 |
| Ações | `vento_nbr6123` (+§8 Cpe local borda/canto + atrito §6.4), `ponte_rolante`, `sismo_nbr15421` | NBR 6123, 8800/8400, **15421** |
| Secundários | `tercas_iteracao` (+distorcional FSM), `secundarios_nbr8800`, `mao_francesa`, `contraventamento`, **`telha_cobertura`**, **`escada`** (patamares Blondel) | NBR 14762, 8800, NBR 9050 |
| Ligações/base | `ligacoes` (joelho/parafusos + furos/Tab.14/block shear/T-stub), `base_chumbador` | NBR 8800 + AISC DG1 + ACI 318 + EN 1993-1-8 |
| Fundação | `fundacao_sapata` (rasa), `sapata_divisa` (divisa rasa), **`viga_equilibrio`** (divisa sobre estacas), **`viga_baldrame`** (amarração), **`estaca_profunda`** (profunda) | NBR 6118, 6122 + Aoki/Décourt/Teixeira |
| Montagem/Obra | **`montagem`** (sequência 10 passos, guindaste, estai, prumo H/500) | NBR 8800 §12.3 + AISC 303 + Bellei 7.6.4 |
| Fabricação 3D/2D | **`marcas_peca`** (takeoff/corte 3D), **`tolerancias_fabricacao`** (tabela 2D Q09T) | NBR 8800 §12.2/12.3 + Bellei Ap. C |
| Verif. flexão avançada | **`props_I_mono`** (perfil I monossimétrico), **`dg25_ltb`** (DG25 FLT + envelope), **`forcas_localizadas`** (NBR 8800 §5.7), **`console_ponte`** (FLT Anexo G Tab G.1) | AISC DG25 + NBR 8800 Anexo G / §5.7 |
| Interoperabilidade BIM | **`modelo_neutro`**, **`ifc_emit`**, **`ifc_map`**, **`modelo_analitico`** | IFC4 Physical (ISO 16739-1) / IFC4 Structural |
| Auto-sizing | `redimensionamento` | usa check |
| Orquestração | `rodar_galpao`, `rodar_projeto`, `framework`, `projeto_spec`, **`romaneio`**, `acos` | — |
| Geometria/saída | `build_galpao`, `dxf_vistas`, `terreno` (KML) | — |


**Sismo no envelope:** `galpao_portico`/`estabilidade_b1b2` têm caso `SISMO` (global `gp.SISMO`, `case_sismo` no beiral) + combos excepcionais C6 (1,2G±E / 1,0G±E, sem vento/Q, NBR 15421 §5.4) — entram no envelope do pórtico, base e joelho. `rodar_galpao` computa `E = H·(vão/comprimento)` e θ/P-Δ. Zona 0 (default) → E=0 → nada muda.

**Gate de divisa (`rodar_galpao`):** com `params["divisa"]`, ramifica — se há
`params["estaca"]`+`res["estaca"]` → `viga_equilibrio` (variante PROFUNDA, usa a `P_adm`
da estaca já calculada); senão → `sapata_divisa` (rasa). `res["divisa"]["tipo"]` ∈
{estaca, sapata}. Aliases `est_res`/`veq` p/ evitar shadowing.

**Fundação profunda/baldrame:** opt-in via `params["estaca"]` / `params["baldrame"]`. `estaca_profunda` = 3 métodos de capacidade (Aoki-Velloso/Décourt-Quaresma/Teixeira) + tração/grupo/atrito negativo/recalque + bloco de coroamento (bielas-tirantes+ancoragem+punção). N_pilar/N_uplift do envelope de base.

## Quadro de verificações (pass/fail consolidado)
`rodar_galpao` monta o **QUADRO DE VERIFICAÇÕES** no topo do MEMORIAL-CONSOLIDADO: uma
linha por elemento (`util = solicitação/resistência ≤ 1,0`) + alerta se algo não atende.
Único ponto de verdade pass/fail. Regras (pós-auditoria [[04-decisions#D49]]):
- Toda verificação com pass/fail calculado entra no quadro: coluna/viga/tesoura, base,
  sapata, joelho, zona de painel, terça, telha, secundários, contravento/gusset, viga de
  rolamento, console, fogo, estaca/travamento/baldrame, sismo θ, junta, calha, divisa,
  terreno, escada, plataforma.
- Helpers `_uok(util,ok)`/`_uokd(dict)` forçam `util>1` quando a flag de OK reprova mesmo
  com `util≤1` (base sob interação T-V, sapata sob punção, viga-rolamento sob fadiga/
  flecha). Elemento não rodado → linha ausente (não conta como falha).
- `fogo` reporta `θ_aço/θ_crítica` (não °C absoluto). `rodar_projeto` exporta o mesmo
  conjunto (`resultados`+`estados`) para a tabela das pranchas TechDraw.

## Auditoria geométrica
`verifica_conexoes` mede as formas reais no modelo 3D (assentamento medido `_assenta`) → auto-captura defeitos de conexão/geometria. Sapata desenhada (bloco+pedestal) no take-off com densidade própria (concreto categoria separada, não soma na tonelagem de aço).

## Projeto executivo (2D) — split calc/model/executivo
Pipeline: **calc** (`rodar_projeto.calcular`, python) → **3D** (`build_galpao`, freecadcmd ou MCP) → **executivo** (`rodar_projeto.rodar_executivo` lança `freecad.exe` c/ `techdraw_exec`). `build_final.py` encadeia + gera memorial PDF (`relatorio_calculo`). Detalhes D33–D36.
- **`techdraw_exec`** roda DENTRO do freecad.exe (config gerada FORA por `config_de_spec`, injetada via `script_bootstrap`). `construtores` = lista de builders `_pr_*`; detalhes (`_pr_base/_joelho/_contravent/_ligacoes`) recebem `todos` (inclui miudezas); gerais recebem `objs` (sem `_MIUDEZAS`).
- **Padrão de detalhe:** crop `Part.makeBox`+`Shape.common` → compound `<PREFIXO>_CROP` → `_vista` HLR. Eixo de vista curado (`_AXES`), não heurística.
- **Guard de cobertura** `_cobertura`: toda peça (tipo, normalizado por lado) desenhada em ≥1 prancha; `PREFIXOS_SEM_DESENHO`=("VAO",). Guard anti-silhueta `_n_edges`≥15. `smoke_executivo` sela 4 geometrias.

## Convenções
- Convenção do modelo: **comprimento em X, vão em Y, altura em Z** (build_galpao; `comp_x=True` fixo no executivo).
- `L` // eixo do momento do pórtico. Momento no plano do pórtico → dimensão L.
- γa1=1,10, γa2=1,35, γw2=1,35 (aço); γc=γn=1,40 (concreto).
- `_pt()` troca ponto decimal por vírgula nos memoriais (preserva nº de item tipo 6.118).
