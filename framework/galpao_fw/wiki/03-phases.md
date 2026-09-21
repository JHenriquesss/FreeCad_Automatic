# 03 — Fases

## FECHADA — Auditoria "Diretrizes Técnicas" (bugs 8.1–8.36) — 2026-07-15
Auditoria de conformidade via MCP NotebookLM (notebook "Diretrizes Técnicas para Revisão
de Projetos de Engenharia"), 5 lotes. **33 bugs reais corrigidos + 3 falsos positivos**
(8.9 junta aditiva ✓; 8.11 `L_livre=Lc` conservador ✓; 8.14 cortante sem B2 — D.2.4 ✓).
- Lote 1 (8.1–8.4) `dad7b87`; Lote 9 (8.5–8.13, 7+2FP) `06130c0`; Lote 10 (8.14–8.17,
  3+1FP) `ac529a2`; Lote 11 (8.18–8.20) `a6e3808`; Lote 12 (8.21–8.36) `741221d`.
- Temas: cortante viga alavanca; uplift γq=0; flexo-tração abs; fencepost `Lb_terca=
  L_raft/n_terca`; travas B1/B2 (denom≤0→inf); console `(|M|+|Mz|)`; `SEC_COLS_EXTERNO`
  (B1 por-coluna); fogo incremental Anexo B + `θ/θ_cr`; `Nsd_tirante` geométrico; calha
  `h_elevacao`; **observabilidade do QUADRO** (14 verificações antes omitidas surfaçam;
  `_uok`/`_uokd`); `terreno.py` deixou de ser órfão; export TechDraw completo.
- Verificação: `_selftest()` por módulo ✅ + simulação da lógica do quadro ✅. **Smoke
  completo pendente** (pipeline exige `pycufsm`, ausente no ambiente). Branch
  `revisao/homologacao-12-modulos` **não pushada**. Ver [[04-decisions#D49]],
  [[06-open-threads#T13]].

## FECHADA — Balde 4 (backlog de gaps) fases 6.15–6.19 + homologação 45–49 — 2026-07-13/14
**Escopo:** resolver os 6 itens residuais de refino (não-bug) do sistema: perfil I
monossimétrico, envelope DG25 de estados de flexão, forças localizadas §5.7, viga de
equilíbrio de divisa sobre estacas, glyph de solda AWS headless, PE09 legível.
Detalhe por fase em [[04-decisions#D48]].
- **6.15 `props_I_mono.py`** (novo): propriedades de perfil I monossimétrico (Wxc≠Wxt,
  Iyc/Iy, hc/hp/ho, Cw mono, J, rt) → habilita o ramo monossimétrico real do DG25;
  `dg25_ltb` fica mono-aware por `.get()` (dupl-sim byte-idêntico). `test_fase615` (11).
- **6.16 `dg25_ltb` estendido:** envelope FLB §5.4.4 / TFY §5.4.5 / ruptura §5.4.6 /
  Mn=min §5.4.7 (verbatim DG25 pág 62–64). INFORMATIVO. `test_fase616` (13).
- **6.17 `forcas_localizadas.py`** (novo): NBR 8800 §5.7 completo (flexão mesa 5.7.2,
  escoamento alma 5.7.3, enrugamento 5.7.4, flamb. lateral 5.7.5, flamb. par 5.7.6) +
  enrijecedor de apoio §5.7.9 (barra comprimida, Lb=0,75h, faixa 12tw/25tw). Verbatim
  pág 57–62. `test_fase617` (11). Fecha backlog "enrijecedor de apoio §5.7.4".
- **6.18 `viga_equilibrio.py`** (novo): variante PROFUNDA (estaca) da fundação de
  divisa; R'=P·l/(l−e), viga alavanca RC. Wiring ramifica estaca/sapata em
  `rodar_galpao` (gate divisa). `test_fase618` (13).
- **6.19 glyph solda + PE09 (`techdraw_exec`):** símbolo AWS A2.4 de filete headless
  via `DrawViewSymbol`+SVG inline (resolve o último resíduo do 2D, T6 glyph); PE09
  quadros ampliados via `DrawViewSpreadsheet.Scale`. `test_fase619` (9).

**HOMOLOGAÇÃO (5 pareceres sênior, 2026-07-13/14): 9 correções técnicas reais.**
REVISAO-INDICE **itens 45, 47, 48 HOMOLOGADOS; 46 e 49 em PARECER**. Cada alegação conferida contra PDF/estática antes de
aceitar. 7 bugs contra-segurança + 2 omissões normativas; 1 rejeição minha revertida
com evidência. Correções: (45) `rt` hc²→**hw²** (5.4-11); (46) `kc` hc→**hw** (5.4-24)
+ teto `Mp` do Rpt Sxt→**Sxc** (5.4-28 erratum, remete ao Rpc pág 60); (47) homologado
(k/ln documentados, inércia I_par aceita ~0,05%); (48) M do fletor da viga **R'·e→P·e**
(erro de estática) + cisalhamento §17.4 (biela VRd2+estribo, V=ΔP) + peso próprio ~5%
nas estacas + armadura de pele §17.3.5.2.3 (h>60cm); (49) glyph arrow/other/both AWS
A2.4 (posição do triângulo = lado da junta). Ver [[04-decisions#D48]], [[06-open-threads#T12]].
Não-regressão: pytest **245 passed**; `smoke_executivo` **7/7**. Commits `12ff107`→`01e14e7`.
**Gate humano:** push branch + merge PR (bloqueado p/ assistente).

## FECHADA — Backlog do parecer 6.b (fases 6.4–6.8) + revisão itens 34–38 — 2026-07-11
**Escopo:** esgotar o backlog do parecer da alma variável (coluna tapered, zona de
painel, FLT Anexo J, vento→tesoura) + desdobramento (alma esbelta Anexo H); processar
os 5 REVISAO-*.md (índice 34–38). Detalhe por fase em [[04-decisions#D45]].
**Resultado: itens 1–38 todos ✅ HOMOLOGADO.**
- **6.4 coluna tapered:** `_secoes_coluna`/`coluna_segmentos`; +compressão global J.3
  (`util_col_global`); continuidade estrita no nó. Módulos novos: nenhum (estende
  `galpao_portico`/`rodar`/`build`). Testes `test_fase64_coluna_tapered` (10 fast+1 build).
- **6.5 zona de painel:** módulo novo `zona_painel.py` (§5.7.7 + §5.7.2/3/4/6 + doubler);
  `FSd=M/dm−V_col`; enrugamento §5.7.4 (0,66/0,33); esbeltez do doubler §5.4.3. Build
  desenha `CONEX_JOELHO_*_DOUBLER` só quando exigido. `test_fase65_zona_painel` (13+1).
- **6.6 FLT mísula:** módulo novo `flt_misula.py` (Anexo J: λ maior altura + Cb racional
  §5.4.2.3a + demanda max M/Wx; sem γ). `test_fase66_flt_misula` (9).
- **6.7 vento→tesoura:** `w_vento` auto NBR 6123; **bug de sinal do uplift corrigido**
  (`+0,9·w_dead`, sem Q). `test_fase67_vento_tesoura` (7).
- **6.8 alma esbelta:** módulo novo `alma_esbelta.py` (Anexo H, despacho por
  `h/tw>5,70√(E/fy)`; Anexo G intocado). `test_fase68_alma_esbelta` (11).
**Padrão de revisão:** conferir cada alegação contra código+PDF; **8 "erros graves"
refutados** (Anexo J=seção variável, coef 0,66/0,33, FLM/Cb já no código) — imagens do
PDF via `SendUserFile` encerraram citações; **1 bug real acolhido** (sinal do uplift).
Não-regressão: ref prismática 20×10 intocada (Anexo G); smoke/calc-sweep 7/7 (smoke
completo estoura o cap de background ~2min → validado por-caso). Commits
`1baef85`→`a55a1fe` (branch `revisao/homologacao-12-modulos`).

## FECHADA — Homologação dos 6 pareceres sênior (itens 28–33) — 2026-07-11
**Escopo:** processar os 6 REVISAO-*.md pendentes (gusset, console, fundação
profunda, ponte 8400, alma variável, tesoura); homologar/corrigir. Detalhe por
item em [[04-decisions#D44]]. **Resultado: itens 1–33 todos ✅ HOMOLOGADO.**
- **Correções reais aplicadas:** gusset (ruptura líquida, Kl/Thornton, K=0,65),
  console (SRSS colinear→algébrico, 2 cordões, flexão em balanço, L_ef), fundação
  (FS gate 3,0/prova, biela tan≥1,0, momento no grupo, baldrame transversal n≤2),
  alma variável (FLT member-level + Lb dinâmico pela mesa comprimida), tesoura
  (banzo reto duas águas, tração ruptura líquida, compressão 2 eixos, guard
  n_paineis par).
- **3 alegações de "erro grave" REFUTADAS com prova de bancada** (console SRSS,
  ponte H_long=ΣR_motoras, alma-var array não-invertido) — sênior retratou-se.
  Regra [[04-decisions#D6]] reforçada: conferir contra código+PDF, não aceitar cego.
- **Evidência:** selftests verdes; builds estaca/tesoura 0 interferências; fase6b/6c
  tests passed. Commits 718bbe8→35cda72. [[06-open-threads#T8]].

## FECHADA — Pórtico treliçado / tesoura (fase 6.c) — 2026-07-10
**Escopo:** pórtico treliçado (tesoura) fim-a-fim. `tesoura.py` era **só geometria**
(nós+barras isostática); esta fase **cria o cálculo** (solver+verificação) + 3D.
- **Solver NOVO:** `tesoura.resolve_trelica` — método dos nós (equilíbrio nodal,
  sistema `2j×(b+3)`, `numpy.linalg.solve`); N>0 tração; banzo inf traciona, sup
  comprime. Equilíbrio global testado.
- **Verificação:** `verifica_tesoura` — combos gravidade `1,4w` + vento
  `1,4w_v+0,9(−w)`; barras por NBR 8800 (tração escoamento `A·fy/γa1`; compressão
  `χ·Q·A·fy/γa1` via `check_nbr8800.chi_compressao/fator_Q`). Sucção de vento = INPUT.
- **Spec/3D:** gate `tipo_portico=tesoura` + `estrutura.trelica`; `_desenha_tesoura`
  desenha as barras (cilindros) biapoiadas no topo dos pilares, **sem joelho/
  cumeeira** (treliça rotulada). Geometria da treliça **replicada numpy-free** no
  build (self-contained); `numpy` só no solver (lazy). Cobertura PE-04.
- **Memorial:** `gate6-tesoura.txt` + METODOS `3c`.
- **Regressão:** smoke 7/7 (caso `tesoura`); prismático/alma_var inalterados.
  Commit `820b0e0`. PENDENTE `REVISA-TESOURA-INTEG.md` Q1–Q5, INDICE 33.

## FECHADA — Pórtico de alma variável / tapered (fase 6.b) — 2026-07-10
**Escopo:** integrar o pórtico de mísula de alma variável (calc + 3D). Gerador
`alma_variavel.secao_tapered` já homologado; fase é integração análise+spec+3D.
- **Análise:** gate `estrutura.tipo_portico`=alma_variavel → rafter com seção por
  segmento (`galpao_portico._chain_var` + `secao_tapered`, funda no joelho → rasa
  na cumeeira; `NSEG=8`). `frame2d.add_element` já aceitava I/A por elemento. A
  distribuição de momento reflete a rigidez variável. `configurar(tapered=)` usa
  **sentinela** `_UNSET` → `tapered=None` RESETA (prismático byte-idêntico).
- **Spec:** `estrutura.tipo_portico` (default prismatico; inválido bloqueia) +
  `estrutura.tapered` {h_joelho,h_cumeeira,bf,tw,tf}; mappers to_rodar/to_build.
- **3D:** `build_galpao.tapered_rafter` = `_sweep_tapered` (loft `Part.makeLoft`
  entre o I do joelho e o da cumeeira; cai no prismático se h1==h2).
- **Memorial:** `gate6-alma-variavel.txt` (tabela seção/segmento + peso) +
  METODOS `3b`; a **seção do joelho governa** (verificação por segmento = FLAG).
- **Regressão:** smoke 6/6 (caso `alma_var`); prismáticos inalterados. Commit `21d9941`.
- **PENDENTE sênior:** `REVISA-ALMA-VARIAVEL-INTEG.md` Q1–Q4, INDICE 32.
- **Próxima:** 6.c tesoura (treliça — topologia nova).

## FECHADA — Wiring calha + sapata de divisa (fase 6.a) — 2026-07-10
**Escopo:** ligar 2 módulos homologados ÓRFÃOS (não alcançáveis pelo pipeline) ao
fluxo: dimensionamento de **calha** (hidráulico NBR 10844/Bellei) e **sapata de
divisa** (excêntrica + viga alavanca, Alonso). Cálculo já existia; fase é wiring.
- **Gates:** `cobertura.chuva_I_mm_h` (default 150, A CONFIRMAR regional — não
  bloqueia); `fundacao.divisa` (None|dict `{dist_divisa}` — dispara só quando setado).
- **rodar_galpao:** calha roda da geometria (comprimento × meia-água / cos slope, I)
  quando `params["calha"]` → `gate-calha.txt` + `res["calha"]`; divisa roda
  `dimensiona_divisa(P=maior compressão do envelope, dist_eixos=bay, dist_divisa)`
  → `gate7-divisa.txt` + `res["divisa"]`. Ambos entram no MEMORIAL-CONSOLIDADO.
- **Memorial:** `relatorio_calculo.METODOS` +`13. CALHAS` (NBR 10844/Bellei) +`11g.
  SAPATA DE DIVISA` (Alonso); estaca já tinha `11c`.
- **Regressão:** smoke 5/5 (calha no memorial); 9 testes fase6a; divisa só com gate.
  Commit `5fd4003`.
- **Órfãos restantes:** `neve` (não escolhido pelo usuário — fica documentado, não
  wired); `alma_variavel`/`tesoura` = Fase 6.b (tipo de pórtico, build 3D novo).

## FECHADA — Corte seccionado 2D (fase 5) — 2026-07-10
**Escopo:** corte SECCIONADO real (hachurado) nos detalhes de ligação. Fecha o
resíduo de polimento 2D de [[06-open-threads#T6]].
- **Blocker resolvido:** `DrawViewSection` **constrói headless no FreeCAD 1.1**
  (probe: box → seção com 4 arestas; nenhum `failed to create section CS`). O erro
  histórico era da versão antiga.
- **`techdraw_exec._secao_ligacao`:** DrawViewSection do crop compound, plano de
  corte pelo centro, `CutSurfaceDisplay="SvgHatch"` (material cortado). Descarta a
  seção se vazia (arestas=0 → não engana o guard, `mne-1`). Wire em
  `_detalhe_ligacao` (view extra `VLIG_SEC_*`, sem mexer na elevação/callouts).
- **Guard:** resultado expõe `detalhes_secoes` (nome→arestas); `smoke_executivo`
  exige ≥1 seção e nenhuma vazia. Cobertura ignora DrawViewSection (não-DrawViewPart).
- **Fora (menor):** símbolo AWS de solda = `DrawWeldSymbol` é GUI-only; segue
  callout de texto (dado já rastreável ao cálculo).
- **Regressão:** smoke 5/5; `tests/test_fase5_corte_seccionado.py` (build).

## FECHADA — Ponte rolante estendida (fase 4) — 2026-07-10
**Escopo:** fechar o backlog da ponte rolante. **Fadiga Anexo K já estava
implementada** (T3 wiki desatualizado). Três adições:
- **Rodas motoras:** `ponte_rolante.forcas_horizontais(..., n_rodas_motoras)` —
  frenagem longitudinal `H_long = frac_long·R_roda_max·n_motoras` (só rodas
  motrizes; default = `n_rodas_lado` ⇒ retrocompatível). Saturação se `> n_lado`.
- **NBR 8400-1:2019 (novo `nbr8400.py`, lido do PDF verbatim):** φ (Ψ) da Tab.12
  (`Ψ=Ψmín+β2·Vh`, HC1–HC4, cap Vh=1,5) + Nº de ciclos da Tab.9 (B0–B10, limite
  superior conservador). `analisa` usa a classe (HC/Vh → φ ; B → N do Anexo K)
  quando dada, senão input flagado. Fadiga Anexo K só **recebe** o N — inalterada.
- **Gate:** `projeto_spec.REQUERIDOS_PONTE` — `validar()` bloqueia ponte incompleta
  (dados do fabricante) quando `ponte != None`; `ponte=None` segue válido.
- **Regressão:** `smoke_executivo` 5/5 (caso ponte 14 pranchas inalterado);
  27 fast tests; selftests nbr8400/ponte/spec. Commit `<fase4>`.
- **PENDENTE sênior:** `REVISA-PONTE-8400.md` (Q1–Q4) + INDICE item 31.

## FECHADA — Fundação profunda no ProjetoSpec + 3D (fase 3) — 2026-07-10
**Escopo:** integrar a fundação PROFUNDA (estaca Aoki-Velloso + bloco de coroamento
+ viga de baldrame) — antes opt-in só via `params` — como gate de 1ª classe no
`ProjetoSpec` e como geometria no build 3D. Cálculo já existia (`rodar_galpao`
411/426); a fase é wiring de spec + geometria, sem fórmula normativa nova.
- **Spec:** `fundacao.tipo` (sapata|estaca) BLOQUEIA; bloco `estaca` (perfil SPT da
  sondagem — sem default, bloqueia) + `baldrame`; `validar()` condicional; mappers
  `to_rodar_params`/`to_build_kwargs` (estaca EXCLUSIVA da sapata — `mne-2`).
- **Cálculo→spec:** `rodar_galpao` expõe D/L/n/espaçamento/bloco/baldrame no
  envelope (N_pilar compressão, N_uplift tração, V_base amarração); `calcular`
  grava `estaca_adotada`/`bloco_adotado`/`baldrame_adotado`.
- **3D:** `build_galpao` desenha ESTACA (cilindros)/BLOCO (envelope do grupo + coroa
  150 mm)/BALDRAME (entre pórticos); concreto de fundação MONOLÍTICO isento de clash
  interno concreto×concreto (aço×concreto continua verificado); take-off de concreto;
  cobertura na planta PE-02.
- **Regressão:** `smoke_executivo` 5/5 (5º caso `estaca`); ref 20×10 sapata inalterada.
  `tests/test_fase3_fundacao_profunda.py`: 13 fast + 1 build. Commit `9ac3c4f`.
- **PENDENTE sênior:** `REVISAO-FUNDACAO-PROFUNDA-INTEG.md` (só integração/geometria,
  Q1–Q6; método já homologado em ESTACA/BALDRAME) + INDICE item 30.

## FECHADA — Revisão sênior módulo-a-módulo (r2) — 2026-07-07
**Escopo:** conferência matemática/normativa dos 12 módulos de cálculo por engenheiro sênior (parecer colado pelo usuário) + auditoria independente. Regra: verificar CADA finding contra o PDF da norma (não de memória) e contra o código-fonte real (não o snippet do doc). Fixar defeitos reais; rejeitar findings inválidos com citação exata.

**Resultado:** 12/12 homologados. Docs `REVISAO-*.md` sincronizadas com código verbatim + respostas; `REVISAO-INDICE.md` rastreia status.

**Fixes de código (4):** ver [[04-decisions]] D2–D5.
**Pareceres rejeitados (3):** ligações esmagamento, contravento "Anexo L", mão-francesa "bugs de snippet". Ver [[04-decisions#D6]].

**Entregáveis:** commits `d668daf` (base…fundação), `d0638b8` (redim). Branch `revisao/homologacao-12-modulos` → PR #1.

## FECHADA — Features pós-homologação (punção, recalque, ancoragem, cone, cortante, fadiga, junta, sismo) — 2026-07-07/08
7 features novas homologadas pelo sênior (ciclo parecer→resposta). Ver [[04-decisions]] D8–D22 e `REVISAO-INDICE.md` (tabela de features). Base 100% nos modos do concreto (§9-§13: ancoragem, cone ACI, cortante-tríade, edge breakout, interação T-V).

## FECHADA — Análise de lacunas do galpão COMPLETO — 2026-07-08
**Escopo:** fechar TODOS os gaps de um projeto de galpão completo, na ordem pequenos→médios→grande. Depois, TODOS os FLAGs residuais. Regra zero-erro mantida (todo valor verificado no PDF via texto OU render de imagem; nunca de memória; Décourt/Aoki/Teixeira/Tab.14 lidas por imagem quando o OCR falhou).

**Gaps (6):** pequenos — furos ligações (6.3.9/10/11+Tab.14), Cpe local borda/canto (6123 Tab.4/5), telha vão×carga (14762 → `telha_cobertura.py`); médios — sismo→envelope (15421 §5.4 combinação excepcional no pórtico/base/joelho), viga de baldrame/amarração (`viga_baldrame.py`); grande — fundação profunda (`estaca_profunda.py`).

**FLAGs (16, todos fechados):** ver [[04-decisions]] D23–D32. Destaques: 3 métodos de estaca (Aoki-Velloso, Décourt-Quaresma, Teixeira 1996 — cross-check), tração/uplift, grupo (Converse-Labarre), atrito negativo, recalque de grupo, bloco de coroamento (biela 22.3.2 + ancoragem 9.3.2 + punção pilar/estaca), sismo θ/P-Δ (9.6) + 100/30, block shear (6.5.6), T-stub/prying (EN 1993-1-8).

**Entregáveis:** commits `c8d10de`→`7009b61` (~20). Todos: `_selftest()` PASSED, doc REVISAO-*.md, não-regressivos (ref 20×10 inalterada). Novos módulos: `telha_cobertura`, `viga_baldrame`, `estaca_profunda`.

## FECHADA — Projeto executivo 2D (TechDraw) + memorial PDF + detalhes de ligação — 2026-07-09
**Escopo:** 2D completo e genérico para qualquer projeto. Substituiu scripts de vistas à mão por TechDraw headless (`freecad.exe`). Ver [[04-decisions]] D33–D36.
- **Pranchas gerais (9):** cobertura, fundações, elevações, pórtico, contraventamento, det. base, det. joelho, fechamento, quadros. A1 ISO5457, PDF+SVG+DXF+PNG + `executivo.FCStd`.
- **Detalhes de ligação (PE10–14):** cumeeira, gusset cob/parede, clipe girt, console (só ponte) — auto-gerados, eixo curado por tipo. Total dinâmico: 13 (sem ponte) / 14 (ponte).
- **Guard de cobertura:** toda peça do modelo desenhada (`PREFIXOS_SEM_DESENHO`=VAO); guard anti-silhueta `_n_edges`≥15.
- **Memorial PDF:** `relatorio_calculo.py`, método+cálculo, no `build_final.py`.
- **Regressão:** `smoke_executivo.py` — 4 geometrias headless (padrão, vão>comp, baixo-largo, ponte) calc+3D(freecadcmd)+pranchas(freecad.exe)+PDF, sem MCP. Pré-flight sem freecad: carimbo (anti-`__PENDENTE__`) + cobertura. **4/4 OK.**
- **Entregáveis:** commits e696b84→b0c2e89. Branch → **PR #4**. Scripts antigos (`vistas_fc`,`dxf_vistas`,`techdraw_vistas`) removidos.
- **Fora de escopo (adiado):** detalhe de ligação nível fabricação (section+hachura+símbolo solda) — hoje elevação+arranjo, sizing no memorial. [[06-open-threads#T6]].

## FECHADA — Detalhe de ligação nível fabricação (A+B) — 2026-07-09
**Escopo:** callouts de fabricação nos detalhes de ligação, todo número rastreável ao CÁLCULO (fonte única). Decisão A+B; C (enriquecer 3D) rejeitado. Ver [[04-decisions#D37]].
- **Cálculo novo (compõe primitivos homologados, sem fórmula nova):** `gusset_ligacao.verifica_gusset` (tração/compressão Whitmore 30° AISC, block shear, solda — reusa `ligacoes`+`check_nbr8800`); `console_ponte.verifica_console` (grupo de solda elástico, dimensiona perna, cortante da chapa). Ambos `_selftest` PASSED. Wiring: `rodar_galpao` gate7-gusset/console + `res[*_adotado]`; `rodar_projeto.calcular` copia p/ `spec['estrutura']`.
- **Callouts (B):** `techdraw_exec.config_de_spec` passa joelho/gusset/console ao cfg; `_callout_fab` desenha leader+texto (joelho/cumeeira "N×db, chapa t"; gusset/console "chapa t, solda perna"). Sem número inventado (guard `mne-1`).
- **Corte seccionado (A):** `DrawViewSection` **falha headless** (`failed to create section CS`, mesmo em box trivial) → **fallback elevação** (já boa). Dado de fabricação entregue via callout. Símbolo AWS de solda ausente headless → texto. [[06-open-threads#T6]].
- **Regressão:** `smoke_executivo.py` 4/4 — callouts (cfg tem joelho/gusset sempre; console só ponte) + cobertura + edges≥15 + memorial PDF. Ref 20×10 inalterada (`mne-3` limpo).
- **PENDENTE sênior:** REVISAO-INDICE itens 28 (gusset) + 29 (console). Módulos entram no memorial PDF automático (`relatorio_calculo` lê consolidado).

## FECHADA — Balde 2 (dívidas a/b/c/d) fases 6.9–6.12 + revisão itens 39–42 — 2026-07-13
Escopo: fechar as 4 dívidas técnicas residuais do parecer 6.b (não-bugs; economia/validação).
Módulos novos: `tensao_ponto.py` (§5.5.2.3 M-V), `cortante_tapered.py` (equilíbrio),
`dg25_ltb.py` (cross-check AISC DG25); +vento por zona (90°+0°) em `tesoura.py`/`vento_nbr6123.py`.
Testes: `test_fase69`..`test_fase612` (11+14+13+9 = 47), regressão fase-6 completa
com 2 suítes de build = **113 passed**. Revisão sênior item-a-item: **2 bugs reais
acolhidos** (braço `h_0` 6.10; vento 0° longitudinal 6.11 — refino removia carga real),
1 refutação com prova (Cpi). Base lida por imagem de PDF (Tabela 5 NBR 6123; DG25 pág
60–61). REVISAO-INDICE **itens 1–42 ✅**. Ver [[04-decisions#D46]], [[06-open-threads#T10]].
Commits `6e3551f`→`a18b524`. **Gate humano:** push branch + merge PR (bloqueado p/ assistente).

## FECHADA (impl.) — Balde 3 (dívida e + refino DG25) fases 6.13–6.14 — 2026-07-13
Escopo: fechar os 2 resíduos NÃO-bug restantes (crane já estava 100% homologado — itens
9/29/31 — backlog "crane no toolkit" era estale). **6.13 enrijecedor de painel:** módulo
novo `enrijecedor_painel.py` (NBR 8800 §5.4.3.1 verbatim pág 50–51: `kv=5+5/(a/h)²`,
V_Rd 3 domínios, requisitos §5.4.3.1.3 b/t·I_st·j); relaxa cap `h/tw≤260` do Anexo H em
`alma_esbelta._valida(sec,a)` quando `a/h≤3`; wire informativo/opt-in na zona de painel.
`test_fase613` (15). **6.14 DG25 full:** estende `dg25_ltb.py` (Cb tapered 5.4-1/2, Rpc
5.4-4/5, Rpg 5.4-6/7, F_L, Mn nominal 3 regiões 5.4-16/17/18; `cross_check_capacidade`
onde Cb NÃO cancela). Base verbatim DG25 pág 58–62. `test_fase614` (17). Achado honesto:
prismático capacidade 0,951 (curva inelástica White-Kim ≠ Anexo G ~5%), elástico ≡ 0,998.
Ambos INFORMATIVOS (dimensionamento segue NBR). REVISAO-INDICE **itens 43–44 ⏳ aguardam
parecer**. Não-regressão: `a=None`⇒kv=5 byte-idêntico; `cross_check_flt` intocado.

## FECHADA — Handoff / aguardando pareceres — 2026-07-08 (histórico; superado pelas fases S16–S42 abaixo)
- **NADA pendente de implementação do lado do assistente.** Todos os gaps + FLAGs corrigíveis fechados.
- ~~6 pareceres sênior pendentes~~ → **TODOS HOMOLOGADOS 2026-07-09** (calhas, divisa, telha, vento §8, sismo §6; demais já eram). REVISAO-INDICE zero pendente. [[06-open-threads#T7]]
- PR #1 mergeado (`4fde82b`, 2026-07-07) — o "ainda aberto" deste bloco era falso (task-9). [[06-open-threads#T1]]
- Continuação em outro chat: ver [[06-open-threads#HANDOFF]].

## FECHADA — Job periódico da suíte de build 3D (PR #49, Sessão 18) — 2026-07-22
Revisão técnica e auditoria do PR **#49** (`chore/ci-build-suite-agendada`).
- **Escopo:** Automação do runner periódico para a suíte de testes de build 3D (os 9 testes marcados `@pytest.mark.build` que constroem o modelo 3D no `freecadcmd` e verificam a interpenetração de peças via `checa_interferencia`).
- **Problema resolvido:** Como os testes de build 3D são mais lentos (~5 min), eles ficam deselecionados no regresso diário padrão (`-m "not build"`). Isso permitia que regressões de geometria 3D passassem em silêncio.
- **Componentes:**
  - `tools/run_build_suite.ps1`: Runner PowerShell headless que executa `pytest -m build`, gera logs em `tools/build-logs/build_stamp.log` e atualiza `LATEST.txt`. Não afeta instâncias abertas do FreeCAD GUI/bridge.
  - `tools/register_build_task.ps1`: Script PowerShell idempotente para registrar/remover a tarefa agendada do Windows `GalpaoFW-BuildSuite` (Weekly Domingo 03:00 por padrão, com suporte ao parâmetro `-Remover`).
  - `tools/README.md` e `.gitignore`: documentação de uso e exclusão dos arquivos de log.
- **Resultado:** **APROVADO COM LOUVOR (APPROVED FOR MERGE)**. Exercitado e validado ao vivo: reprovou corretamente antes do fix do PR #48 (exit 1) e passou 100% verde com o fix (9 passed, exit 0).

## FECHADA — Plano de montagem e escoramento (PR #47, Sessão 18) — 2026-07-22
Revisão técnica completa e auditoria do PR **#47** (`feat/plano-montagem-escoramento`).
- **Escopo:** Plano de montagem e escoramento (última etapa turnkey, fase de OBRA). Módulo puro `montagem.py` + Gate 8 + prancha nova **PE16_MONTAGEM**.
- **Normas consultadas no NotebookLM:** NBR 8800 item 1.10 (casos omissos $\rightarrow$ AISC 303), 4.2.6 (içamento / impactos), 4.4 / 4.3.2 (desenhos de montagem e sequência), 4.9.6.5 ($\gamma_{f3}=1,30$), 12.3.2.1 (contraventamento temporário), 12.3.2.2 (estabilidade parcial permanente + vento + montagem), 12.3.3.1.1 (prumo $\max(H/500, 5\text{ mm})$) e 4.12.6 (escoramento). Bellei 7.6.4.
- **Componentes:**
  - **Sequência de montagem (10 passos):** nivelamento de base $\rightarrow$ 1º pórtico $\rightarrow$ **estaiamento prévio** $\rightarrow$ interligação com terças e contravento $\rightarrow$ contraventamento definitivo $\rightarrow$ só então remoção de estais provisórios $\rightarrow$ prumo/esquadro $\rightarrow$ aperto/solda.
  - **Guindaste e içamento:** peça mais pesada $\times$ $\gamma_{imp}=1,10$ (NBR 8800 4.2.6) $\rightarrow$ momento de carga ($t\cdot m$). Rafter considerado pré-montado no solo (2 meias-águas), governando o içamento.
  - **Estai provisório:** $T = F / (n \cdot \cos\alpha)$, compressão adicional na coluna e ancoragem na fundação $N = T \cdot \sin\alpha$.
  - **Vento de montagem:** $\gamma_{f3}=1,30$ (NBR 8800 4.9.6.5).
  - **Prumo:** $\max(H/500, 5\text{ mm})$, teto $25\text{ mm}$ global (NBR 8800 12.3.3.1.1).
  - **Prancha PE16_MONTAGEM:** 4 tabelas estruturadas + notas NBR 8800.
- **Resultado:** **APROVADO COM LOUVOR (APPROVED FOR MERGE)**. 12 novos testes verdes em `test_montagem.py`. Suíte não-build com 705 passed.

## FECHADA — Revisão técnica dos PRs #45 e #46 (Sessão 17) — 2026-07-22
Revisão técnica completa e auditoria dos PRs empilhados **#45** (`feat/gaps-nivel-a-contra-seguranca`) e **#46** (`feat/fabricacao-shop-drawings`).
- **PR #45 (gaps Nível A/C + wizard + romaneio):**
  - **Fadiga da solda do console:** NBR 8800 Anexo K Tabela K.1 item 8.2 (cat. F, $C_f=150\times 10^{10}$, $\sigma_{TH}=55\text{ MPa}$). Equação K.4b $\Delta\sigma = (11\times 10^4 C_f/N)^{0,167}$. Verificação de variaço de tensão na garganta $\tau_{SR}$ sob $N$ ciclos NBR 8400.
  - **Atrito do vento longitudinal:** NBR 6123 6.4.2 $F'_{at}$ no telhado + 2 paredes longitudinais com $L_{ef}$ descontando faixa descolada. Somado ao arrasto $F_a$ para dimensionamento do contraventamento longitudinal.
  - **Pattern loading / Carga em xadrez:** NBR 8681 em pórticos multi-vão ($N_{VAOS}\ge 2$). Casos $Q_a/Q_b$ e combinações $C2_{xadrez}$ amplificam momento de desequilíbrio na coluna interna.
  - **Gate de empocamento:** NBR 8800 9.3 declividade $\ge 3\%$ dispensa ($OK=True$), $<3\%$ reprova ($OK=False$, exige análise adicional).
  - **Torção e efeitos combinados:** NBR 8800 5.5.2. Tubo retangular (3 faixas $T_{rd}$ + interação 5.5.2.2). Perfil aberto I/U por tensões de Saint-Venant $\tau_t$ (gate de empenamento/flexo-torção se $\tau_t>0,20\tau_{Rd}$).
  - **Wizard tipo de ligação:** pergunta soldada/parafusada (default soldada), validação estrita no spec, notas 5/6 da PE09 atualizadas.
  - **Romaneio preliminar:** agrupa peças primárias ($C1, V1..Vn$) com marca, quantidade e peso por perfil adotado no clculo.
- **PR #46 (fabricação 3D/2D + diafragma NBR 15421):**
  - **Piece marks 3D (`marcas_peca.py`):** grava propriedade `Marca` nos objetos 3D no FreeCAD por categoria/perfil; `por_marca` extrai comprimento de CORTE unitário.
  - **Quadro unificado de materiais / Lista de corte:** tabela `Q09M` na PE09 com colunas MARCA | ELEMENTO | PERFIL | QTD | CORTE(m) | MASSA(kg). Fallback sem sobreposição.
  - **Quadro de tolerâncias (`tolerancias_fabricacao.py`):** tabela `Q09T` na PE09 com tolerâncias de fabricação/montagem (NBR 8800 12.2/12.3 + Bellei Ap. C) e folga do furo-padrão.
  - **Shop drawings por peça (PE14 CROQUIS DE FABRICAÇÃO):** prancha `PE14_CROQUIS` com 3 vistas projetadas A1 por peça principal ($C1, V1, MI1$), rótulo com corte e nota de solda AWS.
  - **Efeito de diafragma da cobertura (`diafragma.py`):** classificação NBR 15421 8.3.2 (deflexão no plano $>2\times\text{drift}_{médio}\rightarrow$ FLEXÍVEL), validando a distribuição tributária; suporte a diafragma RÍGIDO (rigidez + torção).
- **Resultado:** **APROVADOS COM LOUVOR (APPROVED FOR MERGE)**. Suíte completa de 702 testes verdes. Consolidados aqui e em [[04-decisions#D68]] / [[04-decisions#D69]].

## FECHADA — Revisão técnica PR #44 (Sessão 16) — 2026-07-21
Parecer externo do PR #44 (`fix/gate-mao-francesa-e-cache-de-modulo`), **reconciliado** com o
estado final (7 commits, 643 testes; o parecer original dizia 5/622, escrito antes de `c5c73d9`/
`a406012`; diffstat 18 arq./+1544/−129 confere). Amalgamado aqui; markdown `PR_44_Review` removido.
- **Resultado: APROVADO SEM RESSALVAS.** Fórmulas de cantoneira, esbeltez equivalente (E.1.4.2),
  capacidade de compressão e rigidez nodal validadas contra NBR 8800 e por método independente
  (Green a 1e-9). Sem regressões.
- Verificado por mim contra o código: E.1.4 "mais conservador", Grupo 3 da Tab. F.1, mísula −2,6 t,
  cache de módulo, API `atende_global` — todos conferem. Detalhe em [[04-decisions#D67]].
- **Pendente (do usuário, não código):** merge do #44; confirmar a bitola da cantoneira
  (`_a_confirmar`). Ver [[06-open-threads#T17]].

## FECHADA — Revisão técnica T15 (correções+features+validação) — 2026-07-17
Consolidada em [[04-decisions#D52]]–[[04-decisions#D57]] e [[00-index]]. Markdown de trabalho
`07-review-results` removido (mesmo precedente de 2026-07-15). Núcleo: fix de sinal do frame2d
(UDL), state-leak no `reset()`, validação CBCA <1%.

## Status (histórico, 2026-07-08) — 18 módulos matemáticos + features (todos com selftest verde; defasado — ver fases S16–S42 abaixo)
12 r2 (Pórtico·Perfil·Vento·Terças·Secundários·Base·Ligações·Ponte·Mão-francesa·Contravento·Fundação·Redim) + Junta + Sismo + **Telha** + **Baldrame** + **Estaca profunda** + **Contenção lateral** (mão-francesa, NBR 8800 4.11.3.4).

## FECHADA — S19: Interoperabilidade BIM/IFC4 físico e analítico (PRs #55–#61) — 2026-07-22/23
Revisão e integração completas (fonte: 00-index:66-75 + git/task-3). **PRs #55–#61 revisados,
aprovados e mergeados em `main`** (merges 2026-07-22T21:58Z → 2026-07-23T00:15Z; base do commit
mais antigo `40844a3` authored 2026-07-22T18:19:29Z). Tema: **interoperabilidade BIM / IFC4
físico e analítico direto do cálculo, sem dependência do FreeCAD GUI**.
- **#55 (`feat/gaps-e-wiki-para-main`, merge `83570c9`):** cherry-pick dos Gaps A3/C5 e da wiki da
  S18 para a `main` (mrd_flt_chapa + patamar Blondel — task-9 D74).
- **#56 (`feat/ifc-export-bim`, `e4a7918`):** exportador IFC4 (BIM) no `build_galpao.export()`
  consumindo **`ifc_map.py`** (mapeamento semântico de marcas → categorias IfcColumn/Beam/Member/
  Plate/Footing/Pile/Covering/MechanicalFastener). Gerou IFC4 de 1,67 MB com 789 elementos.
- **#57 + #59 (`feat/bridge-headless` → main):** `montar_modelo` com **auto-fallback headless**
  (bridge → `freecadcmd`; `rodar_projeto.py:210-217`). #57 mergeado em branch intermediária
  `feat/ifc-export-bim`; conteúdo chega à main via #59 (`5863532`).
- **#58 (`feat/ifc-emissor-puro`, `e2f235c`):** modelo neutro de dados **`modelo_neutro.py`** +
  emissor IFC4 puro-Python **`ifc_emit.py`** (via `ifcopenshell`), sem invocar o FreeCAD.
- **#60 (`feat/ifc-secundarios`, `495b594`):** secundários lineares no IFC puro — funções reais
  `tercas()`, `girts()`, `tirantes_parede()`, `contrav_cobertura()`, `frame_completo()` em
  `modelo_neutro.py` (correção task-9: o nome `secundarios_lineares` NÃO existe no código).
- **#61 (`feat/modelo-analitico`, `ea48acf`):** modelo analítico via **função**
  `galpao_portico.modelo_analitico()` + `ifc_emit.emitir_ifc_analitico`/`emitir_ifc_analitico_do_spec`
  (IfcStructuralAnalysisModel/IfcStructuralPointConnection; `ifc_emit.py:535-548`) — **NÃO é módulo
  `modelo_analitico.py`** (correção task-9; módulo inexistente no disco). Gera `galpao.ifc`
  (físico) + `galpao_analitico.ifc` (estrutural) em `EXPORT_DIR/ifc/` (`rodar_projeto.py:533-534`).
- **Resultado:** **831 testes verdes** (00-index:67 — claim da wiki; contagem de suíte não
  re-executada, task-9). Ver [[04-decisions#D74]]–[[04-decisions#D79]] (reconstruídas em 04),
  [[06-open-threads#T22]].

## FECHADA — S19-ext: IFC físico puro — expansão e fechamento (PRs #62–#80) — 2026-07-23
**Cluster próprio** (classificação task-3 §3 cluster 2): 19 PRs, merges 2026-07-23T00:53Z →
17:30Z, todos tocando `modelo_neutro.py`/`ifc_emit.py` (21 commits em cada, 22–23/07). Não
fundido com S19 (#55–61) porque a wiki já fechou a S19 no review PR_55_61_Review (00-index:66-75);
não fundido com S20 (#81+, concreto) porque é 100% IFC/estrutura metálica, sem concreto.
- **Expansão IFC puro (#62–#78):** esforços 2ª ordem por barra no analítico (#62); fundações
  sapata/bloco (#63); telha IfcCovering (#64); tapamento de parede (#65); pórtico alma variável
  (tapered) (#66) + seu modelo analítico (#67); fix escala 1000× + placas de base (#68); nervuras
  (#69); clipes de terça/girt IfcPlate (#70); mãos-francesas IfcMember (#71); escoras/cumeeiras +
  oitão (#72); tirantes segmentados (#73); conectores da base IfcMechanicalFastener (#74);
  drenagem calhas/condutores/bocais (#75); gussets IfcPlate triangular (#76); mísula do joelho
  (#77); IfcPile + ponte rolante (#78).
- **Auditoria de fechamento do aço (#79–#80):** 3 gaps (ELS girt + corrosão + camber, #79);
  flecha do baldrame sob alvenaria (NBR 6118 Tab. 13.3) + dreno (#80).
- **Resultado:** sem contagem de suíte na evidência (não verificado).

## FECHADA — S20: Vertical de CONCRETO (PRs #81–#101) — 2026-07-23/27
Galpão pré-moldado engastado (merges 2026-07-23T22:52Z → 2026-07-27T20:00Z; 21 PRs).
Orquestrador stateless **`galpao_concreto.py`** (#83) + módulos: `pilar_concreto` (flexão
composta reta + oblíqua/biaxial, 17.2.5, α=1,2 — #81/#87), `viga_concreto` (#82), BIM IFC4 do
concreto + material (#84), executivo quadro+memorial (#85), desenho formas/armação SVG (#86),
`viga_protendida` (pré-tração vãos >12 m, #88), `premoldado_nbr9062` (ligação pré-moldada, #89),
`fogo_nbr15200` (situação de incêndio, #90), fissuração ELS-W 17.3.3 (#91), `estabilidade_global_
nbr6118` (α, γz — #92), `perdas_protensao_nbr6118` (9.6.3 — #93), estaca (#94), cortante
protendida 17.4.2 (#95), torção 17.5 (#96), planta de formas SVG (#97), quantitativo de armadura
IFC Pset (#98), varredura de interpenetração (#99), **build 3D SÓLIDO** (`build_concreto`, #100),
**pranchas A1 TechDraw** (`techdraw_concreto`/`executivo_concreto`, P1–P20, #101).
- **Resultado:** 153 testes no grupo concreto (17 arquivos; protensão estrita 31 — task-8; 00-index:68-70), fixtures Bastos/Araújo/Carvalho.

## FECHADA — S21–S26: Vertical ELÉTRICO (PRs #102–#106) — 2026-08-01/02
Merges 2026-08-01T23:56Z → 2026-08-02T02:02Z (5 PRs). Orquestrador **`galpao_eletrico.py`**
(#102) + 9 módulos: `cargas_eletricas`/`condutores_nbr5410`/`curto_circuito`/`protecao_nbr5410`/
`fator_potencia` (P21 núcleo BT), `aterramento_nbr15749` + `spda_nbr5419` (P21 aterramento/SPDA),
`subestacao_nbr14039` (P22 MT, NBR 14039), BIM/IFC elétrico (P23, #104), build 3D + executivo A1
(P24–P25, #105), `luminotecnica_nbr8995` (P26, NBR 8995 — #106). Notebook próprio c5934f22.
- **Resultado:** suíte atual: 1353 selecionados / 1340 passed / 1 failed (F1 fitz) / 15 skipped (2026-08-11, task-18).

## FECHADA — S27–S30: Vertical INCÊNDIO/AVCB + climatização standalone (PRs #107–#110) — 2026-08-02
Merges 2026-08-02T02:35Z → 03:04Z (4 PRs). Orquestrador **`galpao_seguranca_incendio.py`** +
módulos: `iluminacao_emergencia_nbr10898` (emergência, #107), `sinalizacao_nbr16820` (#107),
`deteccao_alarme_nbr17240` (alarme, #107), `proteccao_sprinklers_nbr10897` (sprinklers NBR 10897,
#108), `iluminacao_externa_nbr5101` (iluminação externa NBR 5101, #109), `climatizacao_nbr16401`
(climatização NBR 16401, #110 — standalone nesta fase).
- **Resultado:** sem contagem de suíte na evidência (não verificado).

## FECHADA — S31: Loop elétrico (PR #111) — 2026-08-02
Merge 2026-08-02T03:22Z. P31 fecha o loop: iluminação externa + climatização passam a entrar como
cargas do QGF.
- **Resultado:** sem contagem de suíte na evidência (não verificado).

## FECHADA — S32: TURNKEY orquestrador-mestre (PR #112) — 2026-08-02
Merge 2026-08-02T14:27Z. **`galpao_turnkey.rodar(spec)`** despacha TODOS os verticais, consolida
gates + ATENDE global; falha isolada por disciplina; **modelo federado** (IFC + 3D + clash AABB
com triagem esperado×revisar) (00-index:33-35).
- **Resultado:** sem contagem de suíte na evidência (não verificado).

## FECHADA — P33–P39: Robustez, executivo incêndio, caderno único, hidrantes, revisão total, dispatch (PRs #113–#119) — 2026-08-02
Merges 2026-08-02T14:37Z → 16:43Z (7 PRs).
- **P33 (#113):** harness de robustez dos verticais novos.
- **P34 (#114):** executivo A1 incêndio — rotas de fuga/AVCB (`desenho_incendio`).
- **P35 (#115):** acionadores para galpão alongado (NBR 17240).
- **P36 — CADERNO ÚNICO (#116):** `caderno_turnkey` — capa+índice+pranchas A1 de todas as
  disciplinas num PDF (via fitz), montado ao vivo no freecad.exe (00-index:36-37).
- **P37 (#117):** hidrantes e mangotinhos (NBR 13714).
- **P38 — REVISÃO TOTAL (#118):** drawing-vs-data na planta de incêndio + guards de entrada
  degenerada (geometria/tensão/área/Fu=0 → ValueError) em 4 orquestradores (00-index:38-39).
- **P39 (#119):** dispatch do aço no caderno turnkey.

## FECHADA — Fixes contra-segurança + BIM incêndio (PRs #120–#123) — 2026-08-02
Merges 2026-08-02T19:55Z → 20:38Z (4 PRs). Fix hidrantes de cobertura (NBR 13714 5.3.2 por malha +
2 jatos, #120); fix guards elétrico nos 7 módulos (#121); BIM/IFC dos equipamentos de incêndio
(#122); fix planta de iluminação de emergência count-driven (#123).

## FECHADA — Turnkey federado BIM/IFC + clash + 3D (PRs #124–#134) — 2026-08-02/03
Merges 2026-08-02T20:46Z → 2026-08-03T02:42Z (11 PRs). Modelo BIM/IFC federado consolidado
(#124); aço dentro do federado (#125); clash detection federado (#126); build 3D sólido federado
(`build_federado`) + fix AABB orientado (#127); apêndice de coordenação no caderno (#128);
triagem esperado×revisar (#129); fix escala das caixas do aço federado (#130); vertical
climatização federada (#131); render-and-look PNG federado (#132); **vertical hidráulica
federada — 6ª disciplina** (`galpao_hidraulica`, #133); prancha de coordenação no caderno
(`desenho_coordenacao`/`techdraw_coordenacao`, #134).

## FECHADA — HVAC velocidade do duto (PR #135) — 2026-08-03
Merge 2026-08-03T02:51Z. Velocidade do duto ancorada na NBR 16401-1 Tab.1 (era flagada).

## FECHADA — S39: HIDRÁULICA + COORDENAÇÃO (PRs #136–#147) — 2026-08-03
Merges 2026-08-03T06:35Z → 15:33Z (12 PRs). **`galpao_hidraulica` + `hidraulica_predial`**
dimensionam NBR 5626:2020/8160/10844 (#136; sem método dos pesos → v≤3 m/s, 00-index:40-43);
prancha A1 de coordenação do federado (#137); reservatório de incêndio como torre elevada no
render (#138); revisão NBR (2 gaps: DN75 vertical, declividade mínima — #139); método dos pesos
NBR 5626:1998 (#140); verificação de pressão Fair-Whipple-Hsiao (#141); ventilação do esgoto +
calhas pluviais (#142); executivo A1 hidro/clima (`techdraw_hidraulica`, #143); janela lateral
wizard (L,H)→faixa (#144); revisão S39 (pressão por ponto, saturação pluvial, área do dreno,
#145); condutor curto exige paralelo (não satura, #146); água quente (NBR 5626:2020 SPAFAQ,
#147).

## FECHADA — S40: HARDENING — saturação silenciosa (PR #148) — 2026-08-03
Merge 2026-08-03T16:17Z. Caça à **saturação silenciosa** (tabela satura no maior valor + gate que
não reprova + OK=True): fechou terça-ELS/flecha (aço) e placa de sinalização (incêndio); concreto
verificado limpo. **1ª auditoria NLM formal de concreto/aço** (As_max pilar, flecha terça
L/180-L/120, drift H/300, flexo-compressão 5.5.1.2 — todos batem) (00-index:44-49).

## FECHADA — S40: Docs — consolidação do arco S20–S40 (PR #149) — 2026-08-03
Merge 2026-08-03T16:33Z. Docs da wiki consolidando o arco S20–S40.

## FECHADA — S40: Janela dupla-conversão — fecha T40 (PR #150) — 2026-08-03
Merge 2026-08-03T18:31Z (00-index:50-52). `janelas_laterais` unificada na convenção **FAIXA**
(canônica); conversão (L,H)→faixa só no wizard via `_janela_band`; `aberturas_para_build` virou
pass-through (mata a reconversão que #144 abrira). **Suíte 100% verde** (00-index:50-52).
[[06-open-threads#T40]] ✅.

## FECHADA — S40: Docs — T40 resolvido (PR #151) — 2026-08-03
Merge 2026-08-03T18:32Z. Docs da wiki marcando o T40 RESOLVIDO.

## FECHADA — S40: Runner de regressão confiável (PR #152) — 2026-08-03
Merge 2026-08-03T18:55Z. **`tools/run_tests.py`** — PRIMÁRIO: pytest-xdist `-n auto` (1353
selecionados em ~5 min, 2026-08-11); FALLBACK sem xdist: 2 lanes (rápidos primeiro, pesados
isolados — 23 arquivos: 22 `test_fase*` + `test_crashes_wiki07`); `requirements-dev.txt` +
`tools/README.md` (00-index:98-104).

## FECHADA — S40: Docs — situação atual (PR #153) — 2026-08-04
Merge 2026-08-04T13:14Z (último PR antes do hiato). Wiki reflete a situação S40 (T40 fechado +
runner #152 + regressão verde).

## FECHADA — S41: Fixes de desenho/pranchas + planta elétrica (PRs #154–#161) — 2026-08-09
**Trabalho pós-2026-08-04** (hiato 04→09/08; merges 2026-08-09T04:12Z → 06:00Z, 8 PRs — task-3
§4; a wiki emudeceu nesse período). Escape &<> no SVG (unifilar XML malformado, #154); fix carimbo
elétrico vazava ESTRUTURAL (#155); docs proveniência `bacia_caixa=0,96` (#156); centraliza quadros
PE-EL-03/PE-HID-02 (#157); escape &<> em incêndio/clima/coord (#158); centraliza quadros verticais
(#159); planta de iluminação e tomadas (#160); fecha 4 gaps da planta elétrica (QDC,
bitola/eletroduto, leiaute, 3D/BIM — #161).

## FECHADA — S42: Dez módulos de engenharia (PRs #162–#171) — 2026-08-09
**Pós-2026-08-04** (merges 2026-08-09T15:27Z → 16:10Z, 10 PRs — task-3 §4). Um módulo novo por PR
(todos no main, task-3 §6):
- `piso_industrial` (placa sobre solo, #162); `geotecnia_spt` (SPT→tensão admissível + escolha de
  fundação, #163); `orcamento` (5D, curva ABC + BDI, #164); `compatibilizacao` (BCF-like, #165);
  `fotovoltaico` (GD on-grid, #166); `esgoto_reuso` (fossa NBR 7229 + reuso cisterna Rippl, #167);
  `terraplenagem` (corte/aterro + greide, #168); `cronograma` (4D, CPM + curva S, #169);
  `caderno_encargos` (#170); `pacote_legal` (ART, PPCI/LOD/O&M, #171).
- **Resultado:** sem contagem de suíte na evidência (não verificado).

---

## Arco G43→G77 — reconstruído do git no G88 (2026-09-09)

A wiki emudeceu em S42 (2026-08-09) enquanto o trabalho seguiu na branch
`feat/tipologias-e-verticais-de-projeto`. O arco abaixo foi reconstruído no G88 a partir de
fonte independente — `git log --no-walk` dos commits do arco + os verbetes de
`wiki/04-decisions.md` (D80–D105). Nada aqui é palpite: cada lote cita hash, data e decisão.
(Nota: na medição do backlog as decisões paravam em D105; D106/G78 e D107/G86 foram
registrados depois, por outras sessões.)

## FECHADA — G42–G46: escada da casa desce, detector fala 5 disciplinas, estribo dimensionado — 2026-09-04
Commit `5f95622`. Escada da casa (`test_escada_casa_g42`), `varredura_descoberta` estendida ao
G43, validação de sistema G15, pilar de concreto. Ver [[04-decisions]] (arco D80–D84).

## FECHADA — G47–G48: estribo com ramos, lente ampliada aos cálculos, s de pilar pela 18.4.3 — 2026-09-04
Commit `b52df76`. Teto do estribo sobe com ramos 2/4/6 (não com bitola, φ≤10 congelado);
`varredura_descoberta` ampliada aos cálculos (G48); `s_estribo_max` mínimo entre 18.3 e 18.4.3
com `s_limite_governante` dizendo qual mandou. Ver [[04-decisions#D83]], [[04-decisions#D84]].

## FECHADA — G49–G50: C55–C90 deixa de ser calculado com as fórmulas de C50 — 2026-09-05
Commits `a39e41a` + docs `e11f6c2`. `fctm = 2,12·ln(1+0,11·fck)` acima de C50 (8.2.5) + NOTA de
ductilidade 18.4.3 como fail-closed (G49); resto da família (17.2.2/14.6.4.3, `Eci` 8.2.8,
8.2.10.1, gancho 135 no artefato) + a regra da **asserção tautológica** (G50).
Ver [[04-decisions#D85]], [[04-decisions#D86]].

## FECHADA — G51: a faixa de validade declarada vira guarda, e a varredura vira portão — 2026-09-05
Commit `a70af35`. `varredura_faixa_validade.py` (106 declarações; baseline `DESGUARDADAS_TRIADAS`
nos dois sentidos, vermelho por injeção em `tmp_path`); fix θ 30..45° da torção como recusa
fail-closed; órfãs `LAMBDA_BLOCO`/`ALPHA_C`/`XD_LIM` com sufixo `_C50` + compat que avisa.
Ver [[04-decisions#D87]].

## FECHADA — G52: a obra inteira rodada, aberta e medida; a laje deixa de pesar duas vezes — 2026-09-06
Commit `027e5a3`. Fronteira laje→viga (permanente além do peso próprio; `test_fronteira_carga_laje_g52`
como relação); índice×pasta no `pacote-legal.md`; seção **A CONFIRMAR** no `relatorio.txt`
(nomear, nunca estimar). Ver [[04-decisions#D88]].

## FECHADA — G53–G54: as instalações ganham geometria e o prédio ganha compatibilização — 2026-09-06
Commit `ede4484`. `bim_instalacoes_edificio.py` (prumadas no mesmo frame do `bim_edificio`,
traçado convencional declarado); hook `_write_coordination` com três portas de `not_available`;
390 membros, 126 conflitos medidos na obra. Ver [[04-decisions#D89]].

## FECHADA — G55–G60: o furo previsto fecha por decisão, o prédio emite as 13 folhas e a parede vira elemento — 2026-09-07
Commit `37bfae9`. G55 terceira categoria `furo_previsto` (NBR 6118 13.2.5/21.3, fecha por
`resolution_requests`); G56 prédio 13/13 pranchas (reuso por parâmetro, laço índice⇄disco);
G57 SPDA/emergência com `not_available` honesto atravessando o pacote; G58 casa com 9
entregáveis (`gestao_casa.py` próprio); G59 baldrame/recalque com motivo escrito + ρmín C55–C90
da p. 130 + rename `tracado_convencional_das_prumadas`; G60 vertical de alvenaria estrutural
(NBR 16868-1 lida página a página, errata aplicada).
Ver [[04-decisions#D90]]–[[04-decisions#D95]].

## FECHADA — G61–G65: a alvenaria vira caminho de carga, e a laje passa a repartir pela charneira — 2026-09-07
Commits `1ff22f2` + `0aa3a5f`. `fundacao_sapata_corrida.py`; tipologia portante com fronteira
(térrea); G62 desenho/BIM da alvenaria; G63 Qh por rigidez 9.6.2; G64 lente do G51 como portão
de cobertura; G65 7229→17076/13792→16981 conferidas na página vigente + varredura NBR×catalogo
com `skipif` (não quebra checkout sem `fontes/`). Revisão: quinhão da laje pela charneira
(não por comprimento), recusa de apoio em linha sem parede, corte dos cruzamentos, sapata
corrida B×1,00 m, Parte B consultada, verga `not_available`. Ver [[04-decisions#D96]].

## FECHADA — G66–G70: o telhado de madeira, e a carga que fechava contra si mesma — 2026-09-08
Commit `0114d27`. `madeira_nbr7190.py` + `telhado_casa_madeira.py` (tesoura Howe, Tab. 3/4/5,
γw, Hankinson, 12 modos 7.3 — célula a célula com o PDF); G67 cisalhamento 11.4 da alvenaria +
sobrado com vento por nível + G68 recusa do sobrado sem vento (fecha o gap da viga contínua
do G13); G70 verga dimensionada (adotado × necessário). Revisão: tributário do beiral levava
painel inteiro (25 % de carga a mais; `confere_fechamento_area` de origem independente),
a2 de prego (3+6·|sen α|)·d, 6.2.4 com as duas condições, L/200→faixa da Tab. 21, apoio da
terça em tramo inteiro, elevação com cabeçalho no fim (largura real 1126), nota "a" da Tab. 9
como declaração obrigatória. Ver [[04-decisions#D97]].

## FECHADA — G71–G73: o telhado voa, entra no BIM e o nó sai em madeira-madeira — 2026-09-08
Commit `c106bd9`. G71 vento na tesoura (Tab. 5 por bloco h/b, 0,9 favorável como extremo estrito
declarado, ancoragem contra arrancamento); G72 `bim_telhado_madeira.py` (IfcMember/IfcBeam,
`ref_hint` contra a viga deitada, portão volume×rótulo); G73 ligação madeira-madeira 7.2
(beta, 6+4 modos, Tab. 16 como portão, `n_cortes` numérico); revisão D101 (conjunto congelado
que vira derivado da spec, `except Exception`→`ImportError`, censo a 20 guardas; **aberto,
nomeado: telhado reprovado some do federado** — virou G86). Ver [[04-decisions#D98]]–[[04-decisions#D101]].

## FECHADA — G74–G76: o default deixa de decidir, a 6.6 vira geometria e a folha passa a ser olhada — 2026-09-09
Commit `33e3af8` (lote **G74–G76**, verificado em 44 focais + 249 vizinhos = 293 verdes).
G75 `varredura_defaults_veredito.py` (declara-ou-recusa em 7 módulos, recusas `... nao declarado`
grep-áveis, baseline nos dois sentidos em `tmp_path`); G74 alternativo da 6.5.6 + 6.6 do
conjunto (`contraventamento_banzo_inf_m` numérico, chave bool antiga recusa com endereço,
gate 6.6 informativo, duas ausências nomeadas com artigo); G76 `confere_folha_svg` genérica
+ varredura anti-`replace` de cabeçalho + renderizar-e-olhar (Edge headless).
Ver [[04-decisions#D102]]–[[04-decisions#D104]].

## FECHADA — G77: o censo das folhas vira portão, e a folha de armação deixa de ter altura fixa — 2026-09-09
Commit `fb53107`. `censo_de_folhas` por AST (32 folhas, `ISENTAS` vazio, portão nos dois
sentidos, vermelho por injeção em diretório temporário); defeito achado: `prancha_armacao_svg`
com altura fixa jogava a cota 3,5 px fora da folha (guarda antiga só olhava X, por regex);
legenda da planta de incêndio vira count-driven (um teste cristalizava o defeito);
folha válida-e-vazia reprova. **Aberto, nomeado:** planta de água do pavimento-tipo magra
(um ramal). Ver [[04-decisions#D105]].

## FECHADA — G78–G88: o lote das onze folhas, e os portões que ficaram vermelhos — 2026-09-09
Os onze goals de `BACKLOG-GOALS.md` foram executados **e ficaram sem commit** na árvore —
a armadilha do G74 outra vez. Fechados aqui em bloco, com auditoria antes do commit.

**O que entrou (censo de folhas 32 → 37):**
- **G78** planta baixa da casa (PE-AR-02), layout canônico em `turnkey.arquitetura.layout`
  com o elétrico virando espelho conferido; PE-AR-01/03 `not_available` com o dado que
  falta **nomeado** (lote, níveis) em vez de recuo e soleira arbitrados.
- **G79** duas folhas de terraplenagem; **G80** locação/formas da fundação do prédio
  (PE-CO-04); **G81** escada de emergência (PE-IN-03). As três com entrada no índice —
  sem ela a folha evapora no `continue` (o D89, que já custou duas vezes).
- **G82** contrato da hidráulica escrito: no galpão 1 arquivo **cobre** os 3 códigos, e isso
  deixa de ser silêncio; **G86** o telhado reprovado passa a entrar no federado, carimbado.
- **G83** lente das guardas de um eixo só; **G84** declara-ou-recusa nos 4 módulos com mais
  `A CONFIRMAR` (a lente do G75 passa de 101 para 152 sítios); **G85** veredito por módulo
  nos nove que nenhum teste nomeava; **G87** orçamento com três estados.
- **G88** a própria dívida de documentação (arco G43→G77 reconstruído do git).

**A auditoria do lote (G89), e o que ela achou.** Suíte completa: **3563 passed, 6 failed**.
Um dos seis não era do lote — `test_g19_quarto_caso_1_comando_output` deu timeout por
contenção e **passa isolado em 285 s** (reproduzido antes de ser culpado, receita do D81).
Dos cinco reais, o mais instrutivo não veio do lote: **o portão do G77 estava vermelho desde
o próprio commit `fb53107`** e ninguém viu, porque `test_09_cobertura` tem dois asserts em
sequência e o primeiro mascarava o segundo. Também se confirmou que
**`desenho_terraplenagem` era ilha**: o G79 fez a folha certa e ninguém a emitia — "a folha
está certa" e "a folha sai" são dois aceites, e o segundo não se deduz do primeiro.
Ver [[04-decisions#D106]]–[[04-decisions#D117]].

**Aberto, nomeado, medido — a fila do próximo arco:** a casa promete **16** pranchas no
índice e mapeia **3** (só PE-AR); o galpão não tem laço índice↔disco nenhum (o prédio fecha
15/15); e o caderno executivo em PDF só existe no galpão.


## FECHADA — G91–G97: o laço índice↔disco vira uma lente só, e o caderno chega às três tipologias — 2026-09-10
O arco anterior (G78–G88) fez **folhas certas**; este trata do segundo aceite — *a folha sai* —
e do que o cliente recebe na mão.

**O que entrou.**
- **G91** `varredura_indice_disco.py`: uma máquina para as três tipologias, no lugar de três
  implementações do mesmo contrato. Três gaps (`faltando`, `sobrando`, `sem_mapa`), entrada
  malformada que **levanta** em vez de devolver `OK`, e o `except` do prédio virado função
  reusável ([[04-decisions#D119]]).
- **G92** a casa passa a confrontar o pacote inteiro: `_PRANCHA_ARQUIVO_CASA` de **3 → 17**
  entradas, cada código sem folha saindo com o **dado que falta nomeado**
  ([[04-decisions#D120]]).
- **G93** o galpão troca a contagem (número contra número) pelo código nomeado, com mapa de
  19 entradas medido página TechDraw a página TechDraw ([[04-decisions#D121]]).
- **G94** caderno executivo em PDF para casa e prédio (SVG → PNG → página, reusando
  `_add_pagina_imagem` e `_add_paginas_texto`), com o portão
  `n_pranchas + n_declaradas == len(indice)` ([[04-decisions#D122]]).
- **G95** terraplenagem numa rodada real (`projects/galpao-tp-g95`), com a premissa marcada
  como premissa — `not_real_engineering_input` exigido pelo próprio portão
  ([[04-decisions#D123]]).
- **G96** decisão escrita, sem código: o aço executivo precisa do FreeCAD em **11** folhas
  projetadas; PE09 e PE16 são 2D puro e migram só quando houver emissor, rota de export sem
  `freecad.exe` e fonte declarada para os 3 números que hoje saem do BoundBox
  ([[04-decisions#D118]]).
- **G97** a lente do "portão que esconde portão": asserts independentes em sequência viram
  uma mensagem só ([[04-decisions#D124]]).

**Aberto, nomeado, medido — a fila do próximo arco.** PE-EL-01/02/04 da casa saem declarados
como "sem emissor ligado" e os emissores **existem e estão provados** (a classe do G79/G89, de
novo); `mezanino` é executado pelo turnkey do galpão e não existe no índice, evaporando no
`continue` (D89 vivo, do lado da promessa); e o portão das três tipologias do G91 mede
índice × **mapa** — o lado do disco vive nos portões por tipologia, e essa distinção precisa
de portão próprio.

## FECHADA — G99–G105: a declaração vira folha onde o emissor já existia — 2026-09-11
O arco anterior fez o pacote parar de mentir (todo código sai no disco **ou** nomeado). Este
trocou nomeado por folha.

**O que entrou.**
- **G99** a casa chama o emissor elétrico que já calculava: unifilar, quadro e planta no
  disco ([[04-decisions#D128]]).
- **G100** PE-CO-02/03/04 da casa pelas primitivas do prédio, sem cópia; rodada real do spec
  persistido sai com 12 folhas (eram 6) ([[04-decisions#D129]]).
- **G101** o galpão sem escada declarada deixa de prometer PE-IN-03 ([[04-decisions#D126]]).
- **G102** índice × disco de rodada real + o quarto lado `extra_no_disco`
  ([[04-decisions#D130]]).
- **G103** disciplina executada sem prancha: `mezanino` isento com motivo
  ([[04-decisions#D131]]).
- **G104** hidráulica/incêndio/climatização em A1 sem `freecad.exe`: ~49,9 s → ~1,75 s
  ([[04-decisions#D125]]).
- **G105** o harness por prancha do aço — ferramenta pronta, número ainda não medido
  ([[04-decisions#D127]]).

**Auditoria (G106, [[04-decisions#D132]]).** Quatro defeitos, todos "dado que some sem
aviso": quadro A1 cortado em 220 caracteres, except que apagava a exceção do emissor,
título que prometia pilar, e portão de custo que conferia uma constante. Os portões de censo
estavam verdes na entrega — a regra do lote funcionou pela primeira vez.

**Aberto, medido — a fila G107–G112 (G109 fechado, [[04-decisions#D133]]).** O galpão ainda exige `freecad.exe` para o deliverable
inteiro; o prazo do caderno reserva tempo de FreeCAD para disciplinas de 0,6 s; o número por
prancha do aço existe para 16 de 17 (PE05 sem número: trava no recompute, declarada);
PE-CO-02 promete pilar e ninguém desenha; PE-CO-03 mostra um
painel de seis; o carimbo do galpão numera diferente do índice.

## FECHADA — G107–G112: a folha diz o que desenha — 2026-09-11
**O que entrou.**
- **G107** o galpão sem `freecad.exe` emite as pranchas de esquema e declara o resto por
  código, com status `partial` ([[04-decisions#D134]]).
- **G108** os pesos do prazo do caderno vêm da medição; a fração do aço sobe de 55 % para
  82 % ([[04-decisions#D135]]).
- **G109** o número por prancha do aço existe para 16 de 17 folhas, ~578 s no total; a PE05
  trava no recompute ([[04-decisions#D133]]).
- **G110** PE-CO-02 passa a desenhar pilar, abaixo das vigas no mesmo arquivo
  ([[04-decisions#D136]]).
- **G111** PE-CO-03 detalha os seis painéis ([[04-decisions#D137]]).
- **G112** carimbo × índice: numeração própria e tabela de correspondência no pacote do
  galpão ([[04-decisions#D138]]).

**Auditoria (G113, [[04-decisions#D139]]).** Censos verdes de novo. Corrigidos: o `OK` por
painel de laje que não chegava ao veredito, o estribo de pilar com padrão inventado, a tabela
do G112 em duas cópias, e o confronto 18.4 2014 × 2023 que o G110 pedia (idênticas, pela
imagem). Cinco dos seis goals chegaram sem verbete.

## G114–G118: a norma legível, e o que a régua não media

Arco fechado (2026-09-12). Primeiro lote do projeto com verbete em todos os goals.
- **G117** decodifica a camada de texto da NBR 6118:2023 (F150): 260 páginas, .txt fora do
  git ([[04-decisions#D140]]).
- **G116** mede a migração 2014 → 2023+Em1 sem migrar: inventário dos 51 itens, cada um
  endereçado no framework; 2 pontos em que o número muda ([[04-decisions#D141]]).
- **G114** o caderno reusa o turnkey do adaptador: um `tk.rodar` só ([[04-decisions#D142]]).
- **G115** a armação de pilar mostra todos os trechos, não só a base: 42 trechos no prédio
  ([[04-decisions#D143]]).
- **G118** a PE05 do aço ganha número: o topo travava nos 432 tirantes sem oclusores
  ([[04-decisions#D144]]).

**Auditoria (G119, [[04-decisions#D145]]).** Oito censos verdes, medidos. Corrigidos **sete**
defeitos, dois de classe nova: o medidor de bytes desconhecidos que era incapaz de acusar
(e sob ele "fck ≤ 50 MPa" saía "fck ± 50 MPa" na norma decodificada), e a guarda de intervalo
que nunca reprovava para trecho de um lance só. Mais: a âncora de pesos que a produção não
lia, o mapa de trechos sem confronto, exceção nova na PE05 sem contraventamento de cobertura,
o default plausível no lugar de ausência e o código morto que duplicava a montagem da fileira.
**Medido junto:** o portão `test_indice_disco_rodada_g102.py`, morto quatro vezes por memória
no G113, completou depois do reuso do G114 — 6 passed em 1230 s.

## G120–G124: a cifra fechada, a edição declarada, e o que a lente não procurava
Arco fechado (2026-09-12). Verbete em todos os goals, pela segunda vez seguida.
- **G121** o portão do G102 passa a medir o pico de memória, não só o tempo: galpão 1988,8 MB,
  91 % no freecad.exe; teto 2500 MB com a folga escrita ([[04-decisions#D146]]).
- **G120** 7 dos 8 códigos restantes da F150 conferidos na página e mapeados; o 0BD8 (188×,
  avanço sem marca visível) segue marcador declarado ([[04-decisions#D147]]).
- **G122** confronto 2014 × 2023 nas 45 famílias citadas: uma conta nova fora da Emenda,
  a fct,m do C55+ (+1,3 % no C60) ([[04-decisions#D148]]).
- **G123** toda peça de concreto declara a edição de cálculo, de uma fonte só; a chave
  `2014`/`2023+Em1` existe, desligada ([[04-decisions#D149]]).
- **G124** as 61 constantes que ninguém lia: 7 viram fonte única, 15 resíduos removidos,
  39 dívidas com cláusula ([[04-decisions#D150]]).

**Auditoria (G125, [[04-decisions#D151]]).** Manchetes remedidas e batidas. Corrigidos
**seis** defeitos, com uma classe comum: **a lente olhava para onde o dado já estava
declarado, não para onde ele é produzido.** O item NUMERO-MUDA da 8.2.5 listava 6 módulos
e a conta mora em 10 (o confronto partiu da citação "6118"); o endereço das divergentes era
cobrado no texto inteiro; o carimbo do G123 era conferido só no galpão, e quatro folhas de
concreto da casa e do prédio saíam sem edição; o medidor de memória ficava cego para o
freecad.exe sem acusar. Mais o `test_normas_catalogo` vermelho desde o G116 (remissões da
norma sem lastro) — que a suíte do G119 já tinha mostrado e a auditoria não leu.

## G126–G130: o default que ninguém declarou, a conta numa fonte só, e a entrega que dizia um valor enquanto a conta usava outro
Arco fechado (2026-09-13). Verbete em todos os goals, pela terceira vez seguida.
- **G126** o cimento do fckj deixa de cair no CPV em silêncio: piso conservador s = 0,38
  declarado; cimento desconhecido levanta ([[04-decisions#D152]]).
- **G127** a fct,m sai de 11 cópias em 10 módulos para uma fonte, sem mover um ulp
  ([[04-decisions#D153]]).
- **G128** a edição declarada chega a folhas, compatibilização e caderno das três tipologias
  ([[04-decisions#D154]]).
- **G129** censo de colisão de rótulo em 35 folhas: 19 colisões reais corrigidas, 43 pares
  triados no PNG ([[04-decisions#D155]]).
- **G130** as 39 dívidas normativas saem no pacote legal por tipologia, com a cláusula
  ([[04-decisions#D156]]).

**Auditoria (G131, [[04-decisions#D157]]).** O G127 bateu bit a bit contra o HEAD (99
valores). Corrigidos **cinco** defeitos, e a classe do G125 voltou pela terceira vez, agora do
lado da entrega: **o documento declarava um valor e a conta usava outro.** No galpão real, o
pacote lia o cimento do topo do projeto e o cálculo lia do payload do concreto — cada um dizia
uma coisa, nos dois sentidos; a edição tinha a mesma precedência calada (pacote 2023+Em1,
conta e folhas 2014); o pacote da casa e do prédio afirmava um piso de içamento que nenhuma
conta usou. Mais um catch-all que trocava erro por texto fixo e as cópias literais da linha
de cimento. Ficaram medidos para o G132–G136: a chave 2023+Em1 carimba a edição inteira
trocando só dois pontos; a viga protendida calculada em C40 num projeto C30; a pergunta do
cimento no fluxo metálico, sem conta.

**Tempo de suíte ([[04-decisions#D158]]).** Medido com `--durations` e perfil, antes de
mexer: 99 % de uma rodada do prédio era um laço puro do solver do pilar, e o FSM das terças
repetia 83 % das chamadas. Os invariantes saíram do laço e as duas contas puras foram
memorizadas, com o resultado inteiro do prédio e dos checks do G15 idêntico por hash. Lote 00
42:43 → 11:07; lote 04 21:46 → 7:25. A rodada real compartilhada ficou de fora, com o motivo.

**Suíte em paralelo ([[04-decisions#D164]]).** Depois do lote G132–G136 (~10 h de suíte nos
cinco goals), a medição mostrou que o `-n N` com o padrão ficava mais lento que a serial: cada
teste pesado ocupa ~4 núcleos pelo OpenBLAS do scipy, e três workers saturam os 8. Com 1 thread
de BLAS o paralelo escala (3837 passed em 29 min contra 48 min 33 s), mas o último ulp de contas
do LAPACK muda — opção declarada no runner `tools/suite_paralela.py`, com a serial seguindo
como referência bit a bit. O FreeCAD vai numa fila xdist só, congelada por censo de processos
nos dois sentidos (o grep dava 39 arquivos; 15 sobem freecad). Achado sem correção: o
executivo de aço do portão G102 estoura o prazo por construção (459 s de 787 s medidos),
~8 min de toda suíte — e o veredito do portão depende do relógio: PE01+PE02+PE03 somam
458,4 s, e quando PE02/PE03 chegam ao disco antes do corte saem sem código no mapa e o
portão reprova (corrida de 26 min 58 s: 3836 passed, 1 failed).

## G132–G136: a edição por peça, o concreto da protendida, a pergunta sem conta, o carimbo e a fctd numa fonte
Arco fechado (2026-09-13). Verbete em todos os goals.
- **G133** a viga protendida deixa de calcular num C40 que o projeto não declarou
  ([[04-decisions#D159]]).
- **G135** o carimbo da edição sai de 23 cópias e 49 rótulos para a fonte única
  ([[04-decisions#D160]]).
- **G132** cada peça declara a edição que a sua conta usou; o projeto declara a composição
  ([[04-decisions#D161]]).
- **G134** a pergunta do cimento sai do fluxo metálico, onde nenhuma conta a lia
  ([[04-decisions#D162]]).
- **G136** a fctd sai de sete cópias para uma fonte, com o γc da Tab. 12.1 lido na página
  ([[04-decisions#D163]]).

**Auditoria ([[04-decisions#D165]]).** Medido na função real, sem confiar no verbete: a fctd
dá os mesmos 560 campos no HEAD pré-G136 e na árvore (8 fcks × 7 módulos); a protendida C30
sem chave sai com `lim_comp` −21000 e declara a origem, com `fck_protendida` 40 volta a −28000;
os censos das fontes únicas estão fechados; a casa com a chave 2023+Em1 não tem folha dizendo
2023. O lote se sustenta. No mesmo passo, o portão G102 deixou de esperar o executivo de aço
(sorteio de relógio, D164) e o executivo completo ganhou portão próprio, de auditoria.

### G137–G142 — as folhas que o galpão prometia e não emitia
- **G137** as 17 pranchas de aço ganham código; o prazo do caderno sai do medido
  ([[04-decisions#D166]]).
- **G139** a coordenação sai no recorte com ≥ 2 disciplinas, PE-CD-02 com código
  ([[04-decisions#D167]]).
- **G138** PE-IN-02 do galpão sai do emissor do prédio, adaptado do cálculo
  ([[04-decisions#D168]]).
- **G140** PE-CO-04 do galpão, cada sapata desenhada uma por uma ([[04-decisions#D169]]).
- **G141** o mezanino calculado ganha PE-MZ-01, ausência declarada ([[04-decisions#D170]]).
- **G142** PE-EL-03 da casa segue pulada: nada desenhável sem malha/SPDA
  ([[04-decisions#D171]]).

**Auditoria ([[04-decisions#D172]]).** O emissor do prédio reusado no galpão trouxe o
`or 1` dele: sem hidrantes calculados a PE-IN-02 desenhava HID-1 e reserva 0,0 m³. A INC03
nova, ligada sem try no cfg comum, derrubava INC01/INC02 — e o teste do próprio goal
esperava esse erro. A causa da folha caída passa a chegar ao motivo da pulada, e o
`PYTHONUTF8` sai do shell para o runner. Vermelho provado no `f22dfe9`; runner 3874 passed,
serial 3874 passed, portão do aço 2 passed.

### G143–G148 — o default calado, o fallback calado e a folha do mezanino
- **G143** a estaca do galpão sem default calado (D/L/tipo recusam, resto com origem dita).
- **G144** o gate de interferência do mezanino vira falha nomeada que reprova.
- **G145** os 47 fallbacks `or 0`/`or 1` triados contra o produtor; 3 vivos declaram ausência.
- **G146** PE-MZ-01 do mezanino: formas + armação via primitivas do prédio adaptadas do
  cálculo, cada viga/pilar/sapata um por um ([[04-decisions#D173]]).
- **G147** pesos de concreto (61,1 s) e elétrico (110,5 s) medidos; prazo 2100 s mantido
  ([[04-decisions#D174]]).
- **G148** piso de 200 MB livres no runner, quebra nomeada; ganho sem o galpão do G102
  só relatado ([[04-decisions#D175]]).

**Auditoria ([[04-decisions#D176]]).** O piso do G148 terminava só o pytest pai: os
workers xdist seguiam vivos até o teste corrente acabar (4 processos 10 s depois do
aborto). Agora o runner termina a árvore do próprio filho e nomeia quem sobreviver. A
MZ01 marcava a mesma viga como VX0 na planta e M-VX1 na armação e no BIM, e cortava o
título do carimbo. G143, G144 e G145 não tinham verbete; o resumo medido entra no D176.
Vermelho provado no `9f112ce` (4 failed). Suíte: runner 3916 passed/1 skipped em 26 min,
quebras vazio; serial igual em 56 min; portão do aço 2 passed.

**G148 parte 2 ([[04-decisions#D177]]), decisão do usuário.** O galpão do G102 roda só na
auditoria (`test_10`, `GALPAO_AUDITORIA=1`, 771,7 s verde); casa e prédio seguem no
`test_01` (31,8 s). Suíte 3917 passed/2 skipped, quebras vazio. O ganho de parede não se
demonstrou (máquina carregada, builds do FreeCAD 1,4–2,3× mais lentos); o G153 mede.

### G149–G153 — a estaca calada nas outras portas, o `.get(…, 0)`, o carimbo cortado, a folha reprovada e o piso
Os verbetes do G149 ao G152 estão em `04-decisions` numerados no G157 (D183–D186);
estas linhas foram escritas na auditoria, os goals não escreveram aqui.
- **G149** D/L/tipo/bloco da estaca recusam nomeados no metálico, wizard e prédio; fck/fyk do
  bloco herdam o material do spec; FS com a origem dita ([[04-decisions#D183]]).
- **G150** os 64 `.get(chave, 0/1)` dos emissores + 3 do adaptador do mezanino triados:
  todos mortos, lente estendida ([[04-decisions#D184]]).
- **G151** 13 títulos de carimbo encurtados sem corte, 10 abreviações declaradas, MZ01
  numerada 01/03–03/03 ([[04-decisions#D185]]).
- **G152** a folha de disciplina reprovada declara o veredito (carimbo REPROVADO - VER
  MEMORIAL e linha com os gates), lida de `veredito_folha_g152`; ATENDE byte-idêntica
  ([[04-decisions#D186]]).
- **G153** o piso de memória só aborta com 3 amostras seguidas; série e carga no resumo;
  ganho de parede do D177 medido: 1574 → 1032 s (−34 %) ([[04-decisions#D178]]).

**Auditoria ([[04-decisions#D179]]).** O G149 carimbava o FS 3,0 da estaca como "default
normativo NBR 6122"; a NBR 6122:2022 (p.18, 6.2.1.2.1) diz 2,0 — a afirmação veio do backlog
anterior. Corrigida a atribuição (número e trava ficam, decisão do usuário). O censo do
FreeCAD descartava por PID reusado e o pytest aninhado sobrescrevia o censo de fora; a serial
caiu num teste de runner aninhado que varria o Temp sem `pytest.ini`. Suíte: runner 3955
passed/2 skipped, quebras vazio; serial 3953/1 failed (corrigido e re-rodado pelo runner);
portões do aço (2 passed) e do galpão (884 s) verdes.

### G154–G157 — o material do modelo, as folhas que não dizem que reprovaram, a citação sem item e o verbete sem número (fechado)
- **G154** o material da fundação distingue modelo de declarado desde onde o número
  nasce (wizard pergunta); memorial sempre diz a origem, folha carimba o modelo a
  confirmar; corrida sem 25 MPa calado ([[04-decisions#D180]]).
- **G155** cada folha reprovada do prédio e da casa declara o veredito e os
  gates pela fonte única estendida (gate/OK/ok/circuits; sem veredito a folha
  declara indisponível, sem STATUS); ATENDE byte-idêntica, PNG olhado,
  BASELINE_G83 intacto; suíte 3970 passed/2 skipped, quebras vazio
  ([[04-decisions#D181]]).
- **G156** toda frase que atribui número a NBR tem item e triagem na imagem
  (lente AST, baseline 73, vermelho por injeção); divergências corrigem só a
  atribuição (NM 280→NM 247-3, Wenner, 10 ohm, Rippl, theta 550, faixa do
  incêndio, gamas adotados), números intactos, 6 pendências ao usuário;
  suíte 3973 passed/2 skipped, quebras vazio ([[04-decisions#D182]]).
- **G157** todo goal fechado desde o G149 tem verbete com número D e bullet
  com link na fase (guarda em `tests/test_verbete_fase_g157.py`, baseline
  nos dois sentidos, vermelho por injeção em `tmp_path`); verbetes G149–G152
  numerados D183–D186 sem reescrever o conteúdo, links conferidos; suíte
  3976 passed/2 skipped, quebras vazio ([[04-decisions#D187]]).

### G159 — o código de produção que entra sem deixar registro (fechado)
- **G159** todo commit desde o G149 que toca arquivo de produção tem verbete
  com D ou isenção com motivo (censo por arquivo em
  `tests/test_censo_producao_g159.py`, definição de produção reusada da lente
  do G156, parada fixa no commit do G149, baseline nos três sentidos com
  vermelho por injeção em repo git de verdade em `tmp_path`); os 4 commits
  WKI regularizados no D188, a auditoria D179 isenta com motivo
  ([[04-decisions#D188]]).

### G160 — a lente de citação que só enxergava NBR (fechado)
- **G160** a mesma lente do G156 passa a enxergar fonte normativa de conta
  que não é NBR (distribuidora por código WKI/CNC/ET, IEC, ISO/CIE 8995, com
  a regra escrita no teste e a isenção de livro/catálogo/fabricante mantida);
  as 32 citações de conta triadas na imagem (15 WKI contra o F131 p.5–8,13–14,
  5 CNC contra o F128 p.25, resto REMISSAO/NAO_CONFERIVEL), nenhuma com número
   mudado; suíte com os mesmos resultados ([[04-decisions#D189]]).

### G161 — as 476 células transcritas conferidas na imagem (fechado)
- **G161** as 476 células WKI que a produção lê conferidas na imagem do F131
  (TABELAS 2 e 3 p.14: 370; TABELA 1 p.13: 90; 16 soltas p.5–8; 0 divergências,
  7 anomalias impressas mantidas); guarda em
  `tests/test_wki_transcricao_g161.py` com vermelho por injeção por parte;
  aferição pelo EXEMPLO 1 da fonte (6.6.1 p.28–30, Dc 23,69 kVA); nenhum número
  mudou ([[04-decisions#D190]]).

### G162 — a demanda que chegava à folha como um número sem origem (fechado)
- **G162** a linha da demanda declara fonte + itens + fator locacional
  (WKI-OMBR-MAT-18-0263-INBR-R01, F131); cada recusa do módulo vira gate
  nomeado na folha pela fonte única do G152; ATENDE byte-idêntica, PNG
  olhado das duas folhas ([[04-decisions#D191]]).

### G163 — a tabela de decisão das pendências e dos links sem verbete (fechado)
- **G163** tabela única das pendências (seis do D182 + links D152–D154 do
  D187 + FS 3,0 decidido do D179 + G160/G161 + vigência WKI), cada linha
  conferida na imagem da página com a recomendação conservadora ao lado;
  nenhum número, veredito, default ou trava mudou ([[04-decisions#D192]]).

## Docs do arco (sem código)
- `5157222` (2026-09-09) — backlog pós-G76, medido na árvore.
- `868b93e` (2026-09-09) — backlog de 11 goals executáveis (G78–G88), medidos na árvore;
  fila de trabalho em `framework/galpao_fw/BACKLOG-GOALS.md`.

