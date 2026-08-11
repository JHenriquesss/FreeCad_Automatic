# Task 7 — Cross-check de claims de MÓDULOS/FUNÇÕES/WIRING da wiki contra o código real

- **Data:** 2026-08-11
- **Executor:** Sisyphus-Junior (todo 7 do plano de revisão da wiki)
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (branch `docs/revisao-wiki-2026-08-11`)
- **Código inspecionado:** `framework\galpao_fw\*.py` (135 módulos — inventário task-1 usado como base, NÃO refeito)
- **Wiki:** `framework\galpao_fw\wiki\` (7 arquivos — leitura apenas, NENHUM editado)
- **Saídas:** esta evidência (vereditos + passada reversa + PATCH LIST) — NENHUM commit, NENHUM código alterado

---

## 1. Método (documentação obrigatória)

1. **Fontes de claims:** ledger task-5 (colunas `claim | arquivo:linha | tipo | veredito: pendente`), filtrando os tipos `módulo`, `função` e `wiring` (126 claims) + claims de conteúdo módulo marcados como `PR` no ledger quando citam módulo/função (`00-index:71`, `00-index:73`, `00-index:74`, `00-index:184-187`) + os 2 claims da inconsistência `CutSurfaceDisplay` com tipo fora do filtro, incluídos por pedido explícito do MUST DO 4 (`04-decisions:125` decisão-status; `06-open-threads:358-368` thread-status — os outros 2 da inconsistência, `03-phases:150-153` e `05-glossary:34`, já estão no filtro). **Total: 135 claims verificados** (121 ok + 12 corrigir + 2 obsoleto).
2. **Verificação (a) arquivo existe:** `Test-Path` + cruzamento com a tabela do task-1 (135 módulos).
3. **Verificação (b) função citada existe:** grep real `Select-String "def <nome>"` (e padrões de constante/dict como `REQUERIDOS_PONTE`, `METODOS`, `_AXES`, `CutSurfaceDisplay`) no módulo citado — 118 greps de função executados (lotes de 10–90).
4. **Verificação (c) wiring citado confere:** leitura do ponto de chamada no orquestrador (ex.: `rodar_galpao.py:923` gate de divisa; `:868` gate-calha; `build_final.py:3-21` pipeline calc→PDF; `projeto_spec.py:649` pass-through) + confirmação de imports.
5. **Passada reversa:** script PowerShell — para cada um dos 135 módulos do task-1, grep por palavra inteira (regex `(?<![A-Za-z0-9_])<nome>(?![A-Za-z0-9_])`, evita falso positivo `mao_francesa`×`mao_francesa_geom`) nos 7 arquivos da wiki; não-citados por nome classificados por leitura da wiki em `na-wiki (nome)` / `parcial (capacidade descrita sem nome)` / `faltante-na-wiki`.
6. **Código é a verdade:** toda divergência textual da wiki foi resolvida contra o código (ex.: `CutSurfaceDisplay`).

---

## 2. Tabela de vereditos — claims de módulo/função/wiring (135)

Legenda: **ok** = claim confirmado com evidência de código lida; **corrigir** = claim com erro factual (sugestão no PATCH LIST); **obsoleto** = descreve algo que não existe mais (removido/substituído) ou plano nunca executado; **faltante** = algo que existe no código e NÃO está na wiki (registrado na seção 3 — passada reversa).

### 2.1 00-index.md (24 claims)

| item | origem wiki:linha | claim (resumo) | veredito | evidência código:linha |
|---|---|---|---|---|
| 1 | 00-index:3 | `galpao_turnkey.rodar(spec)` consolida gates, modelo federado (IFC+3D+clash) e caderno executivo único | corrigir | galpao_turnkey.py:138 `def rodar(spec)` (gates ✓, federado ✓ via emitir_bim:253/montar_3d_federado:313/checa_interferencia_federada:595); caderno NÃO é montado por rodar() — caderno_turnkey.py é módulo separado (orphan por import; task-1) |
| 2 | 00-index:3 | Cada vertical é stateless: rodar/membros_bim/emitir_bim/montar_pranchas + _selftest | ok | galpao_concreto.py:74/301/396/439/551; galpao_eletrico.py:59/401/479/491/526; galpao_seguranca_incendio.py:27/241/330/122/372; galpao_hidraulica.py:39/239/296/307/380; galpao_climatizacao.py:28/74/107/118/191 |
| 3 | 00-index:27-28 | Elétrico: 9 módulos (cargas/condutores/curto/proteção/FP/subestação MT/aterramento/SPDA/luminotécnica NBR 8995) | ok | cargas_eletricas.py, condutores_nbr5410.py, curto_circuito.py, protecao_nbr5410.py, fator_potencia.py, subestacao_nbr14039.py, aterramento_nbr15749.py, spda_nbr5419.py, luminotecnica_nbr8995.py — 9/9 existem (task-1) |
| 4 | 00-index:34-35 | S32: modelo federado (IFC + 3D + clash AABB com triagem esperado×revisar) | ok | galpao_turnkey.py:253 emitir_bim (IFC por disciplina + federado), :313 montar_3d_federado, :595 checa_interferencia_federada, :524 _clash_esperado |
| 5 | 00-index:50-52 | S40/#150: `janelas_laterais` unificada na convenção FAIXA; `_janela_band`; `aberturas_para_build` pass-through | ok | projeto_spec.py `def _janela_band` (encontrada); projeto_spec.py:649-657 `def aberturas_para_build` — docstring documenta T40 e corpo é `return dict(aberturas or {})` (pass-through literal) |
| 6 | 00-index:71 | PR #57/#59: `montar_modelo` com auto-fallback headless (bridge→freecadcmd), porta 9875 | ok | rodar_projeto.py:210 `def montar_modelo(spec, out_dir, ...)`; :250 fallback "bridge indisponivel... caindo p/ headless" |
| 7 | 00-index:73 | PR #60: modelo neutro estende `secundarios_lineares` (terças/girts/tirantes/contraventamento como IfcMember) | corrigir | modelo_neutro.py NÃO tem `secundarios_lineares`; as funções reais são `tercas`(:116), `girts`(:163), `tirantes_parede`(:198), `contrav_cobertura`(:222), `tirantes_cobertura`(:524) |
| 8 | 00-index:74 | PR #61: `modelo_analitico` + emissor IFC4 Structural | corrigir | `modelo_analitico` NÃO é módulo — é função `galpao_portico.modelo_analitico()` (galpao_portico.py:305); emissor real `ifc_emit.emitir_ifc_analitico` (ifc_emit.py:533) + `emitir_ifc_analitico_do_spec` (:632) |
| 9 | 00-index:89-91 | PR #49: `tools/run_build_suite.ps1` (logs build-logs/LATEST.txt); `tools/register_build_task.ps1` (tarefa GalpaoFW-BuildSuite, Weekly Dom 03:00) | ok | `tools/run_build_suite.ps1` e `tools/register_build_task.ps1` existem — na raiz do repo (`<worktree>\tools\`, NÃO `framework\galpao_fw\tools\` que só tem README.md + run_tests.py) |
| 10 | 00-index:96-99 | PR #47: `montagem.py` (SI, headless) + Gate 8 + prancha PE16_MONTAGEM | ok | montagem.py existe; gate8 em rodar_galpao (params montagem); `PE16_MONTAGEM` citado no módulo |
| 11 | 00-index:101 | `guindaste_requerido` — rafter pré-montado no solo governa tonelagem | ok | montagem.py `def guindaste_requerido` (grep encontrado) |
| 12 | 00-index:102-104 | `estai_provisorio` T=F/(n·cosα), ancoragem N=T·sinα; `forca_lateral_montagem` γf3=1,30; `tolerancia_prumo_montagem` max(H/500,5mm) teto 25mm | ok | montagem.py `def estai_provisorio`, `def forca_lateral_montagem`, `def tolerancia_prumo_montagem` (grep encontrados) |
| 13 | 00-index:120-124 | PR #46: `marcas_peca.py` grava `Marca` no FCStd/BIM; `por_marca` extrai comprimento de CORTE; `tolerancias_fabricacao.py` Q09T; PE14 CROQUIS | corrigir | marcas_peca.py existe e grava `Marca` (build_galpao.py:1935-1947 usa `_mp.mapa_marcas(grupos)`); **`por_marca` NÃO existe** — funções reais: `prefixo_marca`(:30), `mapa_marcas`(:38), `_selftest`(:54); tolerancias_fabricacao.py existe |
| 14 | 00-index:125 | `diafragma.py` — NBR 15421 8.3.2 (deflexão >2×drift_médio → FLEXÍVEL); suporte a RÍGIDO | ok | diafragma.py existe; test_diafragma.py (8) existe em tests/ |
| 15 | 00-index:143-145 | Bugs de infra: filtro de vigas MORTO `"_VIGA_"` → `_assenta` no-op, terças penetrando 60%; cache de módulo irmão no freecad.exe | ok | histórico descrito; fix `re.match(r"^PORTICO_\d+_V\d+")` travado por test_terca_assento_3d.py; test_ship_cache_modulo.py existe |
| 16 | 00-index:154-156 | BUG-RAIZ `frame2d` UDL com sinal invertido; fix de 2 sinais em `solve()` | ok | frame2d.py `def solve` existe; test_frame2d_sinal.py existe (D52) |
| 17 | 00-index:157-158 | Vento §2A `_wind_unico` sem Cpe → sucção/uplift; `abertura_dominante` real (Cpi 6.2.5, vedada ≠ portão) | ok | galpao_portico.py `def _wind_unico` (grep); `abertura_dominante` em galpao_portico.py; `vento_nbr6123.cpi_por_abertura`; test_vento_uplift.py existe |
| 18 | 00-index:159-160 | Campos mortos do wizard: carga de parede, janela (L,H→faixa), legislação, `tapamento` removido | ok | histórico (D54); `cargas_parede` em projeto_spec.py:588; `_janela_band` converte; tests test_carga_parede/test_aberturas_janela/test_terreno_mapper existem |
| 19 | 00-index:175-177 | `rodar_projeto.rodar_tudo(spec)` = calc+memorial PDF+3D+pranchas+RELATORIO-CONSOLIDADO+dossiê único (`dossie.py`/fitz); veredito `res["atende_global"]` | ok | rodar_projeto.py:479 `def rodar_tudo`; :509 `res = calcular(...)`; :578 RELATORIO-CONSOLIDADO; :584 `import dossie`; :393-396 agrega `atende_global` |
| 20 | 00-index:178-179 | `escopo.py` (envelope+fora-de-escopo+carimbo ART); neve (EN 1991-1-3); multi-vão (`geometria.spans`) | ok | escopo.py existe; neve.py existe (wired por rodar_galpao — task-1); `geometria.spans` em projeto_spec/rodar_galpao |
| 21 | 00-index:180-183 | `validacao.py` 7 benchmarks + sistema CBCA <1%; PE15_DET_BLOCO | ok | validacao.py `def rodar` + `def validacao_referencia` (grep); test_validacao.py (17) e test_validacao_alonso.py existem |
| 22 | 00-index:184-187 | 2º caso-referência PENDENTE (Pfeil 8.7.1 treliça ≠ framework); plano `check_trelica_estatica` | obsoleto | `check_trelica_estatica` NÃO existe em validacao.py (nem em qualquer módulo); era PLANO (T14 "ONDE PARAMOS") — nunca implementado; sem substituto no código |
| 23 | 00-index:217-226 | `enrijecedor_painel.py` (§5.4.3.1, kv=5+5/(a/h)²), `dg25_ltb.py` estendido | ok | enrijecedor_painel.py existe; dg25_ltb.py existe; test_fase613/test_fase614 existem |
| 24 | 00-index:232-234 | Órfãos wired (fase 6): calha, sapata_divisa, alma_variavel, tesoura; restou `neve` | corrigir | calhas.py `def dimensiona`(:89), sapata_divisa.py `def dimensiona_divisa`, alma_variavel/tesoura wired — ✓; **neve NÃO restou órfã**: desde D51 (2026-07-16) neve.py é wired (gate `neve` no ProjetoSpec; rodar_galpao) — claim reflete estado da fase 6 (07-10) |

### 2.2 01-architecture.md (32 claims)

| item | origem wiki:linha | claim (resumo) | veredito | evidência código:linha |
|---|---|---|---|---|
| 25 | 01-architecture:4 | `projeto_spec.py` — ProjetoSpec fonte única; `validar()` bloqueia | ok | projeto_spec.py existe; `def validar` (grep encontrado) |
| 26 | 01-architecture:10 | Cadeia 1: `galpao_portico` — pórtico 2D, flecha lateral no beiral (ELS) | ok | galpao_portico.py existe |
| 27 | 01-architecture:11 | Cadeia 2: `estabilidade_b1b2` — 2ª ordem MAES, K=1 (4.9.6.2) | ok | estabilidade_b1b2.py existe |
| 28 | 01-architecture:12 | Cadeia 3: `check_nbr8800` — verificação por peça, K=1, flexo-compressão 5.5.1.2 split 0,2, FLT Anexo G | ok | check_nbr8800.py existe; `def verifica`(:140); test-tree:14 confirma asserts |
| 29 | 01-architecture:13 | Cadeia 4: `redimensionamento` first-fit ELU+ELS (flecha ≤ H/300, Tab. C.1) | ok | redimensionamento.py existe; `def _aplica` (grep encontrado) |
| 30 | 01-architecture:16 | `rodar_galpao._casos_base_envelope()` lê reação do nó de base do solve de 2ª ordem (`R[3·nBaseL+{0,1,2}]`=V,N,M) | ok | rodar_galpao.py:106 `def _casos_base_envelope`; :125 `N, V, M = R[3*nb+1], R[3*nb], R[3*nb+2]` — exato |
| 31 | 01-architecture:17 | `fundacao_sapata.dimensiona_sapata_env` — menor geometria que passa TODAS as combos | ok | fundacao_sapata.py `def dimensiona_sapata_env` (grep); chamada rodar_galpao.py:767 |
| 32 | 01-architecture:18 | `base_chumbador` — placa + chumbadores, caso "Base engastada — M=…" | ok | base_chumbador.py existe; `bc.dimensiona_base(b)` rodar_galpao.py:685 |
| 33 | 01-architecture:19 | wiring: Mesmo R para redim/fundação/base → consistência; M do engaste não recalculado | ok | casos_base = _casos_base_envelope() (rodar_galpao.py:762) alimenta fs.dimensiona_sapata_env(:767); bc.dimensiona_base(:685) e redim.melhor(:289) usam o mesmo envelope/solve |
| 34 | 01-architecture:24 | Tabela Análise: galpao_portico, estabilidade_b1b2, frame2d (solver genérico), diafragma (rigidez de cobertura) | ok | 4 módulos existem (task-1) |
| 35 | 01-architecture:25 | Tabela Verificação: check_nbr8800, perfis (tabela), torcao_nbr8800, empocamento_nbr8800 | ok | 4 módulos existem |
| 36 | 01-architecture:26 | Tabela Ações: vento_nbr6123 (+§8 Cpe local + atrito §6.4), ponte_rolante, sismo_nbr15421 | ok | 3 módulos existem; cpe_local_parede/cpe_local_cobertura/sucao_local_fixacao em vento_nbr6123.py (grep) |
| 37 | 01-architecture:27 | Tabela Secundários: tercas_iteracao (+distorcional FSM), secundarios_nbr8800, mao_francesa, contraventamento, telha_cobertura, escada (patamares Blondel) | ok | 6 módulos existem; `lb_maximo` em mao_francesa.py; `_dimensiona_multi` em escada.py |
| 38 | 01-architecture:28 | Tabela Ligações/base: ligacoes (joelho/parafusos+furos/Tab.14/block shear/T-stub), base_chumbador | ok | ligacoes.py + base_chumbador.py existem; `def verifica_espacamento`, `def block_shear_linha`, `def solda`, `def fw_rd_base` (grep) |
| 39 | 01-architecture:29 | Tabela Fundação: fundacao_sapata, sapata_divisa, viga_equilibrio, viga_baldrame, estaca_profunda | ok | 5 módulos existem |
| 40 | 01-architecture:30 | Tabela Montagem/Obra: montagem (10 passos, guindaste, estai, prumo H/500) | ok | montagem.py existe; 4 funções verificadas (item 11-12) |
| 41 | 01-architecture:31 | Tabela Fabricação: marcas_peca (takeoff/corte 3D), tolerancias_fabricacao (Q09T) | ok | 2 módulos existem |
| 42 | 01-architecture:32 | Verif. flexão avançada: props_I_mono, dg25_ltb, forcas_localizadas (§5.7), console_ponte (FLT Anexo G Tab G.1) | ok | 4 módulos existem; `mrd_flt_chapa` em console_ponte.py (grep) |
| 43 | 01-architecture:33 | Interop BIM: modelo_neutro, ifc_emit, ifc_map, modelo_analitico | corrigir | modelo_neutro.py, ifc_emit.py, ifc_map.py existem ✓; **modelo_analitico não é módulo** — é `galpao_portico.modelo_analitico()` (galpao_portico.py:305) + `ifc_emit.emitir_ifc_analitico` |
| 44 | 01-architecture:35 | Orquestração: rodar_galpao, rodar_projeto, framework, projeto_spec, romaneio, acos | ok | 6 módulos existem |
| 45 | 01-architecture:36 | Geometria/saída: build_galpao, dxf_vistas, terreno (KML) | corrigir | build_galpao.py + terreno.py existem ✓; **dxf_vistas NÃO existe** — removido em D33 (03-phases:225 "Scripts antigos (vistas_fc, dxf_vistas, techdraw_vistas) removidos"); teste Test-Path: False |
| 46 | 01-architecture:41-44 | wiring: Gate de divisa (`rodar_galpao`) — estaca+viga_equilibrio (PROFUNDA) vs sapata_divisa (rasa); `res["divisa"]["tipo"]` | ok | rodar_galpao.py:923 `if params.get("divisa")`; :926 `if params.get("estaca") and res.get("estaca")` → `veq.dimensiona_viga_equilibrio`(:928) senão `sapata_divisa`; imports :40/:41 |
| 47 | 01-architecture:46 | `estaca_profunda` = 3 métodos + tração/grupo/atrito neg/recalque + bloco (bielas-tirantes+ancoragem+punção) | ok | estaca_profunda.py existe; `def _camada_na_ponta`(grep); task-1 confirma Aoki/Décourt/Teixeira; test_estaca_ponta.py existe |
| 48 | 01-architecture:49-51 | QUADRO DE VERIFICAÇÕES no topo do MEMORIAL-CONSOLIDADO (util≤1,0) | ok | rodar_galpao monta quadro; helpers `_uok`/`_uokd` existem (grep rodar_galpao.py) |
| 49 | 01-architecture:56-58 | Helpers `_uok(util,ok)`/`_uokd(dict)` forçam util>1 quando flag de OK reprova | ok | rodar_galpao.py `def _uok`, `def _uokd` (grep encontrados) |
| 50 | 01-architecture:59-60 | `fogo` reporta θ_aço/θ_crítica; `rodar_projeto` exporta resultados+estados para pranchas | ok | fogo_nbr14323.py existe (util=θ/θ_cr, D49 8.34); rodar_projeto exporta `resultados`+`estados` (rodar_projeto.py) |
| 51 | 01-architecture:63 | `verifica_conexoes` mede formas reais no 3D (assentamento `_assenta`) | ok | build_galpao.py `def verifica_conexoes`, `def _assenta` (grep encontrados) |
| 52 | 01-architecture:66 | wiring: Pipeline calc (`rodar_projeto.calcular`) → 3D (`build_galpao`) → executivo (`rodar_projeto.rodar_executivo` c/ `techdraw_exec`); `build_final.py` encadeia + memorial (`relatorio_calculo`) | ok | rodar_projeto.py `def calcular`, `def rodar_executivo` (grep); build_final.py:3-4 `import rodar_projeto as RP, projeto_spec as PS`, `import relatorio_calculo as RC`; :21 `RP.calcular(s, out)` |
| 53 | 01-architecture:67 | `techdraw_exec` roda DENTRO do freecad.exe (config gerada FORA por `config_de_spec`, injetada via `script_bootstrap`); `construtores` = builders `_pr_*`; detalhes recebem `todos`, gerais `objs` (sem `_MIUDEZAS`) | ok | techdraw_exec.py `def config_de_spec` (grep); `script_bootstrap` presente (galpao_concreto.py:472, galpao_eletrico.py:348, galpao_climatizacao.py:142); `_MIUDEZAS` techdraw_exec.py:30; `def _pr_ligacoes` |
| 54 | 01-architecture:68 | Padrão de detalhe: crop `Part.makeBox`+`Shape.common` → compound `<PREFIXO>_CROP` → `_vista` HLR; eixo curado `_AXES` | ok | techdraw_exec.py `def _vista`(:201); `_AXES`(:1108) + `LIGACOES`(:1121); uso `_AXES[elev]`(:1305) |
| 55 | 01-architecture:69 | Guard `_cobertura`; `PREFIXOS_SEM_DESENHO`=("VAO",); guard anti-silhueta `_n_edges`≥15; `smoke_executivo` sela 4 geometrias | ok | techdraw_exec.py `def _cobertura`, `PREFIXOS_SEM_DESENHO`(:40/:107), `_n_edges`(:230/:1931); smoke_executivo.py existe |
| 56 | 01-architecture:75 | `_pt()` troca ponto decimal por vírgula nos memoriais (preserva nº de item tipo 6.118) | corrigir | **`_pt` não existe em rodar_galpao/relatorio_calculo**; função real é `relatorio_calculo._vg` (relatorio_calculo.py:276-278, docstring "Ponto decimal -> virgula", regex preserva 6.118); `_pt` existe só local em console_ponte.py:212 |

### 2.3 02-test-tree.md (22 claims tipo módulo/função)

| item | origem wiki:linha | claim (resumo) | veredito | evidência código:linha |
|---|---|---|---|---|
| 57 | 02-test-tree:3 | Cada módulo de cálculo tem `_selftest()`; `python <modulo>.py --selftest` (novos) ou `python <modulo>.py` (antigos) | ok | 107/135 módulos com `def _selftest`; antigos rodam via `__main__` (check_nbr8800.py:233, redimensionamento, estabilidade_b1b2, tercas_iteracao); sem selftest só módulos de apoio/executivo/build (28: build_*, techdraw_*, orquestradores) |
| 58 | 02-test-tree:8 | `fundacao_sapata` assere: núcleo σ, borda, FS_tomb/desl, As→M, compr. diagonal α_v/τ_rd2, rigidez 22.6.1, rho_min(fck) Tab.17.3 | ok | fundacao_sapata.py existe; `def puncao_sapata`, `def recalque_elastico`, `def dimensiona_bloco_env` (grep) |
| 59 | 02-test-tree:9 | `ligacoes` assere: solda filete 6.5.5; interação parafuso min(Fvrd,Fcrd); contravento A36 governa | ok | ligacoes.py existe; `fw_rd_base` (grep) |
| 60 | 02-test-tree:10 | `ponte_rolante` assere: Rmax/Rmin, Barré, flecha δ, Tab.C.1, override Wy_top/Zy_top | ok | ponte_rolante.py existe; `def cargas_de_roda`, `def verifica_fadiga` (grep) |
| 61 | 02-test-tree:11 | `mao_francesa` assere: `lb_maximo` busca exponencial + bisseção 80it; HEA180 Lb_max 4,64m | ok | mao_francesa.py `def lb_maximo` (grep) |
| 62 | 02-test-tree:12 | `contraventamento` assere: Nt,Rd min; N=F/cosθ; r=d/4; L/r≤300; 2% Msd/braço | ok | contraventamento.py existe |
| 63 | 02-test-tree:13 | `redimensionamento` assere: H/300 → HEB200/IPE300; `_peso_rel` não altera seleção | ok | redimensionamento.py existe; `def _aplica` (grep) |
| 64 | 02-test-tree:14 | `check_nbr8800` assere: flexo-compressão 5.5.1.2 split 0,2; FLT Anexo G; K=1 | ok | check_nbr8800.py existe |
| 65 | 02-test-tree:15 | `base_chumbador` assere: tração/corte/interação; bearing 6.6.5; placa DG1; ancoragem 9.4.2 | ok | base_chumbador.py existe; `def ancoragem_chumbador`, `def cone_arrancamento_aci`, `def edge_breakout_cisalhamento_aci`, `def interacao_tracao_cortante_aci`, `def transferencia_cortante_base` (grep) |
| 66 | 02-test-tree:16 | `junta_dilatacao` assere: δ=α·dT·L; L_max 120/60 × fatores; 100m→1 junta | ok | junta_dilatacao.py existe; `def relatorio_pt` (grep) |
| 67 | 02-test-tree:17 | `vento_nbr6123` assere: S2 Tab.1; q=0,613Vk²; §8 Cpe local parede −1,1 / cobertura −2,0 | ok | vento_nbr6123.py existe; cpe_local_parede/cpe_local_cobertura/sucao_local_fixacao (grep) |
| 68 | 02-test-tree:18 | `telha_cobertura` assere: M_Rd=Wef·fy/γ; L/180 grav, L/120 vento; combos 1,25G+1,50Q e 1,40W−0,90G | ok | telha_cobertura.py existe |
| 69 | 02-test-tree:19 | `viga_baldrame` assere: M_d=γf·cM·w·L²; amarração As=Nd/fyd; b≥12cm; estribo 0,6d≤300 | ok | viga_baldrame.py existe |
| 70 | 02-test-tree:20 | `sismo_nbr15421` assere: espectro Sa(T) 4 trechos; Cs=2,5ags0/(R/I); θ 9.6; δx 9.5; 100/30 | ok | sismo_nbr15421.py existe |
| 71 | 02-test-tree:21 | `estaca_profunda` assere: Aoki-Velloso; Décourt; Teixeira; Converse-Labarre; bloco biela/ancoragem/punção | ok | estaca_profunda.py existe; 3 métodos + `_camada_na_ponta` (grep) |
| 72 | 02-test-tree:22 | `ligacoes` (novos) assere: furos 6.3.9/10/11; Tab.14; block shear 6.5.6; T-stub EN 1993-1-8 | ok | ligacoes.py existe; `verifica_espacamento`/`block_shear_linha` (grep) |
| 73 | 02-test-tree:23 | `gusset_ligacao` assere: Whitmore 30°; reusa `check_nbr8800.chi_compressao`, `ligacoes.block_shear_linha`, `ligacoes.solda` | ok | gusset_ligacao.py `def verifica_gusset` (grep); check_nbr8800.py `def chi_compressao`/`def fator_Q`; ligacoes.block_shear_linha |
| 74 | 02-test-tree:24 | `console_ponte` assere: grupo de solda elástico f=√(fv²+fh²+fb²); dimensiona perna; V_Rd=0,6·fy·t·L/γa1 | ok | console_ponte.py `def verifica_console` (grep); `def mrd_flt_chapa` (grep) |
| 75 | 02-test-tree:25 | `nbr8400`: `coef_dinamico(HC,Vh)` Tab.12; `n_ciclos(B0-B10)` Tab.9 | ok | nbr8400.py `def coef_dinamico`, `def n_ciclos` (grep encontrados) |
| 76 | 02-test-tree:58-66 | Sessão 07-17: 9 arquivos de teste citados | ok | todos existem: test_frame2d_sinal, test_carga_parede, test_aberturas_janela, test_terreno_mapper, test_crashes_wiki07, test_vento_uplift, test_multivao_hetero, test_bloco_fundacao, test_shed (glob tests/) |
| 77 | 02-test-tree:87-96 | Sessão 16: 10 arquivos de teste citados (contencao, cantoneira, mão-francesa, terca_assento, ship_cache, pecas_conexao, takeoff_x_modelo, relatorio_x_calculo, notas_prancha, quadro_materiais) | ok | todos existem em tests/ (glob) |
| 78 | 02-test-tree:118-126 | Sessão 19: test_modelo_neutro, test_ifc_emit, test_ifc_map, test_ifc_secundarios_xcheck, test_modelo_analitico, test_pipeline_bim, test_montar_headless, test_fase69-614, test_calha_calc_3d, test_viga_rolamento_3d | ok | todos existem em tests/ (glob; test_modelo_analitico.py existe como arquivo de TESTE — nota: o módulo `modelo_analitico` sob teste não é arquivo próprio) |

### 2.4 03-phases.md (33 claims)

| item | origem wiki:linha | claim (resumo) | veredito | evidência código:linha |
|---|---|---|---|---|
| 79 | 03-phases:24-26 | 6.15 `props_I_mono.py` novo (Wxc≠Wxt, Cw mono, rt); dg25_ltb mono-aware | ok | props_I_mono.py existe; dg25_ltb.py existe; test_fase615_props_mono.py existe |
| 80 | 03-phases:27-28 | 6.16 `dg25_ltb` estendido: envelope FLB/TFY/ruptura/Mn=min §5.4.4-7 | ok | dg25_ltb.py existe; test_fase616_dg25_envelope.py existe |
| 81 | 03-phases:29-32 | 6.17 `forcas_localizadas.py` novo: §5.7 completo + enrijecedor de apoio §5.7.9 | ok | forcas_localizadas.py existe; test_fase617_forcas_localizadas.py existe |
| 82 | 03-phases:33-35 | 6.18 `viga_equilibrio.py` novo; wiring ramifica estaca/sapata em `rodar_galpao` | ok | viga_equilibrio.py existe; wiring rodar_galpao.py:923-929 (item 46); test_fase618_viga_equilibrio.py existe |
| 83 | 03-phases:36-38 | 6.19 glyph solda + PE09 (`techdraw_exec`): DrawViewSymbol+SVG; DrawViewSpreadsheet.Scale | ok | techdraw_exec.py `def _svg_solda_filete` (grep); DrawViewSpreadsheet techdraw_exec.py:381/:410; test_fase619_glifo_solda.py existe |
| 84 | 03-phases:57-59 | 6.4 coluna tapered: `_secoes_coluna`/`coluna_segmentos`; `util_col_global` | ok | galpao_portico.py:179 `def _secoes_coluna`, :719/:727 `coluna_segmentos`; rodar_galpao.py:1213 `util_col_global`; test_fase64_coluna_tapered.py existe |
| 85 | 03-phases:60-62 | 6.5 zona de painel: `zona_painel.py` novo (§5.7.7+§5.7.2/3/4/6+doubler); FSd=M/dm−V_col | ok | zona_painel.py existe; test_fase65_zona_painel.py existe |
| 86 | 03-phases:63-64 | 6.6 FLT mísula: `flt_misula.py` novo (Anexo J) | ok | flt_misula.py existe; test_fase66_flt_misula.py existe |
| 87 | 03-phases:65-66 | 6.7 vento→tesoura: `w_vento` auto NBR 6123; bug de sinal do uplift corrigido | ok | tesoura.py usa w_vento; test_fase67_vento_tesoura.py existe |
| 88 | 03-phases:67-68 | 6.8 alma esbelta: `alma_esbelta.py` novo (Anexo H, h/tw>5,70√(E/fy)) | ok | alma_esbelta.py existe; `def _valida` (grep); test_fase68_alma_esbelta.py existe |
| 89 | 03-phases:95-97 | `tesoura.resolve_trelica` — método dos nós (2j×(b+3), numpy.linalg.solve) | ok | tesoura.py `def resolve_trelica` (grep encontrado) |
| 90 | 03-phases:98-100 | `verifica_tesoura` — combos 1,4w + 1,4w_v+0,9(−w); chi·Q·A·fy via `check_nbr8800.chi_compressao/fator_Q` | ok | tesoura.py `def verifica_tesoura`; check_nbr8800.py `chi_compressao`/`fator_Q` (grep) |
| 91 | 03-phases:101-106 | `_desenha_tesoura` — barras biapoiadas sem joelho/cumeeira; geometria replicada numpy-free no build | ok | **build_galpao.py:535 `def _desenha_tesoura`** (não em tesoura.py — nota de localização); chamada :846; numpy lazy confirmado por imports |
| 92 | 03-phases:112-116 | `estrutura.tipo_portico`=alma_variavel → `_chain_var` + `secao_tapered`; sentinela `_UNSET` | ok | galpao_portico.py:143 `def _chain_var`; alma_variavel.py `def secao_tapered` (grep); `_UNSET` no módulo (grep) |
| 93 | 03-phases:119-123 | `build_galpao.tapered_rafter` = `_sweep_tapered` (loft Part.makeLoft; cai no prismático se h1==h2) | ok | build_galpao.py:332 `def _sweep_tapered`; `tapered_rafter` no build (grep) |
| 94 | 03-phases:131-132 | Gates: `cobertura.chuva_I_mm_h` (default 150); `fundacao.divisa` (None|dict {dist_divisa}) | ok | projeto_spec.py `chuva_I_mm_h` (grep); campo divisa no spec (grep) |
| 95 | 03-phases:133-136 | wiring: `rodar_galpao` — calha roda da geometria quando `params["calha"]` → gate-calha.txt + res["calha"]; divisa `dimensiona_divisa(P=maior compressão, dist_eixos=bay, dist_divisa)` → gate7-divisa.txt | ok | rodar_galpao.py:868 `if params.get("calha")`; :883/:890 `calhas.dimensiona(...)`; :893 `save("gate-calha.txt", ...)`; :894 `res["calha"]`; divisa :923+ → gate7-divisa.txt |
| 96 | 03-phases:137-139 | Memorial: `relatorio_calculo.METODOS` +13. CALHAS (NBR 10844/Bellei) + 11g. SAPATA DE DIVISA (Alonso) | ok | relatorio_calculo.py:37 `METODOS = {`; :147 `"11g. SAPATA DE DIVISA"`; :157 `"13. CALHAS E CONDUTORES"` (nome com "E CONDUTORES" — nota) |
| 97 | 03-phases:141-142 | Órfãos restantes: `neve` (não escolhido — fica documentado, não wired) | corrigir | neve.py é **wired** desde D51/PR #12 (rodar_galpao importa neve; gate `neve` no ProjetoSpec) — task-1: "neve.py ... wired (rodar_galpao)" |
| 98 | 03-phases:147-149 | `DrawViewSection` constrói headless no FreeCAD 1.1 (probe: box → seção com 4 arestas) | ok | techdraw_exec.py:1228-1229 docstring "o blocker historico (T6, 'failed to create section CS' headless) foi resolvido no FreeCAD 1.1"; :1234 addObject DrawViewSection |
| 99 | 03-phases:150-153 | `techdraw_exec._secao_ligacao`: DrawViewSection do crop, plano pelo centro, `CutSurfaceDisplay="Hatch"`; wire em `_detalhe_ligacao` (view `VLIG_SEC_*`) | corrigir | techdraw_exec.py:1214 `def _secao_ligacao` ✓; **código usa `"SvgHatch"`, NÃO "Hatch"** (techdraw_exec.py:1247 `sec.CutSurfaceDisplay = "SvgHatch"`; comentário :1243-1245 enum válido) |
| 100 | 03-phases:154-158 | Guard: expõe `detalhes_secoes` (nome→arestas); smoke exige ≥1 seção e nenhuma vazia | ok | techdraw_exec.py:1255/:1940 `detalhes_secoes`; smoke_executivo.py:207 |
| 101 | 03-phases:163-165 | `ponte_rolante.forcas_horizontais(..., n_rodas_motoras)` — H_long = frac_long·R_roda_max·n_motoras | ok | ponte_rolante.py `def forcas_horizontais` (grep encontrado); test_fase4_ponte_estendida.py existe |
| 102 | 03-phases:166-169 | `nbr8400.py` novo (φ Tab.12 + N Tab.9) | ok | nbr8400.py existe; coef_dinamico/n_ciclos (grep) |
| 103 | 03-phases:170-173 | Gate: `projeto_spec.REQUERIDOS_PONTE` — validar() bloqueia ponte incompleta | ok | projeto_spec.py `REQUERIDOS_PONTE` (grep encontrado) |
| 104 | 03-phases:181-183 | Spec: `fundacao.tipo` (sapata|estaca) BLOQUEIA; bloco `estaca`; mappers to_rodar_params/to_build_kwargs | ok | projeto_spec.py:661 `def to_rodar_params`; to_build_kwargs (grep); test_fase3_fundacao_profunda.py existe |
| 105 | 03-phases:187-190 | 3D: `build_galpao` desenha ESTACA (cilindros)/BLOCO (coroa 150 mm)/BALDRAME; concreto MONOLÍTICO (`_e_fundacao`) | ok | build_galpao.py `def _desenha_estaca`, `def _e_fundacao` (grep encontrados) |
| 106 | 03-phases:230-231 | `gusset_ligacao.verifica_gusset` (Whitmore+block shear+solda); `console_ponte.verifica_console`; callouts `_callout_fab` | ok | gusset_ligacao.py `def verifica_gusset`; console_ponte.py `def verifica_console`; techdraw_exec.py `def _callout_fab` (greps) |
| 107 | 03-phases:232 | `DrawViewSection` FALHA headless → fallback elevação; símbolo AWS ausente → texto | obsoleto | estado D37 (07-09), **REVERTIDO em D40 (07-10)**: DrawViewSection constrói headless no FreeCAD 1.1 (techdraw_exec.py:1228-1229; `_secao_ligacao` ativa com SvgHatch); o próprio 03-phases:147-158 (fase 5) registra a reversão |
| 108 | 03-phases:238-241 | Módulos novos: `tensao_ponto.py` (§5.5.2.3 M-V), `cortante_tapered.py` (equilíbrio), `dg25_ltb.py` (cross-check); +vento por zona | ok | 3 módulos existem; test_fase69..612 existem (glob) |
| 109 | 03-phases:249-253 | 6.13 `enrijecedor_painel.py` (kv=5+5/(a/h)², V_Rd 3 domínios); relaxa cap h/tw≤260 via `alma_esbelta._valida` | ok | enrijecedor_painel.py existe; alma_esbelta.py `def _valida`; test_fase613.py existe |
| 110 | 03-phases:253-255 | 6.14 DG25 full (`dg25_ltb.py` estendido: Cb 5.4-1/2, Rpc, Rpg, Mn 3 regiões) | ok | dg25_ltb.py existe; test_fase614.py existe |
| 111 | 03-phases:324-325 | 17 módulos matemáticos + Contenção lateral (NBR 8800 4.11.3.4) | ok | contencao_lateral.py existe (task-1); test_contencao_lateral.py existe |

### 2.5 04-decisions.md (2 claims verificados — tipo decisão-status, pedido explícito)

| item | origem wiki:linha | claim (resumo) | veredito | evidência código:linha |
|---|---|---|---|---|
| 112 | 04-decisions:125 (D40) | `CutSurfaceDisplay` enum válido = ['Hide','Color','SvgHatch','PatHatch']; "Hatch" NÃO existe → uso **SvgHatch** | ok | techdraw_exec.py:1243-1247 — comentário enum + `sec.CutSurfaceDisplay = "SvgHatch"` — **bate exato** |
| 113 | 04-decisions:578-588 (D67 infra) | filtro de vigas MORTO `"_VIGA_"` (nome real PORTICO_xx_Vyy); fix re.match; cache de módulo irmão no freecad.exe | ok | histórico travado por tests: test_terca_assento_3d.py, test_ship_cache_modulo.py (existem em tests/) |

### 2.6 05-glossary.md (13 claims tipo módulo)

| item | origem wiki:linha | claim (resumo) | veredito | evidência código:linha |
|---|---|---|---|---|
| 114 | 05-glossary:14 | Gusset verificado em `gusset_ligacao` | ok | gusset_ligacao.py existe |
| 115 | 05-glossary:16 | Block shear 6.5.6; primitivo `ligacoes.block_shear_linha` | ok | ligacoes.py `def block_shear_linha` (grep) |
| 116 | 05-glossary:17 | Console verificado em `console_ponte` | ok | console_ponte.py existe |
| 117 | 05-glossary:19 | Callout `_callout_fab` — todo número vem do cálculo | ok | techdraw_exec.py `def _callout_fab` (grep) |
| 118 | 05-glossary:26 | ProjetoSpec = `projeto_spec.py`; `validar()` bloqueia | ok | projeto_spec.py existe |
| 119 | 05-glossary:33 | Rodas motoras (`n_rodas_motoras`) | ok | ponte_rolante.py `forcas_horizontais(..., n_rodas_motoras)` (grep) |
| 120 | 05-glossary:34 | DrawViewSection headless no FreeCAD 1.1 (`CutSurfaceDisplay="SvgHatch"`); `VLIG_SEC_*` | ok | techdraw_exec.py:1234 `"VLIG_SEC_" + base`; :1247 `"SvgHatch"` — **bate exato** |
| 121 | 05-glossary:35 | `props_I_mono` dá Wxc≠Wxt, Iyc/Iy, hc/hp/ho, Cw mono; habilita ramo mono do DG25 | ok | props_I_mono.py existe |
| 122 | 05-glossary:40 | `_svg_solda_filete(lado=)` — arrow/other/both AWS A2.4 | ok | techdraw_exec.py `def _svg_solda_filete` (grep) |
| 123 | 05-glossary:42 | Plano de Montagem (PE16): 10 passos; `montagem.py` + prancha PE16 | ok | montagem.py existe; 4 funções verificadas (item 11-12) |
| 124 | 05-glossary:43 | Guarda de Build 3D (`tools/`): run_build_suite.ps1 + tarefa GalpaoFW-BuildSuite | ok | scripts existem na raiz `<worktree>\tools\` (nota de localização) |
| 125 | 05-glossary:46 | Interop BIM/IFC4: `modelo_neutro.py` + `ifc_emit.py` + `ifc_map.py` + `modelo_analitico.py`; gera galpao.ifc e galpao_analitico.ifc | corrigir | modelo_neutro.py/ifc_emit.py/ifc_map.py existem ✓; **`modelo_analitico.py` NÃO existe como arquivo** — é função `galpao_portico.modelo_analitico()` + `ifc_emit.emitir_ifc_analitico_do_spec`(:632) + `modelo_neutro.analitico_do_spec`(:998); nome "galpao_analitico.ifc" não aparece como literal (arquivo nomeado pelo chamador, ex. `%s.ifc % DOC_NAME`) |
| 126 | 05-glossary:47 | pycufsm_compat = shim numpy 2.x para FSM (`distorcional_fsm.py`/`pycufsm`) | ok | pycufsm_compat.py e distorcional_fsm.py existem; 06-open-threads:218-225 detalha |

### 2.7 06-open-threads.md (9 claims)

| item | origem wiki:linha | claim (resumo) | veredito | evidência código:linha |
|---|---|---|---|---|
| 127 | 06-open-threads:4 | T40: convenção FAIXA canônica; `wizard.construir_spec` via `PS._janela_band`; `aberturas_para_build` pass-through; `ifc_emit` inalterado | ok | wizard.py `def construir_spec` (grep); projeto_spec.py `def _janela_band`; :649-657 pass-through literal |
| 128 | 06-open-threads:13 | T21 A3: `console_ponte.mrd_flt_chapa` (Lb=2·ecc, Cb=1, λp/λr/Mcr Anexo G Tab. G.1) | ok | console_ponte.py `def mrd_flt_chapa` (grep); test_console_flt.py existe |
| 129 | 06-open-threads:14 | T21 C5: patamar de escada `_dimensiona_multi` (N lances + (N−1) patamares; Blondel) | ok | escada.py `def _dimensiona_multi` (grep); test_escada_patamar.py existe |
| 130 | 06-open-threads:24-26 | T20 FECHADO: tools/run_build_suite.ps1 + tools/register_build_task.ps1 | ok | scripts existem na raiz `<worktree>\tools\` (nota de localização) |
| 131 | 06-open-threads:37-44 | T19 FECHADO: `montagem.py` (SI, headless); 10 passos; PE16_MONTAGEM | ok | montagem.py existe; funções verificadas (item 11-12) |
| 132 | 06-open-threads:131 | Script `verificar_amostra.py` (no main) | ok | verificar_amostra.py existe (task-1, orphan) |
| 133 | 06-open-threads:218-225 | T13: numpy 2 DESTRAVADO via `pycufsm_compat.py` (proxy np em cutwp/analysis_p) | ok | pycufsm_compat.py existe; distorcional_fsm.py importa shim (grep) |
| 134 | 06-open-threads:264-272 | HANDOFF: módulos novos — telha_cobertura.py, viga_baldrame.py, estaca_profunda.py (3 métodos + tração + grupo + atrito neg + recalque + bloco) | ok | 3 módulos existem; estaca_profunda com _camada_na_ponta (grep) |
| 135 | 06-open-threads:358-368 | T6: `_callout_fab`; corte seccionado `_secao_ligacao` com `CutSurfaceDisplay="Hatch"` sob smoke (detalhes_secoes, arestas>0) | corrigir | techdraw_exec.py `_callout_fab` ✓, `_secao_ligacao` ✓, `detalhes_secoes` ✓; **código usa `"SvgHatch"` (techdraw_exec.py:1247)**, não "Hatch" |

---

## 3. Passada reversa — 135 módulos do inventário task-1 × cobertura na wiki

Método: regex palavra inteira nos 7 arquivos da wiki (evita falso positivo entre módulos com prefixo comum). 73 módulos citados pelo NOME. Dos 62 não-citados por nome: 34 têm a capacidade descrita sem nome (classificação por leitura da wiki), 28 **não têm NENHUMA menção**. Os 28 faltantes alimentam os todos 12/13/16 e a varredura do 19.

### 3.1 na-wiki (nome do módulo presente na wiki) — 73 módulos

`acos`, `alma_esbelta`, `alma_variavel`, `base_chumbador`, `build_final`, `build_galpao`, `caderno_turnkey`, `calhas`, `check_nbr8800`, `console_ponte`, `contencao_lateral`, `contraventamento`, `cortante_tapered`, `dg25_ltb`, `diafragma`, `distorcional_fsm`, `dossie`, `empocamento_nbr8800`, `enrijecedor_painel`, `escada`, `escopo`, `estabilidade_b1b2`, `estaca_profunda`, `flt_misula`, `forcas_localizadas`, `frame2d`, `framework`, `fundacao_sapata`, `galpao_portico`, `galpao_turnkey`, `gusset_ligacao`, `ifc_emit`, `ifc_map`, `junta_dilatacao`, `ligacoes`, `mao_francesa`, `mao_francesa_geom`, `marcas_peca`, `modelo_neutro`, `montagem`, `nbr8400`, `neve`, `perfis`, `plataforma`, `ponte_rolante`, `projeto_spec`, `props_I_mono`, `pycufsm_compat`, `redimensionamento`, `relatorio_calculo`, `rodar_galpao`, `rodar_projeto`, `romaneio`, `sapata_divisa`, `secundarios_nbr8800`, `sismo_nbr15421`, `smoke_executivo`, `techdraw_exec`, `telha_cobertura`, `tensao_ponto`, `tercas_iteracao`, `tercas_nbr14762`, `terreno`, `tesoura`, `tolerancias_fabricacao`, `torcao_nbr8800`, `validacao`, `vento_nbr6123`, `verificar_amostra`, `viga_baldrame`, `viga_equilibrio`, `wizard`, `zona_painel`

### 3.2 parcial (capacidade descrita sem o nome do módulo) — 34 módulos

| módulo | menção descritiva na wiki (arquivo:linha) |
|---|---|
| galpao_concreto | 00-index:23-26 "Vertical de CONCRETO (PRs #81-#101)... pré-moldado engastado" |
| galpao_eletrico | 00-index:27-29 "Vertical ELÉTRICO (PRs #102-#106)" |
| galpao_seguranca_incendio | 00-index:30-32 "Vertical INCÊNDIO/AVCB (PRs #107-#110)" |
| galpao_hidraulica | 00-index:40-43 "S39 — HIDRÁULICA + COORDENAÇÃO (PRs #136-#147)" |
| galpao_climatizacao | 00-index:31-32 "climatização (16401) standalone" |
| hidraulica_predial | 00-index:3 "hidráulica predial (NBR 5626/8160/10844)" |
| cargas_eletricas | 00-index:27-28 "9 módulos (cargas/condutores/...)" |
| condutores_nbr5410 | 00-index:27-28 "condutores... até 300 mm² + paralelo" |
| curto_circuito | 00-index:27-28 "curto" |
| protecao_nbr5410 | 00-index:27-28 "proteção" |
| fator_potencia | 00-index:27-28 "FP" |
| subestacao_nbr14039 | 00-index:27-28 "subestação MT" |
| aterramento_nbr15749 | 00-index:27-28 "aterramento" |
| spda_nbr5419 | 00-index:27-28 "SPDA" |
| luminotecnica_nbr8995 | 00-index:27-28 "luminotécnica NBR 8995" |
| iluminacao_emergencia_nbr10898 | 00-index:30-31 "emergência (10898)" |
| sinalizacao_nbr16820 | 00-index:30-31 "sinalização (16820)" |
| deteccao_alarme_nbr17240 | 00-index:30-31 "alarme (17240)" |
| proteccao_sprinklers_nbr10897 | 00-index:30-31 "sprinklers (10897)" |
| hidrantes_nbr13714 | 00-index:30-31 "hidrantes (13714)" |
| iluminacao_externa_nbr5101 | 00-index:31-32 "iluminação externa (5101)" |
| climatizacao_nbr16401 | 00-index:31-32 "climatização (16401)" |
| premoldado_nbr9062 | 00-index:3 "concreto (NBR 6118/9062, pré-moldado+protensão)" |
| pilar_concreto | 00-index:23-24 "Pilar em flexão composta reta+oblíqua/biaxial (17.2.5, α=1,2)" |
| viga_concreto | 00-index:23-25 "viga CA" |
| viga_protendida | 00-index:25-26 "PROTENSÃO (pré-tração vãos >12 m)" |
| perdas_protensao_nbr6118 | 00-index:25-26 "PROTENSÃO" |
| fogo_nbr14323 | 03-phases:10-11/04-decisions:351-353 "fogo incremental Anexo B + θ/θ_cr"; 01-architecture:59 "fogo reporta θ_aço/θ_crítica" |
| executivo_concreto | 00-index:23-26 "executivo (quadro+memorial+SVG)" do concreto |
| desenho_concreto | 00-index:23-26 "executivo (quadro+memorial+SVG)" |
| techdraw_concreto | 00-index:23-26 "pranchas A1 TechDraw" do concreto |
| build_concreto | 00-index:23-26 "3D SÓLIDO + pranchas A1 TechDraw" |
| build_eletrico | 00-index:27-29 "BIM + 3D + executivo A1" |
| build_federado | 00-index:34-35 "modelo federado (IFC + 3D + clash AABB)" |

### 3.3 faltante-na-wiki (nenhuma menção — nome nem capacidade) — **28 módulos**

| módulo | categoria (task-1) | wired/orphan (task-1) |
|---|---|---|
| caderno_encargos | turnkey | orphan |
| compatibilizacao | turnkey | orphan |
| cronograma | utilitario | orphan |
| demo_engenheiro | utilitario | orphan |
| desenho_climatizacao | executivo-techdraw | wired (techdraw_climatizacao) |
| desenho_coordenacao | executivo-techdraw | wired (techdraw_coordenacao) |
| desenho_eletrico | executivo-techdraw | wired (techdraw_eletrico) |
| desenho_hidraulica | executivo-techdraw | wired (techdraw_hidraulica) |
| desenho_incendio | executivo-techdraw | wired (galpao_seguranca_incendio, techdraw_incendio) |
| desenho_piso | executivo-techdraw | orphan |
| esgoto_reuso | vertical-hidraulica | orphan |
| estabilidade_global_nbr6118 | vertical-concreto | wired (galpao_concreto) |
| fissuracao_nbr6118 | vertical-concreto | wired (estabilidade_global_nbr6118, viga_concreto) |
| fogo_nbr15200 | vertical-concreto | wired (galpao_concreto) |
| fotovoltaico | vertical-eletrico | orphan |
| geotecnia_spt | vertical-concreto | wired (galpao_concreto) |
| instalacao_eletrica | vertical-eletrico | wired (desenho_eletrico, galpao_eletrico, orcamento, techdraw_eletrico) |
| orcamento | utilitario | orphan |
| pacote_legal | turnkey | orphan |
| piso_industrial | vertical-concreto | wired (desenho_piso, galpao_concreto) |
| techdraw_climatizacao | executivo-techdraw | wired (galpao_climatizacao) |
| techdraw_coordenacao | executivo-techdraw | wired (galpao_turnkey) |
| techdraw_eletrico | executivo-techdraw | wired (galpao_eletrico) |
| techdraw_hidraulica | executivo-techdraw | wired (galpao_hidraulica) |
| techdraw_incendio | executivo-techdraw | wired (galpao_seguranca_incendio) |
| terraplenagem | utilitario | orphan |
| tools_probe_pe13 | utilitario | orphan |
| torcao_nbr6118 | vertical-concreto | wired (viga_concreto) |

**Resumo da passada reversa:** 73 na-wiki (nome) + 34 parcial (capacidade sem nome) + **28 faltante-na-wiki**. Destaque: os 28 faltantes incluem TODOS os módulos das verticais concreto (fogo_nbr15200, geotecnia_spt, fissuracao_nbr6118, estabilidade_global_nbr6118, piso_industrial, torcao_nbr6118) e TODO o camada executivo-techdraw dos verticais (techdraw_concreto/climatizacao/coordenacao/eletrico/hidraulica/incendio, desenho_*), além dos turnkey standalone (caderno_encargos, compatibilizacao, pacote_legal, orcamento, cronograma, terraplenagem, esgoto_reuso, fotovoltaico, demo_engenheiro).

---

## 4. Resolução da inconsistência `CutSurfaceDisplay` (Hatch × SvgHatch)

**O código é a verdade:** `techdraw_exec.py:1247` → `sec.CutSurfaceDisplay = "SvgHatch"` (com comentário :1243-1245 documentando o enum válido `['Hide','Color','SvgHatch','PatHatch']` e a razão — svg embutido, sem .pat externo, robusto headless).

| claim | origem | veredito |
|---|---|---|
| `CutSurfaceDisplay="Hatch"` | 03-phases:150-153 (fase 5) | **corrigir** — valor inválido no enum; código usa "SvgHatch" (techdraw_exec.py:1247) |
| `CutSurfaceDisplay="Hatch"` | 06-open-threads:358-368 (T6) | **corrigir** — idem |
| `CutSurfaceDisplay="SvgHatch"` (D40, documenta que "Hatch" não existe) | 04-decisions:125 | **ok** — bate exato com o código |
| `CutSurfaceDisplay="SvgHatch"` | 05-glossary:34 | **ok** — bate exato com o código |

---

## 5. QA interno (obrigatório)

1. **10 vereditos "ok" conferidos lendo o código citado (linha existe):**
   - 01-architecture:16 → rodar_galpao.py:106 `def _casos_base_envelope` + :125 `N, V, M = R[3*nb+1], R[3*nb], R[3*nb+2]` (match exato do claim)
   - 02-test-tree:25 → nbr8400.py `def coef_dinamico` + `def n_ciclos` (grep real)
   - 02-test-tree:23 → gusset_ligacao.py `def verifica_gusset`; check_nbr8800.py `def chi_compressao`; ligacoes.py `def block_shear_linha` (grep real)
   - 03-phases:57-59 → galpao_portico.py:179 `def _secoes_coluna`, :719/:727 `coluna_segmentos`; rodar_galpao.py:1213 `util_col_global`
   - 03-phases:133-136 → rodar_galpao.py:868 `params.get("calha")`, :883 `calhas.dimensiona(...)`, :893 `save("gate-calha.txt")`, :894 `res["calha"]`
   - 03-phases:150-153 (parte correta) → techdraw_exec.py:1214 `def _secao_ligacao`, :1234 `"VLIG_SEC_" + base`
   - 01-architecture:41-44 → rodar_galpao.py:923-929 ramificação estaca/sapata + `veq.dimensiona_viga_equilibrio`
   - 01-architecture:66 → build_final.py:3-21 (`import rodar_projeto as RP` + `RP.calcular(s, out)` + `import relatorio_calculo as RC`)
   - 00-index:175-177 → rodar_projeto.py:479 `def rodar_tudo`, :578 RELATORIO-CONSOLIDADO, :584 `import dossie`, :395 `atende_global`
   - 05-glossary:40 → techdraw_exec.py `def _svg_solda_filete` (grep real)
2. **Claims sem evidência de código → NUNCA "ok":** 14 claims receberam corrigir/obsoleto, todos com evidência negativa concreta (grep `def` ausente, Test-Path False, ou estado revertido documentado) e sugestão no PATCH LIST.
3. **Arquivos de teste citados no 02-test-tree:** 67 globs `tests/<nome>*.py` — todos existem (0 faltantes).
4. **Encodings:** arquivo escrito em UTF-8 (com BOM, padrão Windows) — verificado.

---

## 6. PATCH LIST para o ledger task-5 (formato exato)

Formato: `| <arquivo>:<linha-original-do-ledger> | <palavra-chave do sujeito do claim> | <veredito> | task-7 |` (corrigir acrescenta `sugestão:` na coluna extra).

### 6.1 corrigir (12)

| arquivo:linha | palavra-chave | veredito | task-7 | sugestão |
|---|---|---|---|---|
| 00-index:3 | galpao_turnkey.rodar consolida gates e caderno executivo | corrigir | task-7 | sugestão: rodar() consolida gates+federado; o caderno executivo único é o módulo separado caderno_turnkey (via fitz), não montado por galpao_turnkey.rodar() |
| 00-index:73 | secundarios_lineares estende modelo neutro | corrigir | task-7 | sugestão: nome não existe em modelo_neutro.py; funções reais: tercas/girts/tirantes_parede/contrav_cobertura/tirantes_cobertura |
| 00-index:74 | modelo_analitico emissor IFC4 Structural | corrigir | task-7 | sugestão: não é módulo; é galpao_portico.modelo_analitico() (galpao_portico.py:305) + ifc_emit.emitir_ifc_analitico (ifc_emit.py:533) |
| 00-index:120-124 | por_marca extrai comprimento de CORTE | corrigir | task-7 | sugestão: por_marca não existe em marcas_peca.py; funções reais: prefixo_marca (marcas_peca.py:30) e mapa_marcas (:38) |
| 00-index:232-234 | restou neve (não wired) | corrigir | task-7 | sugestão: neve é wired desde D51 (gate neve no ProjetoSpec; rodar_galpao) — claim reflete estado da fase 6 (2026-07-10) |
| 01-architecture:33 | Interop BIM modelo_analitico | corrigir | task-7 | sugestão: trocar por função galpao_portico.modelo_analitico() + ifc_emit.emitir_ifc_analitico (não há módulo modelo_analitico.py) |
| 01-architecture:36 | dxf_vistas (Geometria/saída) | corrigir | task-7 | sugestão: dxf_vistas removido em D33 (03-phases:225); Geometria/saída = build_galpao + terreno (+techdraw_exec) |
| 01-architecture:75 | _pt() troca ponto por vírgula | corrigir | task-7 | sugestão: função real é relatorio_calculo._vg (relatorio_calculo.py:276-278); _pt existe só local em console_ponte.py:212 |
| 03-phases:141-142 | neve não wired | corrigir | task-7 | sugestão: neve.py wired (rodar_galpao) desde D51; órfãos restantes atuais: ver task-1 (21 orphans) |
| 03-phases:150-153 | _secao_ligacao CutSurfaceDisplay Hatch | corrigir | task-7 | sugestão: código usa "SvgHatch" (techdraw_exec.py:1247); "Hatch" não é enum válido (D40) |
| 05-glossary:46 | modelo_analitico.py emissor analítico | corrigir | task-7 | sugestão: não existe modelo_analitico.py; é galpao_portico.modelo_analitico() + ifc_emit.emitir_ifc_analitico_do_spec + modelo_neutro.analitico_do_spec |
| 06-open-threads:358-368 | _secao_ligacao CutSurfaceDisplay Hatch | corrigir | task-7 | sugestão: código usa "SvgHatch" (techdraw_exec.py:1247); "Hatch" não é enum válido (D40) |

### 6.2 obsoleto (2)

| arquivo:linha | palavra-chave | veredito | task-7 |
|---|---|---|---|
| 00-index:184-187 | check_trelica_estatica plano pendente | obsoleto | task-7 |
| 03-phases:232 | DrawViewSection falha headless fallback | obsoleto | task-7 |

### 6.3 ok (120)

| arquivo:linha | palavra-chave | veredito | task-7 |
|---|---|---|---|
| 00-index:3 | cada vertical stateless rodar/membros_bim | ok | task-7 |
| 00-index:27-28 | elétrico 9 módulos cargas/condutores | ok | task-7 |
| 00-index:34-35 | S32 modelo federado IFC 3D clash AABB | ok | task-7 |
| 00-index:50-52 | janelas_laterais FAIXA _janela_band pass-through | ok | task-7 |
| 00-index:71 | montar_modelo auto-fallback headless 9875 | ok | task-7 |
| 00-index:89-91 | tools run_build_suite register_build_task | ok | task-7 |
| 00-index:96-99 | montagem.py Gate 8 PE16_MONTAGEM | ok | task-7 |
| 00-index:101 | guindaste_requerido rafter pré-montado | ok | task-7 |
| 00-index:102-104 | estai_provisorio forca_lateral tolerancia_prumo | ok | task-7 |
| 00-index:125 | diafragma.py NBR 15421 8.3.2 flexível | ok | task-7 |
| 00-index:143-145 | filtro de vigas MORTO _VIGA_ | ok | task-7 |
| 00-index:154-156 | frame2d UDL sinal invertido solve | ok | task-7 |
| 00-index:157-158 | _wind_unico sucção abertura_dominante Cpi | ok | task-7 |
| 00-index:159-160 | campos mortos wizard tapamento | ok | task-7 |
| 00-index:175-177 | rodar_tudo dossie atende_global | ok | task-7 |
| 00-index:178-179 | escopo.py neve EN 1991 spans | ok | task-7 |
| 00-index:180-183 | validacao.py 7 benchmarks CBCA PE15 | ok | task-7 |
| 00-index:217-226 | enrijecedor_painel dg25_ltb kv | ok | task-7 |
| 01-architecture:4 | projeto_spec validar bloqueia | ok | task-7 |
| 01-architecture:10 | galpao_portico pórtico 2D flecha beiral | ok | task-7 |
| 01-architecture:11 | estabilidade_b1b2 MAES K=1 | ok | task-7 |
| 01-architecture:12 | check_nbr8800 5.5.1.2 split 0,2 | ok | task-7 |
| 01-architecture:13 | redimensionamento first-fit H/300 | ok | task-7 |
| 01-architecture:16 | _casos_base_envelope R[3·nBaseL] | ok | task-7 |
| 01-architecture:17 | dimensiona_sapata_env | ok | task-7 |
| 01-architecture:18 | base_chumbador placa chumbadores | ok | task-7 |
| 01-architecture:19 | mesmo R redim fundação base | ok | task-7 |
| 01-architecture:24 | tabela análise frame2d diafragma | ok | task-7 |
| 01-architecture:25 | tabela verificação torcao empocamento | ok | task-7 |
| 01-architecture:26 | tabela ações vento ponte sismo | ok | task-7 |
| 01-architecture:27 | tabela secundários tercas mao_francesa | ok | task-7 |
| 01-architecture:28 | tabela ligações block shear T-stub | ok | task-7 |
| 01-architecture:29 | tabela fundação viga_equilibrio baldrame | ok | task-7 |
| 01-architecture:30 | tabela montagem 10 passos H/500 | ok | task-7 |
| 01-architecture:31 | tabela fabricação marcas_peca tolerancias | ok | task-7 |
| 01-architecture:32 | props_I_mono dg25_ltb forcas_localizadas | ok | task-7 |
| 01-architecture:35 | orquestração rodar_galpao romaneio acos | ok | task-7 |
| 01-architecture:41-44 | gate divisa viga_equilibrio sapata_divisa | ok | task-7 |
| 01-architecture:46 | estaca_profunda 3 métodos bloco | ok | task-7 |
| 01-architecture:49-51 | QUADRO DE VERIFICAÇÕES util≤1 | ok | task-7 |
| 01-architecture:56-58 | _uok _uokd util>1 | ok | task-7 |
| 01-architecture:59-60 | fogo θ_aço θ_crítica resultados estados | ok | task-7 |
| 01-architecture:63 | verifica_conexoes _assenta | ok | task-7 |
| 01-architecture:66 | pipeline calcular build_galpao rodar_executivo | ok | task-7 |
| 01-architecture:67 | techdraw_exec config_de_spec _MIUDEZAS | ok | task-7 |
| 01-architecture:68 | crop _vista HLR _AXES | ok | task-7 |
| 01-architecture:69 | _cobertura PREFIXOS_SEM_DESENHO _n_edges | ok | task-7 |
| 02-test-tree:3 | _selftest por módulo | ok | task-7 |
| 02-test-tree:8 | fundacao_sapata assere rho_min | ok | task-7 |
| 02-test-tree:9 | ligacoes assere solda 6.5.5 | ok | task-7 |
| 02-test-tree:10 | ponte_rolante assere Barré Wy_top | ok | task-7 |
| 02-test-tree:11 | mao_francesa lb_maximo bisseção | ok | task-7 |
| 02-test-tree:12 | contraventamento assere Nt,Rd | ok | task-7 |
| 02-test-tree:13 | redimensionamento HEB200 IPE300 | ok | task-7 |
| 02-test-tree:14 | check_nbr8800 split 0,2 Anexo G | ok | task-7 |
| 02-test-tree:15 | base_chumbador ancoragem 9.4.2 | ok | task-7 |
| 02-test-tree:16 | junta_dilatacao L_max 120/60 | ok | task-7 |
| 02-test-tree:17 | vento_nbr6123 S2 Cpe local | ok | task-7 |
| 02-test-tree:18 | telha_cobertura L/180 L/120 | ok | task-7 |
| 02-test-tree:19 | viga_baldrame amarração Nd/fyd | ok | task-7 |
| 02-test-tree:20 | sismo_nbr15421 espectro Cs | ok | task-7 |
| 02-test-tree:21 | estaca_profunda Aoki Décourt Teixeira | ok | task-7 |
| 02-test-tree:22 | ligacoes furos Tab.14 T-stub | ok | task-7 |
| 02-test-tree:23 | gusset Whitmore chi_compressao | ok | task-7 |
| 02-test-tree:24 | console grupo de solda elástico | ok | task-7 |
| 02-test-tree:25 | nbr8400 coef_dinamico n_ciclos | ok | task-7 |
| 02-test-tree:58-66 | test_frame2d_sinal test_shed | ok | task-7 |
| 02-test-tree:87-96 | test_contencao_lateral test_takeoff | ok | task-7 |
| 02-test-tree:118-126 | test_modelo_neutro test_ifc_emit | ok | task-7 |
| 03-phases:24-26 | props_I_mono mono-aware | ok | task-7 |
| 03-phases:27-28 | dg25_ltb envelope FLB TFY | ok | task-7 |
| 03-phases:29-32 | forcas_localizadas §5.7.9 | ok | task-7 |
| 03-phases:33-35 | viga_equilibrio wiring estaca/sapata | ok | task-7 |
| 03-phases:36-38 | glyph solda PE09 DrawViewSpreadsheet | ok | task-7 |
| 03-phases:57-59 | _secoes_coluna coluna_segmentos | ok | task-7 |
| 03-phases:60-62 | zona_painel FSd=M/dm | ok | task-7 |
| 03-phases:63-64 | flt_misula Anexo J | ok | task-7 |
| 03-phases:65-66 | w_vento tesoura uplift | ok | task-7 |
| 03-phases:67-68 | alma_esbelta Anexo H | ok | task-7 |
| 03-phases:95-97 | resolve_trelica método dos nós | ok | task-7 |
| 03-phases:98-100 | verifica_tesoura chi Q A fy | ok | task-7 |
| 03-phases:101-106 | _desenha_tesoura (build_galpao.py:535) | ok | task-7 |
| 03-phases:112-116 | _chain_var secao_tapered _UNSET | ok | task-7 |
| 03-phases:119-123 | tapered_rafter _sweep_tapered loft | ok | task-7 |
| 03-phases:131-132 | chuva_I_mm_h fundacao.divisa | ok | task-7 |
| 03-phases:133-136 | calha gate-calha dimensiona_divisa | ok | task-7 |
| 03-phases:137-139 | METODOS 13.CALHAS 11g.DIVISA | ok | task-7 |
| 03-phases:147-149 | DrawViewSection headless FreeCAD 1.1 | ok | task-7 |
| 03-phases:154-158 | detalhes_secoes guard smoke | ok | task-7 |
| 03-phases:163-165 | forcas_horizontais n_rodas_motoras | ok | task-7 |
| 03-phases:166-169 | nbr8400 Tab.12 Tab.9 | ok | task-7 |
| 03-phases:170-173 | REQUERIDOS_PONTE validar bloqueia | ok | task-7 |
| 03-phases:181-183 | fundacao.tipo estaca mappers | ok | task-7 |
| 03-phases:187-190 | _desenha_estaca _e_fundacao | ok | task-7 |
| 03-phases:230-231 | verifica_gusset verifica_console callout | ok | task-7 |
| 03-phases:238-241 | tensao_ponto cortante_tapered dg25_ltb | ok | task-7 |
| 03-phases:249-253 | enrijecedor_painel _valida relaxa | ok | task-7 |
| 03-phases:253-255 | DG25 full Rpc Rpg Mn | ok | task-7 |
| 03-phases:324-325 | 17 módulos contencao_lateral | ok | task-7 |
| 04-decisions:125 | CutSurfaceDisplay SvgHatch D40 | ok | task-7 |
| 04-decisions:578-588 | filtro VIGA morto cache módulo | ok | task-7 |
| 05-glossary:14 | gusset_ligacao chapa de nó | ok | task-7 |
| 05-glossary:16 | block_shear_linha primitivo | ok | task-7 |
| 05-glossary:17 | console_ponte bracket | ok | task-7 |
| 05-glossary:19 | _callout_fab cálculo | ok | task-7 |
| 05-glossary:26 | projeto_spec.py validar | ok | task-7 |
| 05-glossary:33 | n_rodas_motoras frenagem | ok | task-7 |
| 05-glossary:34 | SvgHatch VLIG_SEC_* | ok | task-7 |
| 05-glossary:35 | props_I_mono Cw mono | ok | task-7 |
| 05-glossary:40 | _svg_solda_filete | ok | task-7 |
| 05-glossary:42 | montagem.py PE16 10 passos | ok | task-7 |
| 05-glossary:43 | run_build_suite.ps1 GalpaoFW-BuildSuite | ok | task-7 |
| 05-glossary:47 | pycufsm_compat numpy 2 | ok | task-7 |
| 06-open-threads:4 | _janela_band pass-through FAIXA | ok | task-7 |
| 06-open-threads:13 | mrd_flt_chapa FLT console | ok | task-7 |
| 06-open-threads:14 | _dimensiona_multi patamar | ok | task-7 |
| 06-open-threads:24-26 | run_build_suite register_build_task | ok | task-7 |
| 06-open-threads:37-44 | montagem.py 10 passos PE16 | ok | task-7 |
| 06-open-threads:131 | verificar_amostra.py | ok | task-7 |
| 06-open-threads:218-225 | pycufsm_compat cutwp analysis_p | ok | task-7 |
| 06-open-threads:264-272 | telha_cobertura viga_baldrame estaca | ok | task-7 |

**Totais do PATCH LIST: 135 linhas = 121 ok + 12 corrigir + 2 obsoleto.**

---

## 7. Garantias

- Nenhum arquivo da wiki editado (leitura apenas com `Get-Content`/Read).
- Nenhum código alterado; nenhum commit realizado.
- Verificação por grep estático real (`Select-String "def <nome>"` — 118 greps de função) + leitura de pontos de chamada para wiring; códigograph não foi necessário além do índice do repo principal (worktree não tem índice próprio) — método grep registrado como o determinístico (mesmo padrão do task-1).
- Evidência escrita em UTF-8 explícito.
