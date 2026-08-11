# Task 17 — Aplicação das correções do task-10 em README.md (raiz) e COMO-RODAR.md

- **Data:** 2026-08-11
- **Executor:** todo 17 da revisão da wiki
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (HEAD `6358157` = main)
- **Escopo:** aplicar SOMENTE as correções do task-10 nos 2 documentos raiz (README.md, framework/galpao_fw/COMO-RODAR.md). **NENHUM outro arquivo tocado** (wiki/ já atualizada por outros tasks; UPSTREAM.md, tools/README.md, REVISAO-INDICE.md NÃO editados). **NENHUM commit; NENHUM código modificado.**
- **Formato:** UTF-8 puro, sem BOM (bytes iniciais dos 2 arquivos confirmados: README `35,32,70`, COMO-RODAR `35,32,67` — sem EF BB BF).
- **Autoridade:** task-10 (tabela de correções §3, 31 corrigir) + task-4 (ledger, coluna "correto (fonte)") + `rodar_projeto.py` (API real conferida: `calcular` :16, `montar_modelo` :210, `rodar_executivo` :263, `rodar_tudo` :479; `gerar_dxf` NÃO existe).

---

## 1. README.md (raiz) — 12 edições em 9 pontos (12 linhas alteradas + 1 removida + 2 adicionadas)

| # | Linha(s) | Fonte (task-10 §3.1) | Texto novo (resumo) |
|---|---|---|---|
| 1 | 3 | #1 (task-1: 135) | `**53 Python modules**` → `**135 Python modules**` |
| 2 | 10-12 | #2 (REVISAO-INDICE.md:61,:64) + #3 (task-2) | Status: `REVISAO itens 1–49: 47 HOMOLOGADO + 2 PARECER (46, 49)` · `pytest 1353 selecionados / 1340 passed / 1 failed (test_dossie_unico, sem fitz) / 15 skipped` · smoke 7/7 (inalterado — ok) |
| 3 | 27-28 | #4 (rodar_projeto.py:263 → techdraw_exec.py:1907-1908; convenção de caminho rodar_projeto.py:565) | `RP.gerar_dxf(...)` (inexistente) → `RP.montar_modelo(s, 'exports', 'meu_galpao')` + `RP.rodar_executivo(s, 'exports', 'exports/freecad/meu_galpao.FCStd')` |
| 4 | 32 | #5 (grep `save("gate*")` = 40 nomes únicos) | `## Pipeline (23 gates)` → `## Pipeline (40 gates)` (23 = estado 2026-07-08) |
| 5 | 56 | #7 (rodar_galpao.py:156-158; projeto_spec.py:133; PR #12 2026-07-18) | `neve` (stub, não wired) → `neve` (wired desde D51, 2026-07-16) |
| 6 | 61 | #6 (git log cb890b6/e696b84 2026-07-09; Test-Path dxf_vistas.py = NÃO) | `dxf_vistas` removido da célula Geometria/saída (substituído por `techdraw_exec`, já listado) |
| 7 | 68 | #8 (estaca_profunda.py:69 `capacidade_aoki_velloso`) | `estaca (3 métodos)` → `estaca (1 método: Aoki-Velloso)` |
| 8 | 74-76 | #9 (Test-Path pesquisa = NÃO em 2 níveis; PDFs reais no repo) | `verbatim do PDF em pesquisa/` → `verbatim dos PDFs das normas (PDFs no repo: Framework_Galpao_Modulos.pdf na raiz, libraries/standards/gerdau/)` |
| 9 | 77-78 | #13 (REVISAO-INDICE.md:61,:64; 49 arquivos no disco) | Review: `48 REVISAO-*.md … itens 1–49 homologados` → `48 REVISAO-*.md (49 arquivos com o índice) — itens 1–49 vereditados: 47 HOMOLOGADO + 2 PARECER (46 e 49)` |
| 10 | 89 | #10 (Test-Path raiz wiki = NÃO; framework/galpao_fw/wiki = SIM) | Docs: `wiki/` → `framework/galpao_fw/wiki/` |
| 11 | 90 | #11 (Test-Path wiki/revisoes = NÃO; 49 REVISAO-*.md em framework/galpao_fw/) | Docs: `framework/galpao_fw/wiki/revisoes/REVISAO-*.md` → `framework/galpao_fw/REVISAO-*.md` |
| 12 | (removida) | #12 (Test-Path skills = NÃO; clean `4343297` 2026-07-09) | Linha `- skills/build-warehouse/ — AI skill with 10-gate workflow.` REMOVIDA (skills/ não existe) |

Nota: correção #6a ("Fundações 6 → 5") **não exigiu edição**: a tabela do README lista exatamente 5 módulos de fundação reais (linha 59); o "6" era erro de contagem do próprio claim do task-4, não do documento.

## 2. COMO-RODAR.md — 10 edições em 7 pontos (9 linhas alteradas + 6 adicionadas + 3 removidas)

| # | Linha(s) | Fonte (task-10 §3.2) | Texto novo (resumo) |
|---|---|---|---|
| 1 | 27 | #13 (rodar_projeto.py:263) | Fluxo: `-> gerar_dxf (vistas 2D + quadros)` → `-> rodar_executivo (pranchas 2D + DXF)` |
| 2 | 38 | #14 (projects/ removido 4343297; framework.py:25-27/:46) | Comentário: `ver projects/galpao-nf982/work/spec_nf982.py` → `pasta de projeto criada por framework.novo_projeto` |
| 3 | 41 | #15 (rodar_projeto.py:263; techdraw_exec.py:1907-1908; :565) | `RP.gerar_dxf(s, "projeto/exports/dxf", "meu_galpao")` → `RP.rodar_executivo(s, "projeto/exports", "projeto/exports/freecad/meu_galpao.FCStd")` |
| 4 | 44-46 | #16 (rodar_projeto.py:157/:211/:246; techdraw_exec.py:1907) | `calcular e gerar_dxf NÃO precisam do FreeCAD…` → `calcular roda no venv puro; montar_modelo usa a ponte MCP (porta 9875); não existe gerar_dxf — o DXF sai junto com as pranchas do rodar_executivo (freecad.exe headless, TechDraw)` |
| 5 | 76-78 | #17 (Test-Path projects = NÃO; framework.py:25-27) | `Referência validada: projects/galpao-nf982/ (20×10, ponte 100 kN)` → `Referência validada: galpão 20×10 m com ponte rolante 100 kN … (a pasta projects/<slug>/ é criada em runtime por framework.novo_projeto)` |
| 6 | 82-87 | #18 (rodar_galpao.py:800; REVISAO-INDICE.md:15,:39,:45; task-9 fase 3 `9ac3c4f`; D8) + #19 (rodar_galpao.py:1248/:954; task-9 6.c `820b0e0`/6.b `21d9941`; D51 PR #12) + #20 (`gh pr view 46` MERGED 2026-07-22T11:58:57Z; D37 2026-07-09) + #21 (rodar_galpao.py:253-254; REVISAO-INDICE.md:23,:27,:28; task-9 D10/D16) + git log `4625aed` (merge PR #47, 2026-07-22, "feat/plano-montagem-escoramento") | Nova nota > **Já implementado posteriormente** (bloco sobre estacas e punção fase 3+D8 07-07/10; armadura executiva item 24; treliça/alma variável 6.c/6.b 07-10; multi-vão D51 PR #12; sismo D18; fadiga D10/D16; fabricação PR #46+D37; plano de montagem PR #47) |
| 7 | 89-92 | #18 | Bullet Fundação: `ainda faltam bloco sobre estacas/tubulão, sapata flexível (punção) e detalhamento executivo da armadura` → `ainda falta tubulão (bloco sobre estacas, punção e armadura executiva já implementados — ver nota)` |
| 8 | 93-94 | #19 | Bullet tipologias: `tipologias além do portal 1 vão (treliça, multi-vão, alma variável, mezanino, formado a frio como principal)` → `mezanino e formado a frio como principal (treliça, multi-vão e alma variável já implementados — ver nota)` |
| 9 | (removidas) | #20 | Bullet `ligações de fabricação (…sem furação/solda executiva)` REMOVIDO (fabricação implementada — PR #46; coberto pela nota). Bullet fachadas PRESERVADO (task-10: COMO-RODAR:88 ok) |
| 10 | 96-97 | #21 | Bullet cargas: `cargas especiais (sísmica, fadiga, térmica, ponte múltipla)` → `ponte múltipla e carga térmica plena (sísmica e fadiga já implementadas — ver nota; junta_dilatacao cobre só o movimento térmico)` |
| 11 | 107-108 | #22 (Test-Path pesquisa = NÃO; estaca_profunda.py:27 "LIDO do PDF") | `Métodos extraídos das normas (pesquisa/aço)` → `Métodos extraídos das normas — lidos verbatim do PDF, não de memória (ex.: estaca_profunda.py registra "LIDO do PDF")` |

## 3. API real conferida no código (para as correções de quickstart/fluxo)

- `def calcular(spec, out_dir)` — rodar_projeto.py:16 ✔ (README:24 e COMO-RODAR:39 inalterados — ok no task-10)
- `def montar_modelo(spec, out_dir, doc_name, …)` — rodar_projeto.py:210 ✔
- `def rodar_executivo(spec, out_dir, fcstd_path, …)` — rodar_projeto.py:263 ✔ (exporta PDF+SVG+DXF por prancha em out_dir/pranchas; DXF via `TechDraw.writeDXFPage` techdraw_exec.py:1907)
- Convenção do FCStd: `{out_dir}/freecad/{doc_name}.FCStd` — rodar_projeto.py:565 ✔
- `gerar_dxf`: 0 ocorrências em *.py — inexistente ✔ (task-10 QA #2)

## 4. QA interno

- **Re-leitura integral dos 2 arquivos** pós-edição: todas as linhas alteradas/removidas/adicionadas estão na tabela acima, cada uma com fonte task-10 (§3.1/#1-#13, §3.2/#13-#22) ou fonte primária verificada nesta sessão (git log `4625aed` para PR #47; rodar_projeto.py:565 para o caminho do FCStd).
- **Nenhuma linha alterada sem fonte** → nada revertido.
- Tom/estrutura preservados: títulos de seção, bullets e estilo inalterados; só o conteúdo factual foi corrigido (diff mínimo).
- Encoding: UTF-8 puro sem BOM confirmado por bytes iniciais (35,32,70 / 35,32,67) — edição in place, sem reescrita de encoding.
- Escopo: `git status` mostra alterações SÓ em README.md e COMO-RODAR.md por este task (as modificações em framework/galpao_fw/wiki/*.md e os untracked task-12..16 são de outros tasks do plano). UPSTREAM.md, tools/README.md, REVISAO-INDICE.md intactos.

## 5. Declarações finais

- **README.md:** 12 edições (9 pontos; linhas 3, 10-12, 27-28, 32, 56, 61, 68, 74-76, 77-78, 89, 90; 1 linha removida — skills/build-warehouse/).
- **COMO-RODAR.md:** 10 edições (7 pontos; linhas 27, 38, 41, 44-46, 76-78, 82-97, 107-108; 1 bullet removido — fabricação).
- Todas as 13 correções do task-10 para README e 10 para COMO-RODAR foram aplicadas; nenhuma correção do task-10 ficou de fora (a #6a não exigia edição no README, documentado acima).
- **NENHUM commit; NENHUM código modificado; NENHUM outro arquivo editado.**
- Evidência: `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt\.omo\evidence\revisao-wiki\task-17-revisao-wiki.md`
