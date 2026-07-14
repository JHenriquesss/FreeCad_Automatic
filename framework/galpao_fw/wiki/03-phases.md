# 03 — Fases

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

## ATUAL — Handoff / aguardando pareceres — 2026-07-08
- **NADA pendente de implementação do lado do assistente.** Todos os gaps + FLAGs corrigíveis fechados.
- ~~6 pareceres sênior pendentes~~ → **TODOS HOMOLOGADOS 2026-07-09** (calhas, divisa, telha, vento §8, sismo §6; demais já eram). REVISAO-INDICE zero pendente. [[06-open-threads#T7]]
- PR #1 ainda aberto, aguarda merge do usuário. [[06-open-threads#T1]]
- Continuação em outro chat: ver [[06-open-threads#HANDOFF]].

## Status — 17 módulos matemáticos + features (todos com selftest verde)
12 r2 (Pórtico·Perfil·Vento·Terças·Secundários·Base·Ligações·Ponte·Mão-francesa·Contravento·Fundação·Redim) + Junta + Sismo + **Telha** + **Baldrame** + **Estaca profunda**.
