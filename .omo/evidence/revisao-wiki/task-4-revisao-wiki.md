# Task 4 — Inventário de claims factuais: documentos raiz/referência (extração pura + veredito in loco)

- **Data:** 2026-08-11
- **Executor:** todo 4 da revisão da wiki
- **Worktree:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt`
- **Escopo:** 6 arquivos raiz/referência (NÃO a wiki/ — essa é o todo 5, outro executor)
- **Natureza:** extração pura — **NADA foi corrigido**. Todo claim nasce com status `a-verificar`.
- **Este ledger foi atualizado IN LOCO pelo todo 10** (coluna "status: a-verificar" → **veredito** ok/corrigir/faltante/obsoleto, com a coluna extra "correto (fonte)" preenchida para os corrigir). **TODO 10 — 2026-08-11:** 91 ok · 31 corrigir · 0 faltante · 0 obsoleto · 1 não verificado (fonte ausente) — distribuição detalhada em `task-10-revisao-wiki.md`. **Correção de contagem do próprio task-4:** a seção README tem 36 linhas de claim (não 31) e o total real é 123 (não 118) — 36+38+22+9+12+6.

## Método

1. Leitura integral dos 6 arquivos (Read, UTF-8 tolerante a BOM).
2. Extração de claims com referência `arquivo:linha` citável (linha conferida na leitura).
3. Checks de disco via PowerShell: `Get-ChildItem` (contagem real `REVISAO-*.md`) e `Test-Path` (existência de caminhos referenciados).
4. QA interno: 12 claims re-lidos por `Select-String` (linha confere — ver seção QA).
5. Nenhum dos 6 arquivos foi editado; nenhum commit feito.
6. **Todo 10 (in loco):** cada claim cruzado com a realidade (task-1 módulos, task-2 suíte, task-3 PRs, task-7 módulos, task-9 fases/decisões + greps de código + Test-Path) e vereditado; correções com fonte `código:linha`/`task-N` na coluna extra.

## Arquivos extraídos

| # | Arquivo | Linhas | Claims extraídos |
|---|---------|--------|------------------|
| 1 | `README.md` (raiz) | 87 | 36 |
| 2 | `framework/galpao_fw/COMO-RODAR.md` | 99 | 38 |
| 3 | `framework/galpao_fw/REVISAO-INDICE.md` | 114 | 22 |
| 4 | `UPSTREAM.md` (raiz) | 43 | 9 |
| 5 | `tools/README.md` (raiz) | 47 | 12 |
| 6 | `framework/galpao_fw/tools/README.md` | 26 | 6 |
| | **Total** | | **123** |

Legenda de tipos: **contagem** (números de módulos/testes/itens/gates), **caminho** (path referenciado), **lista/status** (features, catálogo, estados homologados), **API** (exemplos de código/comandos), **norma** (citação normativa), **processo** (regra/comportamento declarado).

Legenda de vereditos (todo 10): **ok** (confirmado com fonte) · **corrigir** (erro factual; texto correto + fonte na coluna extra) · **faltante** (existe no real e falta no doc) · **obsoleto** (descreve estado superado) · **não verificado (fonte ausente)** (sem fonte para conferir; justificativa na coluna extra).

---

## 1. `README.md` (raiz) — 36 claims

| claim | arquivo:linha | tipo | veredito | correto (fonte) |
|---|---|---|---|---|
| "53 Python modules" para projeto paramétrico de galpões de aço | README.md:3 | contagem | corrigir | **135 módulos** `framework\galpao_fw\*.py` (task-1: `(Get-ChildItem -Filter *.py).Count` = 135) |
| Pipeline end-to-end: site data → cargas vento/sismo/ponte → análise 2D pórtico (1 ou N vãos, prismático/web-tapered/treliça) → MAES 2ª ordem → verificação NBR 8800 (+ Anexo G/H, §5.7 forças localizadas, DG25 cross-check) → conexões → fundações (rasas/profundas/excêntricas) → fogo → escada → plataforma → modelo 3D FreeCAD → pranchas 2D (TechDraw, símbolos de solda AWS A2.4) → DXF → memoriais PT | README.md:4-8 | lista/status | ok | estágios existem no código: gate5-vento/ponte/neve, gate6-portico/2a-ordem/alma-variavel/tesoura, gate7-* (check-nbr8800, forcas-localizadas, dg25_ltb, fundações, ligações), gate8-fogo/escada/plataforma, gate9 consolidado (rodar_galpao.py); relatorio_consolidado (rodar_projeto.py:380); techdraw_exec (writeDXFPage :1907) |
| Status: REVISAO itens 1–49 senior-homologated | README.md:10 | contagem | corrigir | **47/49 HOMOLOGADO; itens 46 e 49 em status PARECER** (não HOMOLOGADO): 46 = "PARECER 2 RODADAS — 2 CORRIGIDOS", 49 = "PARECER — 1 CORRIGIDO" (REVISAO-INDICE.md:61 e :64) |
| Status: pytest 245 passed | README.md:10 | contagem | corrigir | **Suíte atual (2026-08-11): 1353 selecionados / 1340 passed / 1 failed / 15 skipped** (task-2; falha F1 = `test_dossie_unico` sem módulo `fitz`) |
| Status: smoke 7/7 | README.md:10 | contagem | ok | `smoke_executivo.py` tem exatamente **7 CASOS** (CASOS em smoke_executivo.py:108-120: padrao, vao_maior, baixo_largo, ponte, estaca, alma_var, tesoura); execução não re-feita (todo 18) |
| Setup one time: `.\install.bat` | README.md:16 | API | ok | install.bat existe na raiz; chama install.ps1 -InstallUvIfMissing (install.bat:9) |
| Quick start: `import projeto_spec as PS, rodar_projeto as RP`; `s = PS.novo()` | README.md:21-22 | API | ok | projeto_spec.py e rodar_projeto.py existem; `def novo()` projeto_spec.py:76 |
| Quick start: `RP.calcular(s, 'exports/memoria')` | README.md:24 | API | ok | `def calcular(spec, out_dir)` rodar_projeto.py:16 — assinatura confere |
| Quick start: `RP.gerar_dxf(s, 'exports/dxf', 'meu_galpao')` | README.md:25 | API | corrigir | **Função `gerar_dxf` NÃO existe** (grep global: zero ocorrências em *.py). Fluxo real de DXF: `RP.rodar_executivo(s, out_dir, fcstd, ...)` (rodar_projeto.py:263) → `TechDraw.writeDXFPage(p, base+".dxf")` (techdraw_exec.py:1907-1908). `gerar_dxf` só aparece nos próprios docs (README/COMO-RODAR) |
| Pipeline com 23 gates | README.md:29 | contagem | corrigir | **40 saídas `gate*.txt` atuais em rodar_galpao.py** (gates 5-9 + sub-gates 7b + extras gate-calha/gate-terreno/gate-zona-painel; grep `save("gate*")` = 40 nomes únicos). "23 gates" era o estado 2026-07-08 (REVISAO-INDICE.md:110) |
| Gate 5: Vento NBR 6123 (transversal + longitudinal + Tab.7 multi-span) | README.md:32 | norma | ok | gate5-vento.txt (rodar_galpao.py:263-264, transversal + longitudinal); multi-vão Tab.7 (REVISAO-MULTI-VAO.md, NBR 6123 Tab.7) |
| Gate 5: Sismo NBR 15421 | README.md:33 | norma | ok | sismo_nbr15421.py (wired, task-1); `sismo.verifica_sismo` rodar_galpao.py:253-254; save gate7-sismo.txt :1359 (numeração interna do output difere — sem impacto no claim) |
| Gate 5: Ponte rolante NBR 8800/8400 | README.md:34 | norma | ok | gate5-ponte.txt rodar_galpao.py:225; módulos ponte_rolante.py + nbr8400.py existem (task-1) |
| Gate 6: Pórtico 2D (1 ou N vãos); 2ª ordem MAES (B1/B2) | README.md:35-36 | lista/status | ok | gate6-portico.txt/gate6-2a-ordem.txt (rodar_galpao.py:274-278); estabilidade_b1b2.py existe |
| Gate 7: Redimensionamento (guloso, perfis por coluna); verificação NBR 8800 + mão-francesa + terças + telha | README.md:37-38 | lista/status | ok | gate7-redimensionamento (rodar_galpao.py:285), gate7-check-perfis (:358), gate7-mao-francesa (:323), gate7-tercas (:403), gate7-telha (:458) |
| Gate 7: Alma variável/tesoura: DG25 FLT + envelope FLB/TFY, zona de painel, mísula | README.md:39 | lista/status | ok | módulos dg25_ltb.py, zona_painel.py, flt_misula.py existem (task-1); gate6-alma-variavel/gate6-tesoura (rodar_galpao.py:954/:1248 — no código estes saem no Gate 6, não 7; nota) |
| Gate 7: Forças localizadas §5.7 + enrijecedor de apoio + alma esbelta (Anexo H) | README.md:40 | norma | ok | forcas_localizadas.py, enrijecedor_painel.py, alma_esbelta.py (Anexo H) existem (task-1) |
| Gate 7: Secundários + Contraventamento + Verga; Base + Chumbadores + Sapata + Baldrame + Estaca + Divisa (viga de equilíbrio) + Ligações/Gusset | README.md:41-42 | lista/status | ok | gate7-secundarios, gate7-contraventamento, gate7-verga, gate7-base, gate7-fundacao, gate7-baldrame, gate7-estaca, gate7-divisa, gate7-ligacoes, gate7-gusset (todos os saves existem em rodar_galpao.py) |
| Gate 8: Fogo (NBR 14323) + Escada + Plataforma | README.md:43 | norma | ok | gate8-fogo, gate8-escada, gate8-plataforma (rodar_galpao.py:1423/:1455/:1466) |
| Gate 9: Memorial Consolidado (PDF) + Pranchas executivas 2D (TechDraw headless) | README.md:44 | lista/status | ok | relatorio_consolidado (rodar_projeto.py:380, PDF via reportlab); rodar_executivo (rodar_projeto.py:263) + techdraw_exec.py |
| Catálogo de módulos — 9 categorias (Análise 6, Perfis avançados 11, Cargas 5, Secundários 7, Ligações 4, Fundações 6, Fogo/acessórios 3, Geometria/saída 5, Orquestração 5) | README.md:51-59 | lista/status | corrigir | 50/51 módulos citados existem (task-1); **2 erros**: (a) "Fundações 6" mas só **5 listados** (fundacao_sapata, viga_baldrame, estaca_profunda, sapata_divisa, viga_equilibrio); (b) **`dxf_vistas` NÃO existe** — substituído por `techdraw_exec` (commits cb890b6/e696b84, 2026-07-09; git log --follow dxf_vistas.py) |
| Catálogo: `neve` é stub, "não wired" | README.md:53 | lista/status | corrigir | **neve.py é implementado e wired desde D51 (2026-07-16; PR #12 merged 2026-07-18)**: `import neve as _neve` rodar_galpao.py:158; gate `"neve": None` projeto_spec.py:133; funções `carga_neve` neve.py:13, `relatorio_pt` :47 (task-7: "neve.py wired (rodar_galpao)") |
| Multi-span: N vãos (N≥1), colunas independentes no redim, vento Tab.7 | README.md:63 | lista/status | ok | `geometria.spans` (projeto_spec/rodar_galpao — D51, 2 vãos→3 colunas); REVISAO-MULTI-VAO.md NBR 6123 Tab.7 (task-7 item 20 ok) |
| Portal types: prismático, alma variável (web-tapered, DG25), tesoura (truss) | README.md:64 | lista/status | ok | alma_variavel.py, tesoura.py, dg25_ltb.py existem; gate6-alma-variavel/gate6-tesoura (rodar_galpao.py:954/:1248) |
| Foundations: sapata (NBR 6118), baldrame, estaca (3 métodos), divisa rasa (`sapata_divisa`) e profunda (`viga_equilibrio`) | README.md:65-66 | lista/status | corrigir | **"estaca (3 métodos)" → 1 método: Aoki-Velloso** (`capacidade_aoki_velloso` estaca_profunda.py:69; cabeçalho :3-4). Décourt-Quaresma é FLAG/trabalho futuro (REVISAO-INDICE.md:102-103). Demais itens ok (sapata/baldrame/sapata_divisa/viga_equilibrio existem — task-1) |
| Fire: ISO 834, ky/kE tabelados, proteção intumescente/spray | README.md:67 | norma | ok | fogo_nbr14323.py + REVISAO-FOGO.md (NBR 14323:2013 + ISO 834) |
| 3D Model: FreeCAD headless (`freecadcmd`) + MCP, auditoria de interferências | README.md:68 | lista/status | ok | montar_modelo com auto-fallback headless (rodar_projeto.py:210, :250); checa_interferencia (build_galpao.py:1625) |
| 2D Executive: TechDraw headless (`freecad.exe`) — pranchas A1, cortes seccionados hachurados, símbolos AWS A2.4 (arrow/other/both-side) | README.md:69-70 | lista/status | ok | rodar_executivo(spec, out, fcstd, freecad_exe=...) (rodar_projeto.py:263); corte seccionado "SvgHatch" (techdraw_exec.py:1247, task-9); glyph AWS arrow/other/both (REVISAO-EXECUTIVO-POLISH.md:64) |
| Zero-erro-de-método: valores de norma lidos verbatim do PDF em `pesquisa/` (nunca de memória); tabelas/equações ambíguas lidas por imagem de página | README.md:71-72 | processo | corrigir | **`pesquisa/` NÃO existe** (Test-Path negativo na raiz e em framework/galpao_fw; PDFs no repo: `Framework_Galpao_Modulos.pdf` na raiz e `libraries/standards/gerdau/...`). Método verbatim permanece como processo declarado nos REVISAO docs, mas o caminho citado não existe |
| "48 REVISAO-*.md para parecer sênior — itens 1–49 homologados" (correções acolhidas e refutações provadas com PDF) | README.md:73-74 | contagem | corrigir | Contagem "48 docs" confere (48 docs + índice = 49 arquivos; task-4 glob). **Nuance: itens 46 e 49 são PARECER, não HOMOLOGADO** (REVISAO-INDICE.md:61/:64) |
| Requirements: Windows, FreeCAD ≥ 1.1, Python 3.12, `uv` | README.md:78 | norma | ok | install.ps1:17 `CalcPython = "3.12"`; install.bat usa uv; README do workbench exige FreeCAD 1.1 |
| `numpy < 2` (pycufsm dependency) | README.md:79 | norma | ok | requirements.txt: "OBRIGATORIO: numpy<2 -- pycufsm 0.2.x nao roda em numpy 2.x"; `numpy==1.26.4` |
| MCP: `freecad-mcp` instalado por `install.ps1` | README.md:80 | processo | ok | install.ps1:181-182 "Installing freecad-mcp as a global uv tool" (`uv tool install --force`) |
| Docs: `wiki/` — LLM-oriented wiki (architecture, phases, decisions) | README.md:84 | caminho | corrigir | **`wiki/` na raiz NÃO existe; a wiki real é `framework/galpao_fw/wiki/`** (7 arquivos; Test-Path raiz=NÃO, framework/galpao_fw/wiki=SIM) |
| Docs: `framework/galpao_fw/wiki/revisoes/REVISAO-*.md` — per-module senior review docs | README.md:85 | caminho | corrigir | **`framework/galpao_fw/wiki/revisoes/` NÃO existe; os 49 REVISAO-*.md ficam em `framework/galpao_fw/`** (Get-ChildItem -Filter "REVISAO-*.md" = 49; Test-Path wiki/revisoes=NÃO) |
| Docs: `skills/build-warehouse/` — AI skill com workflow de 10 gates | README.md:86 | caminho | corrigir | **`skills/` NÃO existe** (Test-Path negativo); skills/projetos removidos no commit de limpeza `4343297` "clean: remove projetos, testes, wikis, skills - deixa so framework final" (2026-07-09) |

## 2. `framework/galpao_fw/COMO-RODAR.md` — 38 claims

| claim | arquivo:linha | tipo | veredito | correto (fonte) |
|---|---|---|---|---|
| CONCEITUAL: framework calcula/dimensiona/desenha; engenheiro responsável revisa e assina (ART); nada é projeto executivo | COMO-RODAR.md:3-4 | processo | ok | condiz com a arquitetura real (calcular/montar_modelo/rodar_executivo; carimbo ART em escopo.py) |
| PC novo: duplo-clique `install.bat` (ou `powershell -ExecutionPolicy Bypass -File install.ps1`) | COMO-RODAR.md:8-9 | API | ok | install.bat/install.ps1 existem; install.bat:9 executa exatamente esse comando |
| Instalador monta: servidor MCP do FreeCAD (uv tool) + workbench `RobustMCPBridge` | COMO-RODAR.md:11 | processo | ok | install.ps1:181-182 (uv tool freecad-mcp) e :220/:253 (copia RobustMCPBridge para o FreeCAD) |
| Instalador monta: ambiente Python em `framework/galpao_fw/.venv` (Python 3.12, `numpy<2`, `pycufsm`, `ezdxf`) — onde cálculo e DXF rodam | COMO-RODAR.md:12-13 | caminho | ok | requirements.txt (numpy==1.26.4, pycufsm>=0.2,<0.3, ezdxf>=1.3,<2); install.ps1:17/:40 (CalcPython 3.12, numpy<2); .venv não existe no worktree = esperado (gitignored; .gitignore:2-3) |
| Pré-requisitos: FreeCAD instalado; `uv` no PATH (ou `-InstallUvIfMissing`) | COMO-RODAR.md:15 | processo | ok | `[switch]$InstallUvIfMissing` no param de install.ps1; install.bat passa -InstallUvIfMissing |
| `.venv` NÃO vai no git — cada PC monta o seu pelo instalador | COMO-RODAR.md:17 | processo | ok | .gitignore:2-3 (`.venv/`, `**/.venv/`) |
| Projeto dirigido por spec (fonte única da verdade) | COMO-RODAR.md:21 | processo | ok | projeto_spec.py é o contrato de dados (task-7) |
| Fluxo: spec → validar (trava se faltar decisão) → calcular → montar_modelo → gerar_dxf | COMO-RODAR.md:24-28 | processo | corrigir | **`gerar_dxf` NÃO existe**. Fluxo real: spec → validar (projeto_spec.py:149) → calcular (rodar_projeto.py:16) → montar_modelo (:210) → **rodar_executivo** (:263, pranchas 2D + DXF via TechDraw.writeDXFPage techdraw_exec.py:1907) |
| Código: `import sys; sys.path.insert(0, "framework/galpao_fw")`; `import projeto_spec as PS, rodar_projeto as RP` | COMO-RODAR.md:33-34 | API | ok | projeto_spec.py e rodar_projeto.py existem no caminho citado |
| `s = PS.novo()` — spec com tudo PENDENTE (bloqueia) | COMO-RODAR.md:36 | API | ok | `def novo()` projeto_spec.py:76; validar() bloqueia PENDENTE (:149) |
| Gates do spec: terreno, geometria, cobertura, fechamento, aberturas, vento, ponte, cargas — ver `projects/galpao-nf982/work/spec_nf982.py` | COMO-RODAR.md:37-38 | caminho | corrigir | **`projects/galpao-nf982/` NÃO existe** (removido no clean `4343297`, 2026-07-09; `dir_projetos()` = raiz_repo()/projects cria em runtime — framework.py:25-27). Gates do spec: conferem (projeto_spec.py) |
| `RP.calcular(s, "projeto/exports/memoria")` — dimensiona + memoriais | COMO-RODAR.md:39 | API | ok | `def calcular(spec, out_dir)` rodar_projeto.py:16; gera memoriais por etapa + relatorio_consolidado (:380) |
| `RP.montar_modelo(s, "projeto/exports", "meu_galpao")` — FreeCAD aberto (MCP) | COMO-RODAR.md:40 | API | ok | `def montar_modelo(spec, out_dir, doc_name, ...)` rodar_projeto.py:210 |
| `RP.gerar_dxf(s, "projeto/exports/dxf", "meu_galpao")` — vistas DXF | COMO-RODAR.md:41 | API | corrigir | **Função inexistente**. DXF sai de `RP.rodar_executivo(s, out, fcstd)` (rodar_projeto.py:263) → `TechDraw.writeDXFPage` (techdraw_exec.py:1907-1908) |
| `calcular` e `gerar_dxf` NÃO precisam do FreeCAD (venv); `montar_modelo` precisa do FreeCAD aberto com ponte MCP (porta 9875) | COMO-RODAR.md:44-45 | processo | corrigir | `calcular` ✓ roda no venv puro; `montar_modelo` ✓ bridge XMLRPC porta 9875 (rodar_projeto.py:157, :211, :246). **`gerar_dxf` não existe e o DXF atual roda DENTRO do executivo FreeCAD** (TechDraw.writeDXFPage, headless — techdraw_exec.py:1907) |
| Pasta de projeto isolada nova: `framework.novo_projeto("slug")` | COMO-RODAR.md:47 | API | ok | `def novo_projeto(slug, base=None)` framework.py:46 |
| Exports: `memoria/` — memoriais PT por etapa + MEMORIAL-CONSOLIDADO com QUADRO DE VERIFICAÇÕES e "!!! NÃO ATENDEM !!!" se algo passar de 1,0 | COMO-RODAR.md:51-52 | lista/status | ok | relatorio_consolidado (rodar_projeto.py:380); flags "OK"/"NAO ATENDE" (:88-89) e utilização >1 → "NAO ATENDE" (:372) |
| Exports: `freecad/*.FCStd` + `step/*.step` — modelo 3D | COMO-RODAR.md:53 | lista/status | ok | `out_dir/freecad/{doc_name}.FCStd` (rodar_projeto.py:565); `step/{DOC_NAME}.step` (build_galpao.py:2050) |
| Exports: `takeoff/*.csv` — levantamento de material (aço) | COMO-RODAR.md:54 | lista/status | ok | `exports/takeoff/galpao_levantamento_material.csv` (build_galpao.py:1956-1968; subtotais aço/alvenaria/concreto) |
| Exports: `dxf/*.dxf` — pórtico, elevação, planta, corte (terças/telha), detalhes joelho e base, eixos numerados, níveis, quadros de verificações e materiais; camadas com cor fixa | COMO-RODAR.md:55-57 | lista/status | ok | DXF atual = exportação por página TechDraw (`TechDraw.writeDXFPage`, techdraw_exec.py:1907); a composição das vistas/quadros é herdada das pranchas executivas (descrição histórica da era dxf_vistas — conteúdo equivalente nas pranchas; nota) |
| Escopo tipologia: portal de 1 vão, 2 águas, base engastada/rotulada, com ou sem ponte rolante | COMO-RODAR.md:61 | lista/status | ok | tipologia base do rodar_galpao (parametros de geometria/base/ponte) |
| Faz: vento NBR 6123 (transversal + longitudinal, Cat I–V) | COMO-RODAR.md:63 | norma | ok | gate5-vento/gate5-vento-longitudinal (rodar_galpao.py:263-271); vento_nbr6123.py (task-1) |
| Faz: pórtico 1ª+2ª ordem (MAES) e redimensiona coluna/viga (HEA→HEB300/IPE550) | COMO-RODAR.md:64 | lista/status | ok | gate6-portico/gate6-2a-ordem (:274-278); gate7-redimensionamento (:285, "adota o par (coluna, viga) MAIS LEVE") |
| Faz: dimensiona base (placa/chumbadores/espessura), joelho (chapa/parafusos), terça (Ue), longarina (UPE + tirantes), escora/montante (HEA) | COMO-RODAR.md:65-66 | lista/status | ok | gate7-base, gate7-joelho, gate7-tercas (:403), gate7-secundarios (:524) |
| Faz: sapata isolada (NBR 6118) — tensão no solo + FS tombamento/deslizamento (Parte A); concreto: rigidez 22.6.1, armadura de flexão (22.6.3+17.2.2), compressão diagonal 19.5.3.1 (Parte B, sapata rígida) | COMO-RODAR.md:67-69 | norma | ok | gate7-fundacao (:750, envelope); REVISAO-FUNDACAO.md (item 1 do índice) |
| Faz: terças NBR 14762 (+ distorcional FSM), mão-francesa, contraventamento | COMO-RODAR.md:70 | norma | ok | gate7-tercas (:403, distorcional via pycufsm), gate7-mao-francesa (:323), gate7-contraventamento (:596) |
| Faz: modelo 3D com conexões detalhadas + auditor geométrico (mede a forma real e pega erro de conexão no build) | COMO-RODAR.md:71-72 | lista/status | ok | build_galpao.py com `checa_interferencia` (:1625); auditoria de interferências no 3D |
| Faz: DXF com quadros de verificação e materiais | COMO-RODAR.md:73 | lista/status | ok | pranchas TechDraw com QUADRO DE MATERIAIS (techdraw_exec.py:1507, :1546) e DXF via writeDXFPage (:1907) |
| Referência validada: `projects/galpao-nf982/` (20×10, ponte 100 kN) — roda ponta a ponta com todos os elementos ATENDENDO | COMO-RODAR.md:75-76 | caminho | corrigir | **`projects/galpao-nf982/` NÃO existe** (removido no clean `4343297`, 2026-07-09; pastas de projeto são criadas em runtime por `framework.novo_projeto`/`dir_projetos` — framework.py:25-27/:46) |
| NÃO faz — Fundação: sapata isolada JÁ dimensionada (rígida, NBR 6118), envelope por elemento (bearing pega N máx gravitacional; tombamento pega N mín + M) — ver `REVISAO-FUNDACAO.md`; faltam bloco sobre estacas/tubulão, sapata flexível (punção), detalhamento executivo da armadura | COMO-RODAR.md:80-83 | lista/status | corrigir | **Bloco sobre estacas IMPLEMENTADO** (fase 3, 2026-07-10; gate7-estaca rodar_galpao.py:800; REVISAO-FUNDACAO-PROFUNDA-INTEG.md:45); **punção IMPLEMENTADA** (D8, 2026-07-07; REVISAO-FUNDACAO.md §10, REVISAO-INDICE.md:80); **armadura executiva IMPLEMENTADA** (item 24 do índice — `fundacao_sapata.py` ancoragem+quadro, REVISAO-INDICE.md:39). **Tubulão segue fora de escopo** |
| NÃO faz — tipologias além do portal 1 vão (treliça, multi-vão, alma variável, mezanino, formado a frio como principal) | COMO-RODAR.md:84-85 | lista/status | corrigir | **Treliça IMPLEMENTADA** (fase 6.c, 2026-07-10, commit `820b0e0`; gate6-tesoura rodar_galpao.py:1248); **alma variável IMPLEMENTADA** (fase 6.b, 2026-07-10, commit `21d9941`; gate6-alma-variavel :954); **multi-vão IMPLEMENTADO** (D51, 2026-07-16, PR #12 — `geometria.spans`, 2 vãos→3 colunas). Seguem fora: mezanino, formado a frio como principal (sem módulo; task-1) |
| NÃO faz — ligações de fabricação (conexões 3D conceituais, sem furação/solda executiva) | COMO-RODAR.md:86-87 | lista/status | corrigir | **Fabricação IMPLEMENTADA**: PR #46 (MERGED 2026-07-22T11:58:57Z — "fabricacao - piece marks 3D + lista de corte + tolerancias [S17]"); D37 (2026-07-09, detalhe de ligação fabricação A+B); callouts de fabricação no smoke_executivo (joelho/gusset/console) |
| NÃO faz — fachadas/cortes longitudinais detalhados das paredes | COMO-RODAR.md:88 | lista/status | ok | continua verdadeiro: nenhum módulo de fachada (task-1); tapamento de parede existe só no IFC puro (PR #65, 2026-07-23, task-3) |
| NÃO faz — cargas especiais (sísmica, fadiga, térmica, ponte múltipla) | COMO-RODAR.md:89 | lista/status | corrigir | **Sísmica IMPLEMENTADA** (sismo_nbr15421.py, D18 2026-07-08; rodar_galpao.py:253-254); **fadiga IMPLEMENTADA** (ponte_rolante Anexo K, D10/D16 2026-07-08; REVISAO-PONTE.md §9); **térmica**: junta_dilatacao cobre movimento térmico (Bellei/FCC 65 — não é carga térmica plena); **ponte múltipla segue fora** (nbr8400/ponte_rolante — ponte única) |
| Regra "Ask, Do Not Invent": decisão de engenharia é campo do spec; `validar()` bloqueia enquanto houver PENDENTE | COMO-RODAR.md:93-94 | processo | ok | `def validar(spec)` projeto_spec.py:149; avisos de PENDENTE (:350-354) |
| Regra: Utilização = solicitação/resistência; ≤ 1,0 atende; memorial e quadro do DXF marcam "NÃO ATENDE" em vermelho quando passa de 1 | COMO-RODAR.md:95-96 | processo | ok | `_flag`/"NAO ATENDE" rodar_projeto.py:88-89; u>1 → "NAO ATENDE" (:372) |
| Propriedades de perfil (incl. UPE J/Cw) e alguns dados marcados A CONFIRMAR no catálogo do fornecedor — confirmar antes do executivo | COMO-RODAR.md:97-98 | processo | ok | perfis.py:6 "A CONFIRMAR com o catálogo europeu"; :63 "confirmar no catálogo do fornecedor" |
| Métodos extraídos das normas (`pesquisa/aço`); não de memória | COMO-RODAR.md:99 | processo | corrigir | **`pesquisa/` (e `pesquisa/aço/`) NÃO existe** (Test-Path negativo na raiz e em framework/galpao_fw); estaca_profunda.py:10/:27 confirma o *método* "lido do PDF", mas o caminho citado não existe no repo |

## 3. `framework/galpao_fw/REVISAO-INDICE.md` — 22 claims

| claim | arquivo:linha | tipo | veredito | correto (fonte) |
|---|---|---|---|---|
| Um markdown por módulo de cálculo; cada doc: escopo, itens da norma usados, fórmulas, código verbatim das rotinas e FLAGS/pendências | REVISAO-INDICE.md:3-6 | processo | ok | os 49 REVISAO-*.md em framework/galpao_fw/ seguem esse formato (task-4 glob) |
| CONCEITUAL: métodos extraídos das normas em `pesquisa/aço/` (não de memória) | REVISAO-INDICE.md:8-9 | processo | corrigir | **`pesquisa/aço/` NÃO existe** (Test-Path negativo); método "verbatim do PDF" confirmado no código (ex.: estaca_profunda.py:27), mas o caminho citado não existe |
| Índice declara 49 itens de revisão (linhas 15-64), todos com status ✅ HOMOLOGADO ou PARECER | REVISAO-INDICE.md:15-64 | contagem | ok | 49 itens (15-64); statuses: HOMOLOGADO (47) e PARECER (2: itens 46 e 49) — o claim diz exatamente "HOMOLOGADO ou PARECER" e confere |
| Item 1 REVISAO-FUNDACAO.md (NBR 6118): HOMOLOGADO r2 + features punção §10 + recalque §11 (2026-07-07) | REVISAO-INDICE.md:15 | lista/status | ok | REVISAO-FUNDACAO.md existe; punção = D8 (2026-07-07); recalque §11 (task-9: features D8-D22 ok, merges #1/#4) |
| Itens 2-17 (12 módulos r2, 2026-07-06/08): PÓRTICO (NBR 8800 An. D), CHECK-NBR8800, VENTO (NBR 6123), TERCAS (NBR 14762), SECUNDARIOS, BASE (NBR 8800 + AISC DG1 + ACI 318, 100% §9-§13), LIGACOES, PONTE (NBR 8800 + NBR 8400, fadiga Anexo K §9 + 50% lateral B.7.3.4 §9.1), MAO-FRANCESA, CONTRAVENTAMENTO, REDIMENSIONAMENTO (fix flecha H/150→H/300 Tab.C.1), JUNTA-DILATACAO (Bellei/FCC 65), SISMO (NBR 15421:2023 + envelope §6 NBR 8681), TELHA (NBR 14762), BALDRAME (NBR 6118), ESTACA (Aoki-Velloso/NBR 6122/6118) — todos HOMOLOGADO | REVISAO-INDICE.md:16-31 | lista/status | ok | descreve fielmente o índice (16 itens nas linhas 16-31, todos ✅ HOMOLOGADO; módulos correspondentes existem — task-1) |
| Itens 18-49 (32 módulos/features 2ª leva, 2026-07-10/13): MULTI-VAO, DIVISA, FOGO, CALHAS, PLATAFORMA, ESCADA, armadura, NEVE, ALMA-VARIAVEL, TESOURA, GUSSET, CONSOLE, FUNDACAO-PROFUNDA-INTEG, PONTE-8400, ALMA-VARIAVEL-INTEG, TESOURA-INTEG, COLUNA-TAPERED, ZONA-PAINEL, FLT-MISULA, VENTO-TESOURA, ALMA-ESBELTA, TENSAO-PONTO, CORTANTE-TAPERED, VENTO-ZONA-TESOURA, DG25-CROSSCHECK, ENRIJECEDOR-PAINEL, DG25-FULL, PROPS-MONO, DG25-ENVELOPE, FORCAS-LOCALIZADAS, VIGA-EQUILIBRIO, EXECUTIVO-POLISH — todos com parecer sênior | REVISAO-INDICE.md:33-64 | lista/status | ok | 32 itens (49-18+1) ✓; todos com status de parecer sênior no índice (HOMOLOGADO ou PARECER) |
| Item 45 REVISAO-PROPS-MONO.md: "11 testes" | REVISAO-INDICE.md:60 | contagem | ok | **11** `def test_` em tests/test_fase615_props_mono.py |
| Item 46 REVISAO-DG25-ENVELOPE.md: "PARECER 2 RODADAS — 2 CORRIGIDOS", "13 testes" | REVISAO-INDICE.md:61 | contagem | ok | **13** `def test_` em tests/test_fase616_dg25_envelope.py |
| Item 47 REVISAO-FORCAS-LOCALIZADAS.md: "HOMOLOGADO SEM IMPEDITIVOS", "11 testes" | REVISAO-INDICE.md:62 | contagem | ok | **11** `def test_` em tests/test_fase617_forcas_localizadas.py |
| Item 48 REVISAO-VIGA-EQUILIBRIO.md: "3 CORRIGIDOS + pele", "13 testes" | REVISAO-INDICE.md:63 | contagem | ok | **13** `def test_` em tests/test_fase618_viga_equilibrio.py |
| Item 49 REVISAO-EXECUTIVO-POLISH.md: "PARECER — 1 CORRIGIDO", "9 testes" | REVISAO-INDICE.md:64 | contagem | ok | **9** `def test_` em tests/test_fase619_glifo_solda.py |
| Módulos não-matemáticos (sem conferência de método): `frame2d` (validado contra solução fechada), `build_galpao`/`dxf_vistas`, `rodar_galpao`/`rodar_projeto`/`framework`, `projeto_spec`, `terreno` (KML), `perfis` | REVISAO-INDICE.md:66-69 | lista/status | corrigir | **`dxf_vistas` NÃO existe** — substituído por `techdraw_exec` (commits `cb890b6`/`e696b84`, 2026-07-09; git log --follow). Demais 9 módulos citados existem (task-1) |
| Features novas adicionadas após homologação r2 dos 12 módulos — TODAS HOMOLOGADAS (2026-07-07/08) | REVISAO-INDICE.md:73-76 | lista/status | ok | features 1-14 do índice (D8-D22); merges #1 (07-07) e #4 (07-10) cobrem o período (task-9) |
| 14 features listadas (L80-93): punção NBR 6118 19.5; recalque NBR 6122/Perloff; ancoragem NBR 6118 9.4.2; cone ACI 318 Ch.17; cortante-tríade NBR 8800 (Fakury cap.11); fadiga NBR 8800 Anexo K; junta Bellei 4.5/FCC 65; sismo NBR 15421:2023; furos NBR 8800 6.3.9/10/11; Cpe local NBR 6123 Tab.4/5; telha NBR 14762; sismo→envelope NBR 15421 5.4/NBR 8681; baldrame NBR 6118; estaca Aoki-Velloso/NBR 6122/6118 | REVISAO-INDICE.md:80-93 | lista/status | ok | 14 linhas nas linhas 80-93 (contadas) com os 14 itens citados; todas ✅ HOMOLOGADO no índice |
| Fixes de geometria do build 3D (calha invertida, telha sobre terças, chapa de ápice, regra de auditoria da calha) em `build_galpao.py`, verificados ao vivo no FreeCAD (0 interferências / 0 conexões suspeitas); registrado em `wiki/04-decisions.md` (D7) | REVISAO-INDICE.md:95-98 | lista/status | ok | `wiki/04-decisions.md` existe (framework/galpao_fw/wiki/04-decisions.md, Test-Path SIM); build_galpao.py existe |
| Análise de lacunas ENCERRADA (2026-07-08): fechadas 3 pequenas (furos, Cpe local, telha), 2 médias (sismo→envelope, baldrame) e 1 grande (fundação profunda) | REVISAO-INDICE.md:100-102 | lista/status | ok | task-9: "Lacunas de escopo TODAS FECHADAS — D14/D31/D28/D16/D12/D26 conferem com o código" |
| Resíduos como FLAG: Décourt-Quaresma (2º método de estaca), biela/punção do bloco, efeitos de grupo/atrito negativo da estaca — trabalhos futuros, não bloqueiam | REVISAO-INDICE.md:102-105 | lista/status | ok | consistente com o código: estaca_profunda.py implementa só Aoki-Velloso (:69); Décourt-Quaresma ausente (task-1) |
| Base "100 % completa nos modos do concreto (§9-§13)" | REVISAO-INDICE.md:105 | lista/status | ok | REVISAO-BASE.md:21 "100% HOMOLOGADO §9-§13" |
| "27 módulos matemáticos + features — TODOS HOMOLOGADOS (2026-07-08)" | REVISAO-INDICE.md:109 | contagem | ok | 27 = itens 1-27 do índice (17 + 10) ✓ internamente consistente; data é snapshot de 07-08 (itens 28-49 posteriores têm datas próprias no índice — nota) |
| "Pipeline: 23 gates, 35 módulos totais (incl. não-matemáticos: frame2d, build, dxf, rodar, projeto_spec, perfis, framework)" | REVISAO-INDICE.md:110-111 | contagem | corrigir | **Gates atuais: 40 saídas `gate*.txt` em rodar_galpao.py** (gates 5-9 + sub-gates + gate-calha/terreno/zona-painel). **Módulos totais: 135** (task-1). "23 gates/35 módulos" era o estado 2026-07-08 |
| "Testado end-to-end: galpão 24×12m → FreeCAD 669 obj, 0 interferências, 20.156 kg aço" | REVISAO-INDICE.md:111-112 | contagem | não verificado (fonte ausente) | Claim datado (2026-07-08). Nenhum teste atual referencia "20156" ou o cenário 24×12 (grep em tests/ vazio); smoke_executivo roda 7 casos, não 24×12. Sem rerun nesta revisão (todo 18 cobre smoke/executivo) — não corrigido, apenas sinalizado |
| "Última atualização: 2026-07-08" | REVISAO-INDICE.md:114 | lista/status | corrigir | **Última atualização real: 2026-07-13** — itens 45-49 do próprio índice datados 07-13 (REVISAO-INDICE.md:60-64); último commit no arquivo `01e14e7` (2026-07-13, "fix(executivo): glyph de solda AWS A2.4...") |

## 4. `UPSTREAM.md` (raiz) — 9 claims

| claim | arquivo:linha | tipo | veredito | correto (fonte) |
|---|---|---|---|---|
| O instalador faz vendoring do projeto "FreeCAD Robust MCP" | UPSTREAM.md:3 | processo | ok | install.ps1:220-253 copia `freecad-addon-robust-mcp-server/freecad/RobustMCPBridge` para o workbench do FreeCAD |
| Origem upstream: `https://github.com/spkane/freecad-addon-robust-mcp-server` | UPSTREAM.md:6 | caminho | ok | pasta vendered `freecad-addon-robust-mcp-server/` existe com o layout do projeto (Test-Path SIM; não houve fetch da URL — claim de origem, estrutura local confirma) |
| Código vendered fica em `freecad-addon-robust-mcp-server/` | UPSTREAM.md:12 | caminho | ok | Test-Path SIM (raiz do worktree) |
| Antes de publicar ZIP release: atualizar a pasta vendered e rodar `install.ps1 -Help` e `install.ps1 -WhatIf` | UPSTREAM.md:15-21 | API | ok | install.ps1 tem `[switch]$Help` (param, linha 3) e `SupportsShouldProcess = $true` (WhatIf; documentado em Show-Usage "Preview actions without writing") |
| Manter arquivos de licença upstream no diretório vendered | UPSTREAM.md:23 | processo | ok | LICENSE-CODE e LICENSE-ICON presentes na pasta vendered |
| Wrapper carrega mudanças locais no workbench vendered para o FreeCAD 1.1 carregar o bridge de forma confiável no Windows | UPSTREAM.md:27-28 | lista/status | ok | install.ps1:253 copia o workbench; processo declarado no UPSTREAM — consistente com a pasta e o instalador |
| Patches locais em: `freecad/RobustMCPBridge/Init.py`, `InitGui.py`, `__init__.py` (defensivo `FreeCAD.GuiUp`), `freecad_mcp_bridge/server.py` | UPSTREAM.md:30-34 | lista/status | ok | os 4 arquivos existem; `FreeCAD.GuiUp` defensivo confirmado: `__init__.py:117-129` e `server.py:70/:133/:425/:555` |
| `preferences.py`: `DEFAULT_AUTO_START = True` (upstream default é `False`) | UPSTREAM.md:35 | lista/status | ok | `preferences.py:37: DEFAULT_AUTO_START = True` (lido); usado em `set_auto_start(DEFAULT_AUTO_START)` :150 |
| Máquina com param `RobustMCPBridge/AutoStart` em `user.cfg` mantém seu valor; o default só afeta primeira execução em perfil novo | UPSTREAM.md:38-40 | processo | ok | `get_param().GetBool("AutoStart", DEFAULT_AUTO_START)` preferences.py:55 — default só aplica quando não há valor salvo; consistente |

## 5. `tools/README.md` (raiz) — 12 claims

| claim | arquivo:linha | tipo | veredito | correto (fonte) |
|---|---|---|---|---|
| Testes marcados `build` são 9, em `framework/galpao_fw/tests/` | tools/README.md:5 | contagem | corrigir | **18 marcas `pytest.mark.build` em 17 arquivos** de `framework/galpao_fw/tests/` (task-2; re-verificado: 18 ocorrências / 17 arquivos; `test_build_federado.py` tem 2) |
| Testes build constroem modelo 3D no FreeCAD (`freecadcmd.exe`) e verificam invariantes de geometria, inclusive interpenetração de peças (`checa_interferencia`) | tools/README.md:5-7 | lista/status | ok | `checa_interferencia` build_galpao.py:1625; testes usam freecadcmd (task-2: 17 arquivos com marcador build) |
| Testes build são lentos (~5 min) e ficam deselected no regresso padrão | tools/README.md:7-8 | lista/status | ok | task-2: 21 deselecionados (18 build + 3 crashes na lane 1) na suíte non-build |
| Green bar do dia a dia: `python -m pytest tests/ -m "not build"` | tools/README.md:11 | API | ok | comando válido (task-2 usou equivalente com `-p no:cacheprovider`); suíte roda (1 falha F1 fitz) |
| Regressões de geometria 3D passam em silêncio; 2 bugs de interferência calha/condutor (condutor Ø150 × chapa de base; calha/condutor × coluna tapered) sobreviveram várias sessões | tools/README.md:14-16 | lista/status | ok | claim histórico do job periódico (S18, PR #49/#51, 07-22 — task-9); correto como motivação do job; bugs já corrigidos depois (fixes em gate-calha/condutor) |
| `run_build_suite.ps1` roda `pytest -m build`, grava log com timestamp em `tools/build-logs/` (ignorado no git) e resumo em `build-logs/LATEST.txt`; exit code = do pytest | tools/README.md:20-21 | processo | ok | script real: `$logdir = Join-Path $PSScriptRoot "build-logs"` e `$latest = ...\LATEST.txt` (tools/run_build_suite.ps1:31/:36/:41); .gitignore:58 `tools/build-logs/`; dir criado em runtime (não versionado) |
| Testes usam `freecadcmd` em subprocessos isolados, não o bridge da porta 9875; não mexe no FreeCAD aberto | tools/README.md:22-23 | processo | ok | comentário do próprio script (run_build_suite.ps1:13) + testes com freecadcmd (task-2) |
| `register_build_task.ps1` registra/remove a tarefa agendada Windows `GalpaoFW-BuildSuite`; local (não CI de nuvem) porque exige FreeCAD 1.1 instalado | tools/README.md:24-26 | processo | ok | script real: `$nome = "GalpaoFW-BuildSuite"` (register_build_task.ps1:39); PR #49 MERGED (07-22) — task-9 |
| Uso: `powershell -ExecutionPolicy Bypass -File tools\run_build_suite.ps1` | tools/README.md:32 | API | ok | arquivo existe em `tools/` (raiz do repo; task-6: "raiz do worktree, NÃO framework/galpao_fw/tools") |
| Uso: `register_build_task.ps1` (job semanal domingo 03:00 default); variações `-Frequencia Daily -Hora 02:00`, `-Remover` | tools/README.md:35-39 | API | ok | params reais: `Frequencia` (Weekly/Daily), `Dia` (default Sunday), `Hora` (default 03:00), `Remover` (register_build_task.ps1:30-35) |
| Uso: `Start-ScheduledTask -TaskName GalpaoFW-BuildSuite`; `Get-Content tools\build-logs\LATEST.txt` | tools/README.md:42-43 | API | ok | nome da tarefa = GalpaoFW-BuildSuite (script:39); LATEST.txt escrito pelo runner (run_build_suite.ps1:36/:41) |
| Se `freecadcmd.exe` não estiver no caminho padrão: `-FreeCadCmd <path>` ou env `FREECADCMD` | tools/README.md:46-47 | API | ok | param `[string]$FreeCadCmd` (run_build_suite.ps1:24-25) e FREECADCMD respeitado (comentário :18) |

## 6. `framework/galpao_fw/tools/README.md` — 6 claims

| claim | arquivo:linha | tipo | veredito | correto (fonte) |
|---|---|---|---|---|
| `run_tests.py` roda a suíte `-m "not build"` (~1281 testes) | tools/README.md:5 | contagem | corrigir | **Suíte atual: 1353 selecionados / 1374 coletados / 1340 passed / 1 failed / 15 skipped** (2026-08-11, task-2). "~1281" era o estado S40; lane rápida cresceu +72 |
| Comandos: `python tools/run_tests.py`; `python tools/run_tests.py -x -k terca` | tools/README.md:9-10 | API | ok | `framework/galpao_fw/tools/run_tests.py` existe (task-6); runner passou args extras ao pytest (task-2) |
| Com `pytest-xdist`: paraleliza tudo num comando — ~5 min em 8 núcleos (vs ~15 min sequencial); suíte xdist-safe (verificado S40: 1281 passed com `-n auto`) | tools/README.md:13-15 | contagem | corrigir | Números de S40 desatualizados: suíte atual 1353 sel/1340 pass (task-2). **xdist NÃO instalado no .venv nesta revisão** — caminho xdist não re-verificado; claim "1281 passed" histórico (task-2 nota de dependências) |
| Fallback (sem xdist): 2 lanes — `test_fase*` + `test_crashes_wiki07` (243 testes, ~20 s cada, rodam `rodar_projeto.calcular` completo) isolados dos 1038 rápidos | tools/README.md:16-18 | contagem | corrigir | "243 testes" ✓ (lane 2 = 243 selecionados, task-2); **"1038 rápidos" → 1110 selecionados na lane 1 atual** (task-2). **F2: o glob `tests/test_fase*.py` do runner QUEBRA em shell Windows** (PowerShell não expande glob → "no tests ran"; task-2 F2) |
| Toolchain: `pip install -r requirements.txt -r requirements-dev.txt` | tools/README.md:23 | API | ok | requirements.txt e requirements-dev.txt existem em framework/galpao_fw/ |
| Testes de build 3D (`-m build`, exigem FreeCAD) ficam de fora — rodam à parte | tools/README.md:26 | lista/status | ok | 18 deselecionados na suíte non-build (task-2); job periódico tools/run_build_suite.ps1 roda `-m build` à parte |

---

## Contagem real de REVISAO-*.md no disco vs índice

**Glob real (PowerShell):** `Get-ChildItem framework\galpao_fw -Filter "REVISAO-*.md"` → **49 arquivos**.

Detalhamento: 48 documentos de módulo + `REVISAO-INDICE.md` (o próprio índice) = 49 arquivos.

| Declaração | Fonte | Valor declarado | Real no disco | Veredito (todo 10) |
|---|---|---|---|---|
| Índice com 49 itens (1–49) | REVISAO-INDICE.md:15-64 | 49 itens | 49 arquivos | **ok** (48 docs + índice) |
| "48 REVISAO-*.md" | README.md:73 | 48 docs | 49 - 1 (índice) = 48 docs | **ok** (48 docs + índice = 49) |
| "itens 1–49 homologados" | README.md:10, 73 | 49 itens | 49 | **corrigir** — itens 46 e 49 são PARECER, não HOMOLOGADO (REVISAO-INDICE.md:61/:64) |

## Caminhos referenciados — verificação de existência (com veredito do todo 10)

| Caminho | Referenciado em | Existe no worktree? | Veredito |
|---|---|---|---|
| `framework/galpao_fw/wiki/revisoes/` | README.md:85 | **NÃO** (REVISAO docs reais ficam em `framework/galpao_fw/`) | corrigir |
| `skills/build-warehouse/` (raiz) | README.md:86 | **NÃO** (removido no clean `4343297`, 2026-07-09) | corrigir |
| `wiki/` (raiz) | README.md:84 | **NÃO** (wiki real em `framework/galpao_fw/wiki/`) | corrigir |
| `pesquisa/` (raiz) | README.md:71; COMO-RODAR.md:99; REVISAO-INDICE.md:9 (`pesquisa/aço`) | **NÃO** (nem na raiz nem em framework/galpao_fw) | corrigir |
| `projects/galpao-nf982/` | COMO-RODAR.md:38, 75 | **NÃO** (removido no clean `4343297`; `dir_projetos()` cria em runtime — framework.py:25-27) | corrigir |
| `tools/build-logs/` | tools/README.md:21, 43 | **NÃO** (gerado em runtime pelo runner, ignorado no git — .gitignore:58) | ok |
| `framework/galpao_fw/.venv` | COMO-RODAR.md:12 | **NÃO** (declarado fora do git — esperado; .gitignore:2-3) | ok |
| `install.bat` | README.md:16; COMO-RODAR.md:8 | **SIM** | ok |
| `install.ps1` | README.md:80; COMO-RODAR.md:9; UPSTREAM.md:19-20 | **SIM** | ok |
| `freecad-addon-robust-mcp-server/` | UPSTREAM.md:12 | **SIM** | ok |
| `framework/galpao_fw/tests/` | tools/README.md:5 | **SIM** (136 arquivos test_*.py) | ok |
| `tools/run_build_suite.ps1` | tools/README.md:20, 32 | **SIM** (na RAIZ do repo, não em framework/galpao_fw/tools — task-6) | ok |
| `tools/register_build_task.ps1` | tools/README.md:24, 35 | **SIM** (na RAIZ do repo — task-6) | ok |
| `framework/galpao_fw/tools/run_tests.py` | galpao tools/README.md:9 | **SIM** | ok |
| `framework/galpao_fw/projeto_spec.py` / `rodar_projeto.py` | README.md:21-22; COMO-RODAR.md:34 | **SIM** | ok |

## Contexto extra de disco (registro cru, vereditado pelo todo 10)

| Medida | Comando | Resultado | Veredito |
|---|---|---|---|
| Arquivos `REVISAO-*.md` em `framework/galpao_fw` | `Get-ChildItem -Filter "REVISAO-*.md"` | **49** | ok (48 docs + índice — README:73 ok na contagem) |
| Arquivos `.py` no nível raiz de `framework/galpao_fw` | `Get-ChildItem -Filter "*.py" -File` | **135** (contraste com "53 Python modules", README.md:3) | **corrigir** README.md:3 → 135 |
| Marcas `@pytest.mark.build` em `framework/galpao_fw/tests/*.py` | `Select-String` | **18** em 17 arquivos (contraste com "9" testes build, tools/README.md:5) | **corrigir** tools/README.md:5 → 18 marcas/17 arquivos |

## QA interno (re-leitura de amostra — 12 claims)

Re-verificação por `Select-String -SimpleMatch` nos arquivos-fonte (linha confere):

| Claim | Padrão | Linha esperada | Linha encontrada | OK |
|---|---|---|---|---|
| pytest 245 passed | `pytest 245 passed` | 10 | 10 | ✔ |
| 48 REVISAO-*.md | `48 REVISAO` | 73 | 73 | ✔ |
| numpy < 2 | `numpy < 2` | 79 | 79 | ✔ |
| skills/build-warehouse 10-gate | `10-gate` | 86 | 86 | ✔ |
| ponte MCP porta 9875 | `9875` | 45 | 45 | ✔ |
| HEA→HEB300/IPE550 | `HEB300` | 64 | 64 | ✔ |
| galpao-nf982 20×10 | `20×10` | 75 | 75 | ✔ |
| 23 gates | `23 gates` | 110 | 110 | ✔ |
| 20.156 kg aço | `20.156` | 112 | 112 | ✔ |
| 9 testes build | `marcados \`build\` (9` | 5 | 5 | ✔ |
| 1281 passed | `1281 passed` | 15 | 15 | ✔ |
| DEFAULT_AUTO_START = True | `DEFAULT_AUTO_START = True` | 35 | 35 | ✔ |

Resultado: 12/12 linhas conferem (a extração); o **conteúdo** foi vereditado pelo todo 10 contra o código/task-1/2/3/7/9.

## Declarações finais

- **Total de claims extraídos:** 123 (README 36, COMO-RODAR 38, REVISAO-INDICE 22, UPSTREAM 9, tools/README raiz 12, galpao tools/README 6). *(O task-4 original declarou 118 — erro de aritmética na seção README: 31 declarados, 36 linhas reais; total real 123.)*
- **Vereditos (todo 10):** 91 **ok** · 31 **corrigir** · 0 faltante · 0 obsoleto · 1 **não verificado (fonte ausente)** (REVISAO-INDICE.md:111-112, e2e 24×12m — sem rerun nesta revisão). Distribuição por arquivo e tabela de correções completas em `task-10-revisao-wiki.md`.
- **Contagem REVISAO-*.md no disco:** 49 (48 módulos + índice) — compatível com os 49 itens do índice (REVISAO-INDICE.md:15-64) e com os "48 REVISAO-*.md" do README.md:73.
- **Caminhos verificados:** existem — `install.bat`, `install.ps1`, `freecad-addon-robust-mcp-server/`, `framework/galpao_fw/tests/`, scripts de tools (na raiz do repo); NÃO existem — `wiki/`, `framework/galpao_fw/wiki/revisoes/`, `skills/build-warehouse/`, `pesquisa/`, `projects/galpao-nf982/`, `tools/build-logs/` (runtime), `.venv` (runtime).
- **Nenhum arquivo dos 6 documentos foi editado; nenhum commit.** Veredito e correções ficam neste ledger (in loco) e na evidência task-10; a aplicação das correções é do todo 17.
