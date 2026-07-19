# galpao_fw — LLM wiki

**Pitch:** Framework Python que dimensiona/verifica galpão de aço (steel warehouse) fim-a-fim: pórtico 2D → 2ª ordem (MAES) → verificação NBR 8800 por peça → secundários/terças/ligações/base/fundação → modelo 3D FreeCAD + DXF + memorial PT. Engenheiro roda a skill; sênior revisa e assina (ART). Saídas em português. Unidades SI (m, kN).

Cwd primário: `D:\dev\FreeCad_Automatic\framework\galpao_fw`. Git root: `D:\dev\FreeCad_Automatic`. Norma-fonte: PDFs em `pesquisa/aço/` (nunca de memória).

## TOC
- [[01-architecture]] — spec-driven, cadeia de módulos, envelope, MAES, calc/model split
- [[02-test-tree]] — `_selftest()` por módulo, o que cada um assere
- [[03-phases]] — fases fechadas: revisão sênior 12 módulos (r2) · features pós-homolog · análise de lacunas (gaps+FLAGs) · **projeto executivo 2D (TechDraw)** · handoff/aguarda pareceres
- [[04-decisions]] — log de decisões/fixes normativos (D0–D45)
- [[05-glossary]] — termos de domínio (pórtico, MAES, ELU/ELS, FLT, Lb, sapata rígida, estaca, biela…)
- [[06-open-threads]] — **T15 correções+features+validação de sistema (aberto p/ revisão)**, T14 turnkey, backlog
- [[07-review-results]] — **Relatório de Revisão Técnica (T15) das novas implementações**

## Estado atual (2026-07-17) — correções de segurança + features + VALIDAÇÃO DE SISTEMA
Sessão longa na branch `revisao/homologacao-12-modulos` (**sem commit — árvore de trabalho**).
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
→ **PR #12** (15 commits, NÃO mergeado). **Entregue e testado (suíte completa 256 passed):**
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
**ONDE PARAMOS:** 2º caso-referência de validação — Pfeil/Bellei sem 2º pórtico limpo;
Pfeil 8.7.1 (treliça) tem tabela com vento + geometria ≠ framework. Plano: `check_trelica_
estatica` (solver treliça vs método das seções). Bloqueio momentâneo (classificador Bash
indisponível). Ver [[06-open-threads#T14]], [[04-decisions#D50]], [[04-decisions#D51]].

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
itens 45–49 ✅.** pytest **245 passed**, `smoke_executivo` **7/7**. Ver [[03-phases]],
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
[[06-open-threads#T11]]. **PENDENTE gate humano:** push branch + merge PR #5.

## Estado anterior (2026-07-10)
Galpão completo fim-a-fim. **18 módulos matemáticos** (+`nbr8400`) + features, selftest verde. Cálculo homologado (itens 1–27). **Fases 3–5 FECHADAS (2026-07-10):** (3) fundação profunda integrada ao ProjetoSpec + 3D (estaca/bloco/baldrame desenhados; `fundacao.tipo` gate); (4) ponte estendida — rodas motoras + NBR 8400-1:2019 (φ Tab.12 / N Tab.9 do PDF) + gate do fabricante; (5) **corte seccionado hachurado** nos detalhes (blocker T6 resolvido — DrawViewSection headless FreeCAD 1.1). `smoke_executivo` **5/5**. Commits 9ac3c4f→f912e98 na branch `revisao/homologacao-12-modulos`.
**Órfãos wired (fase 6):** calha (6.a), sapata_divisa (6.a), pórtico alma variável
(6.b), pórtico tesoura (6.c — cálculo NOVO método dos nós). Restou `neve` (não
escolhido). **3 tipos de pórtico**: prismatico | alma_variavel | tesoura.
**Pareceres itens 28–33 HOMOLOGADOS (2026-07-11)** — [[04-decisions#D44]],
[[06-open-threads#T8]]. **Backlog do parecer 6.b esgotado — fases 6.4–6.8, itens 34–38
HOMOLOGADOS (2026-07-11):** coluna tapered (+compressão global J.3), zona de painel do
joelho (`zona_painel.py`, §5.7.7+doubler), FLT de mísula (`flt_misula.py`, Anexo J),
sucção vento→tesoura (bug de sinal do uplift corrigido), alma esbelta (`alma_esbelta.py`,
Anexo H) — [[04-decisions#D45]], [[06-open-threads#T9]]. **REVISAO-INDICE.md 1–38 ✅,
zero pendente.** 8 alegações de erro grave refutadas com o PDF (imagens via SendUserFile),
1 bug real acolhido. **21 módulos matemáticos.** **PENDENTE gate humano:** merge PR #1+#4;
**push da branch** (bloqueado p/ assistente → usuário roda `git push`). [[06-open-threads]].

last-consolidated: 2026-07-17, sessions: 13 (+ sessão CORREÇÕES+FEATURES+VALIDAÇÃO: fix de
sinal frame2d [raiz]; vento uplift/Cpe §2A/§2B/abertura_dominante; campos mortos do wizard;
bugs de pipeline E/C/H/D/J/K [F/G refutados]; bloco de fundação NBR 6122; shed 1 água NBR
6123 Tab.6; multi-vão heterogêneo; VALIDAÇÃO DE SISTEMA contra Alonso/Bellei — sapata 0,5%,
bloco/vento exatos, pilar 0,1%; SEM COMMIT, aberto p/ revisão — ver [[06-open-threads#T15]].
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
