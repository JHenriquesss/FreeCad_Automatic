# Task 11 — Atualização de 00-index.md (bloco Estado atual 2026-08-11 + correções) — revisão da wiki

- **Data:** 2026-08-11
- **Executor:** Sisyphus-Junior (todo 11 do plano de revisão da wiki)
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (branch `docs/revisao-wiki-2026-08-11`)
- **Arquivo editado (ÚNICO da wiki):** `framework\galpao_fw\wiki\00-index.md` — **292 → 352 linhas** (+60), UTF-8 estrito válido, sem BOM (padrão original preservado; verificado byte a byte)
- **Autoridades usadas:** task-1 (135 módulos), task-2 (1353/1340/1/15), task-3 (arco git/PRs), task-5 + task-5-update (ledger 430 claims), task-6 (links), task-7 (módulos/funções), task-8 (contagens), task-9 (datas/status), task-15 (D74–D79), task-16 (T22/T41 + nota memory) — NENHUM veredito inventado
- **NENHUM outro arquivo da wiki editado; NENHUM commit; NENHUM código modificado; nenhum arquivo novo (evidência à parte em `.omo\evidence\`)**

---

## 1. Bloco novo "## Estado atual (2026-08-11) — Revisão da wiki" (linha 18)

Inserido logo após o header/quote, ANTES do bloco "Estado atual (2026-08-03)" (agora linha 60). Conteúdo:
- **Data + escopo:** 7 arquivos (00–06) × código (135 módulos, task-1) × suíte (`tools/run_tests.py`: 1353 selecionados / 1340 passed / 1 failed [F1 fitz] / 15 skipped, task-2) × git/GitHub (171 PRs MERGED, task-3).
- **Log de discrepâncias:** contagem total **68** (ledger task-5: 123 ok / 49 corrigir / 13 obsoleto / 1 não verificado / 5 não-localizados registrados no task-5-update); **top 15 por severidade** (obsoleto → erro-factual; ordem determinística por arquivo:linha; **declarado "truncado em 15 de 68"**): 00-index:173, 184-187, 228, 243; 03-phases:232, 260-263; 06:T21/T20/T19/T16/T14/T1/T3/T4; 00-index:149-153, 00-index:3.
- **Arco pós-2026-08-04** reconstruído do git (task-3): **S41** PRs #154–#161 (fixes desenho/pranchas + planta elétrica, merged 2026-08-09) e **S42** PRs #162–#171 (10 módulos de engenharia, merged 2026-08-09); HEAD `6358157` = merge #171; hiato 04→09/08.

## 2. Correções aplicadas (com origem task-N)

| # | local | correção | origem |
|---|---|---|---|
| 1 | 00:3 (pitch) | `galpao_turnkey.rodar()` consolida gates + federado; caderno executivo = módulo separado `caderno_turnkey` (via fitz) — não montado por rodar() | task-7:1 |
| 2 | 00:20-21 | ref `memory/*.md`/`sessions/` → "Arco consolidado do git (memory/ NÃO versionado no repo — reconstruído do git em 2026-08-11)" | task-6, task-16 |
| 3 | 00:26 | link quebrado `[[../memory]]` removido (`vertical-concreto` mantido) | task-6 |
| 4 | 00:25-26 | "60 testes" → "153 testes no grupo concreto (17 arquivos; protensão estrita: 31 — 2026-08-11)" | task-8 |
| 5 | 00:29 | "Suíte 1040 green" → "1353 sel / 1340 pass / 1 fail / 15 skip (2026-08-11)" | task-8 |
| 6 | 00:53-58 | "~1281 testes; ~28 pesados" → "1353 selecionados; 23 arquivos pesados (22 test_fase* + test_crashes_wiki07)"; xdist "1281 passed" → "1340 passed (2026-08-11)" | task-8 |
| 7 | 00:61-62 | "a-l 770, m-z 511" → "1353/1340/1/15 (2026-08-11); shards não re-deriváveis" | task-8 |
| 8 | 00:67 | S19 "831 testes verdes" → "1353/1340/1/15 (2026-08-11; 831 na época)" | task-8 |
| 9 | 00:79 | S18 "723" → "1353/1340 (2026-08-11; 723 na época)" | task-8 |
| 10 | 00:83 | PR #49 "714 + 9 build" → "1353/1340 (2026-08-11; 714 na época); build atual 18 ocorrências em 17 arquivos" | task-8 |
| 11 | 00:88 | PR #48 "9 passed em 9" + nota "build atual: 18 ocorrências em 17 arquivos" | task-8 |
| 12 | 00:111 | S17 "702" → "1353/1340 (2026-08-11; 702 na época)" | task-8 |
| 13 | 00:130 | S16 "643 (652−9)" → "1353/1340 (2026-08-11; 643 na época)" | task-8 |
| 14 | 00:147 | PR #44 "7 commits, 643 testes" → "643 na época [1353/1340 em 2026-08-11]" | task-8 |
| 15 | 00:121 | `por_marca` → "funções `prefixo_marca`/`mapa_marcas` (o nome `por_marca` não existe)" | task-7:13 |
| 16 | 00:73 | `secundarios_lineares` → "funções reais `tercas`/`girts`/`tirantes_parede`/`contrav_cobertura`/`frame_completo` (modelo_neutro.py)" | task-7:7, task-9, task-15 D78 |
| 17 | 00:74 | `modelo_analitico` (módulo) → "`galpao_portico.modelo_analitico()` + `ifc_emit.emitir_ifc_analitico` (não é módulo próprio)" | task-7:8, task-9, task-15 D79 |
| 18 | 00:150 | "sem commit — árvore de trabalho" FALSO → "6 commits reais (8bd725f/bb36b9b/e4e3468/63451f1, 2026-07-17 16:15–16:16)" | task-9, task-5-update #3 |
| 19 | 00:173 | "PR #12 NÃO mergeado" → "MERGED `4165652` 2026-07-18"; "256 passed" → "na época (1353/1340 em 2026-08-11)" | task-9 |
| 20 | 00:184-187 | "ONDE PARAMOS / plano `check_trelica_estatica`" → SUPERADO: nunca implementado; 2º caso resolvido em T15/D57 (`validacao_alonso`) | task-7:22, task-9 |
| 21 | 00:213 | "245 passed" → "na época (1353/1340 em 2026-08-11); smoke 7/7 (casos confirmados, não re-rodado)" | task-8 |
| 22 | 00:228 | "PENDENTE gate humano: merge PR #5" → "MERGED `50df273`, 2026-07-14" | task-9, task-5-update #4 |
| 23 | 00:232-234 | "Restou `neve` (não escolhido)" → "`neve` wired desde D51 (2026-07-16)" | task-7:24 |
| 24 | 00:243 | "PENDENTE merge PR #1+#4" → "MERGED `4fde82b` 07-07 / `aa02180` 07-10" | task-9, task-5-update #5 |
| 25 | 00:13 (TOC) | T41 adicionado à linha 06-open-threads ("T41 revisão da wiki (2026-08-11), T40…, T40b…, T22 S19 IFC/BIM, T21…, backlog") — T22 já citado, âncora criada pelo task-16 | task-16, task-6 |
| 26 | 00:296 | NOVA entrada `last-consolidated: 2026-08-11` acima da 2026-08-04: revisão (7 arquivos, ledger 123/49/13/1/5, D74–D79, T22/T41, arco S41/S42, memory não versionado) + suíte 1353/1340/1/15 | task-2/3/15/16 |
| 27 | 00:304-312 (entrada 08-04) | "em memory/*.md" → "(memory/ NÃO versionado — arco reconstruído do git em 2026-08-11)"; "Fonte do arco = auto-memória (sessions/ tem só 2 logs antigos)" → "git (reconstrução 2026-08-11; sessions/ não existe no repo)"; "1281 passed (-n auto, 11m14s)" → "2026-08-04 = 1281 passed; 2026-08-11 = 1340 passed (F1 fitz + 15 skipped)" | task-6, task-8 |
| 28 | 00:313 (entrada 07-22) | "723 testes non-build + 9 build" → "na época (2026-08-11: 1353 non-build + 18 build)" | task-8 |
| 29 | 00:324 (entrada 07-17) | "SEM COMMIT" → "6 commits reais (8bd725f/bb36b9b/e4e3468/63451f1, 07-17)" | task-9 |

**Blocos históricos antigos NÃO reescritos** fora das correções acima (regra: só erro factual com evidência dos tasks 7-9). 07-16 "ONDE PARAMOS" e demais snapshots históricos preservados.

## 3. QA interno (obrigatório)

1. **Links re-rodados** (script `%TEMP%\opencode\task11_links.py`, padrão task-6 `re.findall(r'\[\[(.*?)\]\]')`, ignorando spans de código): **80 links, 80 ok, 0 quebrados**. D74–D79 resolvem (task-15 criou as âncoras em 04-decisions); `[[06-open-threads#T22]]` resolve (task-16); `[[../memory]]` removido (0 ocorrências).
2. **Prose refs memory/:** 3 ocorrências restantes = as 3 NOTAS de "memory/ NÃO versionado" (bloco novo, last-consolidated 08-11, entrada 08-04) — intencionais, não ponteiros.
3. **Encoding:** UTF-8 estrito válido (decoder estrito sem erro), sem BOM (preservado do original); 352 linhas.
4. **Claims do bloco novo:** todos com origem nas evidências (task-1/2/3/5/5-update/6/7/8/9/15/16) — nenhum inventado.
5. **OneDrive:** nenhum erro de "arquivo em uso" ocorreu (1ª tentativa OK em todas as escritas).

## 4. Resumo executivo

- Bloco "Estado atual (2026-08-11) — Revisão da wiki" no topo do histórico (linha 18), acima do bloco 2026-08-03 (linha 60).
- 68 discrepâncias registradas (49 corrigir + 13 obsoleto + 1 não verificado + 5 não-localizados), top 15 listadas, truncado declarado.
- 29 correções aplicadas (12 contagens de teste → 1353/1340/1/15; 4 status de merge PENDENTE → MERGED; 3 nomes de módulo/função corrigidos; 1 claim "sem commit" falso; 1 neve; 1 pitch caderno_turnkey; refs memory resolvidas; TOC +T41; last-consolidated novo + 2 entradas históricas com erro factual corrigido).
- QA de links: **80/80 ok, zero quebrados**; UTF-8 válido; nenhum arquivo novo; nenhum commit.
- Evidência em: `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt\.omo\evidence\revisao-wiki\task-11-revisao-wiki.md` (UTF-8)
