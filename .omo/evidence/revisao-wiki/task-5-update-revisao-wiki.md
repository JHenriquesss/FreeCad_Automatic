# Task 5-update — Verdictos aplicados ao ledger task-5 (serialização 7→8→9)

- **Data:** 2026-08-11
- **Executor:** Atlas (agente principal — regra do plano, linha 71: "o ledger é atualizado pelo agente principal após integrar cada evidência"; 3 subagentes não executaram, o script determinístico foi rodado pelo orquestrador)
- **Método:** script Python determinístico `apply_ledger_patches.py` (ordem ESTRITA 7→8→9; matching por (arquivo, linha) + tokens de keyword + containment/overlap de ranges; idempotente; UTF-8)
- **Arquivo alterado:** `.omo/evidence/revisao-wiki/task-5-revisao-wiki.md` (somente a coluna `veredito` e 5ª coluna `evidência` quando sugestão)

## Resultado numérico

| Fonte | Patches lidos | Aplicados | Não-localizados | N/A |
|---|---|---|---|---|
| task-7 (módulos/funções/wiring) | 138 (134 + 3 headers) | 134 | 1 | 3 (headers) |
| task-8 (test-tree/contagens) | 123 (41 corrigir + 82 faltante) | 41 | 0 | 82 (faltante = alvo wiki 02-test-tree.md:126 — cobertura para o todo 13, NÃO linhas do ledger) |
| task-9 (fases/decisões/threads/datas) | 37 (34 + 3 sem-ref) | 30 | 4 | 3 (sem-ref: S19/S20-S42/D74-D79 "sem bloco" → registrados como faltante para todos 14/15) |
| **Total** | **298** | **205** | **5** | **88** |

## Estado final do ledger (430 claims)

- **ok:** 123 | **corrigir:** 49 | **obsoleto:** 13 | **não verificado:** 1 | **faltante:** 0 | **pendente:** 244
- Soma = 430 ✓; zero linhas quebradas (verificação por regex); sugestões preservadas na 5ª coluna (`task-7: <sugestão>` etc.)
- 244 "pendente" = claims não cobertos por nenhum patch dos todos 7-9 (ex.: normas/arquivo-ref sem cross-check específico) — F3 sorteia dos pools ok/corrigir/obsoleto, que estão íntegros

## Não-localizados (5) — justificativa

1. **task-7: `02-test-tree:3 | _selftest por módulo | ok`** — 2 candidatos na mesma ref; resolvido por score de tokens (2/3 no claim `_selftest()` vs 0 no claim de não-regressão) e APLICADO manualmente via script.
2. **task-9: `03-phases:140 | Commit <fase6a>`** — linha 140 da wiki (placeholder de commit) não tem claim próprio no ledger (claims cobrem 137-139 e 141-142). Correção (commit real `5fd4003`) flui via evidência task-9 para o todo 14.
3. **task-9: `00-index:149-153 | "sem commit — árvore de trabalho" (2026-07-17)`** — bloco wiki sem claim no ledger (claims em 146-147 e 154-156). Correção (6 commits reais existem, 8bd725f etc.) flui via task-9 para o todo 11.
4. **task-9: `00-index:228 | PENDENTE gate humano: merge PR #5`** — sem claim no ledger; PR #5 MERGED 50df273 (07-14). Correção flui via task-9 para o todo 11.
5. **task-9: `00-index:243 | PENDENTE gate humano: merge PR #1+#4`** — sem claim no ledger; PRs MERGED 4fde82b/aa02180. Correção flui via task-9 para o todo 11.

## Garantias

- Nenhum arquivo da wiki editado; nenhum código alterado; nenhum commit.
- Ledger íntegro para F3 (pools ok/corrigir/obsoleto mecanicamente legíveis).
- Relatório JSON bruto: `task-5-update-report.json` (mesma pasta).
