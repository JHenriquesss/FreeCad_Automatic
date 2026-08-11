# Task 9 — Cross-check fases × decisões × threads × datas contra git/PRs/código

- **Data da evidência:** 2026-08-11 (todo 9 do plano de revisão da wiki)
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (HEAD `6358157` = main/origin, merge PR #171)
- **Escopo:** conferir 03-phases.md (fases), 04-decisions.md (D1–D73), 06-open-threads.md (T#) e 00-index.md (datas dos blocos) contra `git log`/`git show`/`gh pr view` e contra o código-fonte em `framework/galpao_fw/`
- **Entradas prontas (NÃO refeitas):** task-3 (arqueologia S19→hoje, reconciliação 117/117, tabela de PRs #55–#171), task-6 (links), task-5 (ledger, 430 claims)
- **Saídas:** esta evidência (tabelas de veredito + PATCH LIST p/ ledger task-5). NENHUM arquivo da wiki editado; NENHUM commit.
- **Formato:** UTF-8 explícito. Vereditos: `ok` / `corrigir` / `faltante` / `obsoleto` / `não verificado (fonte ausente)`.

---

## 0. Comandos usados (resumo, detalhe no QA §9)

- `git log --merges --oneline | Select-String "pull request #(…)"` — presença dos merges na main
- `git branch -a --contains <hash>` + `git merge-base --is-ancestor <hash> main` — merges em branch intermediária (#46/#49/#54/#57)
- `git log -1 --format="%h %cI %s" <commit>` — datas dos commits citados nos blocos
- `git ls-tree main --name-only -- <arquivo>` — presença de módulos no main
- `git show <merge>^1..<merge>` / `git diff <merge>^1 <merge> --stat` — conteúdo real dos PRs S19
- `git show main:framework/galpao_fw/<modulo>.py | Select-String …` — código atual dos pontos spot-check
- `gh pr view <N> --json state,mergedAt,title,baseRefName,headRefName`
- `grep` nos 7 arquivos da wiki (headers `## D`, `## T`, `## FECHADA`, `S19`)

---

## 1. (a) Fases de 03-phases.md × git/PRs — veredito por bloco

Conferência: cada bloco `## FECHADA/ATUAL` × commits citados × merges da timeline (task-3) × estado do PR correspondente.

| Fase (linha 03-phases) | Origem | Veredito | Evidência |
|---|---|---|---|
| Auditoria "Diretrizes Técnicas" 8.1–8.36 (07-15) | 03-phases:3-17 | ok | Commits `dad7b87`(09:01) `06130c0`(09:52) `ac529a2`(13:55) `a6e3808`(14:23) `741221d`(16:20) todos 2026-07-15, mensagens batem com os lotes 1/9/10/11/12; conteúdo mergeado via PR #8 (`20a53a5`, 07-15) |
| Balde 4 6.15–6.19 + homologação 45–49 (07-13/14) | 03-phases:19-50 | ok | `12ff107`→`01e14e7` 07-13; merged via PR #5 (`50df273`, 07-14 05:35Z — título "fases 6.4-6.19 (itens 34-49)") |
| Backlog parecer 6.b 6.4–6.8 + itens 34–38 (07-11) | 03-phases:52-74 | ok | `1baef85`→`a55a1fe` 07-11 ✓ (merged via #5) |
| Homologação 6 pareceres 28–33 (07-11) | 03-phases:76-90 | ok | `718bbe8`(07-10 23:56)→`35cda72`(07-11 02:09) ✓ |
| Pórtico treliçado/tesoura 6.c (07-10) | 03-phases:92-107 | corrigir | Commit real `820b0e0` (07-10 17:29); o bloco grava o placeholder `Commit <6c>` (03-phases:106) |
| Pórtico alma variável 6.b (07-10) | 03-phases:109-125 | corrigir | Commit real `21d9941` (07-10 15:24); placeholder `Commit <6b>` (03-phases:123) |
| Wiring calha + divisa 6.a (07-10) | 03-phases:127-142 | corrigir | Commit real `5fd4003` (07-10 14:40); placeholder `Commit <fase6a>` (03-phases:140) |
| Corte seccionado 2D fase 5 (07-10) | 03-phases:144-158 | corrigir | `f912e98` (07-10 13:53) ✓; **mas `CutSurfaceDisplay="Hatch"` (03-phases:151) ≠ código: `techdraw_exec.py:1247` usa `"SvgHatch"`** (D40/05-glossary:34 corretos) |
| Ponte rolante estendida fase 4 (07-10) | 03-phases:160-174 | ok | `4d090e5` (07-10 12:45) "rodas motoras + NBR 8400-1:2019" ✓ |
| Fundação profunda fase 3 (07-10) | 03-phases:176-194 | ok | `9ac3c4f` (07-10 09:56) ✓ |
| Revisão sênior r2 (07-07) | 03-phases:196-204 | ok | `d668daf`/`d0638b8` 07-07 ✓; PR #1 merged (`4fde82b`, 07-07 13:29-03:00) ✓ |
| Features pós-homologação D8–D22 (07-07/08) | 03-phases:206-207 | ok | Merges #1 (07-07) e #4 (07-10) cobrem o período ✓ |
| Análise de lacunas COMPLETA (07-08) | 03-phases:209-216 | ok | `c8d10de`(09:10)→`7009b61`(13:45) 07-08 ✓ |
| Projeto executivo 2D (07-09) | 03-phases:218-226 | ok | `e696b84`(14:36)→`b0c2e89`(22:03) 07-09 ✓; PR #4 merged (`aa02180`, 07-10) |
| Detalhe de ligação fabricação A+B (07-09) | 03-phases:228-234 | ok | D37 (corte A em fallback — superado pela fase 5, D40, coerente no próprio arquivo) |
| Balde 2 6.9–6.12 + itens 39–42 (07-13) | 03-phases:236-245 | ok | `6e3551f`(07-12)→`a18b524`(07-12 22:53) ✓ (header 07-13 = dia da homologação; commits 07-12, janela ±1 dia — observação) |
| Balde 3 6.13–6.14 (07-13, impl. FECHADA) | 03-phases:247-258 | ok | Itens 43–44 ✅ per 00-index:217-228 (homologados 07-13); "⏳ aguardam parecer" superado — bloco interno já registra homologação nas linhas seguintes (D47) |
| **ATUAL — Handoff / aguardando pareceres (07-08)** | 03-phases:260-264 | **obsoleto** | Bloco rotulado "ATUAL" não é mais atual (S16–S42 já existem); **"PR #1 ainda aberto" é falso: PR #1 MERGED (`4fde82b`, 07-07 13:29-03:00)**; "TODOS HOMOLOGADOS" já superado por T8–T13 |
| Job periódico build 3D PR #49 (S18, 07-22) | 03-phases:266-274 | ok | PR #49 state=MERGED (07-22 15:57Z); conteúdo na main via PR #51 (`1f4c38f`) — `tools/run_build_suite.ps1`, `register_build_task.ps1`, `README.md` no main (`git ls-tree`) ✓ |
| Plano de montagem PR #47 (S18, 07-22) | 03-phases:276-287 | ok | Merge `4625aed` (07-22 15:12Z); `montagem.py` no main ✓ |
| Revisão PRs #45/#46 (S17, 07-22) | 03-phases:289-305 | ok | #45 merged `b2baa5b` (07-22 11:58Z); #46 state=MERGED (11:58:57Z, merge em branch `feat/gaps-nivel-a-contra-seguranca` — `2ebade5` NÃO é ancestral de main; conteúdo chega via `a681999` "marcas de peca [S17]" no main) — efeito "MERGED em main" verdadeiro |
| Revisão PR #44 (S16, 07-21) | 03-phases:307-317 | ok | Merge `4760a40` (07-21 22:21Z); branch `fix/gate-mao-francesa-e-cache-de-modulo` confere; "Pendente: merge do #44" → resolvido (merged) |
| Revisão T15 (07-17) | 03-phases:319-322 | ok | Commits `8bd725f`/`bb36b9b`/`e4e3468`/`63451f1` todos 07-17 16:15-16:16 ✓; D52–D57 conferem no código (§2) |
| Status — 17 módulos matemáticos | 03-phases:324-325 | corrigir | Contagem interna inconsistente: 12 r2 + Junta + Sismo + Telha + Baldrame + Estaca + Contenção lateral = **18 itens listados**, header diz "17"; bloco defasado (módulos atuais ≈ 53, README) |

### Achado estrutural (a)

**S19 FALTANTE em 03-phases:** grep `S19|Sessão 19|#5[5-9]|#6[0-1]` em 03-phases.md → **zero ocorrências**. Os PRs #55–#61 (merged 22–23/07/2026, cluster 1 do task-3) só existem em 00-index:66-75. O arquivo termina a sequência de fases na S17/S18 (PRs #44–#49) + T15. Também sem bloco: **S18 unificada** (PRs #51–#54 — só há blocos por PR #49/#47/#45-46) e **todo o arco S20–S42** (PRs #81–#171). S19 marcada **faltante** (reconstrução = todo 14).

---

## 2. (b) Decisões 04-decisions.md — presença + spot-check de 10

**Presença:** grep `^## D` → **D1–D73 presentes** (73 headers + D0 no fim, linha 635). Nenhuma decisão numerada ausente. **D74–D79 ausentes** (§5).

### Spot-check (10 decisões × código-fonte)

| D | Origem | Veredito | Evidência (código no main) |
|---|---|---|---|
| D52 — fix de sinal da UDL no frame2d | 04-decisions:408-417 | ok | `frame2d.py`: montagem com `F_eq_global = T.T @ fef` e comentário "par do += na montagem acima"; esforço de barra `f_loc = k_loc @ (T @ d_e) - fef` (linha 192) com comentário "Antes era +fef" (181-183) — o par de sinais corrigido está no código |
| D63 — estaca ponta na profundidade L | 04-decisions:509-516 | ok | `estaca_profunda.py:116 def _camada_na_ponta(perfil, L)`; usada nos 3 métodos (82/155/224); `tests/test_estaca_ponta.py` cobre boundary→cima e além→última |
| D64 — executivo sempre encerra o freecad.exe | 04-decisions:519-524 | ok | `rodar_projeto.py:331 def _matar_processo_freecad` (kill→taskkill /F /T→WMI); usada no `finally` (322) e reusada pelos 6 verticais (`galpao_concreto.py:498`, `galpao_eletrico.py:374`, `galpao_turnkey.py:420/485`, hidráulica 356, climatização 166, incêndio 177); `tests/test_executivo_cleanup.py` |
| D67 — mão-francesa: `perfis.cantoneira` | 04-decisions:541-588 | ok | `perfis.py:66 def cantoneira(b_mm, t_mm)` (forma fechada); `mao_francesa_geom.py` + `contencao_lateral.py` presentes |
| D40 — Corte seccionado: enum CutSurfaceDisplay | 04-decisions:125 | ok | **O CÓDIGO DECIDE: `techdraw_exec.py:1247` `sec.CutSurfaceDisplay = "SvgHatch"`** — "Hatch" NÃO existe como enum (D40:125 e 05-glossary:34 corretos; **03-phases:151 e 06-open-threads:364 errados — "corrigir"**) |
| D54 — campos mortos do wizard (janela) | 04-decisions:432-437 | ok | `projeto_spec.py:631 def _janela_band(janela, eave_mm, peitoril_mm=1100.0)`; chamado em `wizard.py:279`; `tests/test_aberturas_janela.py` (mapper pass-through, T40) |
| D69 — PR #46 bloco de fabricação | 04-decisions:600-605 | ok | `marcas_peca.py`, `tolerancias_fabricacao.py`, `romaneio.py`, `diafragma.py` **todos no main** (`git ls-tree main`) |
| D70 — PR #47 montagem | 04-decisions:608-614 | ok | `montagem.py` no main; prancha PE16 no código do executivo (funções `guindaste_requerido`/`estai_provisorio`/`tolerancia_prumo_montagem` — spot-check de presença de módulo; fórmulas não re-derivadas) |
| D71 — PR #48 GUT_Y/DOWN_Y | 04-decisions:617-620 | ok | `build_galpao.py:1257-1264`: `_col_d_beiral = COL_SEC[0]` → `_col_d_beiral = max(_col_d_beiral, float(TAPERED_MODEL["h_joelho"]))` → `GUT_Y = _col_d_beiral/2 + UPE_LONG[0] + CALHA_SEC[0]/2 + 30`; `DOWN_Y = max(GUT_Y, BASE_PLATE["L"]/2 + CONDUTOR_D/2 + 40)` — o `max(COL_SEC[0], TAPERED_MODEL["h_joelho"])` do D71 está implementado via intermediária `_col_d_beiral`; o +40 do DOWN_Y confere |
| D73 — PR #54 mrd_flt_chapa + patamar | 04-decisions:629-633 | ok | `console_ponte.py:38 def mrd_flt_chapa(t, L, ecc, fy, Cb=1.0)` + `tests/test_console_flt.py`; `escada._dimensiona_multi` (patamar Blondel) + `tests/test_escada_patamar.py` — todos no main |

### Decisões citadas SEM correspondência exata (regra do QA: → corrigir com sugestão)

| D | Claim da wiki | Realidade no código | Veredito + sugestão |
|---|---|---|---|
| D78 (a reconstruir, §5) | "modelo neutro estendido (`secundarios_lineares`)" | Atributo `secundarios_lineares` **não existe** em nenhum .py (grep vazio). PR #60 (`495b594`) adicionou em `modelo_neutro.py` as funções `tercas()`, `girts()`, `tirantes_parede()`, `contrav_cobertura()`, `frame_completo()` | **corrigir** — reconstruir D78 citando as funções reais |
| D79 (a reconstruir, §5) | "`modelo_analitico` (módulo)" | **`modelo_analitico.py` NÃO existe no disco nem no main** (`git ls-tree main` vazio; só `tests/test_modelo_analitico.py`). Implementação real: `galpao_portico.modelo_analitico()` (função, PR #61) + `ifc_emit.emitir_ifc_analitico` / `emitir_ifc_analitico_do_spec` + `rodar_projeto.py:533-534` gravando `{slug}.ifc` e `{slug}_analitico.ifc` em `EXPORT_DIR/ifc/` | **corrigir → fallback** — reconstruir D79 citando função+emissores (ver §5) |

---

## 3. (c) Threads 06-open-threads.md × git/PRs — status real por T#

| Thread | Origem | Status na wiki | Status REAL (git/gh/código) | Veredito |
|---|---|---|---|---|
| T40 | 06:3-4 | ✅ RESOLVIDO (PR #150) | PR #150 MERGED `7d934a7` (08-03 18:31Z); `projeto_spec._janela_band` + mapper pass-through confirmados (§2 D54) | ok |
| T40b | 06:6-7 | Padrão parcial, sem suspeita aberta | #145/#146/#148 MERGED (task-3: 08-03); terça-ELS/placa fechados no #148 (00-index:44-49 confere) | ok |
| T21 | 06:9-17 | **ABERTO (decisão do usuário): merge PR #54** | PR #54 state=**MERGED** (07-22 18:40:36Z); merge `44ad268` em branch `ci/github-actions-nonbuild` (não ancestral de main); conteúdo **na main via PR #55** (`83570c9`, cherry-pick — `mrd_flt_chapa` e `_dimensiona_multi` presentes no main) | **obsoleto** — item resolvido |
| T20 | 06:19-30 | **ABERTO: merge do PR #49** | PR #49 state=**MERGED** (07-22 15:57:26Z); conteúdo na main via PR #51 (`1f4c38f` — `tools/run_build_suite.ps1` etc. no main) | **obsoleto** — item resolvido |
| T19 | 06:32-48 | **ABERTO: merge do PR #47** | PR #47 **MERGED** (`4625aed`, 07-22 15:12Z) | **obsoleto** — item resolvido |
| T18 | 06:50-67 | MERGED | #45 merged `b2baa5b`; #46 MERGED (branch) + conteúdo no main via `a681999` | ok |
| T17 | 06:69-91 | ABERTO (usuário): cantoneira `_a_confirmar` + revisão dos 7 commits | #44 MERGED (07-21); bitola da cantoneira = decisão de usuário (não verificável em git/código — segue aberta, legítimo) | ok (com nota) |
| T16 | 06:93-142 | AINDA ABERTO: latentes (telha_tipo, multi-vão heterogêneo) + fuzz | PRs #15–#19 MERGED ✓; **latente `telha_tipo` "só rótulo" RESOLVIDO depois**: `projeto_spec.py:769-775` liga `cobertura.telha_tipo` ao perfil verificado no gate 7 | **parcial-obsoleto** (item telha_tipo fechado; fuzz não verificado) |
| T15 | 06:144-171 | MERGED (via #12→#14); itens 3–5 aguardam sênior | PR #12 MERGED `4165652` (07-18); itens 3–5 = parecer humano/ART → não verificável por git | ok (itens 3–5: não verificado — fonte humana) |
| T14 | 06:173-199 | PR #12 **aberto, NÃO mergeado**; 2º caso-referência pendente | PR #12 **MERGED** (`4165652`, 07-18 08:54-03:00); 2º caso-referência resolvido em T15 (`validacao_alonso`, D57) | **obsoleto** |
| T13 | 06:201-241 | RESOLVIDO 07-15; PR #8 MERGED | `20a53a5` (07-15) ✓; smoke rodado per próprio bloco | ok |
| T12 | 06:243-257 | RESOLVIDO 07-13/14 | D48 + pytest 245/smoke 7/7 (00-index:213); gate humano (push+merge) → branch `revisao/homologacao-12-modulos` **pushed** (remote existe) e mergeada (#1-#12) | ok |
| T11 | 06:274-296 | impl. FECHADA; itens 43–44 aguardam | Homologados 07-13 (D47; 00-index:217-228) | ok |
| T10 | 06:298-309 | FECHADO | D46; itens 1–42 ✅ | ok |
| T9 | 06:311-324 | FECHADO | D45; itens 1–38 ✅ | ok |
| T8 | 06:326-328 | FECHADO | D44; itens 1–33 ✅ | ok |
| T7 | 06:330-331 | FECHADO | D44 (superado por T8) | ok |
| T1 | 06:333-334 | "PR #1 aguarda merge" | **PR #1 MERGED** (`4fde82b`, 07-07 13:29-03:00) | **obsoleto** |
| T2 | 06:336-337 | Divergência local↔origin (87 commits) | Resolvida — PR #1 merged sincronizou | **obsoleto** |
| T3 | 06:339-340 | Backlog: ponte rolante estendido | Feito — D39 (rodas motoras + NBR 8400) + D47 (crane 100% homologado); fadiga Anexo K automatizada (D10/D16) | **obsoleto** |
| T4 | 06:352-356 | Flags de projeto executivo | Sapata flexível: RESOLVIDO (D8); **ponte fadiga "sinalizada, não automatizada"**: automatizada (D10/D16/D62); inputs σ/μ/coesão: seguem como INPUT (ok); quantitativo ~10-15%: não re-verificado | **parcial-obsoleto** |
| T5 | 06:380-381 | settings.local.json não criado | Config local do usuário — sem fonte no repo | **não verificado (fonte ausente)** |
| T6 | 06:358-368 | FECHADO | Fase 5 (corte) + 6.19 (glyph) fechadas ✓; **mas linha 364 registra `CutSurfaceDisplay="Hatch"` ≠ código (`"SvgHatch"`, techdraw_exec.py:1247)** | ok (com texto a corrigir) |
| T6-hist | 06:370-378 | histórico, corrigido | D7 confirmado no código (calha CM, telha ZMin, CONEX_CUMEEIRA) | ok |
| HANDOFF | 06:259-272 | histórico | Todos os "próximos passos" executados nas sessões seguintes (T7/T1/estaca 3D fase 3) | ok (histórico) |
| Lacunas de escopo | 06:342-349 | TODAS FECHADAS | D14/D31/D28/D16/D12/D26 — conferem com o código (módulos existem) | ok |

**Threads com status divergente do real: 10** (T1, T2, T3, T4, T6-texto, T14, T16, T19, T20, T21 — todas no sentido "ABERTO/pendente desatualizado, já resolvido no git").

---

## 4. (d) Datas dos blocos de 00-index × datas de commit

Regra: erro = data de fase sem commit correspondente na janela. (Dia da semana ≠ data de merge não conta.)

| Bloco | Origem | Veredito | Evidência |
|---|---|---|---|
| Estado atual (2026-08-03) — Sessões 20–40 | 00-index:18 | ok (observação) | #148 08-03 16:17Z, #150 08-03 18:31Z, #152 08-03 18:55Z — todos dentro de 08-03 ✓; `last-consolidated 2026-08-04` (#153, 08-04 13:14Z) coerente com a reconfirmação 1281 passed de 08-04 |
| Estado anterior (2026-07-23) — S19 #55–#61 | 00-index:66 | ok | Merges 07-22 21:58Z (#55) → 07-23 00:15Z (#61); títulos dos PRs conferem com os 7 bullets (#55 gaps-e-wiki…, #56 ifc-export-bim, #57 bridge-headless, #58 ifc-emissor-puro, #59 headless-para-main, #60 ifc-secundarios, #61 modelo-analitico) |
| Estado anterior (2026-07-22) — S18 #51–#54 | 00-index:78 | ok | #51 18:36Z, #52/#53 18:36-18:37Z, #54 18:40Z (07-22); #47/#48/#49 15:12-15:57Z; #45/#46 11:58Z — todos 07-22 ✓ |
| Estado anterior (2026-07-22) — S17 #45/#46 | 00-index:110 | ok | #45 11:58:52Z, #46 11:58:57Z 07-22 ✓ |
| Estado anterior (2026-07-21) — S16 #40–#44 | 00-index:129 | ok | #44 07-21 22:21Z ✓ (demais #40-43 em 07-21, merges presentes no log) |
| Estado (2026-07-17) — correções+features+validação | 00-index:149-153 | **corrigir** | **"Sessão longa … (sem commit — árvore de trabalho)" é FALSO**: `8bd725f`, `bb36b9b`, `e4e3468`, `63451f1` existem com data 07-17 (16:15-16:16), e o próprio 06-open-threads:145 diz "COMMITADO em 6 commits temáticos". Commit correspondente existe na janela — mas o texto do bloco nega |
| Estado (2026-07-16) — TURNKEY | 00-index:170-187 | corrigir (parcial) | Commits `65d05a7`(07-16 00:13), `4f8696a`/`2f5af9b`/`714cbda`/`003f391`(07-16 17:16-18:14) ✓; **"PR #12 (15 commits, NÃO mergeado)" → obsoleto (merged `4165652`, 07-18)**; "2º caso-referência PENDENTE" → resolvido em T15/D57 |
| Estado 2026-07-15 — Auditoria | 00-index:189-200 | ok | `dad7b87`→`741221d` 07-15 ✓; "não pushada" → superado (merged via #8, 07-15) |
| Estado anterior (2026-07-14) — Balde 4 | 00-index:202-215 | ok (observação) | Commits `12ff107`→`01e14e7` são 07-13 (20:05-23:48); bloco datado 07-14 = dia de fechamento da homologação (03-phases:19 "2026-07-13/14") — janela ±1 dia, sem erro de fase sem commit |
| Estado 2026-07-13 — Balde 3 | 00-index:217-228 | corrigir (parcial) | Conteúdo confere (D47); **"PENDENTE gate humano: merge PR #5" → resolvido (`50df273`, 07-14)** |
| Estado anterior (2026-07-10) — fases 3–5 + 6.a–6.c | 00-index:230-243 | corrigir (parcial) | `9ac3c4f`→`f912e98` 07-10 ✓; **"PENDENTE gate humano: merge PR #1+#4" → resolvido (`4fde82b` 07-07 / `aa02180` 07-10)** |

**Resumo datas:** 9/11 blocos com janela correta; 2 com texto a corrigir (00-index:150 "sem commit"; 00-index:173/228/243 itens "PENDENTE/NÃO mergeado" já resolvidos).

---

## 5. (e) D74–D79: ausência confirmada + evidência para reconstrução (todo 15)

**Ausência:** `grep "## D7[4-9]"` em 04-decisions.md → **vazio**. Último header numerado é D73 (linha 628); D0 (política) na 635. As decisões da S19 **nunca foram registradas** no log — confirmado.

**Fonte de reconstrução (bloco S19, 00-index:69-74) × git × código:**

| D# (proposto) | PR | Fonte 00-index | Evidência git | Evidência código (main) | Reconstruível? |
|---|---|---|---|---|---|
| D74 | #55 (`feat/gaps-e-wiki-para-main`) | 00-index:69 | Merge `83570c9` 07-22 21:58Z (task-3: cherry-pick Gaps A3/C5 + wiki S18) | `console_ponte.mrd_flt_chapa` + `escada._dimensiona_multi` no main (via #55) | ✅ sim |
| D75 | #56 (`feat/ifc-export-bim`) | 00-index:70 | Merge `e4a7918` 07-22 21:58Z; diff +82 `ifc_map.py` +55 `build_galpao.py` +71 `test_ifc_map.py` | `ifc_map.py` no main: `ifc_tipo(nome)` com assert C00→Column, VIGA_ROLAMENTO→Beam, TERCA→Member… e docstring com as 8 categorias (IfcColumn/Beam/Member/Plate/Footing/Pile/Covering/MechanicalFastener) | ✅ sim |
| D76 | #57/#59 (`feat/bridge-headless` + `chore/headless-para-main`) | 00-index:71 | #57 merge `f0026ae` em branch `feat/ifc-export-bim` (não ancestral de main); conteúdo na main via #59 (`5863532` 07-23 00:15Z) | `rodar_projeto.py:210-217 montar_modelo(…, headless=None)`: "None (default) tenta o BRIDGE… e, se ele não responder, cai automaticamente para o FREECADCMD HEADLESS"; `_ship_build_src` (D65) no mesmo fluxo | ✅ sim (com nota do caminho #57→#59) |
| D77 | #58 (`feat/ifc-emissor-puro`) | 00-index:72 | Merge `e2f235c` 07-22 22:10Z; diff +98 `modelo_neutro.py` +167 `ifc_emit.py` + `requirements.txt` (ifcopenshell) | `modelo_neutro.py` + `ifc_emit.py` no main; `rodar_projeto.py:528-540` importa `ifc_emit` e chama `emitir_ifc_do_spec` quando `ifcopenshell` disponível | ✅ sim |
| D78 | #60 (`feat/ifc-secundarios`) | 00-index:73 | Merge `495b594` 07-23 00:15Z; diff +151 `modelo_neutro.py` +55 `ifc_emit.py` + `test_ifc_secundarios_xcheck.py` | **Nome `secundarios_lineares` NÃO existe**; funções reais: `tercas()`, `girts()`, `tirantes_parede()`, `contrav_cobertura()`, `frame_completo()` em `modelo_neutro.py`; emissor `_perfil_ifc` em `ifc_emit.py` | ⚠️ sim, **com correção de nome** |
| D79 | #61 (`feat/modelo-analitico`) | 00-index:74 | Merge `ea48acf` 07-23 00:15Z; diff +82 `ifc_emit.py` +52 `galpao_portico.py` +38 `modelo_neutro.py` +18 `rodar_projeto.py` +88 `test_modelo_analitico.py` | **Módulo `modelo_analitico.py` NÃO existe no disco/main (só o teste)**; implementação real: função `galpao_portico.modelo_analitico()` + `ifc_emit.emitir_ifc_analitico` / `emitir_ifc_analitico_do_spec` (emite `IfcStructuralAnalysisModel`/`IfcStructuralPointConnection` — ifc_emit.py:535-548) + `rodar_projeto.py:533-534` → `{slug}.ifc` e `{slug}_analitico.ifc` em `EXPORT_DIR/ifc/` | ⚠️ sim, **com fallback** (nome real = função + emissores; corrigir 00-index:74 e 05-glossary:46 que citam o módulo inexistente) |

**Datas (task-3):** todos os 7 PRs merged 2026-07-22T21:58Z → 2026-07-23T00:15Z; 831 testes verdes conforme 00-index:67 (não re-verificado — contagem de suíte).

**Nota para o todo 15:** D74–D79 reconstruíveis (3 plenas: D74/D75/D77; 2 com correção: D76 via #57→#59, D78 nome real; 1 com fallback: D79 sem módulo). A reconstrução deve citar os nomes reais de função/arquivo, não os nomes do 00-index.

---

## 6. Vereditos por categoria (resumo)

| Categoria | ok | corrigir | obsoleto | faltante | não verificado |
|---|---|---|---|---|---|
| Fases (24 blocos de 03-phases) | 17 | 6 (placeholders `<6a>/<6b>/<6c>`, "Hatch", "17 módulos", "ATUAL") | 1 (bloco ATUAL/PR #1) | **1 (S19)** | 0 |
| Decisões (presença D1–D73) | 73 presentes | — | — | **D74–D79** | — |
| Decisões spot-check (10) | 10 | 0 (2 nomes de D78/D79 corrigidos na reconstrução) | 0 | 0 | 0 |
| Threads (26 itens T#) | 15 | 1 (T6 texto "Hatch") | 8 (T1, T2, T3, T14, T19, T20, T21 + T16/T4 parciais) | 0 | 1 (T5) |
| Datas (11 blocos 00-index) | 8 | 3 (00-index:150 "sem commit"; itens "NÃO mergeado/PENDENTE" em 2 blocos) | 0 | 0 | 0 |

**Threads com status divergente: 10** (§3). **Inconsistência Hatch×SvgHatch resolvida pelo código: "SvgHatch"** (techdraw_exec.py:1247) — D40 e 05-glossary:34 corretos; 03-phases:151 e 06-open-threads:364 errados. **D74–D79: reconstruíveis** (3 plenas, 2 com correção de nome, 1 com fallback).

---

## 7. PATCH LIST — formato exato (aplicação futura no ledger task-5; NÃO editado agora)

`| <arquivo>:<linha-origem-do-ledger> | <palavra-chave do sujeito> | <veredito> | task-9 |`

### 03-phases (fases)

| 03-phases:150-153 | CutSurfaceDisplay="Hatch" | corrigir — código usa "SvgHatch" (techdraw_exec.py:1247); alinhar ao D40 | task-9 |
| 03-phases:106 | Commit <6c> | corrigir — commit real 820b0e0 (07-10) | task-9 |
| 03-phases:123 | Commit <6b> | corrigir — commit real 21d9941 (07-10) | task-9 |
| 03-phases:140 | Commit <fase6a> | corrigir — commit real 5fd4003 (07-10) | task-9 |
| 03-phases:260-263 | ATUAL Handoff / PR #1 ainda aberto | obsoleto — PR #1 MERGED 4fde82b (07-07); bloco histórico, não "ATUAL" | task-9 |
| 03-phases:324-325 | 17 módulos matemáticos | corrigir — 18 itens listados; defasado (≈53 módulos hoje) | task-9 |
| 03-phases:(sem bloco) | S19 PRs #55–#61 | faltante — nenhum bloco em 03-phases; só 00-index:66-75 (todo 14) | task-9 |
| 03-phases:(sem bloco) | S20–S42 PRs #81–#171 | faltante — arco pós-S18 sem blocos de fase (todo 14) | task-9 |

### 04-decisions (spot-check + presença)

| 04-decisions:408-417 | D52 frame2d sinal UDL | ok — f_loc = k·d − fef + montagem += (frame2d.py:149/192) | task-9 |
| 04-decisions:509-516 | D63 _camada_na_ponta | ok — estaca_profunda.py:116, 3 métodos | task-9 |
| 04-decisions:519-524 | D64 _matar_processo_freecad | ok — rodar_projeto.py:331 + reuso 6 verticais | task-9 |
| 04-decisions:541-588 | D67 perfis.cantoneira | ok — perfis.py:66 | task-9 |
| 04-decisions:125 | D40 SvgHatch | ok — código decide: techdraw_exec.py:1247 "SvgHatch" (desmente 03-phases:151/06:364) | task-9 |
| 04-decisions:432-437 | D54 _janela_band | ok — projeto_spec.py:631 + wizard.py:279 | task-9 |
| 04-decisions:600-605 | D69 marcas_peca/Q09M/PE14 | ok — 4 módulos no main | task-9 |
| 04-decisions:608-614 | D70 montagem/PE16 | ok — montagem.py no main | task-9 |
| 04-decisions:617-620 | D71 DOWN_Y/GUT_Y | ok — max(COL_SEC[0], TAPERED_MODEL["h_joelho"]) via _col_d_beiral; DOWN_Y +40 confere | task-9 |
| 04-decisions:629-633 | D73 mrd_flt_chapa/patamar | ok — console_ponte.py:38 + test_console_flt/test_escada_patamar | task-9 |
| 04-decisions:(sem header) | D74–D79 | faltante — grep ## D74..D79 vazio; reconstrução no todo 15 (evidência §5) | task-9 |

### 06-open-threads (threads)

| 06-open-threads:9-17 | T21 merge PR #54 | obsoleto — #54 MERGED (18:40Z 22/07); conteúdo na main via #55 | task-9 |
| 06-open-threads:19-30 | T20 merge PR #49 | obsoleto — #49 MERGED (15:57Z 22/07); conteúdo na main via #51 | task-9 |
| 06-open-threads:32-48 | T19 merge PR #47 | obsoleto — #47 MERGED (4625aed 22/07) | task-9 |
| 06-open-threads:358-368 | T6 CutSurfaceDisplay="Hatch" | corrigir — código: "SvgHatch" (techdraw_exec.py:1247) | task-9 |
| 06-open-threads:333-334 | T1 PR #1 aguarda merge | obsoleto — MERGED 4fde82b (07-07) | task-9 |
| 06-open-threads:336-337 | T2 divergência 87 commits | obsoleto — resolvida via merge #1 | task-9 |
| 06-open-threads:339-340 | T3 backlog ponte | obsoleto — D39/D47 (rodas motoras, NBR 8400, fadiga Anexo K) | task-9 |
| 06-open-threads:352-356 | T4 fadiga ponte "sinalizada" | obsoleto — automatizada (D10/D16/D62); demais itens ok/não re-verificado | task-9 |
| 06-open-threads:173-174 | T14 PR #12 NÃO mergeado | obsoleto — MERGED 4165652 (07-18); 2º caso-referência resolvido (T15/D57) | task-9 |
| 06-open-threads:127-142 | T16 latente telha_tipo "só rótulo" | obsoleto — projeto_spec.py:769-775 liga tipo→perfil (gate 7); fuzz não re-verificado | task-9 |
| 06-open-threads:380-381 | T5 settings.local.json | não verificado (fonte ausente — config local do usuário) | task-9 |

### 00-index (datas)

| 00-index:149-153 | "sem commit — árvore de trabalho" (2026-07-17) | corrigir — 6 commits 07-17 existem (8bd725f/bb36b9b/e4e3468/63451f1/…); contradiz 06-open-threads:145 | task-9 |
| 00-index:173 | PR #12 (15 commits, NÃO mergeado) | obsoleto — MERGED 4165652 (07-18) | task-9 |
| 00-index:184-187 | 2º caso-referência PENDENTE | obsoleto — resolvido em T15/D57 (validacao_alonso) | task-9 |
| 00-index:228 | PENDENTE gate humano: merge PR #5 | obsoleto — MERGED 50df273 (07-14) | task-9 |
| 00-index:243 | PENDENTE gate humano: merge PR #1+#4 | obsoleto — MERGED 4fde82b (07-07) / aa02180 (07-10) | task-9 |
| 00-index:74 | PR #61 modelo_analitico (módulo) | corrigir — módulo inexistente; implementação real: galpao_portico.modelo_analitico() + ifc_emit.emitir_ifc_analitico* (fallback p/ todo 15) | task-9 |
| 00-index:73 | PR #60 secundarios_lineares | corrigir — nome inexistente; funções reais tercas/girts/tirantes_parede/contrav_cobertura/frame_completo (modelo_neutro.py) | task-9 |

---

## 8. Nada foi editado além desta evidência

- Wiki (7 arquivos): **NÃO editados** (git status limpo exceto `.omo/` não rastreado — esta evidência)
- Ledger task-5: **NÃO editado** (PATCH LIST acima é a entrega)
- Código: **NÃO modificado**; NENHUM commit realizado

---

## 9. QA interno (registro)

1. **5 vereditos conferidos com comandos git reais:**
   - T21 (#54): `gh pr view 54 --json state,mergedAt` → MERGED 18:40:36Z + `git merge-base --is-ancestor 44ad268 main` → False + conteúdo (`mrd_flt_chapa`) presente no main → veredito "obsoleto" sustentado por 3 comandos
   - T20 (#49): `gh pr view 49` → MERGED 15:57:26Z + `git ls-tree main -- tools/` → run_build_suite.ps1 presente → "obsoleto"
   - S19 faltante: `grep "S19\|#5[5-9]\|#6[0-1]" 03-phases.md` → 0 ocorrências + `git log --merges` mostra #55–#61 → "faltante"
   - D79: `git ls-tree main -- framework/galpao_fw/modelo_analitico.py` → vazio + `git diff ea48acf^1 ea48acf --stat` → test_modelo_analitico.py (não módulo) + `git grep IfcStructuralAnalysisModel` em ifc_emit.py:535-548 → fallback
   - D40/Hatch: `grep CutSurfaceDisplay techdraw_exec.py` → `"SvgHatch"` (1247) vs wiki "Hatch" (03-phases:151, 06:364) → código decide
2. **Decisões citadas sem correspondência exata** → "corrigir" com sugestão: D78 `secundarios_lineares` (nome real: 5 funções) e D79 `modelo_analitico.py` (módulo inexistente; função `galpao_portico.modelo_analitico()` + emissores em ifc_emit) — ambos na PATCH LIST e no §5.
3. **Contagens de suíte não re-verificadas** (831/723/702/714/1281/770+511/245): tomadas da timeline task-3 e dos próprios blocos — sem pytest re-executado (não faz parte do escopo de cross-check estrutural).
4. **OneDrive:** nenhuma falha de "arquivo em uso" ocorreu (1ª tentativa OK em todas as leituras).
5. **Não fabricado:** T5 (config local), itens 3–5 do T15 (parecer humano), bitola da cantoneira (T17) → marcados "não verificado (fonte ausente)" ou "decisão do usuário".
