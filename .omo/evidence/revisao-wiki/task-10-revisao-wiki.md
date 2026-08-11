# Task 10 — Cross-check dos claims dos docs raiz contra a realidade + veredito in loco do ledger task-4

- **Data:** 2026-08-11
- **Executor:** todo 10 da revisão da wiki
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt` (HEAD `6358157` = main, merge PR #171)
- **Escopo:** claims do ledger task-4 (6 documentos raiz/referência: README.md, COMO-RODAR.md, REVISAO-INDICE.md, UPSTREAM.md, tools/README.md raiz, framework/galpao_fw/tools/README.md) cruzados com a realidade verificada
- **Contagem real:** **123 claims** (36 README + 38 COMO-RODAR + 22 REVISAO-INDICE + 9 UPSTREAM + 12 tools/README raiz + 6 galpao tools/README). O task-4 declarou 118 por erro de aritmética na seção README (31 declarados × 36 linhas reais) — as 36 linhas foram todas preservadas e vereditadas; o total correto é 123.
- **Entradas usadas (NÃO refeitas):** task-1 (135 módulos), task-2 (136 testes; suíte 1353 sel/1340 pass/1 fail/15 skip), task-3 (timeline PRs), task-6 (caminhos), task-7 (vereditos módulos), task-9 (vereditos fases/decisões) + greps de código e Test-Path novos
- **Saídas:** (1) ledger task-4 atualizado IN LOCO (coluna "status: a-verificar" → **veredito**, com coluna extra "correto (fonte)"); (2) esta evidência. **NENHUM dos 6 documentos editado; NENHUM commit; NENHUM código modificado.**
- **Formato:** UTF-8 explícito. Vereditos: `ok` / `corrigir` / `faltante` / `obsoleto` / `não verificado (fonte ausente)`.

---

## 1. Método

1. Leitura integral dos 6 arquivos (feita no todo 4; linhas conferidas no QA do task-4 — 12/12).
2. Para cada claim, verificação contra a realidade, priorizando **fonte primária**:
   - Contagens: task-1 (módulos), task-2 (suíte 2026-08-11), grep `pytest.mark.build`, contagem `def test_` nos arquivos de teste dos itens 45-49, grep `save("gate*")` em `rodar_galpao.py`.
   - APIs: grep de `def <nome>` em `rodar_projeto.py`, `projeto_spec.py`, `framework.py` (assinaturas reais).
   - Caminhos: `Test-Path` (raiz e `framework/galpao_fw`) + `git log` para explicação de remoções (`4343297` clean; `cb890b6`/`e696b84` dxf2fc).
   - Features/pipeline: greps de gate no `rodar_galpao.py`, módulos do task-1, datas de PR via `gh pr view` (#12/#46/#5) e task-9 (D8/D10/D16/D18/D51, fases 6.b/6.c, fase 3).
   - UPSTREAM/tools: leitura dos scripts reais (`install.ps1`, `run_build_suite.ps1`, `register_build_task.ps1`, `preferences.py` vendered, arquivos do bridge).
3. Veredito por claim no ledger task-4 (in loco); correções com fonte `código:linha` ou `task-N` na coluna extra.
4. QA interno (seção 6): 10 correções re-conferidas por re-grep nesta sessão.
5. Nada além de `.omo/evidence/revisao-wiki/` foi escrito.

## 2. Distribuição de vereditos (123 claims)

| Arquivo | Claims | ok | corrigir | faltante | obsoleto | não verificado (fonte ausente) |
|---|---|---|---|---|---|---|
| README.md (raiz) | 36 | 23 | 13 | 0 | 0 | 0 |
| COMO-RODAR.md | 38 | 28 | 10 | 0 | 0 | 0 |
| REVISAO-INDICE.md | 22 | 17 | 4 | 0 | 0 | 1 |
| UPSTREAM.md | 9 | 9 | 0 | 0 | 0 | 0 |
| tools/README.md (raiz) | 12 | 11 | 1 | 0 | 0 | 0 |
| galpao tools/README.md | 6 | 3 | 3 | 0 | 0 | 0 |
| **Total** | **123** | **91** | **31** | **0** | **0** | **1** |

Leitura: 91/123 claims confirmados (74,0%); 31 corrigir (25,2%); 1 não verificável nesta revisão. Zero "faltante" (nada nos docs raiz que exista no real e esteja ausente dos docs) e zero "obsoleto" (nenhum claim descreve algo que deixou de existir — todos os 31 corrigir são de valor/estado desatualizado ou caminho inexistente, não de remoção funcional). UPSTREAM.md 100% ok (9/9).

## 3. Correções propostas (31) — claim | arquivo:linha | atual | correto | fonte

### 3.1 README.md (raiz) — 13 correções

| # | Claim | arquivo:linha | Atual | Correto | Fonte (código/evidência:linha) |
|---|---|---|---|---|---|
| 1 | "53 Python modules" | README.md:3 | 53 módulos | **135 módulos** | task-1: `(Get-ChildItem framework\galpao_fw -Filter *.py).Count` = 135 (re-executado nesta sessão: 135) |
| 2 | "REVISAO itens 1–49 senior-homologated" | README.md:10 | 1-49 homologados | **47/49 HOMOLOGADO; itens 46 e 49 são PARECER** (46 "PARECER 2 RODADAS — 2 CORRIGIDOS"; 49 "PARECER — 1 CORRIGIDO") | REVISAO-INDICE.md:61, :64 |
| 3 | "pytest 245 passed" | README.md:10 | 245 passed | **1353 selecionados / 1340 passed / 1 failed / 15 skipped** (2026-08-11; falha F1 `test_dossie_unico` — falta `fitz`) | task-2 (linhas-resumo verbatim lane 1 + lane 2) |
| 4 | "`RP.gerar_dxf(s, 'exports/dxf', 'meu_galpao')`" | README.md:25 | função existe | **`gerar_dxf` NÃO existe** (0 ocorrências em *.py — só nos docs). Fluxo real: `RP.rodar_executivo(s, out, fcstd)` → `TechDraw.writeDXFPage` | rodar_projeto.py:263 (`def rodar_executivo`); techdraw_exec.py:1907-1908 (`writeDXFPage`) |
| 5 | "Pipeline com 23 gates" | README.md:29 | 23 gates | **40 saídas `gate*.txt` atuais** em rodar_galpao.py (gates 5-9 + sub-gates + gate-calha/terreno/zona-painel). 23 era o estado 2026-07-08 | grep `save("gate*")` em rodar_galpao.py = 40 nomes únicos (gate5-* 4, gate6-* 4, gate7-* 24, gate7b 1, gate8-* 4, gate-calha/terreno/zona-painel 3); REVISAO-INDICE.md:110 (estado antigo) |
| 6 | Catálogo: "Fundações 6" + lista com `dxf_vistas` | README.md:51-59 | 9 categorias com 52 entradas | **50/51 módulos existem; 2 erros**: Fundações = **5** (não 6); `dxf_vistas` NÃO existe → substituído por `techdraw_exec` (2026-07-09) | task-1 tabela (50/51 conferem); git log --follow dxf_vistas.py: `cb890b6` "substitui DXF externo por vistas 2D nativas" + `e696b84` (2026-07-09); Test-Path dxf_vistas.py = NÃO |
| 7 | "`neve` é stub, 'não wired'" | README.md:53 | neve stub órfã | **neve implementado e wired desde D51 (2026-07-16; PR #12 merged 2026-07-18)**: gate `neve` no spec + import no orquestrador | rodar_galpao.py:156-158 (`import neve as _neve`); projeto_spec.py:133 (`"neve": None`); neve.py:13 (`def carga_neve`), :47 (`def relatorio_pt`); task-7 item 24; `gh pr view 12` (MERGED 2026-07-18T11:54:26Z) |
| 8 | "estaca (3 métodos)" | README.md:65-66 | 3 métodos de estaca | **1 método: Aoki-Velloso** (`capacidade_aoki_velloso`); Décourt-Quaresma é FLAG/trabalho futuro | estaca_profunda.py:69 (`def capacidade_aoki_velloso`), :3-4 (cabeçalho "método semi-empírico de AOKI-VELLOSO"); REVISAO-INDICE.md:102-103 (resíduos FLAG) |
| 9 | "valores de norma lidos verbatim do PDF em `pesquisa/`" | README.md:71-72 | `pesquisa/` existe | **`pesquisa/` NÃO existe** (raiz e framework/galpao_fw); PDFs no repo: `Framework_Galpao_Modulos.pdf` (raiz), `libraries/standards/gerdau/...` | Test-Path pesquisa = NÃO; Test-Path framework/galpao_fw/pesquisa = NÃO; glob `*.pdf` no repo |
| 10 | "Docs: `wiki/`" | README.md:84 | wiki na raiz | **wiki real em `framework/galpao_fw/wiki/`** (7 arquivos) | Test-Path wiki (raiz) = NÃO; Test-Path framework/galpao_fw/wiki = SIM; task-1 (3 subdirs: tests/tools/wiki) |
| 11 | "Docs: `framework/galpao_fw/wiki/revisoes/REVISAO-*.md`" | README.md:85 | revisoes/ na wiki | **`wiki/revisoes/` NÃO existe; os 49 REVISAO-*.md ficam em `framework/galpao_fw/`** | Test-Path framework/galpao_fw/wiki/revisoes = NÃO; `Get-ChildItem framework\galpao_fw -Filter "REVISAO-*.md"` = 49 |
| 12 | "Docs: `skills/build-warehouse/` — 10-gate workflow" | README.md:86 | skills/ existe | **`skills/` NÃO existe** — removido no clean `4343297` "clean: remove projetos, testes, wikis, skills - deixa so framework final" (2026-07-09) | Test-Path skills = NÃO; `git log -1 4343297` (2026-07-09T09:05:45-03:00) |
| 13 | "48 REVISAO-*.md … — itens 1–49 homologados" | README.md:73-74 | itens 1-49 homologados | **48 docs ✓ (49 arquivos com o índice); nuance: itens 46 e 49 são PARECER, não HOMOLOGADO** (46 "PARECER 2 RODADAS — 2 CORRIGIDOS"; 49 "PARECER — 1 CORRIGIDO") | REVISAO-INDICE.md:61, :64; `Get-ChildItem framework\galpao_fw -Filter "REVISAO-*.md"` = 49 |

### 3.2 COMO-RODAR.md — 10 correções

| # | Claim | arquivo:linha | Atual | Correto | Fonte (código/evidência:linha) |
|---|---|---|---|---|---|
| 13 | Fluxo "spec → validar → calcular → montar_modelo → gerar_dxf" | COMO-RODAR.md:24-28 | etapa `gerar_dxf` existe | **etapa real final: `rodar_executivo`** (pranchas 2D + DXF) | rodar_projeto.py:263 (`def rodar_executivo`); techdraw_exec.py:1907 (`TechDraw.writeDXFPage`) |
| 14 | "ver `projects/galpao-nf982/work/spec_nf982.py`" | COMO-RODAR.md:37-38 | pasta exemplo existe | **`projects/` NÃO existe** (removido no clean 4343297, 2026-07-09); projetos criados em runtime por `framework.novo_projeto` | Test-Path projects = NÃO; framework.py:25-27 (`dir_projetos()` → raiz_repo()/projects), :46 (`def novo_projeto(slug, base=None)`) |
| 15 | "`RP.gerar_dxf(s, "projeto/exports/dxf", "meu_galpao")`" | COMO-RODAR.md:41 | função existe | **função inexistente**; DXF via `RP.rodar_executivo(s, out, fcstd)` → `writeDXFPage` | rodar_projeto.py:263; techdraw_exec.py:1907-1908 |
| 16 | "`calcular` e `gerar_dxf` NÃO precisam do FreeCAD; `montar_modelo` precisa (porta 9875)" | COMO-RODAR.md:44-45 | gerar_dxf roda no venv | **`calcular` ✓ venv puro; `montar_modelo` ✓ bridge XMLRPC 9875; `gerar_dxf` não existe e o DXF roda DENTRO do executivo FreeCAD (TechDraw headless)** | rodar_projeto.py:157/:211/:246 (porta 9875, bridge/headless); techdraw_exec.py:1907 (writeDXFPage executa no FreeCAD) |
| 17 | "Referência validada: `projects/galpao-nf982/` (20×10, ponte 100 kN)" | COMO-RODAR.md:75-76 | pasta existe | **`projects/galpao-nf982/` NÃO existe** (removido 4343297; pastas criadas em runtime) | Test-Path projects = NÃO; framework.py:25-27; git log 4343297 |
| 18 | "NÃO faz — Fundação: faltam bloco sobre estacas/tubulão, sapata flexível (punção), detalhamento executivo da armadura" | COMO-RODAR.md:80-83 | 3 itens faltando | **bloco sobre estacas IMPLEMENTADO** (fase 3, 2026-07-10); **punção IMPLEMENTADA** (D8, 2026-07-07); **armadura executiva IMPLEMENTADA** (item 24 do índice); **só TUBULÃO segue fora** | rodar_galpao.py:800 (gate7-estaca); REVISAO-INDICE.md:15 (punção §10 + recalque §11), :39 (item 24 — fundacao_sapata.py ancoragem+quadro), :45 (FUNDACAO-PROFUNDA-INTEG); task-9 (fase 3 ok — `9ac3c4f` 07-10; D8) |
| 19 | "NÃO faz — tipologias além do portal 1 vão (treliça, multi-vão, alma variável...)" | COMO-RODAR.md:84-85 | 3 tipologias faltando | **treliça IMPLEMENTADA** (fase 6.c, 2026-07-10); **alma variável IMPLEMENTADA** (fase 6.b, 2026-07-10); **multi-vão IMPLEMENTADO** (D51, 2026-07-16, PR #12); seguem fora: mezanino, formado a frio como principal | rodar_galpao.py:1248 (gate6-tesoura), :954 (gate6-alma-variavel); task-9 (6.b `21d9941` 07-10 15:24; 6.c `820b0e0` 07-10 17:29); task-5 D51 (`geometria.spans` 2 vãos→3 colunas); task-1 (sem módulo mezanino/formado a frio) |
| 20 | "NÃO faz — ligações de fabricação (sem furação/solda executiva)" | COMO-RODAR.md:86-87 | fabricação não existe | **fabricação IMPLEMENTADA**: PR #46 (2026-07-22) — piece marks 3D + lista de corte + tolerâncias; D37 (2026-07-09) detalhe A+B; callouts de fabricação no smoke | `gh pr view 46` (MERGED 2026-07-22T11:58:57Z, "fabricacao - piece marks 3D + lista de corte + tolerancias [S17]"); task-9 (D37 ok; #46 efeito na main via `a681999`); smoke_executivo.py:176-182 (asserts joelho/gusset/console — "callouts de fabricacao (me-4)") |
| 21 | "NÃO faz — cargas especiais (sísmica, fadiga, térmica, ponte múltipla)" | COMO-RODAR.md:89 | 4 cargas faltando | **sísmica IMPLEMENTADA** (D18, 2026-07-08); **fadiga IMPLEMENTADA** (D10/D16, 2026-07-08 — Anexo K); **térmica**: junta_dilatacao cobre movimento térmico (não carga térmica plena); **ponte múltipla segue fora** | rodar_galpao.py:253-254 (`sismo.verifica_sismo`); sismo_nbr15421.py (D18, task-5); REVISAO-INDICE.md:23 (fadiga Anexo K §9 + B.7.3.4), :27 (junta Bellei/FCC 65), :28 (sismo NBR 15421:2023); task-9 (D10/D16) |
| 22 | "Métodos extraídos das normas (`pesquisa/aço`)" | COMO-RODAR.md:99 | pasta existe | **`pesquisa/` NÃO existe**; método "lido do PDF" confirmado no código, mas o caminho citado não | Test-Path pesquisa = NÃO; estaca_profunda.py:27 ("LIDO do PDF") — método real, caminho inexistente |

### 3.3 REVISAO-INDICE.md — 4 correções

| # | Claim | arquivo:linha | Atual | Correto | Fonte (código/evidência:linha) |
|---|---|---|---|---|---|
| 23 | "métodos extraídos das normas em `pesquisa/aço/`" | REVISAO-INDICE.md:8-9 | pasta existe | **`pesquisa/aço/` NÃO existe** (raiz e framework/galpao_fw) | Test-Path (negativo em 2 níveis) |
| 24 | Módulos não-matemáticos incluem `dxf_vistas` | REVISAO-INDICE.md:66-69 | dxf_vistas existe | **`dxf_vistas` NÃO existe** — substituído por `techdraw_exec` (2026-07-09); demais 9 módulos citados existem | git log --follow dxf_vistas.py (`cb890b6`/`e696b84` 2026-07-09); Test-Path dxf_vistas.py = NÃO; techdraw_exec.py existe; task-1 |
| 25 | "Pipeline: 23 gates, 35 módulos totais" | REVISAO-INDICE.md:110-111 | 23 gates / 35 módulos | **40 saídas gate*.txt** (rodar_galpao.py) e **135 módulos** (task-1); números de 2026-07-08 | grep `save("gate*")` rodar_galpao.py (40); task-1 (135) |
| 26 | "Última atualização: 2026-07-08" | REVISAO-INDICE.md:114 | atualizado em 07-08 | **2026-07-13** — itens 45-49 do próprio índice datados 07-13; último commit no arquivo `01e14e7` (07-13) | REVISAO-INDICE.md:60-64 (datas 07-13); `git log -1 -- framework/galpao_fw/REVISAO-INDICE.md` = `01e14e7 2026-07-13T23:48:27-03:00` |

### 3.4 tools/README.md (raiz) — 1 correção

| # | Claim | arquivo:linha | Atual | Correto | Fonte (código/evidência:linha) |
|---|---|---|---|---|---|
| 27 | "Testes marcados `build` são 9" | tools/README.md:5 | 9 testes build | **18 marcas `pytest.mark.build` em 17 arquivos** de `framework/galpao_fw/tests/` (`test_build_federado.py` tem 2) | task-2 (18 ocorrências/17 arquivos, lista dos 17); re-verificado: `(Get-ChildItem tests\*.py \| Select-String "pytest.mark.build").Count` = 18 |

### 3.5 framework/galpao_fw/tools/README.md — 3 correções

| # | Claim | arquivo:linha | Atual | Correto | Fonte (código/evidência:linha) |
|---|---|---|---|---|---|
| 28 | "suíte `-m "not build"` (~1281 testes)" | tools/README.md:5 | 1281 testes | **1353 selecionados / 1374 coletados / 1340 passed / 1 failed / 15 skipped** (2026-08-11); lane rápida cresceu +72 desde S40 | task-2 (tabela de contagens + comparação com claim) |
| 29 | "verificado S40: 1281 passed com `-n auto`" (xdist ~5 min/8 núcleos) | tools/README.md:13-15 | 1281 passed (estado atual) | **números de S40 desatualizados** (suíte atual 1353 sel/1340 pass); **xdist NÃO instalado no .venv nesta revisão** — caminho xdist não re-verificado; manter como registro histórico | task-2 (nota de dependências: "pytest-xdist: NÃO instalado"); task-2 tabela |
| 30 | Fallback 2 lanes: "243 testes ... isolados dos 1038 rápidos" | tools/README.md:16-18 | 1038 rápidos | **243 ✓** (lane 2); **lane 1 atual = 1110 selecionados** (não 1038); **F2: o glob `tests/test_fase*.py` do runner QUEBRA em shell Windows** (PowerShell não expande glob → "no tests ran in 0.00s") — fallback funciona só com glob expandido | task-2 (lane 1 = 1110; lane 2 = 243; F2 com linhas-resumo verbatim) |

## 4. Vereditos ok — resumo por arquivo (91)

**README.md (23 ok):** pipeline end-to-end (:4-8, todos os estágios no rodar_galpao/rodar_projeto); smoke 7/7 (:10 — 7 CASOS em smoke_executivo.py:108-120); `.\install.bat` (:16); quick start imports + `PS.novo()` (:21-22 — projeto_spec.py:76); `RP.calcular(s, 'exports/memoria')` (:24 — rodar_projeto.py:16); Gate 5 vento (:32 — rodar_galpao.py:263-271); Gate 5 sismo (:33 — sismo_nbr15421.py, rodar_galpao.py:253-254); Gate 5 ponte (:34 — rodar_galpao.py:225); Gate 6 pórtico 2D + MAES (:35-36 — rodar_galpao.py:274-278); Gate 7 redimensionamento/verificação/mão-francesa/terças/telha (:37-38); Gate 7 alma var/tesoura DG25 + zona painel + mísula (:39 — dg25_ltb/zona_painel/flt_misula); Gate 7 forças localizadas + enrijecedor + alma esbelta Anexo H (:40); Gate 7 secundários/base/fundações/ligações (:41-42); Gate 8 fogo/escada/plataforma (:43 — rodar_galpao.py:1423/:1455/:1466); Gate 9 memorial + pranchas (:44 — rodar_projeto.py:380/:263); multi-span (:63 — geometria.spans); portal types (:64); Fire ISO 834 (:67); 3D headless + auditoria (:68 — rodar_projeto.py:210/:250, build_galpao.py:1625); 2D Executive TechDraw (:69-70 — rodar_projeto.py:263, techdraw_exec.py:1247 SvgHatch, glyph AWS); Requirements (:78); numpy<2 (:79 — requirements.txt); MCP freecad-mcp (:80 — install.ps1:181-182).

**COMO-RODAR.md (28 ok):** conceitual ART (:3-4); install PC novo (:8-9); MCP + RobustMCPBridge (:11 — install.ps1:181-182/:220-253); venv Python 3.12/numpy<2/pycufsm/ezdxf (:12-13 — requirements.txt + install.ps1:17/:40); pré-requisitos uv (:15 — install.ps1 `InstallUvIfMissing`); .venv fora do git (:17 — .gitignore:2-3); spec fonte única (:21); imports (:33-34); `PS.novo()` PENDENTE (:36 — projeto_spec.py:76); `RP.calcular` (:39 — rodar_projeto.py:16); `RP.montar_modelo` (:40 — rodar_projeto.py:210); `framework.novo_projeto` (:47 — framework.py:46); memoriais + MEMORIAL-CONSOLIDADO (:51-52 — rodar_projeto.py:88-89/:372/:380); FCStd + STEP (:53 — rodar_projeto.py:565, build_galpao.py:2050); takeoff CSV (:54 — build_galpao.py:1956-1968); dxf com quadros/camadas (:55-57, :73 — techdraw_exec.py:1907/:1507, nota de conteúdo herdado das pranchas); escopo tipologia (:61); vento Cat I-V (:63); pórtico 1ª+2ª ordem + redim (:64); base/joelho/terça/longarina/escora (:65-66); sapata NBR 6118 (:67-69 — gate7-fundacao + REVISAO-FUNDACAO); terças NBR 14762 + mão-francesa + contraventamento (:70); 3D conexões + auditor (:71-72 — build_galpao.py:1625); fachadas continuam fora (:88 — sem módulo, task-1; tapamento só IFC PR #65); Ask Do Not Invent (:93-94 — projeto_spec.py:149); Utilização ≤1,0 (:95-96 — rodar_projeto.py:372); A CONFIRMAR perfis (:97-98 — perfis.py:6/:63).

**REVISAO-INDICE.md (17 ok):** formato dos docs (:3-6); 49 itens HOMOLOGADO ou PARECER (:15-64); item 1 FUNDACAO r2 + punção/recalque (:15 — D8, task-9); itens 2-17 todos HOMOLOGADO (:16-31); itens 18-49 32 módulos/features com parecer (:33-64); item 45 "11 testes" (:60 — test_fase615_props_mono.py 11); item 46 "13 testes" (:61 — test_fase616 13); item 47 "11 testes" (:62 — test_fase617 11); item 48 "13 testes" (:63 — test_fase618 13); item 49 "9 testes" (:64 — test_fase619_glifo_solda.py 9); features novas TODAS HOMOLOGADAS 07-07/08 (:73-76 — merges #1/#4, task-9); 14 features (:80-93 — 14 linhas contadas); fixes build 3D + wiki/04-decisions.md D7 (:95-98 — Test-Path wiki/04-decisions.md SIM); lacunas ENCERRADA (:100-102 — task-9); resíduos FLAG (:102-105 — estaca_profunda só Aoki-Velloso); base 100% concreto (:105 — REVISAO-BASE.md:21); "27 módulos matemáticos" (:109 — 27 = itens 1-27 do próprio índice, consistente).

**UPSTREAM.md (9 ok):** vendoring do projeto (:3 — install.ps1:220-253); origem spkane (:6 — pasta vendered existe); código vendered (:12 — Test-Path SIM); `-Help`/`-WhatIf` (:15-21 — install.ps1 param `[switch]$Help` + SupportsShouldProcess); licenças (:23 — LICENSE-CODE/LICENSE-ICON); wrapper FreeCAD 1.1 (:27-28); patches Init.py/InitGui.py/__init__.py/server.py (:30-34 — arquivos existem; GuiUp defensivo em __init__.py:117-129 e server.py:70/:133/:425/:555); DEFAULT_AUTO_START = True (:35 — preferences.py:37); user.cfg preserva valor (:38-40 — preferences.py:55 GetBool("AutoStart", DEFAULT_AUTO_START)).

**tools/README.md raiz (11 ok):** build constrói 3D + checa_interferencia (:5-7 — build_galpao.py:1625); lentos/deselected (:7-8 — task-2: 18 deselected); comando green bar (:11); regressões silenciosas + 2 bugs calha/condutor (:14-16 — histórico, task-9 PR #49/#51); run_build_suite logs/LATEST/exit code (:20-21 — run_build_suite.ps1:31/:36/:41; .gitignore:58); freecadcmd subprocessos (:22-23); register_build_task local (:24-26 — register_build_task.ps1:39); comandos de uso (:32, :35-39 — params reais :30-35, :42-43, :46-47 — FreeCadCmd :24-25 + FREECADCMD :18).

**galpao tools/README (3 ok):** comandos run_tests.py (:9-10 — arquivo existe); pip install requirements (:23); build fora da suíte (:26).

## 5. Não verificado (1) — com justificativa

| Claim | arquivo:linha | Justificativa |
|---|---|---|
| "Testado end-to-end: galpão 24×12m → FreeCAD 669 obj, 0 interferências, 20.156 kg aço" | REVISAO-INDICE.md:111-112 | Claim datado (2026-07-08). Sem rerun nesta revisão: nenhum teste atual referencia "20156"/24×12 (grep em tests/ vazio); o smoke (todo 18) roda 7 casos de espec, não esse cenário. **Não recebe correção sem fonte** — apenas sinalizado para re-verificação no todo 18 (Wave 5) |

## 6. QA interno — 12 correções/confirmações re-conferidas contra o código (2026-08-11)

| # | Correção | Comando de re-verificação | Resultado |
|---|---|---|---|
| 1 | 135 módulos (README:3) | `(Get-ChildItem framework\galpao_fw -Filter *.py -File).Count` | 135 ✔ |
| 2 | `gerar_dxf` inexistente | grep `gerar_dxf` em todos os `*.py` do repo | só em README.md/COMO-RODAR.md (docs) — 0 em código ✔ |
| 3 | `rodar_executivo` é o fluxo DXF real | `Select-String "def rodar_executivo" rodar_projeto.py` → :263; `writeDXFPage` techdraw_exec.py:1907 | ✔ |
| 4 | 18 marcas build / 17 arquivos | `(Get-ChildItem tests\*.py \| Select-String "pytest.mark.build").Count` | 18 ✔ (17 arquivos únicos) |
| 5 | 40 saídas gate*.txt | `Select-String 'save\("(gate[^"]+)"' rodar_galpao.py` | 40 nomes únicos ✔ |
| 6 | neve wired (não stub) | `import neve as _neve` rodar_galpao.py:158; `def carga_neve` neve.py:13; gate `"neve": None` projeto_spec.py:133 | ✔ |
| 7 | estaca = 1 método (Aoki-Velloso) | `def capacidade_aoki_velloso` estaca_profunda.py:69; sem Décourt no módulo | ✔ |
| 8 | `pesquisa/` inexistente | `Test-Path` raiz e `framework\galpao_fw\pesquisa` | NÃO / NÃO ✔ |
| 9 | wiki real em framework/galpao_fw/wiki | `Test-Path framework\galpao_fw\wiki` = SIM; raiz `wiki` = NÃO; `wiki\revisoes` = NÃO; 49 REVISAO-*.md em galpao_fw | ✔ |
| 10 | DEFAULT_AUTO_START = True | `Select-String DEFAULT_AUTO_START preferences.py` | :37 = True ✔ |
| 11 | item 49 "9 testes" | `Select-String "def test_" test_fase619_glifo_solda.py` | 9 ✔ |
| 12 | REVISAO-INDICE atualizado 07-13 | `git log -1 -- REVISAO-INDICE.md` | `01e14e7` 2026-07-13 ✔ |

QA: 12/12 conferências bateram com o código/evidências nesta sessão (11 correções + 1 contagem ok). Nenhuma correção ficou sem fonte.

## 7. Declarações finais

- **Distribuição (123 claims):** 91 ok · 31 corrigir · 0 faltante · 0 obsoleto · 1 não verificado (fonte ausente). *(O task-4 declarou 118 — erro de aritmética: 31 README declarados × 36 linhas reais; todas as 36 foram vereditadas; total real 123.)*
- **31 correções com fonte verificável** (13 README + 10 COMO-RODAR + 4 REVISAO-INDICE + 1 tools/README raiz + 3 galpao tools/README) — todas com `código:linha`, `git log`/`gh pr view` ou `task-N` como fonte; zero correção sem fonte.
- **Ledger task-4 atualizado IN LOCO:** coluna "status: a-verificar" renomeada para **veredito** nas 6 tabelas de claims (seções 1-6) e coluna extra "correto (fonte)" adicionada; tabelas de contexto (REVISAO count, caminhos, disco) também vereditadas. Nada além de `.omo/evidence/revisao-wiki/` foi escrito.
- **NENHUM dos 6 documentos raiz editado** (README/COMO-RODAR/REVISAO-INDICE/UPSTREAM/tools READMEs) — as correções da seção 3 são a PATCH LIST para o todo 17.
- **NENHUM commit; NENHUM código modificado.**
- Bloqueia o todo 17 (aplicar correções nos docs raiz).
