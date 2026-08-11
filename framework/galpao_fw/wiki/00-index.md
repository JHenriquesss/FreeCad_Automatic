# galpao_fw — LLM wiki

**Pitch:** Framework Python que projeta um galpão industrial **turnkey multi-disciplina** fim-a-fim. Começou como galpão de aço (pórtico 2D → 2ª ordem MAES → NBR 8800 por peça → secundários/base/fundação → 3D FreeCAD + IFC + memorial PT) e cresceu para **6 verticais** — concreto (NBR 6118/9062, pré-moldado+protensão), aço (NBR 8800/14762), elétrico (NBR 5410/14039/5419), incêndio/AVCB (NBR 10898/16820/17240/10897/13714), hidráulica predial (NBR 5626/8160/10844) e climatização (NBR 16401) — orquestrados por um **`galpao_turnkey.rodar(spec)`** que consolida gates e monta o **modelo federado** (IFC + 3D + clash); o **caderno executivo único** (pranchas A1 TechDraw de todas as disciplinas) é montado pelo módulo separado `caderno_turnkey` (via fitz). Cada vertical é stateless: `rodar/membros_bim/emitir_bim/montar_pranchas` + `_selftest` aferido contra livro/norma. Engenheiro roda; sênior revisa e assina (ART). Saídas PT, SI (m, kN).

Cwd primário: `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic\framework\galpao_fw`. Git root: um nível acima. Norma-fonte: PDFs no NotebookLM (via `nlm` CLI) — **nunca de memória** (regra AR300). Push a `main` bloqueado → sempre branch+PR+merge.

## TOC
- [[01-architecture]] — spec-driven, cadeia de módulos, envelope, MAES, calc/model split
- [[02-test-tree]] — `_selftest()` por módulo, o que cada um assere
- [[03-phases]] — fases fechadas: revisão sênior 12 módulos (r2) · features pós-homolog · análise de lacunas (gaps+FLAGs) · **projeto executivo 2D (TechDraw)** · handoff/aguarda pareceres
- [[04-decisions]] — log de decisões/fixes normativos (D0–D45)
- [[05-glossary]] — termos de domínio (pórtico, MAES, ELU/ELS, FLT, Lb, sapata rígida, estaca, biela…)
- [[06-open-threads]] — T41 revisão da wiki (2026-08-11), T40 janela dupla-conversão (✅ resolvido #150), T40b saturação (padrão, parcial), T22 S19 IFC/BIM, T21 gaps A3/C5, backlog

> Wiki mantida na estrutura do skill (00–07 + revisoes/). Relatórios de trabalho (`PR_45_46_Review`, `PR_47_Review`, `PR_49_Review`, `PR_51_54_Review`, `PR_55_61_Review`) foram **consolidados aqui e integrados** — precedente: 2026-07-15 (07-/08-/review_completo) e 2026-07-21 (PR_44_Review).


## Estado atual (2026-08-11) — Revisão da wiki

Revisão completa dos 7 arquivos (00–06) contra o código (135 módulos — task-1), a suíte
(`tools/run_tests.py`: **1353 selecionados / 1340 passed / 1 failed [F1: test_dossie_unico sem
fitz] / 15 skipped** — task-2) e git/GitHub (171 PRs MERGED; arqueologia S19→2026-08-11 — task-3).

**Discrepâncias corrigidas: 68** (ledger task-5, 430 claims: 123 ok / 49 corrigir / 13 obsoleto /
1 não verificado / 5 não-localizados registrados no task-5-update). Top 15 por severidade
(obsoleto/erro-factual primeiro; ordem determinística por arquivo:linha; truncado em 15 de 68):

1. 00-index:173 — PR #12 "NÃO mergeado" → MERGED `4165652` (07-18)
2. 00-index:184-187 — plano `check_trelica_estatica` nunca implementado (2º caso resolvido em T15/D57)
3. 00-index:228 — "PENDENTE merge PR #5" → MERGED `50df273` (07-14)
4. 00-index:243 — "PENDENTE merge PR #1+#4" → MERGED `4fde82b`/`aa02180`
5. 03-phases:232 — "DrawViewSection FALHA headless" → revertido em D40 (fase 5)
6. 03-phases:260-263 — bloco "ATUAL — Handoff" + "PR #1 ainda aberto" → MERGED
7. 06:T21 — "ABERTO: merge PR #54" → MERGED, conteúdo na main via #55
8. 06:T20 — "ABERTO: merge PR #49" → MERGED, via #51
9. 06:T19 — "ABERTO: merge PR #47" → MERGED
10. 06:T16 — latente `telha_tipo` → resolvido (projeto_spec.py:769-775)
11. 06:T14 — "PR #12 NÃO mergeado; 2º caso PENDENTE" → MERGED + resolvido (T15/D57)
12. 06:T1 — "PR #1 aguarda merge" → MERGED
13. 06:T3/T4 — backlog ponte/fadiga → automatizados (D39/D47/D10/D16/D62)
14. 00-index:149-153 — "sem commit — árvore de trabalho" FALSO → 6 commits reais (8bd725f…)
15. 00-index:3 — `galpao_turnkey.rodar()` citado montando caderno executivo → `caderno_turnkey` é
    módulo separado (via fitz)

Contagens históricas (770+511 / 831 / 723 / 714 / 702 / 643 / 256 / 245 / 1281) atualizadas
para a suíte real 1353/1340/1/15 (task-2/task-8); D74–D79 criadas em 04-decisions (task-15 —
os links `[[04-decisions#D74]]`..`[[#D79]]` agora resolvem); T22/T41 criadas em 06-open-threads
(task-16 — `[[06-open-threads#T22]]` resolve).

**Arco pós-2026-08-04 (hiato de 5 dias — reconstruído do git, task-3):**
- **S41 — Fixes de desenho/pranchas + planta elétrica (PRs #154–#161, merged 2026-08-09):** escape
  &<> no SVG (unifilar XML malformado); carimbo elétrico vazava ESTRUTURAL; proveniência
  `bacia_caixa=0,96`; centraliza quadros; escape &<> em incêndio/clima/coord; planta de
  iluminação e tomadas; fecha 4 gaps da planta elétrica (QDC, bitola/eletroduto, leiaute, 3D/BIM).
- **S42 — Dez módulos de engenharia (PRs #162–#171, merged 2026-08-09):** piso industrial,
  geotecnia SPT, orçamento 5D, compatibilização BCF-like, fotovoltaico, saneamento,
  terraplenagem, cronograma 4D, caderno de encargos, pacote legal. HEAD `6358157` = merge #171.


## Estado atual (2026-08-03) — Sessões 20–40: os 6 verticais + turnkey federado + hardening

Arco consolidado do git (reconstrução 2026-08-11) — *(memory/ NÃO versionado no repo; o
registro fino de S16→S40 foi reconstruído do git nesta revisão)*. **De galpão-de-aço para
turnkey multi-disciplina.**

- **S20 — Vertical de CONCRETO (PRs #81–#101):** galpão pré-moldado engastado. Pilar em
  flexão composta reta+**oblíqua/biaxial** (17.2.5, α=1,2) → viga CA → sistema stateless →
   BIM IFC4 → executivo (quadro+memorial+SVG) → **PROTENSÃO** (pré-tração vãos >12 m). **153 testes
   no grupo concreto** (17 arquivos; protensão estrita: 31 — 2026-08-11), fixtures
   Bastos/Araújo/Carvalho. 3D SÓLIDO + pranchas A1 TechDraw. `vertical-concreto`.
- **S21–26 — Vertical ELÉTRICO (PRs #102–#106):** notebook próprio (c5934f22). 9 módulos
  (cargas/condutores/curto/proteção/FP/subestação MT/aterramento/SPDA/**luminotécnica NBR 8995**)
   + BIM + 3D + executivo A1. Condutores até 300 mm² + paralelo. Suíte 2026-08-11: **1353
   selecionados / 1340 passed / 1 failed / 15 skipped**. `vertical-eletrico`.
- **S27–30 — Vertical INCÊNDIO/AVCB (PRs #107–#110):** emergência (10898) + sinalização (16820)
  + alarme (17240) + sprinklers (10897) + hidrantes (13714), orquestrados; + iluminação externa
  (5101) e climatização (16401) standalone. `vertical-seguranca-incendio`.
- **S32 — TURNKEY (PR #112):** `galpao_turnkey.rodar(spec)` despacha TODOS os verticais,
  consolida gates + ATENDE global; falha isolada por disciplina; **modelo federado** (IFC + 3D +
  clash AABB com triagem esperado×revisar). `galpao-turnkey-orquestrador`.
- **S36 — CADERNO ÚNICO (PR #116):** `caderno_turnkey` (capa+índice+pranchas A1 de todas as
  disciplinas num PDF, via fitz), montado ao vivo no freecad.exe.
- **S38 — Revisão total (PR #118):** drawing-vs-data na planta de incêndio + guards de entrada
  degenerada (geometria/tensão/área/Fu=0 → ValueError) em 4 orquestradores. `revisao-total-s38`.
- **S39 — HIDRÁULICA + COORDENAÇÃO (PRs #136–#147):** destravou o dimensionamento hidráulico
  (NBR 5626:2020 SEM método dos pesos → v≤3 m/s; 8160 UHC; 10844 Q=i·A/60) + água quente SPAFAQ
  + prancha A1 de coordenação do federado + reservatório vira torre elevada no render. Revisão NLM
  achou 2 gaps (DN75 vertical, declividade mín). `hidraulica-e-coordenacao-s39`.
- **S40 — HARDENING (PR #148 + auditoria):** caça à **saturação silenciosa** (tabela satura no
  maior valor + gate que não reprova + OK=True): fechou terça-ELS/flecha (aço, veredito global de
  `rodar_galpao`) e placa de sinalização (incêndio); concreto verificado limpo. **1ª auditoria NLM
  formal de concreto/aço** (notebook Diretrizes bf7feaa3): As_max pilar, flecha terça L/180-L/120,
  drift H/300, flexo-compressão 5.5.1.2 — TODOS batem. `saturacao-silenciosa-padrao`,
  `auditoria-nlm-concreto-aco-s40`.
- **S40 — Janela dupla-conversão (PR #150):** fechou a T40 — `janelas_laterais` unificada na
  convenção **FAIXA** (canônica); conversão (L,H)→faixa só no wizard via `_janela_band`;
  `aberturas_para_build` virou pass-through (matou a reconversão que #144 abrira). Suíte 100% verde.
- **S40 — Runner de regressão confiável (PR #152):** `tools/run_tests.py` — a suíte non-build
  (2026-08-11: 1353 selecionados; 23 arquivos pesados — 22 `test_fase*` + `test_crashes_wiki07` —
  a ~20 s cada estouravam o limite de foreground do ambiente ao rodar sequencial). PRIMÁRIO:
  **pytest-xdist `-n auto`** (a suíte é xdist-safe, verificado S40: 1281 passed; 2026-08-11:
  1340 passed) → ~5 min, UM comando. FALLBACK sem xdist: 2 lanes
  (rápidos primeiro, pesados isolados depois). `requirements-dev.txt` + `tools/README.md`.
  Substitui o antigo "tocados + m-z na mão".

**Validado ao vivo (S40):** caderno turnkey completo no freecad.exe — 6 disciplinas + coordenação,
26 páginas, 14 pranchas A1, render 3D, render-and-look confirmando HID/CLI/COORD. **Regressão
pós-#150: suíte completa VERDE** (2026-08-11: 1353 selecionados / 1340 passed / 1 failed [F1 fitz]
/ 15 skipped; os shards a-l 770 / m-z 511 da época não são re-deriváveis — a falha pré-existente
da janela eliminada).

---

## Estado anterior (2026-07-23) — Sessão 19: Interoperabilidade BIM e IFC4 Físico/Estrutural (PRs #55 a #61 MERGED)
Revisão e integração completas. **TODOS OS PRS DA SESSÃO 19 (#55 A #61) FORAM REVISADOS, APROVADOS E MERGEADOS EM `main`**. **Suíte completa: 1353 selecionados / 1340 passed / 1 failed / 15 skipped (2026-08-11; 831 na época)**.
Tema central: **"interoperabilidade BIM / IFC4 físico e analítico direto do cálculo, sem dependência do FreeCAD GUI"**.
- **PR #55 (`feat/gaps-e-wiki-para-main`):** cherry-pick dos Gaps A3/C5 e da wiki da Sessão 18 para a `main`. [[04-decisions#D74]]
- **PR #56 (`feat/ifc-export-bim`):** exportador IFC4 (BIM) no `build_galpao.export()` consumindo o `ifc_map.py` (mapeamento semântico de marcas $C1, V1...$ para categorias `IfcColumn`, `IfcBeam`, `IfcMember`, `IfcPlate`, `IfcFooting`, `IfcPile`, `IfcCovering`, `IfcMechanicalFastener`). Gerou IFC4 de 1,67 MB com 789 elementos no modelo real. [[04-decisions#D75]]
- **PR #57 / PR #59 (`feat/bridge-headless`):** `montar_modelo` com auto-fallback headless (`bridge` $\rightarrow$ `freecadcmd`). Elimina a necessidade de manter o FreeCAD GUI aberto com o bridge na porta 9875. [[04-decisions#D76]]
- **PR #58 (`feat/ifc-emissor-puro`):** modelo neutro de dados (`modelo_neutro.py`) + emissor IFC4 **puro-Python** (`ifc_emit.py` via `ifcopenshell`). Emite o arquivo IFC4 BIM da estrutura primária direto do cálculo, sem invocar o FreeCAD. [[04-decisions#D77]]
- **PR #60 (`feat/ifc-secundarios`):** estende o modelo neutro (funções reais `tercas`/`girts`/`tirantes_parede`/`contrav_cobertura`/`frame_completo` em `modelo_neutro.py` — o nome `secundarios_lineares` não existe) e o emissor puro para incluir terças, girts de parede, tirantes e contraventamento como `IfcMember` com perfil/marca reais no IFC puro. [[04-decisions#D78]]
- **PR #61 (`feat/modelo-analitico`):** modelo analítico estrutural via `galpao_portico.modelo_analitico()` + `ifc_emit.emitir_ifc_analitico` (não é módulo próprio — função + emissores; task-9/D79) com `IfcStructuralAnalysisModel`, `IfcStructuralPointConnection`, `IfcStructuralCurveMember`, `IfcStructuralBoundaryNodeCondition`, `IfcStructuralLoadCase`. Gera automaticamente `galpao.ifc` (BIM físico) e `galpao_analitico.ifc` (BIM estrutural p/ SAP2000/Eberick/Robot) em `EXPORT_DIR/ifc/`. [[04-decisions#D79]]
- **Revisão técnica de todos os PRs (#55–#61): MERGEADOS EM `main` COM SUCESSO** (831 testes verdes). [[03-phases]], [[06-open-threads#T22]]


## Estado anterior (2026-07-22) — Sessão 18: Gaps A3/C5 + CI GitHub Actions + Tooling (PRs #51, #52, #53, #54)
Revisão completa dos PRs abertos. **PRs #51, #52, #53, #54 REVISADOS E MERGEADOS** (S18). **1353/1340 passed (2026-08-11; 723 na época)**.
- **PR #51 & #52:** cherry-pick da tooling `tools/` e consolidação da wiki.
- **PR #53:** GitHub Actions `.github/workflows/ci.yml`.
- **PR #54:** Gap A3 (FLT do console Anexo G Tab. G.1) + Gap C5 (patamar de escada Blondel).
a 3D. **PR #49 REVISADO E APROVADO COM LOUVOR** (S18). **1353/1340 passed (2026-08-11; 714 na época)**; build atual: 18 ocorrências em 17 arquivos.
Tema central: **"guarda periódica da suíte de build 3D contra regressões silenciosas de interferência de peças"**.
- **PR #48 (fix de interferência 3D calha/condutor):**
  - **`CONDUTOR × PLACA_BASE` (tesoura):** afastamento dinâmico $DOWN\_Y = L/2 + CONDUTOR\_D/2 + 40$ mm (raio do tubo + folga) corrigindo invasão do tubo Ø150 (NBR 10844). [[04-decisions#D71]]
  - **`CALHA/BOCAL/CONDUTOR × COLUNA` (tapered):** $GUT\_Y$ derivado de $\max(COL\_SEC[0], TAPERED\_MODEL[\text{"h\_joelho"}])$ evitando sobreposição no beiral. [[04-decisions#D71]]
  - **Resultado:** `pytest -m build` passa de 7 passed + 2 failed para **9 passed em 9** (build atual: 18 ocorrências em 17 arquivos).
- **PR #49 (job periódico da suíte de build 3D):**
  - **`tools/run_build_suite.ps1`:** runner PowerShell que executa `pytest -m build`, grava logs em `tools/build-logs/build_stamp.log` e atualiza `LATEST.txt`. Isolado via `freecadcmd.exe` sem interferir na sessão GUI/bridge. [[04-decisions#D72]]
  - **`tools/register_build_task.ps1`:** registra a tarefa agendada do Windows `GalpaoFW-BuildSuite` (Weekly, Domingo 03:00 default) idempotente com suporte a `-Remover`. [[04-decisions#D72]]
  - **`tools/README.md` & `.gitignore`:** documentação e exclusão de logs locais. [[04-decisions#D72]]
- **Revisão técnica do PR #49: APROVADO COM LOUVOR** (executado e verificado ao vivo; detectou falha sem o fix do #48 e passou verde com o fix). [[03-phases]], [[06-open-threads#T20]]


## Estado anterior (2026-07-22) — Sessão 18: Plano de Montagem e Escoramento (PR #47)
Último item do turnkey (fase de OBRA). **PR #47 REVISADO E APROVADO COM LOUVOR** (S18). **714 testes verdes**.
- **Módulo puro `montagem.py` (SI, headless) + Gate 8 + Prancha PE16_MONTAGEM:**
  - Sequência de 10 passos (Bellei 7.6.4), guindaste $\gamma_{imp}=1,10$ (4.2.6), estai provisório $T=F/(n\cos\alpha)$, $\gamma_{f3}=1,30$ (4.9.6.5), prumo $\max(H/500, 5\text{ mm})$. Prancha PE16. [[04-decisions#D70]]

  - **Guindaste e içamento (`guindaste_requerido`):** peça mais pesada $\times$ coef. de impacto $\gamma_{imp}=1,10$ (NBR 8800 4.2.6) $\rightarrow$ momento de carga ($t\cdot m$). Considera rafter **pré-montado no solo** (2 meias-águas), que governa a tonelagem. [[04-decisions#D70]]
  - **Estai provisório (`estai_provisorio`):** tração no cabo $T = F / (n \cdot \cos\alpha)$, compressão adicional na coluna e força de ancoragem na fundação $N = T \cdot \sin\alpha$. [[04-decisions#D70]]
  - **Vento de montagem (`forca_lateral_montagem`):** aplica fator de combinação de construção $\gamma_{f3} = 1,30$ (NBR 8800 4.9.6.5). [[04-decisions#D70]]
  - **Prumo de montagem (`tolerancia_prumo_montagem`):** $\max(H/500, 5\text{ mm})$ por coluna, teto $25\text{ mm}$ global (NBR 8800 12.3.3.1.1). [[04-decisions#D70]]
  - **Graceful degradation (Ask-do-not-invent):** parâmetros de canteiro ausentes degradam para "A CONFIRMAR" sem inventar dados. [[04-decisions#D70]]
  - **Prancha PE16_MONTAGEM:** apêndice de procedimento com 4 quadros estruturados (Sequência, Guindaste, Estaiamento, Prumo) e notas NBR 8800. [[04-decisions#D70]]
- **Revisão técnica do PR #47: APROVADO COM LOUVOR** (verificado contra NBR 8800 1.10/4.2.6/4.4/4.9.6.5/12.3/AISC 303 via NotebookLM; 12 novos testes verdes em `test_montagem.py`). [[03-phases]], [[06-open-threads#T19]]


## Estado anterior (2026-07-22) — Sessão 17: Gaps Nível A/C + Bloco de Fabricação 3D/2D + Diafragma (PRs #45 e #46 MERGED)
Trabalho via PRs empilhados. **PRs #45 e #46 REVISADOS, APROVADOS E MERGEADOS em `main`** (S17). **1353/1340 passed (2026-08-11; 702 na época)**.
Tema central: **"gaps normativos contra-segurança + entregáveis de fabricação 3D/2D"**.
- **PR #45 (gaps Nível A/C + wizard + romaneio):**
  - **Fadiga da solda do console** (NBR 8800 Anexo K cat. F / NBR 8400 Tab. 9): adicionada cat. F ($C_f=150\times 10^{10}, \sigma_{TH}=55\text{ MPa}$, eq. K.4b $\Delta\sigma=(11\times 10^4 C_f/N)^{0,167}$). Perna da solda dimensionada por estática **E** fadiga simultaneamente. [[04-decisions#D68]]
  - **Força de atrito do vento** (NBR 6123 6.4): $F'_{at}$ no telhado + 2 paredes longitudinais ($L_{ef}$ descontando a 1ª faixa) soma no contraventamento longitudinal. [[04-decisions#D68]]
  - **Pattern loading / carga em xadrez** (NBR 8681): cargas alternadas $Q_a/Q_b$ e combos $C2_{xadrez}$ capturam momento de desequilíbrio na coluna interna de pórticos multi-vão. [[04-decisions#D68]]
  - **Empocamento progressivo** (NBR 8800 9.3): gate geométrico ($\ge 3\%$ dispensa, $<3\%$ reprova exigindo análise incremental). [[04-decisions#D68]]
  - **Torção e efeitos combinados** (NBR 8800 5.5.2): tubular retangular (3 regimes $T_{rd}$ + interação quadrtica 5.5.2.2); perfil aberto I/U por tensões de Saint-Venant (gate de empenamento/flexo-torção se $\tau_t > 0,20\tau_{Rd}$). [[04-decisions#D68]]
  - **Wizard tipo de ligação + Romaneio:** pergunta soldada/parafusada (default soldada, normalizada e validada), nota técnica 5/6 da PE09 atualizada; romaneio preliminar com marcas de peça ($C1, V1..Vn$) do cálculo. [[04-decisions#D68]]
- **PR #46 (fabricação 3D/2D + diafragma NBR 15421):**
  - **Piece marks 3D (`marcas_peca.py`):** grava propriedade `Marca` no FCStd/BIM por categoria/perfil ($C1, V1, T1, TP1, PB1...$); funções `prefixo_marca`/`mapa_marcas` (o nome `por_marca` não existe — task-7). [[04-decisions#D69]]
  - **Quadro unificado de materiais / Lista de corte na PE09:** tabela única `Q09M` (MARCA | ELEMENTO | PERFIL | QTD | CORTE(m) | MASSA(kg)) com cadeia de fallback sem sobreposição. [[04-decisions#D69]]
  - **Quadro de tolerâncias (`tolerancias_fabricacao.py`):** tabela `Q09T` na PE09 com tolerâncias de fabricação/montagem (NBR 8800 / Bellei) e folga do furo-padrão ($d_b<24\text{ mm}\rightarrow +1,5\text{ mm}$; $d_b\ge 24\text{ mm}\rightarrow +2,0\text{ mm}$). [[04-decisions#D69]]
  - **Shop drawings por peça (PE14 CROQUIS DE FABRICAÇÃO):** nova 14ª prancha com vistas projetadas em 3 colunas A1 por peça principal ($C1, V1, MI1$), rótulo com corte e notas AWS. [[04-decisions#D69]]
  - **Efeito de diafragma da cobertura (`diafragma.py`):** classificação NBR 15421 8.3.2 (deflexão no plano $>2\times\text{drift}_{médio}\rightarrow$ FLEXÍVEL), validando a distribuição tributária que o 2D adota; suporte a diafragma RÍGIDO (rigidez + torção). [[04-decisions#D69]]
- **Revisão técnica dos PRs #45 e #46: APROVADOS E MERGEADOS** (702 testes verdes, zero erros normativos ou de métodos). [[03-phases]], [[06-open-threads#T18]]


## Estado anterior (2026-07-21) — Sessão 16: mão-francesa fecha, 4 varreduras sistemáticas
Trabalho em `main` via PRs. **PRs #40–#44 abertos/mergeados** (S16). **1353/1340 passed (2026-08-11; 643 na época)**.
Tema central: **"o cálculo/modelo decide, o entregável não vê"** — 4 varreduras sistemáticas
acharam 8+ defeitos, todos na periferia (geometria de desenho, rótulos, textos), motor OK.
- **Mão-francesa completa** (#41–#44): (a) pontas apontavam p/ FORA do galpão [#41]; (b) era
  barra redonda Ø16 [tirante] onde a norma exige tração+compressão → **cantoneira escolhida
  pelo eng.** (`estrutura.mao_francesa={b,t}`), verificada por **NBR 8800 4.11.3.4 + E.1.4.2 +
  5.3.2**; (c) propriedades da cantoneira **derivadas por forma fechada** (`perfis.cantoneira`,
  validada por Green a 1e-9), sem inventar catálogo; (d) **amostra passa a ATENDER**. [[04-decisions#D67]]
- **4 varreduras** (o padrão "duas descrições da mesma coisa, uma envelhece"): interpenetração
  de conexões [#42: porca no pedestal, 2 esticadores no mesmo ponto, gusset na escora]; rótulo
  do takeoff [#44: **mísula maciça inflava o aço em 2,6 t**]; relatório×cálculo [#44: quadro
  omitia a peça que reprova; API `atende` mentia]; notas da prancha [#44: datum errado em 100 mm,
  gancho 180 vs 60 mm; **quadro de materiais sumia em silêncio**]. [[04-decisions#D67]], [[06-open-threads#T17]]
- **Bugs de infra corrigidos** (#40, #44): filtro de vigas MORTO (`"_VIGA_"` nunca casava →
  `_assenta` era no-op, terças penetrando 60%); **cache de módulo irmão no freecad.exe** escondia
  fix já mergeado (#41 fora do 3D até o reload). [[04-decisions#D67]]
- **Revisão técnica do PR #44: APROVADO SEM RESSALVAS** (parecer externo, reconciliado —
  7 commits, 643 testes na época [1353/1340 em 2026-08-11]; verdito e análise preservados). [[03-phases]], [[06-open-threads#T17]]

## Estado (2026-07-17) — correções de segurança + features + VALIDAÇÃO DE SISTEMA
Sessão longa na branch `revisao/homologacao-12-modulos` (**6 commits reais — 8bd725f,
bb36b9b, e4e3468, 63451f1, 2026-07-17 16:15–16:16**; o bloco dizia "sem commit" — corrigido na
revisão 2026-08-11, task-9).
Disparada por uma amostra ao engenheiro que expôs bugs e campos mortos. **Tudo testado**
(subsuítes verdes; 2 águas sem regressão: 7 benchmarks + CBCA <1%). Ver [[04-decisions#D52]]–
[[04-decisions#D57]], [[06-open-threads#T15]].
- **BUG-RAIZ corrigido:** `frame2d` aplicava toda UDL com **sinal invertido** (gravidade p/
  cima) — mascarado por asserts em |valor|; fundações superdimensionadas + uplift ignorado.
  Fix de 2 sinais em `solve()` + par no esforço de barra. [[04-decisions#D52]]
- **Vento:** §2A `_wind_unico` sem Cpe → agora sucção/uplift (Tab.5); §2B alvenaria → fundação/
  baldrame (não na coluna); `abertura_dominante` real (Cpi 6.2.5, vedada ≠ portão). [[04-decisions#D53]]
- **Campos mortos do wizard corrigidos:** carga de parede, janela (L,H→faixa), legislação
  (gate rodava?), `tapamento` removido. [[04-decisions#D54]]
- **Bugs de pipeline (revisão externa, triados):** E/C/H/D/J/K reais corrigidos; **F/G falsos
  positivos refutados** (build usa `SPAN` local). [[04-decisions#D55]]
- **Features novas:** **bloco de fundação** (`fund_tipo='bloco'`, NBR 6122 7.8.2 β≥60°);
  **telhado de 1 água (shed)** 1 vão (NBR 6123 Tab.6, 3D limpo); multi-vão heterogêneo
  (cumeeira por vão). [[04-decisions#D56]]
- **VALIDAÇÃO DE SISTEMA** contra livros resolvidos (NotebookLM): sapata **0,5%**, bloco
  **exato**, pilar NBR 8800 **0,1%**, vento **exato** (Alonso/Bellei). Fecha o item que faltava
  (2º caso-referência). `tests/test_validacao_alonso.py`. [[04-decisions#D57]]

## Estado (2026-07-16) — TURNKEY + escopo ampliado
Objetivo do usuário: ferramenta **turnkey** ("digo o que preciso + condições do local →
entrega 3D + 2D + cálculos NBR confiáveis"). Push na branch `revisao/homologacao-12-modulos`
→ **PR #12** (15 commits, **MERGED `4165652` 2026-07-18**). **Entregue e testado (256 passed na época; 1353/1340 em 2026-08-11):**
- **Entrada:** `wizard.py` guiado (presets, `_checa_faixa` faixas, `_avisos_coerencia`).
- **Orquestrador:** `rodar_projeto.rodar_tudo(spec)` = calc + memorial PDF + 3D + pranchas +
  `RELATORIO-CONSOLIDADO` + **dossiê PDF único** (`dossie.py`/fitz). Veredito GLOBAL honesto
  (`res["atende_global"]`).
- **Escopo:** `escopo.py` (envelope + fora-de-escopo + carimbo ART); **neve** (EN 1991-1-3)
  e **multi-vão** (`geometria.spans`; 2 vãos→3 colunas, 0 interf.) integrados.
- **Confiança:** `validacao.py` 7 benchmarks + **sistema CBCA** (galpão real reproduzido
  <1%, dados via NotebookLM).
- **Pranchas:** varredura visual completa (7 casos + renders 3D), **6 defeitos de layout
  corrigidos**; nova PE15_DET_BLOCO (fundação profunda).
**ONDE PARAMOS (SUPERADO na revisão 2026-08-11):** 2º caso-referência de validação — Pfeil/Bellei
sem 2º pórtico limpo; Pfeil 8.7.1 (treliça) tem tabela com vento + geometria ≠ framework. Plano
`check_trelica_estatica` (solver treliça vs método das seções) **nunca foi implementado**; o 2º
caso-referência foi **resolvido em T15/D57** (`validacao_alonso`). Ver [[06-open-threads#T14]], [[04-decisions#D50]], [[04-decisions#D51]].

## Estado 2026-07-15 — Auditoria "Diretrizes Técnicas"
**Auditoria "Diretrizes Técnicas" (bugs 8.1–8.36) concluída** — via MCP NotebookLM, 5
lotes: **33 bugs reais corrigidos + 3 falsos positivos** (8.9 junta aditiva, 8.11 `Lc`
conservador, 8.14 cortante sem B2). Temas: cortante viga alavanca, uplift γq=0,
flexo-tração abs, fencepost `Lb_terca`, travas B1/B2, console `Mz`, `SEC_COLS` por-coluna,
fogo incremental (Anexo B) + `θ/θ_cr`, `Nsd_tirante` geométrico, calha `h_elevacao`, e a
**observabilidade do QUADRO DE VERIFICAÇÕES** (14 verificações antes omitidas surfaçam;
`terreno.py` deixou de ser órfão; export TechDraw completo). Commits `dad7b87`→`741221d`
na branch `revisao/homologacao-12-modulos` (**não pushada**). Selftests por módulo ✅;
**smoke completo pendente** (exige `pycufsm`). Ver [[03-phases]], [[04-decisions#D49]],
[[06-open-threads#T13]]. Os relatórios de trabalho `07-`/`08-`/`review_completo.md` foram
**consolidados aqui e removidos** (wiki mantida na estrutura do skill).

## Estado anterior (2026-07-14)
**29 módulos matemáticos.** Balde 4 (fases 6.15–6.19) FECHADO **e HOMOLOGADO** — 6 itens
residuais de refino: **6.15** `props_I_mono.py` (perfil I monossimétrico → ramo mono
real do DG25, `dg25_ltb` mono-aware); **6.16** DG25 envelope FLB/TFY/ruptura §5.4.4–7;
**6.17** `forcas_localizadas.py` (NBR 8800 §5.7 + enrijecedor de apoio §5.7.9);
**6.18** `viga_equilibrio.py` (viga de divisa sobre estacas, wiring estaca/sapata em
`rodar_galpao`); **6.19** glyph solda AWS A2.4 headless (`DrawViewSymbol`+SVG) + PE09
legível. **5 pareceres → 9 correções reais** (7 bugs contra-segurança + 2 omissões),
cada uma conferida contra PDF/estática: `rt` hc²→hw², `kc` hc→hw, teto `Mp` Sxt→Sxc
(erratum DG25), M da viga `R'·e→P·e`, +cisalhamento/peso-próprio/pele na viga, glyph
arrow/other/both. 1 rejeição minha revertida com evidência (Mp Sxc). **REVISAO-INDICE
itens 45–49 ✅.** pytest **245 passed na época** (1353/1340 em 2026-08-11); `smoke_executivo` **7/7** (casos confirmados, não re-rodado). Ver [[03-phases]],
[[04-decisions#D48]], [[06-open-threads#T12]]. **PENDENTE gate humano:** push branch +
merge PR. Commits `12ff107`→`01e14e7`.

## Estado 2026-07-13
**26 módulos matemáticos.** Balde 3 (fases 6.13–6.14) FECHADO na implementação —
resíduos NÃO-bug (crane já era 100% homologado): **6.13** `enrijecedor_painel.py`
(NBR 8800 §5.4.3.1, `kv=5+5/(a/h)²`, requisitos §5.4.3.1.3; relaxa cap h/tw≤260 do
Anexo H) e **6.14** DG25 full (`dg25_ltb.py` estendido: Cb tapered 5.4-1/2, Rpc/Rpg,
Mn nominal 3 regiões; `cross_check_capacidade` onde Cb NÃO cancela). Ambos INFORMATIVOS
(dimensionamento segue NBR). **Itens 43 (APROVADO COM LOUVOR) + 44 (validado)
HOMOLOGADOS (2026-07-13).** Item 43: 2 refutações confirmadas (eixo I singelo = plano
médio NBR; §5.4.3.2 ≠ tension field) + `a_min→a_max`. Item 44: `γ·f_r=F_eLTB` "mais
elegante"; 5% inelástico = diferença de método; F_L monossim. já coberto (5.4-15).
**REVISAO-INDICE itens 1–44 ✅, zero pendente.** Ver [[04-decisions#D47]],
[[06-open-threads#T11]]. **Gate humano concluído:** push branch + merge PR #5 (**MERGED `50df273`, 2026-07-14**).

## Estado anterior (2026-07-10)
Galpão completo fim-a-fim. **18 módulos matemáticos** (+`nbr8400`) + features, selftest verde. Cálculo homologado (itens 1–27). **Fases 3–5 FECHADAS (2026-07-10):** (3) fundação profunda integrada ao ProjetoSpec + 3D (estaca/bloco/baldrame desenhados; `fundacao.tipo` gate); (4) ponte estendida — rodas motoras + NBR 8400-1:2019 (φ Tab.12 / N Tab.9 do PDF) + gate do fabricante; (5) **corte seccionado hachurado** nos detalhes (blocker T6 resolvido — DrawViewSection headless FreeCAD 1.1). `smoke_executivo` **5/5**. Commits 9ac3c4f→f912e98 na branch `revisao/homologacao-12-modulos`.
**Órfãos wired (fase 6):** calha (6.a), sapata_divisa (6.a), pórtico alma variável
(6.b), pórtico tesoura (6.c — cálculo NOVO método dos nós). ~~Restou `neve` (não
escolhido)~~ — **`neve` wired desde D51 (2026-07-16)** (task-7). **3 tipos de pórtico**: prismatico | alma_variavel | tesoura.
**Pareceres itens 28–33 HOMOLOGADOS (2026-07-11)** — [[04-decisions#D44]],
[[06-open-threads#T8]]. **Backlog do parecer 6.b esgotado — fases 6.4–6.8, itens 34–38
HOMOLOGADOS (2026-07-11):** coluna tapered (+compressão global J.3), zona de painel do
joelho (`zona_painel.py`, §5.7.7+doubler), FLT de mísula (`flt_misula.py`, Anexo J),
sucção vento→tesoura (bug de sinal do uplift corrigido), alma esbelta (`alma_esbelta.py`,
Anexo H) — [[04-decisions#D45]], [[06-open-threads#T9]]. **REVISAO-INDICE.md 1–38 ✅,
zero pendente.** 8 alegações de erro grave refutadas com o PDF (imagens via SendUserFile),
1 bug real acolhido. **21 módulos matemáticos.** **Gate humano concluído:** merge PR #1+#4
(**MERGED `4fde82b` 07-07 / `aa02180` 07-10**);
**push da branch** (bloqueado p/ assistente → usuário roda `git push`). [[06-open-threads]].

last-consolidated: 2026-08-11, revisão da wiki (todos 0–19) (+ os 7 arquivos da wiki
cross-checkados contra código (135 módulos, task-1) / suíte (task-2) / git-GitHub (171 PRs,
task-3): ledger 430 claims — 123 ok / 49 corrigir / 13 obsoleto / 1 não verificado /
5 não-localizados; bloco "Estado atual (2026-08-11)" no topo; D74–D79 criadas em 04-decisions
(task-15); T22/T41 criadas em 06-open-threads (task-16); arco pós-S40 reconstruído do git —
S41 #154–161 + S42 #162–171, MERGED 2026-08-09, HEAD 6358157; memory/ NÃO versionado no repo —
arco reconstruído do git em 2026-08-11). Suíte real 2026-08-11 via tools/run_tests.py:
1353 selecionados / 1340 passed / 1 failed (F1 fitz) / 15 skipped.
last-consolidated: 2026-08-04, sessions: 40 (+ SESSÕES 20–40: os 6 verticais [concreto
#81–101 / elétrico #102–106 / incêndio #107–110 / hidráulica #136–147] + TURNKEY federado
#112 + caderno único #116 + revisão total #118 + hardening/saturação #148 + 1ª auditoria NLM
concreto/aço + janela dupla-conversão RESOLVIDA #150 [T40, convenção FAIXA canônica] + wiki T40
#151 + runner de regressão xdist #152; arco detalhado no bloco "Estado atual 2026-08-03" acima
*(memory/ NÃO versionado — arco reconstruído do git em 2026-08-11)*; T40 FECHADO, T40b saturação
= padrão parcial). Fonte do arco S20–40 = git (reconstrução 2026-08-11; sessions/ não existe no
repo). Regressão verde: 2026-08-04 = 1281 passed (-n auto, 11m14s); 2026-08-11 = 1340 passed
(F1 fitz + 15 skipped).
last-consolidated: 2026-07-22, sessions: 18 (+ SESSÃO 17: gaps normativos Nível A/C [fadiga
console/atrito vento/pattern loading/empoçamento/torção, D68 PR #45] + wizard soldada/parafusada +
FABRICAÇÃO 3D/2D [piece marks, lista de corte, tolerâncias, PE14 croquis, D69 PR #46] + diafragma
NBR 15421 [D69]; SESSÃO 18: plano de montagem/escoramento [montagem.py, gate8, PE16, NBR 8800
12.3+AISC 303, D70 PR #47] + FIX interferência 3D calha/condutor×chapa e coluna tapered [28 interf.
pré-existentes que os testes `build` DESELECTED escondiam, D71 PR #48] + guarda de build agendada
[tools/, tarefa Windows semanal, D72 PR #49] + CI GitHub Actions non-build [pegou de 1ª uma regressão
do #48 nos testes de string do GUT_Y, D72/PR #53] + 2ª auditoria NLM: GAPS A3 [FLT do console, NBR
8800 Anexo G, D73 PR #54] e C5 [patamar de escada Blondel, D73] — "o poço secou" (3 falsos-positivos
refutados). 723 testes non-build + 9 build na época (suíte 2026-08-11: 1353 non-build + 18 build). T19/T20/T21)
last-consolidated: 2026-07-21, sessions: 16 (+ SESSÃO 16: mão-francesa completa [pontas p/ fora
#41; barra redonda→cantoneira do eng. verificada NBR 8800 4.11.3.4+E.1.4.2+5.3.2; propriedades
por forma fechada validada Green 1e-9; amostra ATENDE]; 4 varreduras sistemáticas [interpenetração
#42, rótulo takeoff/mísula −2,6t #44, relatório×cálculo #44, notas da prancha #44]; filtro de vigas
morto #40; cache de módulo irmão no freecad.exe escondia fix mergeado #44; revisão PR #44 APROVADA.
D67; T17. wiki/07 + PR_44_Review consolidados aqui e removidos)
last-consolidated: 2026-07-17, sessions: 13 (+ sessão CORREÇÕES+FEATURES+VALIDAÇÃO: fix de
sinal frame2d [raiz]; vento uplift/Cpe §2A/§2B/abertura_dominante; campos mortos do wizard;
bugs de pipeline E/C/H/D/J/K [F/G refutados]; bloco de fundação NBR 6122; shed 1 água NBR
6123 Tab.6; multi-vão heterogêneo; VALIDAÇÃO DE SISTEMA contra Alonso/Bellei — sapata 0,5%,
bloco/vento exatos, pilar 0,1%; 6 commits reais (8bd725f/bb36b9b/e4e3468/63451f1, 07-17), aberto p/ revisão — ver [[06-open-threads#T15]].
wiki/07 removido, consolidado aqui)
last-consolidated: 2026-07-19, sessions: 14 (+ REVISÃO CONTINUADA + VERIFICAÇÃO VISUAL:
bridge destravado [WMI mata freecad.exe travado; autostart era contaminação dos zumbis]; achou
regressão do 3D no main [#20/#24], estaca ponta contra-segurança [#23, o mais grave], executivo
deixava zumbis [#22], PE07 crop [#25]; mão-francesa confirmada no modelo dX=294mm. D63–D66;
ver [[06-open-threads#T16]])
former: 2026-07-18, sessions: 13 (+ CAÇA DE BUGS sessão 14: motor correto
[frame2d/B1B2/mão-francesa-Bellei/ponte-NBR8800/tesoura, cruzados NotebookLM]; bugs só na
periferia → mão-francesa geometria 3D [#15], validação de entrada COMPLETA [#13/#16/#18],
pistas baixa-prob [#19]; PRs #12–#19 MERGED. Aberto: verificação VISUAL do executivo bloqueada
por 3 freecad.exe TRAVADOS na 9875 [reboot]; ver [[06-open-threads#T16]], [[04-decisions#D58]]–[[04-decisions#D62]])
former: 2026-07-16, sessions: 12 (+ sessão TURNKEY: wizard/rodar_tudo/escopo/
validacao CBCA <1% + neve + multi-vão + dossiê PDF + PE15 bloco + varredura visual 6
defeitos; PR #12; 2º caso-referência PENDENTE — ver [[06-open-threads#T14]])
former: 2026-07-15, sessions: 11 (fases 3–6.c + homologação itens 28–33 +
backlog parecer 6.b fases 6.4–6.8 itens 34–38 + balde 2 fases 6.9–6.12 itens 39–42 +
balde 3 fases 6.13–6.14 itens 43–44 + balde 4 fases 6.15–6.19 itens 45–49 + **auditoria
"Diretrizes Técnicas" bugs 8.1–8.36 via NotebookLM: 33 reais + 3 falsos positivos**;
markdowns 07-/08-/review_completo consolidados e removidos)
