# Task F3 — QA FINAL INDEPENDENTE (agent-executed) da revisão da wiki (gate F3)

- **Data:** 2026-08-11
- **Executor:** Sisyphus-Junior (todo F3 do plano revisao-wiki — QA puro, agent-executed)
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (branch `docs/revisao-wiki-2026-08-11`, HEAD `069f9ab`)
- **Wiki (7 arquivos canônicos):** `framework\galpao_fw\wiki\00-index.md`, `01-architecture.md`, `02-test-tree.md`, `03-phases.md`, `04-decisions.md`, `05-glossary.md`, `06-open-threads.md`
- **Entradas:** `task-5-revisao-wiki.md` (ledger 430 claims, vereditos finais), `task-18-revisao-wiki.md` (log da suíte), `task-19-revisao-wiki.md` (links finais)
- **Python (caminho absoluto):** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic\framework\galpao_fw\.venv\Scripts\python.exe` (venv do repo principal)
- **Scripts (temporários em `%TEMP%\opencode\`, read-only):** `taskF3_links.py` (cópia do padrão task-19/task-6), `taskF3_select.py` (parse do ledger + sorteio); saídas brutas: `taskF3_links_result.json`, `taskF3_select.json`
- **Regras respeitadas:** NÃO re-rodou a suíte (verificou a evidência task-18 por leitura); NÃO corrigiu nada (QA puro); NÃO usou arquivo:linha do ledger como verdade (re-localização por CONTEÚDO/sujeito); NENHUM commit; UTF-8 explícito (escrita utf-8 sem BOM).

---

## 1. Evidência task-18 — VERIFICADA (por leitura, NÃO re-rodada)

Leitura integral de `task-18-revisao-wiki.md` (156 linhas). Itens conferidos:

| item da evidência | valor registrado | consistência interna | veredito |
|---|---|---|---|
| Contagens da re-rodada (§2) | coletados 1374 / deselecionados 21 / **selecionados 1353 / passed 1340 / failed 1 / skipped 15** / errored 0 | linhas-resumo verbatim citadas (lane 1: `1 failed, 1097 passed, 15 skipped, 15 deselected`; lane 2: `243 passed, 6 deselected`) — 1097+243=1340 ✓; 15+0=15 ✓; 1+0=1 ✓; 1110+243=1353 ✓ | ok |
| Exit codes (§1/§2) | runner = **5** (lane 1 rc 5 por 1 falha; lane 2 rc 4 por erro de uso F2 — OR binário); lane 2 manual = **0** | igual ao baseline task-2 (5/0) ✓ | ok |
| Baseline vs re-rodada (§3) | delta ZERO em todas as contagens (1353/1340/1/15); duração 703,26s → 567,04s (variância, contagens idênticas) | tabela completa com deltas 0 | ok |
| Falha única (F1) | `tests/test_validacao.py::test_dossie_unico` — `ModuleNotFoundError: No module named 'fitz'` (`dossie.py:105`) | pré-existente, idêntica ao task-2, NÃO corrigida — documentada como finding | ok |
| F2 (glob lane 2) | `tests/test_fase*.py` não expandido pelo PowerShell → `no tests ran in 0.00s`; contornado com 23 caminhos explícitos | reproduzido e documentado (pré-existente) | ok |
| F3 (correções wiki §5A) | 3 divergências de contagem em `03-phases.md` corrigidas (C1 60→153; C2 1040→1353/1340/1/15; C3 ~1281/~28→1353/23) com re-verificação pós-correção | git diff de 1 arquivo; regra QA "corrigir a wiki, nunca o código" respeitada | ok |
| F4 (smoke) | smoke não completou (timeout 5 min); `freecadcmd --version` 197ms; pre-flight 7/7 limpo; "smoke 7/7" = claim histórico, não re-verificado — registrado como finding NÃO bloqueante | documentado por caso | ok |
| Escopo (§7) | nenhum código/teste corrigido; nenhum commit; wiki editada só na regra QA (§5A); `-m build` não rodado (claim de inventário) | consistente com o resto da evidência | ok |
| QA interno (§8) | contagens conferidas com logs brutos (`%TEMP%\opencode\suite_task18_*.log`); 23 arquivos da lane pesada listados | procedimento documentado | ok |

**Conclusão §1: evidência task-18 VERIFICADA (exit codes, contagens e falhas pré-existentes/divergência/parcial documentadas; divergências de wiki corrigidas com regra QA e re-verificadas).** NÃO re-rodada, conforme regra F3.

## 2. Links `[[…]]` — RE-RODADOS (script read-only padrão task-19/task-6)

Comando: `python %TEMP%\opencode\taskF3_links.py` (7 canônicos; extração `re.findall(r'\[\[(.*?)\]\]')` linha a linha, spans de código ignorados, âncoras por token inicial exato ou título completo, fallback `arquivo+".md"`).

**Resultado: total 229 / ok 229 / quebrado-ancla 0 / quebrado-arquivo 0 / externo 0 — ZERO quebrados ✓**

| arquivo | total | ok | quebrados |
|---|---|---|---|
| 00-index.md | 80 | 80 | 0 |
| 01-architecture.md | 2 | 2 | 0 |
| 02-test-tree.md | 7 | 7 | 0 |
| 03-phases.md | 34 | 34 | 0 |
| 04-decisions.md | 50 | 50 | 0 |
| 05-glossary.md | 2 | 2 | 0 |
| 06-open-threads.md | 54 | 54 | 0 |

Distribuição por arquivo **idêntica** à do task-19 (80/2/7/34/50/2/54) e total 229/229 ✓ — confirma o check 2 do gate (229/229 esperado, conferido).

## 3. Sorteio REGISTRADO (cego — registrado ANTES de qualquer grep/abertura de código)

**Método:** parse mecânico do ledger task-5 (430 claims) + seleção determinística com `random.Random(SEED)`, SEED = **20260811** (data do gate, anotada). O script `taskF3_select.py` lê SOMENTE o ledger e sorteia; não toca código.

**Sanidade do parser:** contagens globais do ledger re-parsed = **ok 123 / corrigir 49 / obsoleto 13 / não verificado 1 / pendente 244 / TOTAL 430** — idêntico ao parse do task-19 e ao task-5-update ✓.

**Pools por arquivo (ok | corrigir+obsoleto):**

| arquivo | ok | corrigir+obsoleto |
|---|---|---|
| 00-index.md | 18 | 22 |
| 01-architecture.md | 29 | 3 |
| 02-test-tree.md | 21 | 4 |
| 03-phases.md | 26 | 13 |
| 04-decisions.md | 11 | **0** |
| 05-glossary.md | 12 | 1 |
| 06-open-threads.md | 6 | 19 |

**Log do sorteio (saída verbatim do script):**
```
tentativa 1: arquivos sorteados = ['05-glossary.md', '03-phases.md', '04-decisions.md', '01-architecture.md', '02-test-tree.md']
  -> algum arquivo sem os 2 pools; re-sorteando conjunto...
tentativa 2: arquivos sorteados = ['03-phases.md', '06-open-threads.md', '05-glossary.md', '01-architecture.md', '02-test-tree.md']
```
- Tentativa 1 descartada porque **04-decisions.md tem 0 claims corrigir/obsoleto** (pool vazio) — impossível 1 ok + 1 corrigir por arquivo com ela sorteada.
- Tentativa 2: os 5 arquivos sorteados têm os 2 pools → sorteio concluído SEM relaxação (≤3 tentativas; nenhuma relaxação de cota necessária).
- **Cota final: 5 claims do pool "ok" + 5 claims do pool "corrigir/obsoleto" = 10/10 ✓** (≥5 e ≥5 atingido sem relaxação).

**5 arquivos sorteados (REGISTRADOS ANTES de verificação):** `03-phases.md`, `06-open-threads.md`, `05-glossary.md`, `01-architecture.md`, `02-test-tree.md`.

**10 claims sorteadas (registradas ANTES de verificação — número do ledger = ordinal global do parse; ref = arquivo:linha original do ledger):**

| # | id ledger | ref ledger | sujeito (resumo) | pool | veredito no ledger |
|---|---|---|---|---|---|
| 1 | 180 | 03-phases:65-66 | 6.7 vento→tesoura: `w_vento` auto NBR 6123; uplift (+0,9·w_dead, sem Q); `test_fase67_vento_tesoura` (7) | ok | ok (task-7) |
| 2 | 200 | 03-phases:150-153 | `techdraw_exec._secao_ligacao`: DrawViewSection crop compound, plano pelo centro, `CutSurfaceDisplay="Hatch"`; descarta se vazia; wire `_detalhe_ligacao` (VLIG_SEC_*) | corrigir/obsoleto | corrigir (task-9) |
| 3 | 385 | 06-open-threads:37-44 | T19 FECHADO: `montagem.py` (SI, headless); 10 passos Bellei 7.6.4; γimp=1,10 (4.2.6); T=F/(n·cosα); γf3=1,30 (4.9.6.5); prumo max(H/500,5mm) teto 25mm (12.3.3.1.1); "A CONFIRMAR"; PE16_MONTAGEM (última folha 15/15, 4 quadros) | ok | ok (task-7) |
| 4 | 425 | 06-open-threads:358-368 | T6 — Projeto executivo 2D (FECHADO 2026-07-09): 9 pranchas + PE10–14 + memorial PDF; smoke 4/4; PR #4 aberto; `_callout_fab`; corte seccionado RESOLVIDO (`CutSurfaceDisplay="Hatch"`); glyph AWS RESOLVIDO | corrigir/obsoleto | corrigir (task-9) |
| 5 | 354 | 05-glossary:34 | DrawViewSection / corte seccionado; headless FreeCAD 1.1 (`CutSurfaceDisplay="SvgHatch"`); `VLIG_SEC_*` | ok | ok (task-7) |
| 6 | 366 | 05-glossary:46 | Interop BIM/IFC4 Físico & Analítico: `modelo_neutro.py` + `ifc_emit.py` (ifcopenshell) + `ifc_map.py` + `modelo_analitico.py`; gera `galpao.ifc`/`galpao_analitico.ifc` | corrigir/obsoleto | corrigir (task-7) |
| 7 | 88 | 01-architecture:11 | Cadeia 2: `estabilidade_b1b2` — 2ª ordem MAES (rigidez 0,8 + forças nocionais) → Nsd/Msd/Vsd amplificados; K=1 (NBR 8800 4.9.6.2) | ok | ok (task-7) |
| 8 | 104 | 01-architecture:33 | Tabela Interop BIM: `modelo_neutro`, `ifc_emit`, `ifc_map`, `modelo_analitico` — IFC4 Physical (ISO 16739-1) / IFC4 Structural | corrigir/obsoleto | corrigir (task-7) |
| 9 | 138 | 02-test-tree:23 | `gusset_ligacao`: Whitmore (30° AISC, FLAG não-NBR); reusa `check_nbr8800.chi_compressao`; `ligacoes.block_shear_linha`; `ligacoes.solda`; adota {t_mm, bw_mm} | ok | ok (task-7) |
| 10 | 128 | 02-test-tree:13 | `redimensionamento`: sob H/300 adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez); `_peso_rel` não altera seleção | corrigir/obsoleto | corrigir (task-8) |

## 4. Verificação das 10 claims contra a fonte

Regra aplicada: claim "ok" → verificado o claim ORIGINAL (texto atual da wiki re-localizado por conteúdo, deve ler ok). Claim "corrigir/obsoleto" → verificado o TEXTO CORRIGIDO da wiki (re-localizado por CONTEÚDO via grep do sujeito nos arquivos atuais; linha do ledger NUNCA usada como verdade) contra a fonte.

### 4.1 [180] ok — `03-phases.md:65-66` (vento→tesoura) — **VERIFICAÇÃO OK**

Re-localizado por conteúdo: `03-phases.md:65-66` atual = "**6.7 vento→tesoura:** `w_vento` auto NBR 6123; **bug de sinal do uplift corrigido** (`+0,9·w_dead`, sem Q). `test_fase67_vento_tesoura` (7)." (idêntico ao claim do ledger).

Fonte (código):
- `tesoura.py:162-163` — `_P_vento_zonas`: "NBR 6123 Tabela 5, barlavento EF / sotavento GH" (vento automático por água); `tesoura.py:279-282` — `cfg["w_vento_zonas"]=(w_barl,w_sot) -> NBR 6123 Tabela 5 por agua, ENVELOPE`; ausente → escalar back-compat.
- `tesoura.py:152-156` — `_gamma_g_dead`: sucção (wv≤0) → **0,9** (peso favorável); pressão → 1,4; `tesoura.py:166-167,181` — combinação `1,4 w_vento + gamma_g w_dead, com gamma_g=0,9` (uplift, peso favorável); `tesoura.py:248-250` — "A sobrecarga Q NAO estabiliza" (sem Q no uplift).
- `tests/test_fase67_vento_tesoura.py` — **7 funções `def test_`** (linhas 47-120: succao_auto_negativa, casa_net_q_bay, override_honrado, gate_cita_nbr6123, combo_uplift_gravidade_opoe_vento, uplift_reverte_banzo_inferior, prismatico_sem_w_vento_auto) = "(7)" ✓.

### 4.2 [200] corrigir (task-9) — `techdraw_exec._secao_ligacao` — **VERIFICAÇÃO OK**

Correção task-9: `CutSurfaceDisplay="Hatch"` **não existe** como enum; código usa `"SvgHatch"` (techdraw_exec.py:1247) — "alinhar ao D40".

Texto CORRIGIDO re-localizado por conteúdo (grep `_secao_ligacao` nos 7 canônicos): `03-phases.md:150-153` atual = "`techdraw_exec._secao_ligacao`: DrawViewSection do crop compound, plano de corte pelo centro, `CutSurfaceDisplay="SvgHatch"` (material cortado). Descarta a seção se vazia (arestas=0 → não engana o guard, `mne-1`). Wire em `_detalhe_ligacao` (view extra `VLIG_SEC_*`, sem mexer na elevação/callouts)." Também `04-decisions.md:125` (D40) e `06-open-threads.md:384` idem.

Fonte (código):
- `techdraw_exec.py:1214` — `def _secao_ligacao(...)` existe.
- `techdraw_exec.py:1234` — `doc.addObject("TechDraw::DrawViewSection", "VLIG_SEC_" + base)` (VLIG_SEC_*).
- `techdraw_exec.py:1237-1238` — `SectionOrigin` no centro (ou `origem` explícita = centro da peça detalhada; docstring 1221-1226: "PASSE O CENTRO DA PECA DETALHADA... o compound inclui os perfis conectados").
- `techdraw_exec.py:1243-1247` — enum válido `['Hide','Color','SvgHatch','PatHatch']`; `sec.CutSurfaceDisplay = "SvgHatch"` ("Hatch" NÃO existe) ✓.
- Wire: `techdraw_exec.py:1343` — `sec = _secao_ligacao(doc, page, base, feat, v, _nrm, esc, _sx, _sy, origem=c0)` DENTRO de `_detalhe_ligacao` (def em 1266); comentário 1336-1337: corta pelo centro da peça, não do compound.
- "Descarta se vazia": docstring `1218-1219` "Retorna a view, ou None se o corte nao produzir arestas (vazio -> nao engana o guard)"; guard final `detalhes_secoes` (03-phases:154-155; smoke exige ≥1 e nenhuma vazia) — consistente com o texto corrigido.
- Aplicação confirmada no git: `git show a96c63d^:…/03-phases.md` = `CutSurfaceDisplay="Hatch"` → `git show a96c63d:…` = `CutSurfaceDisplay="SvgHatch"` (correção feita de propósito no commit 2 do plano).

### 4.3 [385] ok — `06-open-threads.md:37-44` (T19/montagem.py) — **VERIFICAÇÃO OK**

Re-localizado por conteúdo: `06-open-threads.md:48-60` (T19) = "Módulo puro `montagem.py` (SI, headless). Sequência de montagem (10 passos Bellei 7.6.4)... coef. de impacto γimp=1,10 (NBR 8800 4.2.6)... T = F / (n·cosα)... γf3 = 1,30 (NBR 8800 4.9.6.5)... max(H/500, 5 mm), teto 25 mm global (NBR 8800 12.3.3.1.1)... degradam para 'A CONFIRMAR'... Prancha nova **PE16_MONTAGEM** (última folha 15/15) com 4 quadros + notas NBR 8800 / AISC 303" (idêntico ao claim).

Fonte (código):
- `montagem.py:149-177` — `sequencia_montagem()` retorna **10 passos numerados** (Bellei 7.6.4 nas etapas 2/4/8; NBR 8800 12.3.2.x).
- `montagem.py:50` — `GAMMA_CONSTRUCAO = 1.30 # NBR 8800 4.9.6.5`; `montagem.py:51` — `COEF_IMPACTO_MONTAGEM = 1.10 # default A CONFIRMAR (NBR 8800 4.2.6)`.
- `montagem.py:123-125` — "T.cos(a) por cabo -> T = F/(n.cos a)".
- `montagem.py:57-61` — prumo `max(H/500 ; 5 mm)`, desvio global `25 mm` (12.3.3.1.1).
- "A CONFIRMAR" (graceful degradation): múltiplas ocorrências (linhas 88, 101-102, 111, 125, 143, 185, 197-199, 206-207, 214).
- `techdraw_exec.py:1704` — `_nova_prancha(doc, "PE16_MONTAGEM", ...)`; `techdraw_exec.py:1835-1840` — "PLANO DE MONTAGEM por ultimo (apendice de PROCEDIMENTO, apos os quadros)" (última folha ✓); blocos de texto/tabelas na prancha (4 quadros: sequência, içamento/guindaste, estai/vento, prumo — estrutura visível nas linhas 1713-1755).

### 4.4 [425] corrigir (task-9) — T6 (06:358-368) — **VERIFICAÇÃO OK**

Correção task-9: linha do T6 com `CutSurfaceDisplay="Hatch"` ≠ código (`"SvgHatch"`, techdraw_exec.py:1247) + status do PR #4 ("aberto" → verificado MERGED).

Texto CORRIGIDO re-localizado por conteúdo (grep `^## T6 `): `06-open-threads.md:378-388`:
- `:379` — "**PR #4** ~~aberto~~ → **MERGED** (`aa02180`, 10/07; conferido 2026-08-11, task-9)".
- `:381-385` — "corte seccionado... `techdraw_exec._secao_ligacao` adiciona um corte hachurado (`CutSurfaceDisplay="SvgHatch"`) a cada detalhe de ligação, sob smoke (`detalhes_secoes`, arestas>0)".
- `:386-388` — glyph AWS: "DrawWeldSymbol é só-GUI; substituído por `DrawViewSymbol`+SVG inline headless (arrow/other/both AWS A2.4)".

Fonte:
- `git log --oneline -1 aa02180` → `aa02180 Merge pull request #4 from JHenriquesss/revisao/homologacao-12-modulos`; `git show -s --format="%ci"` → `2026-07-09 22:26:42 -0300` (= 2026-07-10 01:26 UTC → "10/07" correto em UTC) — PR #4 MERGED confirmado.
- `techdraw_exec.py:1247` — `CutSurfaceDisplay = "SvgHatch"` ✓ (corrigido no T6).
- `git show a96c63d:…/06-open-threads.md` → texto já com `CutSurfaceDisplay="SvgHatch"` (correção aplicada no commit 2).

### 4.5 [354] ok — `05-glossary.md:34` (DrawViewSection) — **VERIFICAÇÃO OK**

Re-localizado por conteúdo: `05-glossary.md:34` = "**DrawViewSection / corte seccionado** — vista de corte hachurada do TechDraw (material cortado). Constrói headless no FreeCAD 1.1 (`CutSurfaceDisplay="SvgHatch"`). `VLIG_SEC_*` = corte do detalhe de ligação." (idêntico ao claim).

Fonte (código): `techdraw_exec.py:1216-1217` (corte hachurado), `1228-1229` ("o blocker historico (T6, 'failed to create section CS' headless) foi resolvido no FreeCAD 1.1 - a secao constroi via freecadcmd/freecad.exe"), `1247` (SvgHatch), `1234` (VLIG_SEC_*).

### 4.6 [366] corrigir (task-7) — interop BIM (05:46) — **VERIFICAÇÃO OK**

Correção task-7/9: `modelo_analitico` NÃO é módulo próprio (não existe `modelo_analitico.py`) — é a função `galpao_portico.modelo_analitico()` + `ifc_emit.emitir_ifc_analitico*`.

Texto CORRIGIDO re-localizado por conteúdo (grep `modelo_neutro|ifc_emit|ifc_map|modelo_analitico`): `05-glossary.md:46` = "...Modelo neutro de dados (`modelo_neutro.py`) + emissor IFC4 puro-Python (`ifc_emit.py` via `ifcopenshell`) e mapeamento semântico (`ifc_map.py`), gerando `galpao.ifc` (BIM físico) e `galpao_analitico.ifc` (`IfcStructuralAnalysisModel` para SAP2000/Eberick/Robot) direto do cálculo sem GUI. **Corrigido 2026-08-11 (task-7/9):** o modelo analítico NÃO é módulo próprio — é a função `galpao_portico.modelo_analitico()` + o emissor `ifc_emit.emitir_ifc_analitico` / `emitir_ifc_analitico_do_spec` (grava `{slug}_analitico.ifc` em EXPORT_DIR/ifc/; não existe `modelo_analitico.py`)." (verbatim com a marca de correção).

Fonte (código):
- `galpao_portico.py:305` — `def modelo_analitico():` (modelo analítico 2D do pórtico) — função, não módulo.
- `ifc_emit.py:533` — `def emitir_ifc_analitico(...)`; `:632` — `def emitir_ifc_analitico_do_spec(...)`.
- `rodar_projeto.py:525-536` — wiring: `EM.emitir_ifc_do_spec(spec, {slug}.ifc)` + `EM.emitir_ifc_analitico_do_spec(spec, {slug}_analitico.ifc)` em `EXPORT_DIR/ifc/`, direto do cálculo sem FreeCAD.
- `ifc_emit.py:535-548` — `IfcStructuralAnalysisModel` / `IfcStructuralPointConnection` / `IfcBoundaryNodeCondition` / `IfcStructuralCurveMember`.
- `modelo_neutro.py`, `ifc_emit.py`, `ifc_map.py` existem; `modelo_analitico.py` **não existe** (`Get-ChildItem -Filter "modelo_analitico*"` = vazio) ✓.

### 4.7 [88] ok — `01-architecture.md:11` (Cadeia 2 estabilidade_b1b2) — **VERIFICAÇÃO OK**

Re-localizado por conteúdo: `01-architecture.md:11` = "2. `estabilidade_b1b2` — 2ª ordem **MAES** (rigidez 0,8 + forças nocionais) → Nsd/Msd/Vsd amplificados. Permite **K=1** (NBR 8800 4.9.6.2)." (idêntico ao claim).

Fonte (código):
- `estabilidade_b1b2.py:2,7` — "Analise de 2a ordem APROXIMADA (MAES, NBR 8800 Anexo D)"; `:4` — "calcula B1 (local) e B2 (global), e amplifica Msd/Nsd/Vsd".
- `:144-145` — `m = B1 * mf_nt[e][im] + B2 * mf_lt[e][im]`; `n = sgn * (mf_nt[e][iN] + B2 * mf_lt[e][iN])` (amplificação por grupo).
- `:242` — `Efac = 0.8 if reduziu else 1.0` (rigidez 0,8).
- `:46,74,171` — `FN_FRAC = 0.003` + `_forca_nocional(combo)` (forças nocionais).
- K=1 (4.9.6.2): `check_nbr8800.py:235` — "Com o MAES, usa-se K=1,0 (4.9.6.2)"; `REVISAO-PORTICO.md:177,269` — "Ne = π²EI/L² com L = comprimento real da barra e K = 1 (4.9.6.2)"; `rodar_galpao.py:367,376` — "(K=1; gov ...)".

### 4.8 [104] corrigir (task-7) — Tabela Interop BIM (01:33) — **VERIFICAÇÃO OK**

Texto CORRIGIDO re-localizado por conteúdo (grep `Interop|modelo_analitico|ifc_map`): `01-architecture.md:33` = "| Interoperabilidade BIM | **`modelo_neutro`**, **`ifc_emit`**, **`ifc_map`** + analítico via `galpao_portico.modelo_analitico()` e `ifc_emit.emitir_ifc_analitico` (não é módulo próprio) | IFC4 Physical (ISO 16739-1) / IFC4 Structural |".

Fonte (código): mesmos do 4.6 — `modelo_neutro.py`/`ifc_emit.py`/`ifc_map.py` existem; `galpao_portico.py:305` função; `ifc_emit.py:533` emissor; sem `modelo_analitico.py` ✓. "IFC4 Structural" confirmado pelas entidades IfcStructural* em `ifc_emit.py:535-548`.

### 4.9 [138] ok — `02-test-tree.md:23` (gusset_ligacao) — **VERIFICAÇÃO OK**

Re-localizado por conteúdo: `02-test-tree.md:23` = "`gusset_ligacao` | chapa de gusset compondo primitivos: tração escoamento/ruptura na **largura de Whitmore** (espalhamento 30° AISC, FLAG não-NBR análogo T-stub); compressão da faixa efetiva (reusa `check_nbr8800.chi_compressao`); block shear (reusa `ligacoes.block_shear_linha`); solda filete (reusa `ligacoes.solda`, perna mín `solda_filete_minimo`); esforço=tração da diagonal de contravento; adota {t_mm, bw_mm}" (idêntico ao claim).

Fonte (código):
- `gusset_ligacao.py:9-10,37-40` — "Whitmore = espalhamento de 30° a partir da 1ª fixação (CONVENÇÃO AISC/Thornton — não é item da NBR)" / `def largura_whitmore(w0, Lc, ang_graus=30.0)`.
- `:30` — `from check_nbr8800 import chi_compressao, E, GA1`; `:61` — `chi = chi_compressao(lam)`.
- `:29` — `import ligacoes as LG`; `:129` — `bs = LG.block_shear_linha(...)`; `:187` — `ref = LG.solda({...})` (mesmo Fw_Rd, verificado no teste `:183-189`).
- `:144` — `res["adotado"] = {"t_mm": ..., "bw_mm": ...}` ✓.

### 4.10 [128] corrigir (task-8) — `redimensionamento` (02:13) — **FALHA**

Correção task-8 aplicada e verificada: `_peso_rel` → `_peso` (task-8 evidência linha 200: "`_peso_rel` (02-test-tree:13) NÃO existe — real: `_peso(cols_perfil, raf)` em redimensionamento.py:66"). Texto atual `02-test-tree.md:13` = "...sob **H/300** adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez); `_peso` não altera seleção (ordem da escada)".

**Parte corrigida — VERIFICAÇÃO OK:** `redimensionamento.py:66` — `def _peso(cols_perfil, raf)` existe; `_peso` só alimenta o dict de resultado (`avalia()` linha 105: `"peso": _peso(...)`) e NÃO participa da seleção gulosa (`melhor()` 108-148 sobe perfis por interação, não por peso) → "`_peso` não altera seleção (ordem da escada)" ✓.

**Parte NÃO corrigida — FALHA (texto ainda errado contra a fonte):** a asserção "sob H/300 adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez)" é **falsa no código atual**:

1. Execução empírica do selftest do próprio módulo (`python redimensionamento.py` — caminho canônico, mesmo do task-8 "selftest via __main__"):
   ```
   REDIMENSIONAMENTO - 1 vao(s) - otimizacao gulosa
   Flecha: 12,8mm <= H/300 = 20,0mm
   Interacao pior: 0,85
   Perfis: Col 0: HEA200 / Col 1: HEA200 / Viga: HEA180
   B2max = 1,004  →  PASSA
   Aprovado: cols=['HEA200','HEA200'] raf=HEA180
   ```
   → o caso-referência 20×10 **PASSA no seed HEA200/HEA180** (drift 12,8 ≤ H/300=20,0; interação 0,85 ≤ 1) — HEA200/HEA180 **NÃO reprovam por rigidez**; nada adota HEB200/IPE300.
2. Comentário do próprio pipeline (fonte): `rodar_galpao.py:288` — "Referencia 20x10 ja passa no seed -> inalterada" (o gate 7 documenta exatamente o contrário da wiki).
3. Varredura suplementar de cenários com drift governando (spans 20/25/30, mesmos defaults): NENHUM adota exatamente HEB200 col + IPE300 raf (20→HEB240/HEA240+IPE360; 25→HEB280/HEB260+IPE450; 30→IPE500/HEB300+IPE500).
4. Origem histórica da asserção: o texto foi escrito no estado do código de `603bce3` (2026-07), quando o ladder era `("HEB200","IPE300")` e o default escalava; o código evoluiu (fixes da auditoria 8.1-8.36 — commits `dad7b87`/`741221d`/`11cb25a`) e a wiki não foi atualizada nesse ponto (só `_peso_rel`→`_peso` foi corrigido).

**Conclusão 4.10: claim [128] = FALHA — o texto corrigido da wiki ainda contém asserção falsa sobre o comportamento de `redimensionamento`.**

## 5. Tabela final (claim | pool | veredito no ledger | verificação | evidência)

| # | claim (id/ref ledger) | pool | veredito no ledger | verificação | evidência (comando/arquivo:linha) |
|---|---|---|---|---|---|
| 1 | 180 — 03-phases:65-66 | ok | ok (task-7) | **ok** | grep `w_vento`/`test_fase67`; `tesoura.py:152-167,248-250,279-282`; `tests/test_fase67_vento_tesoura.py` (7 defs) |
| 2 | 200 — 03-phases:150-153 | corrigir/obsoleto | corrigir (task-9) | **ok** | grep `_secao_ligacao`; texto corrigido `03-phases.md:150-153` (`"SvgHatch"`); `techdraw_exec.py:1214,1234,1237-1238,1243-1247,1343`; `git show a96c63d^/a96c63d` (Hatch→SvgHatch) |
| 3 | 385 — 06:37-44 | ok | ok (task-7) | **ok** | grep T19; `06-open-threads.md:48-60`; `montagem.py:50-51,57-61,123-125,149-177`; `techdraw_exec.py:1704,1835-1840` |
| 4 | 425 — 06:358-368 | corrigir/obsoleto | corrigir (task-9) | **ok** | grep `^## T6`; texto corrigido `06:379,381-385` (`PR #4 MERGED aa02180`, `"SvgHatch"`); `git log/show aa02180` (merge PR #4, 07-09 22:26 -0300 = 10/07 UTC); `techdraw_exec.py:1247` |
| 5 | 354 — 05-glossary:34 | ok | ok (task-7) | **ok** | grep `DrawViewSection`; `05-glossary.md:34`; `techdraw_exec.py:1216-1217,1228-1229,1234,1247` |
| 6 | 366 — 05-glossary:46 | corrigir/obsoleto | corrigir (task-7) | **ok** | grep `modelo_neutro|ifc_emit|ifc_map`; texto corrigido `05-glossary.md:46` ("não existe modelo_analitico.py"); `galpao_portico.py:305`; `ifc_emit.py:533,632`; `rodar_projeto.py:525-536`; glob `modelo_analitico*` = vazio |
| 7 | 88 — 01-architecture:11 | ok | ok (task-7) | **ok** | grep `estabilidade_b1b2`; `01-architecture.md:11`; `estabilidade_b1b2.py:2-4,46,74,144-145,171,242`; `check_nbr8800.py:235` (K=1 4.9.6.2) |
| 8 | 104 — 01-architecture:33 | corrigir/obsoleto | corrigir (task-7) | **ok** | grep `Interop|modelo_analitico`; texto corrigido `01-architecture.md:33` ("não é módulo próprio"); `galpao_portico.py:305`; `ifc_emit.py:533,535-548` |
| 9 | 138 — 02-test-tree:23 | ok | ok (task-7) | **ok** | grep `gusset_ligacao`; `02-test-tree.md:23`; `gusset_ligacao.py:9-10,29-30,37-40,61,121,129,144,183-189` |
| 10 | 128 — 02-test-tree:13 | corrigir/obsoleto | corrigir (task-8) | **FALHA** | execução `python redimensionamento.py` → adota HEA200/HEA180, drift 12,8 ≤ H/300=20,0, PASSA; `rodar_galpao.py:288` "Referencia 20x10 ja passa no seed"; sweep spans 20/25/30 nunca adota HEB200/IPE300; texto wiki 02:13 mantém "adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez)" |

**Resumo: 9/10 verificações ok; 1 FALHA (claim 128, `02-test-tree.md:13`).**

## 6. Achados adicionais (registrados, NÃO corrigidos — QA puro)

1. **[FALHA F3] `02-test-tree.md:13`:** asserção "sob H/300 adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez)" desatualizada/falsa no código atual — o caso-referência 20×10 passa no seed (HEA200/HEA180, drift 12,8 ≤ 20,0 mm) e nenhum cenário testado adota HEB200/IPE300. Remédio (com o orquestrador): reescrever a célula, ex. "parte do seed HEA200/HEA180; referência 20×10 passa no seed (drift ≤ H/300)" — a parte `_peso` já está correta.
2. **[informativo — código, fora do escopo da wiki] `rodar_galpao.py:286`:** comentário do Gate 7 diz "flecha<=H/150" mas o limite real é H/300 (`redimensionamento.py:16` `LIM_FLECHA = gp.EAVE / 300.0`; `:80`). Comentário de código desatualizado (o limite mudou em `d0638b8`), não citado pela wiki — sem ação necessária na wiki.
3. **[confirmação] Sorteio com 04-decisions no conjunto (tentativa 1) inviável** — pool corrigir/obsoleto vazio naquele arquivo; re-sorteio registrado (tentativa 2) sem relaxação; cota 5/5 atingida.

## 7. Escopo respeitado

- Suíte **NÃO re-rodada** (verificação da evidência task-18 por leitura, §1) ✓
- **NADA corrigido** (wiki, README, código — zero edições; `git status` do worktree: apenas evidências `.omo/` untracked) ✓
- Linha do ledger usada apenas como referência; re-localização por conteúdo/grep do sujeito nos arquivos atuais ✓
- Exceção de remoção: NÃO aplicável (nenhum sujeito removido dos arquivos — todos os sujeitos sorteados existem; as correções verificadas foram reescritas in place, confirmadas por `git show` antes/depois) ✓
- Verificações contra a fonte do tipo certo: código (módulos/funções/wiring, 9 claims), git (datas/PRs: PR #4 `aa02180`), suíte (contagens via evidência task-18) ✓
- UTF-8 explícito nesta evidência (escrita utf-8, sem BOM); scripts com leitura utf-8-sig / saída utf-8 ✓
- NENHUM commit ✓

## 8. VERDICTO EXPLÍCITO

**VERDICT: REJECT**

**Falhas:**
- **F3-FALHA-1 (única, bloqueante):** claim [128] (pool corrigir/obsoleto, veredito no ledger "corrigir (task-8)", `02-test-tree.md:13`): o texto corrigido da wiki ainda contém a asserção falsa "sob H/300 adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez)". Evidência: execução do selftest do módulo (`python redimensionamento.py`) adota HEA200/HEA180 com drift 12,8 mm ≤ H/300 = 20,0 mm (PASSA); comentário do pipeline `rodar_galpao.py:288` ("Referencia 20x10 ja passa no seed -> inalterada"); sweep spans 20/25/30 nunca produz HEB200/IPE300. A correção `_peso_rel` → `_peso` (parte sinalizada pelo task-8) está aplicada e correta, mas a célula como um todo permanece "ainda-errado" contra a fonte (regra F3: claim corrigido ainda-errado = FALHA). A asserção é resíduo do estado de código de 2026-07 (`603bce3`), não atualizado nas reescritas.

**Demais gates do F3: PASSARAM** — evidência task-18 verificada (contagens/exit/findings documentados); links 229/229 zero quebrados (re-rodado); sorteio registrado (seed 20260811, 5 arquivos, cota 5/5 sem relaxação); 9/10 claims verificadas ok contra a fonte (código/git).

**Recomendação ao orquestrador:** aplicar o remédio do achado 1 do §6 em `02-test-tree.md:13` (reescrever a célula de `redimensionamento` sem a asserção HEB200/IPE300) e re-executar o F3 para o conjunto corrigido.

---

## 9. Re-execução do gate (2026-08-11) — correção da FALHA aplicada e re-verificada

- **Motivo:** orquestrador aplicou o remédio da F3-FALHA-1 em `02-test-tree.md:13`; o F3 foi re-executado para o conjunto corrigido (QA puro — NADA editado por este gate, apenas a evidência).
- **Regras:** wiki NÃO editada por este gate (correção já aplicada pelo orquestrador); NÃO commitado; UTF-8 explícito.

### 9.1 Célula corrigida — antes/depois (git diff do worktree, aplicado fora deste gate)

```
-| `redimensionamento` | roda escada completa; sob **H/300** adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez); `_peso` não altera seleção (ordem da escada) |
+| `redimensionamento` | roda escada completa; seed 20×10 sob **H/300** PASSA com HEA200/HEA180 (drift 12,8 ≤ 20,0 mm; interação 0,85); `_peso` não altera seleção (ordem da escada) |
```

A asserção falsa ("adota HEB200/IPE300 / HEA200/HEA180 reprova por rigidez") foi substituída pela descrição da saída real do selftest.

### 9.2 Selftest RE-RODADO (confirmar a célula contra a fonte)

Comando: `python redimensionamento.py` (venv do repo principal por caminho absoluto; cwd `worktree\framework\galpao_fw`).

```
REDIMENSIONAMENTO - 1 vao(s) - otimizacao gulosa
Flecha: 12,8mm <= H/300 = 20,0mm
Interacao pior: 0,85
Perfis:
  Col 0: HEA200
  Col 1: HEA200
  Viga: HEA180
  B2max = 1,004
  PASSA
Aprovado: cols=['HEA200', 'HEA200'] raf=HEA180
```

### 9.3 Re-verificação da célula corrigida (02-test-tree.md:13) — claim [128]: FALHA → **CORRIGIDA**

Conferência número a número da célula atual contra a saída do selftest:

| célula corrigida (02-test-tree.md:13) | saída do selftest | bate? |
|---|---|---|
| "roda escada completa" | loop guloso `melhor()` executa a escada de perfis (redimensionamento.py:108-148) | ✓ |
| "seed 20×10" | caso-referência 1 vão (SPANS=[20], EAVE=6m → H/300 = 20,0 mm) | ✓ |
| "sob **H/300** PASSA" | `PASSA`; `Flecha: 12,8mm <= H/300 = 20,0mm` | ✓ |
| "HEA200/HEA180" | `Col 0: HEA200 / Col 1: HEA200 / Viga: HEA180` | ✓ |
| "drift 12,8 ≤ 20,0 mm" | `12,8mm <= 20,0mm` | ✓ |
| "interação 0,85" | `Interacao pior: 0,85` | ✓ |
| "`_peso` não altera seleção (ordem da escada)" | `_peso()` só alimenta o dict de `avalia()` (linha 105); `melhor()` sobe perfis por interação (linhas 127-148), nunca por peso (verificado na 1ª rodada, §4.10) | ✓ |

Nenhum número da célula contradiz a fonte; a asserção falsa do estado 2026-07 (`603bce3`) foi removida. **Claim [128] re-verificado: CORRIGIDO.**

### 9.4 Demais pontos da verificação anterior — NENHUM sem tratamento

Re-leitura da evidência F3 original (§1–§6):
- **Evidência task-18** (§1): verificada ok — nada a tratar (contagens/exit/findings documentados). Sem re-ação.
- **Links 229/229** (§2): ok — sem tratamento.
- **Sorteio** (§3): ok, cota 5/5 sem relaxação — sem tratamento.
- **Claims 1–9** (§4.1–4.9, tabela §5): todas verificadas **ok** contra a fonte (código/git) — sem tratamento.
- **Achado 2 do §6** (`rodar_galpao.py:286` — comentário de código "flecha<=H/150" vs limite real H/300): registrado como **informativo de código, FORA do escopo da wiki** (a wiki diz H/300, correto) — NÃO era falha do gate e NÃO bloqueia. Continua registrado como observação para o orquestrador, sem ação na wiki.
- **Achado 3 do §6** (re-sorteio por pool vazio em 04-decisions): confirmação procedural — sem tratamento.
- **F3-FALHA-1 (claim [128])**: a ÚNICA falha bloqueante do gate — **corrigida e re-verificada (§9.3)** ✓.

### 9.5 Veredicto final

**VERDICT: APPROVE**

- A falha bloqueante do gate (F3-FALHA-1: célula de `redimensionamento` em `02-test-tree.md:13`) foi corrigida pelo orquestrador e **re-verificada contra a fonte** (selftest re-rodado: 12,8 ≤ 20,0 mm, interação 0,85, HEA200/HEA180, PASSA — todos os números da célula corrigida batem).
- Nenhuma outra falha da verificação anterior ficou sem tratamento (única bloqueante = F3-FALHA-1; demais claims 9/9 ok; achados remanescentes informativos, fora do escopo da wiki).
- Este veredicto **substitui o REJECT da §8** (que permanece como registro histórico da 1ª rodada).

**Estado final do gate F3:** evidência task-18 verificada ✓ · links 229/229 zero quebrados ✓ · sorteio registrado (seed 20260811, 5 arquivos, cota 5/5) ✓ · 10/10 claims verificadas (9 ok na 1ª rodada + claim 128 corrigida e re-verificada) ✓ → **VERDICT: APPROVE**.
