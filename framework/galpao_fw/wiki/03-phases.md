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
REVISAO-INDICE **itens 45–49 ✅**. Cada alegação conferida contra PDF/estática antes de
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
  Commit `<6c>`. PENDENTE `REVISA-TESOURA-INTEG.md` Q1–Q5, INDICE 33.

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
- **Regressão:** smoke 6/6 (caso `alma_var`); prismáticos inalterados. Commit `<6b>`.
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
  Commit `<fase6a>`.
- **Órfãos restantes:** `neve` (não escolhido pelo usuário — fica documentado, não
  wired); `alma_variavel`/`tesoura` = Fase 6.b (tipo de pórtico, build 3D novo).

## FECHADA — Corte seccionado 2D (fase 5) — 2026-07-10
**Escopo:** corte SECCIONADO real (hachurado) nos detalhes de ligação. Fecha o
resíduo de polimento 2D de [[06-open-threads#T6]].
- **Blocker resolvido:** `DrawViewSection` **constrói headless no FreeCAD 1.1**
  (probe: box → seção com 4 arestas; nenhum `failed to create section CS`). O erro
  histórico era da versão antiga.
- **`techdraw_exec._secao_ligacao`:** DrawViewSection do crop compound, plano de
  corte pelo centro, `CutSurfaceDisplay="Hatch"` (material cortado). Descarta a
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

## ATUAL — Handoff / aguardando pareceres — 2026-07-08
- **NADA pendente de implementação do lado do assistente.** Todos os gaps + FLAGs corrigíveis fechados.
- ~~6 pareceres sênior pendentes~~ → **TODOS HOMOLOGADOS 2026-07-09** (calhas, divisa, telha, vento §8, sismo §6; demais já eram). REVISAO-INDICE zero pendente. [[06-open-threads#T7]]
- PR #1 ainda aberto, aguarda merge do usuário. [[06-open-threads#T1]]
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

## Status — 17 módulos matemáticos + features (todos com selftest verde)
12 r2 (Pórtico·Perfil·Vento·Terças·Secundários·Base·Ligações·Ponte·Mão-francesa·Contravento·Fundação·Redim) + Junta + Sismo + **Telha** + **Baldrame** + **Estaca profunda** + **Contenção lateral** (mão-francesa, NBR 8800 4.11.3.4).

