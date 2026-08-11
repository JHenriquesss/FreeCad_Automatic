# Task 16 — Glossário (05) + Open threads (06): termos faltantes, correções e status reais

- **Data:** 2026-08-11
- **Executor:** Sisyphus-Junior (todo 16 do plano de revisão da wiki)
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (branch `docs/revisao-wiki-2026-08-11`)
- **Arquivos editados (ÚNICOS, 2):** `framework\galpao_fw\wiki\05-glossary.md` (47 → 70 linhas) e `framework\galpao_fw\wiki\06-open-threads.md` (385 → 405 linhas)
- **Autoridades usadas:** task-1 (inventário 135 módulos — critério determinístico), task-6 (links/memory), task-7 (vereditos glossário), task-9 (status threads), task-3 (arco S41/S42) — NENHUM veredito inventado
- **Formato:** UTF-8 explícito (sem BOM, como o original; conferido — ver QA §7)

---

## 1. 05-glossary.md — correções de definição

| item | linha | antes | depois (correção) | fonte |
|---|---|---|---|---|
| 1 | 46 (Interoperabilidade BIM/IFC4) | citava o módulo `modelo_analitico.py` como gerador do `galpao_analitico.ifc` | **`modelo_analitico.py` NÃO existe** (task-7 item 125; task-9 D79: `git ls-tree main` vazio, só `tests/test_modelo_analitico.py`); corrigido para: função `galpao_portico.modelo_analitico()` + emissor `ifc_emit.emitir_ifc_analitico` / `emitir_ifc_analitico_do_spec` (grava `{slug}_analitico.ifc` em EXPORT_DIR/ifc/) | task-7:125, task-9 §5 |

- **05:34 (`CutSurfaceDisplay="SvgHatch"`) CONFERIDO — JÁ CORRETO** (task-7 item 120: "bate exato" com `techdraw_exec.py:1247`); nenhuma alteração feita.

## 2. 05-glossary.md — termos ADICIONADOS (23, critério determinístico)

**Critério:** conceito central do inventário (task-1) com módulo/arquivo/função REAL e sem verbete; termo sem módulo → NÃO adicionado. Todos os 23 abaixo têm módulo ou função real verificados no task-1:

| # | termo | módulo/função real (task-1) | wired/orphan |
|---|---|---|---|
| 1 | Turnkey | `galpao_turnkey.py` (rodar) | wired |
| 2 | Vertical / disciplina | `galpao_concreto.py`, `galpao_eletrico.py`, `galpao_seguranca_incendio.py`, `galpao_hidraulica.py`, `galpao_climatizacao.py` | wired |
| 3 | Caderno único | `caderno_turnkey.py` | orphan (consumido pelo turnkey) |
| 4 | Modelo federado | `build_federado.py` (despachado por fonte via `rodar_projeto._ship_build_src`); `galpao_turnkey.montar_3d_federado` | orphan (runtime) |
| 5 | Clash AABB | `galpao_turnkey.checa_interferencia_federada` / `_clash_esperado` | wired |
| 6 | Compatibilização | `compatibilizacao.py` (BCF-like) | orphan |
| 7 | BIM (IFC4 físico) | `modelo_neutro.py` + `ifc_emit.py` + `ifc_map.py` | wired |
| 8 | Modelo neutro | `modelo_neutro.py` (funções reais `tercas()/girts()/tirantes_parede()/contrav_cobertura()/frame_completo()` — nome `secundarios_lineares` não existe, task-7) | wired |
| 9 | Emissor IFC | `ifc_emit.py` (emitir_ifc_do_spec / emitir_ifc_analitico / emitir_ifc_analitico_do_spec) | wired |
| 10 | IFC4 Structural (analítico) | `galpao_portico.modelo_analitico()` + `ifc_emit.emitir_ifc_analitico` (NÃO há módulo) | wired |
| 11 | Pacote legal | `pacote_legal.py` | orphan |
| 12 | Caderno de encargos | `caderno_encargos.py` | orphan |
| 13 | Cronograma 4D | `cronograma.py` (CPM + curva S) | orphan |
| 14 | Orçamento 5D | `orcamento.py` (ABC + BDI, SINAPI ref.) | orphan |
| 15 | Terraplenagem | `terraplenagem.py` | orphan |
| 16 | Esgoto / reuso | `esgoto_reuso.py` (NBR 7229 + Rippl) | orphan |
| 17 | Fotovoltaico | `fotovoltaico.py` (NBR 16690) | orphan |
| 18 | Geotecnia SPT | `geotecnia_spt.py` (N/50, Terzaghi, FS=3) | wired |
| 19 | Piso industrial | `piso_industrial.py` (Westergaard) + `desenho_piso.py` | wired |
| 20 | Protensão | `viga_protendida.py` + `perdas_protensao_nbr6118.py` | wired |
| 21 | Wizard | `wizard.py` (construir_spec) | wired |
| 22 | Pilar de concreto | `pilar_concreto.py` | wired |
| 23 | Viga de concreto | `viga_concreto.py` (+ `torcao_nbr6118.py`) | wired |

**Nenhum termo adicionado sem módulo real** (ex.: shed, multi-vão, neve não foram adicionados — sem módulo dedicado ou já cobertos).

## 3. 06-open-threads.md — status das threads atualizados (task-9 = autoridade)

### 3.1 Status reais aplicados (append-only; ABERTO riscado `~~…~~` e anexada nota de resolução)

| thread | status ANTES (wiki) | status DEPOIS (task-9 + git/gh conferido) |
|---|---|---|
| T21 | ABERTO (decisão do usuário): merge PR #54 | ✅ RESOLVIDO — #54 MERGED 18:40:36Z 22/07 (merge `44ad268` em branch do CI, não ancestral da main); conteúdo na main via PR #55 (`83570c9`, cherry-pick; `mrd_flt_chapa`/`_dimensiona_multi` presentes) |
| T20 | ABERTO: merge PR #49 | ✅ RESOLVIDO — #49 MERGED 15:57:26Z 22/07; conteúdo na main via PR #51 (`1f4c38f`; scripts em `<worktree>\tools\`) |
| T19 | ABERTO: merge PR #47 | ✅ RESOLVIDO — #47 MERGED (`4625aed`, 22/07 15:12Z) |
| T14 | PR #12 aberto, NÃO mergeado; 2º caso PENDENTE | ✅ PR #12 MERGED (`4165652`, 18/07); 2º caso-referência RESOLVIDO em T15 (D57/`validacao_alonso`) |
| T16 | latente `telha_tipo` só rótulo | ~~latente~~ → **RESOLVIDO depois**: `projeto_spec.py:769-775` liga `cobertura.telha_tipo` ao perfil verificado no gate 7; multi-vão heterogêneo e fuzz = **não re-verificados** (sem inventar) |
| T1 | PR #1 aguarda merge | ✅ RESOLVIDO — #1 MERGED (`4fde82b`, 07/07/2026) |
| T2 | Divergência local↔origin (87 commits) | ✅ RESOLVIDO — sincronizada via merge do #1 |
| T3 | Backlog ponte estendido | ✅ RESOLVIDO — rodas motoras + NBR 8400 (D39), fadiga Anexo K automatizada (D10/D16/D62); crane 100% homologado |
| T4 | fadiga Anexo K "sinalizada, não automatizada" | ~~item~~ → **RESOLVIDO** (automatizada; categoria de detalhe = INPUT); demais itens mantidos |
| T5 | settings.local.json não criado | **NÃO VERIFICADO (fonte ausente)** — config local do usuário, sem fonte no repo (task-9) |

### 3.2 Threads com status mantidos (conferidos OK pelo task-9)

T40 (✅ #150), T40b (parcial, sem suspeita), T18 (MERGED), T17 (decisão do usuário legítima — não verificável em git), T15 (MERGED; itens 3–5 = parecer humano, não verificado), T13, T12, T11, T10, T9, T8, T7 (OK), T6-hist, HANDOFF, Lacunas de escopo (OK).

### 3.3 Threads NOVAS (2)

| thread | conteúdo |
|---|---|
| **T22 — Sessão 19 (2026-07-22/23): IFC/BIM — PRs #55–#61 MERGED** | Criada porque 00-index:75 e o TOC (00:13) já referenciavam `[[06-open-threads#T22]]` sem a thread existir (achado task-6). Conteúdo real do git/task-9: #55 cherry-pick gaps+wiki; #56 exportador IFC4 via `ifc_map.py`; #57/#59 montar_modelo auto-fallback headless; #58 modelo_neutro + emissor puro; #60 secundários lineares (funções reais, não `secundarios_lineares`); #61 modelo analítico (função + emissores, não módulo). |
| **T41 — Revisão da wiki (2026-08-11)** | memory/ não versionado + wiki revisada (ver 00-index "Estado atual") + trabalho pós-S40 (S41/S42, PRs #154–#171) documentado (task-3: todos MERGED 2026-08-09; HEAD `6358157` = merge #171). |

> Ordem no arquivo: T41 no topo (mais recente), T22 entre T40b e T21 (ordem cronológica descendente mantida).

## 4. Refs `memory/*.md` corrigidas (task-6)

| linha (original) | ref | ação |
|---|---|---|
| 06:4 | `memory/janela-dupla-conversao-aberta.md` | marcada *(memory/ não versionado — arco reconstruído do git em 2026-08-11)* |
| 06:7 | `memory/saturacao-silenciosa-padrao.md` | idem |
| 06:340 | memory `crane-module-backlog` (T3) | idem + thread marcada RESOLVIDO |
| 00:20/26/250 | (00-index) | **NÃO editado** — fora de escopo (todo 11; registrado para o todo 11) |

## 5. Âncoras `[[ ]]` quebradas DENTRO de 06 corrigidas (bônus do task-6, escopo próprio do arquivo)

| linha | link | correção |
|---|---|---|
| 06:137 | `[[04-decisions#D53?]]` | `[[04-decisions#D53]]` (removido o `?` residual) |
| 06:359 | `[[03-phases#FECHADA — Projeto executivo 2D]]` (truncado) | título completo com travessão U+2014 igual ao header real (03-phases:218) + "PR #4 aberto" → ~~aberto~~ **MERGED** (`aa02180`, 10/07) |
| 06:364 | `CutSurfaceDisplay="Hatch"` | `"SvgHatch"` (task-7 item 135, task-9; código `techdraw_exec.py:1247` decide) |
| 06:365 | `[[03-phases#FECHADA — Corte seccionado 2D]]` (truncado) | título completo (03-phases:144) |

## 6. QA interno (obrigatório)

1. **Nenhuma thread removida:** grep `^## ` antes (26 headers) × depois (28 headers) — os 26 originais (T40, T40b, T21, T20, T19, T18, T17, T16, T15, T14, T13, T12, HANDOFF, T11, T10, T9, T8, T7, T1, T2, T3, Lacunas de escopo, T4, T6, T5, Resolvidos nesta sessão) continuam presentes, em ordem; +2 novos (T41 no topo, T22 entre T40b e T21).
2. **5 status de thread conferidos contra git/gh (amostra):** `gh pr view` → **#54 MERGED** (18:40:36Z 22/07), **#49 MERGED** (15:57:26Z 22/07), **#47 MERGED** (15:12:38Z 22/07), **#12 MERGED** (11:54:26Z 18/07), **#1 MERGED** (16:29:14Z 07/07) — todos batem com as notas anexadas (T21/T20/T19/T14/T1). (Task-9 já havia conferido #150/#55/#51 com `git merge-base`/`git ls-tree`.)
3. **Nenhum termo de glossário sem módulo real:** os 23 verbetes novos referenciam módulos/funções reais do inventário task-1 (tabela §2); a única correção (§1) substitui um módulo inexistente pelas funções reais.
4. **Encoding UTF-8 explícito:** ambos os arquivos lidos com `Get-Content -Encoding UTF8` → 0 caracteres inválidos; sem BOM (padrão original preservado pelo editor); 05 = 70 linhas, 06 = 405 linhas.
5. **Git:** `git diff --stat` → apenas `05-glossary.md` (+25) e `06-open-threads.md` (+75/−32) tocados por este todo; os outros 4 arquivos wiki modificados no worktree são de todos anteriores do plano (10–15) — **nenhum editado aqui**.
6. **OneDrive:** nenhum erro de "arquivo em uso" (1ª tentativa OK em todas as escritas).

## 7. Garantias

- Nenhuma thread removida; nenhum status inventado (task-9 é a autoridade; T5 e fuzz = "não verificado (fonte ausente)").
- Nenhum outro arquivo da wiki (00–04) editado; NENHUM commit; NENHUM código modificado.
- Únicos arquivos alterados: os 2 alvos do todo + esta evidência (em `.omo\evidence\revisao-wiki\`, não rastreada).

## 8. Entregáveis

- **05:** 23 termos adicionados (com módulo de origem) + 1 definição corrigida (modelo_analitico) + 1 conferida sem alteração (05:34 SvgHatch) — 47 → 70 linhas.
- **06:** 11 threads com status atualizado (T21, T20, T19, T14, T16, T1, T2, T3, T4, T5, T6-texto "Hatch"); 2 threads novas (T22, T41); 3 refs memory corrigidas; 4 âncoras/erros corrigidos — 385 → 405 linhas.
- Alimenta: todo 11 (00-index: TOC/T22 agora existe; memory refs de 00 continuam para o 11), todo 19 (re-varredura de links).
