# task-F2 — Revisão de qualidade dos DOCS como leitor novo (gate F2)

- **Data:** 2026-08-11
- **Escopo:** leitura integral dos 9 arquivos (wiki 00–06 + README.md + COMO-RODAR.md), spot-check de nomes citados contra o código, estrutura, consistência interna, diff mínimo do README/COMO-RODAR, cobertura do todo 19.
- **Arquivos lidos (integrais, em ordem):** `wiki/00-index.md` (352 l), `01-architecture.md` (164), `02-test-tree.md` (279), `03-phases.md` (495), `04-decisions.md` (657), `05-glossary.md` (70), `06-open-threads.md` (405), `README.md`, `framework/galpao_fw/COMO-RODAR.md` (108).
- **Regra:** revisão pura — NADA editado.

---

## 1. Impressões de leitor novo (curtas)

- A wiki flui: 00-index dá o pitch + TOC + estado atual; 01 explica a cadeia de cálculo; 02 o que cada módulo assere; 03 as fases; 04 o porquê das decisões; 05 os termos; 06 o que está aberto. Leitura coerente de ponta a ponta.
- Correções conhecidas (secundarios_lineares, modelo_analitico não-módulo, neve wired, dxf_vistas removido, Hatch→SvgHatch) aparecem explicitamente marcadas como "não existe" — um leitor novo não é induzido a erro.
- Observação menor (não é falha): 00-index:15 menciona "estrutura do skill (00–07 + revisoes/)" — o wiki atual tem 00–06 (07 consolidado/removido; REVISAO-*.md na raiz do galpao_fw). Frase histórica sobre o skill, contexto dedutível.
- Observação menor: a contagem "9 correções reais" do bloco 45–49 (00-index:253/03-phases:40) soma 8 itens listados (rt, kc, Mp-Sxc, M=P·e, cortante, peso próprio, pele, glyph) — internamente auto-consistente com a própria quebra "7 bugs + 2 omissões", mantida como observação.

## 2. Spot-check de nomes citados (lista definida ANTES de grepar)

Amostra principal (22 nomes: 12 funções + 10 módulos) — verificado com `grep "def <nome>("` no arquivo-alvo ou glob do módulo:

| # | Nome citado | Onde na wiki | Verificação real (grep/glob) | OK |
|---|---|---|---|---|
| 1 | `galpao_turnkey.rodar` | 00:3, 01:110 | `galpao_turnkey.py:138 def rodar(spec, out_dir=None)` (01 cita :138 — exato) | ✓ |
| 2 | `rodar_projeto.montar_modelo` | 00:119, 03:337 | `rodar_projeto.py:210 def montar_modelo(...)` (03 cita :210-217 — exato) | ✓ |
| 3 | `ifc_emit.emitir_ifc_analitico` | 00:122, 01:33, 05:56 | `ifc_emit.py:533 def emitir_ifc_analitico(...)` + `:632 emitir_ifc_analitico_do_spec` (D79 cita :533/:632 — exato) | ✓ |
| 4 | `checa_interferencia_federada` | 01:118, 05:52 | `galpao_turnkey.py:595 def checa_interferencia_federada(...)` | ✓ |
| 5 | `caderno_turnkey.montar_caderno` | 01:121, 00:81 | `caderno_turnkey.py:272 def montar_caderno(spec, out_dir, ...)` | ✓ |
| 6 | `_janela_band` | 00:96, 06:10 | `projeto_spec.py:631 def _janela_band(janela, eave_mm, peitoril_mm=1100.0)` | ✓ |
| 7 | `galpao_portico.modelo_analitico` | 00:122, 01:33, 05:46/57 | `galpao_portico.py:305 def modelo_analitico()` (D79 cita :305 — exato) | ✓ |
| 8 | `modelo_neutro.tercas` | 00:121, 05:55, 06:21 | `modelo_neutro.py:116 def tercas(...)` (D78 cita :116 — exato) | ✓ |
| 9 | `modelo_neutro.girts` | idem | `modelo_neutro.py:163 def girts(...)` (D78 cita :163 — exato) | ✓ |
| 10 | `modelo_neutro.frame_completo` | 00:121, 05:55 | `modelo_neutro.py:920 def frame_completo(...)` (D78 cita :920 — exato) | ✓ |
| 11 | `modelo_neutro.tirantes_parede` | 00:121, 06:21 | `modelo_neutro.py:198 def tirantes_parede(...)` (D78 cita :198 — exato) | ✓ |
| 12 | `modelo_neutro.contrav_cobertura` | idem | `modelo_neutro.py:222 def contrav_cobertura(...)` (D78 cita :222 — exato) | ✓ |
| 13 | `pacote_legal` | 00:57, 03:493, 05:58 | `pacote_legal.py` existe | ✓ |
| 14 | `compatibilizacao` | 01:42, 05:53 | `compatibilizacao.py` existe | ✓ |
| 15 | `geotecnia_spt` | 01:37, 05:65 | `geotecnia_spt.py` existe | ✓ |
| 16 | `orcamento` | 01:42, 05:61 | `orcamento.py` existe | ✓ |
| 17 | `terraplenagem` | 01:42, 05:62 | `terraplenagem.py` existe | ✓ |
| 18 | `cronograma` | 01:42, 05:60 | `cronograma.py` existe | ✓ |
| 19 | `esgoto_reuso` | 01:40, 05:63 | `esgoto_reuso.py` existe | ✓ |
| 20 | `fotovoltaico` | 01:38, 05:64 | `fotovoltaico.py` existe | ✓ |
| 21 | `piso_industrial` | 01:37, 05:66 | `piso_industrial.py` existe | ✓ |
| 22 | `caderno_encargos` | 01:42, 05:59 | `caderno_encargos.py` existe | ✓ |

**22/22 OK.** Bônus (9 nomes adicionais de risco, citados no 01/05): padrão stateless `rodar/membros_bim/emitir_bim/montar_pranchas` confirmado por grep nos **5 verticais** (`galpao_concreto` :74/:301/:396/:439, `galpao_eletrico` :59/:401/:479/:317, `galpao_seguranca_incendio` :27/:241/:330/:122, `galpao_hidraulica` :39/:239/:296/:307, `galpao_climatizacao` :28/:74/:107/:118) — bate 01:81-83 "confirmado por grep nos 5 orquestradores"; `montar_caderno_de_pdfs` (`caderno_turnkey.py:173`), `gerar_pendencias` (`compatibilizacao.py:79`), `montar_3d_federado` (`galpao_turnkey.py:313`), `_clash_esperado` (`galpao_turnkey.py:524`) — **9/9 OK.**

Reforço: glob de **96 módulos** adicionais citados na wiki (montagem, marcas_peca, tolerancias_fabricacao, diafragma, empocamento_nbr8800, torcao_nbr8800, contencao_lateral, mao_francesa_geom, zona_painel, flt_misula, alma_esbelta, enrijecedor_painel, tensao_ponto, cortante_tapered, forcas_localizadas, props_I_mono, dg25_ltb, nbr8400, junta_dilatacao, telha_cobertura, viga_baldrame, viga_equilibrio, estaca_profunda, sapata_divisa, fundacao_sapata, base_chumbador, ligacoes, gusset_ligacao, console_ponte, ponte_rolante, check_nbr8800, perfis, redimensionamento, frame2d, galpao_portico, estabilidade_b1b2, alma_variavel, tesoura, sismo_nbr15421, vento_nbr6123, neve, escada, plataforma, fogo_nbr14323, tercas_iteracao, secundarios_nbr8800, mao_francesa, contraventamento, calhas, wizard, escopo, validacao, dossie, relatorio_calculo, build_galpao, techdraw_exec, terreno, romaneio, acos, modelo_neutro, ifc_emit, ifc_map, build_federado, build_concreto, build_eletrico, desenho_coordenacao, techdraw_coordenacao, executivo_concreto, hidraulica_predial, climatizacao_nbr16401, caderno_turnkey, pilar_concreto, viga_concreto, viga_protendida, perdas_protensao_nbr6118, premoldado_nbr9062, fogo_nbr15200, fissuracao_nbr6118, estabilidade_global_nbr6118, torcao_nbr6118, cargas_eletricas, condutores_nbr5410, curto_circuito, protecao_nbr5410, fator_potencia, subestacao_nbr14039, aterramento_nbr15749, spda_nbr5419, luminotecnica_nbr8995, iluminacao_externa_nbr5101, instalacao_eletrica, iluminacao_emergencia_nbr10898, sinalizacao_nbr16820, deteccao_alarme_nbr17240, proteccao_sprinklers_nbr10897, hidrantes_nbr13714) — **96/96 encontrados. Zero nome inexistente.** Nomes que NÃO existem seguem NÃO citados como existentes (secundarios_lineares, modelo_analitico.py, dxf_vistas, Hatch) — a wiki os marca como "não existe", correto.

**Total: 127 nomes spot-checkados + varredura mecânica task-19 (135 módulos + 136 testes) — ZERO inventado.**

## 3. Estrutura

- `wiki/` tem exatamente os **7 arquivos** 00-index/01-architecture/02-test-tree/03-phases/04-decisions/05-glossary/06-open-threads — nenhum novo, nenhum renomeado, nenhum removido. ✓
- TOC do 00-index (linhas 8–13) aponta os 7 arquivos (00 na raiz + 01–06) e anuncia os ranges **D0–D79** (04 tem D0 política + D1–D79, 79 decisões + D0) e **T1–T41** (06 tem T1–T41, incluindo T22 e T41 criadas na revisão). ✓
- Âncoras citadas em 00 existem em 04/06: `[[04-decisions#D74]]`..`[[#D79]]` (D74:635, D75:638, D76:641, D77:644, D78:647, D79:650), `[[06-open-threads#T22]]` (06:15), `[[06-open-threads#T41]]` (06:3). ✓

## 4. Consistência interna

- **Contagens da suíte** — `1353 selecionados / 1340 passed / 1 failed (F1 fitz) / 15 skipped (2026-08-11)` idênticas em: 00-index (:21-22, :46, :74, :99, :101, :108-109, :115, :127, :131, :159, :178, :195, :223, :263, :303), 02-test-tree (:3, :53), 03-phases (:389) e README (Status). ✓
- **Contagens históricas** — shards a-l 770 / m-z 511 (00:109 × 06:T40:10), 1281 passed (00:101, :311), 831 (00:115 × 03:350), 723 (00:127 × 06:T21:26), 714 (00:131 × 06:T20:36), 702 (00:159 × 06:T18:67), 643 (00:178, :195 × 06:T17:86), 705+9=714 (03:287 × 06:T19:49), 256 (00:223 × 06:T14:198), 245 (00:263 × 03:49). ✓
- **Fases S19–S42 × PRs** — 03-phases × 00-index: S19 #55–#61, S19-ext #62–#80, S20 #81–#101 (153 testes/17 arquivos/31 protensão nos dois), S21–S26 #102–#106, S27–S30 #107–#110, S31 #111, S32 #112, P33–P39 #113–#119 (S36 #116, S38 #118), #120–#123, #124–#134, #135, S39 #136–#147, S40 #148/#150/#152/#153, S41 #154–#161, S42 #162–#171 (HEAD 6358157 = merge #171; git log confirma `6358157 Merge pull request #171`). ✓
- **D74–D79** existem em 04-decisions e são referenciadas em 00-index (:117–122) com conteúdo coerente (D75 1,67 MB/789 elementos; D76 fallback headless :210-217; D79 função+emissores, sem módulo). ✓
- **23 arquivos pesados** — "22 `test_fase*` + `test_crashes_wiki07`" idêntico em 00:99 e 03:470-471. ✓
- **135 módulos** — README "135 Python modules" × 00:20 "135 módulos — task-1" × task-19. ✓

## 5. FALHA — contradição interna (status de homologação itens 46/49)

- **README.md** (Status e Key Features, corrigido nesta revisão — commit `f5742d3`, ancorado em REVISAO-INDICE.md:61/:64 segundo task-17): **"REVISAO itens 1–49: 47 HOMOLOGADO + 2 PARECER (46, 49)"**.
- **REVISAO-INDICE.md** (tracker canônico, último commit `01e14e7` 2026-07-13): item **46 = "PARECER 2 RODADAS - 2 CORRIGIDOS"** e item **49 = "PARECER - 1 CORRIGIDO"**; 45 = HOMOLOGADO SEM RESSALVAS, 47 = HOMOLOGADO SEM IMPEDITIVOS, 48 = HOMOLOGADO - 3 CORRIGIDOS + pele.
- **Wiki**: diz **"REVISAO-INDICE itens 45–49 ✅"** em 03-phases:40, **"itens 45–49 ✅ HOMOLOGADOS"** em 04-decisions:319 (D48) e 00-index:263 — supera o que o próprio tracker citado registra (46 e 49 continuam PARECER).
- Ledger task-5 registrou a claim (03-phases:40-43) como **"pendente"** — nunca resolvida; o README foi corrigido no sentido INDICE (2 PARECER) e a wiki ficou contradizendo-o.
- Impacto para leitor novo: README diz "2 PARECER (46, 49)"; 03/04/00 dizem "45–49 ✅ HOMOLOGADOS". Impossível saber a verdade sem abrir o REVISAO-INDICE.md. Contagem/status contraditória ENTRE arquivos revisados → falha do critério "zero contradição interna (datas, PRs, contagens entre arquivos)".

## 6. Diff mínimo do README/COMO-RODAR

- `git show f5742d3 --stat` → **exatamente 2 arquivos**: `README.md` (30 linhas alteradas) e `framework/galpao_fw/COMO-RODAR.md` (39). Nenhum outro arquivo tocado.
- Natureza do diff: correção factual de claims desatualizados (53→135 módulos; status 47+2; `gerar_dxf`→`montar_modelo`/`rodar_executivo`; gates 23→40; `neve` stub→wired; `dxf_vistas` removido da tabela; estaca "3 métodos"→"1 método: Aoki-Velloso"; seção Docs corrigida) + bloco "Já implementado posteriormente" no §5 do COMO-RODAR. **Tom e estrutura originais preservados** (mesmas seções, mesma linguagem, mesmo fluxo Quick Start; correções pontuais sem reescrita). ✓

## 7. Cobertura do todo 19 (varredura mecânica — conferida, NÃO re-rodada)

`task-19-revisao-wiki.md`: veredito **PASSOU**; módulos **132/135** cobertos por nome + **3 justificados** (fogo_nbr14323 parcial-capacidade; demo_engenheiro e tools_probe_pe13 orphan/dev) = 135/135; testes **136/136**; sweep 15/15 itens com correspondência mecânica; zero datas futuras; 3 achados de consistência registrados ao orquestrador (nenhum corrigido, regra da tarefa). Conferido o requisito "135 módulos + 136 testes cobertos ou justificados". ✓

## 8. Veredicto

**VERDICT: REJECT**

**Falha (1):** contradição interna entre arquivos revisados sobre o status de homologação — wiki (03-phases:40, 04-decisions:319/D48, 00-index:263) afirma "REVISAO-INDICE itens 45–49 ✅ HOMOLOGADOS"; README afirma "47 HOMOLOGADO + 2 PARECER (46, 49)"; o tracker canônico REVISAO-INDICE.md registra itens 46 e 49 como PARECER (2 CORRIGIDOS / 1 CORRIGIDO). Leitor novo não consegue determinar o status verdadeiro sem abrir o INDICE. Correção sugerida ao orquestrador: alinhar as 3 ocorrências da wiki ao INDICE (45/47/48 HOMOLOGADO; 46/49 PARECER) — ou, se houver evidência de re-homologação posterior, atualizar INDICE+README no sentido contrário.

**PASS em tudo o mais:** leitura flui e não se contradiz; 127 nomes spot-checkados + varredura task-19 (135 módulos/136 testes) com ZERO nome inventado; estrutura 00–06 intacta (7 arquivos, TOC e ranges D0–D79/T1–T41 corretos, D74–D79 e T22/T41 existentes e referenciados); contagens 1353/1340/1/15 e históricas consistentes entre arquivos; fases S19–S42 com PRs coerentes entre 03-phases e 00-index; diff README/COMO-RODAR mínimo (2 arquivos, tom preservado); task-19 conferido.

---

# Re-execução do gate F2 (2026-08-11) — falha corrigida

## 1. Correção confirmada (grep pós-edição)

Grep `itens 45, 47, 48 HOMOLOGADOS` nos 3 arquivos da wiki — as 3 ocorrências foram corrigidas; **zero** claim residual de "45–49 ✅" / "45–49 ✅ HOMOLOGADOS" / "45-49 ✅" em qualquer arquivo da wiki:

| Arquivo | Antes (falha F2) | Depois (corrigido) |
|---|---|---|
| 03-phases.md:41 | "REVISAO-INDICE **itens 45–49 ✅**" | "REVISAO-INDICE **itens 45, 47, 48 HOMOLOGADOS; 46 e 49 em PARECER**" |
| 04-decisions.md:319 (D48) | "**REVISAO-INDICE itens 45–49 ✅ HOMOLOGADOS.**" | "**REVISAO-INDICE itens 45, 47, 48 HOMOLOGADOS; 46 e 49 em PARECER.**" |
| 00-index.md:262-263 | "**REVISAO-INDICE itens 45–49 ✅.**" | "**REVISAO-INDICE itens 45, 47, 48 HOMOLOGADOS; 46 e 49 em PARECER.**" |

Ocorrências residuais de "45–49" (06:267 "9 correções dos pareceres 45–49 aplicadas"; 03:19 título da seção "homologação 45–49"; 00:350 faixa de itens do balde 4) são referências neutras de faixa/título — nenhuma é claim de homologação. ✓

## 2. Alinhamento com o tracker canônico REVISAO-INDICE.md (linhas 60-64, lidas integrais)

| Item | Status no INDICE | Wiki agora afirma | Bate |
|---|---|---|---|
| 45 | ✅ HOMOLOGADO SEM RESSALVAS | HOMOLOGADO | ✓ |
| 46 | ✅ PARECER 2 RODADAS — 2 CORRIGIDOS | PARECER | ✓ |
| 47 | ✅ HOMOLOGADO SEM IMPEDITIVOS | HOMOLOGADO | ✓ |
| 48 | ✅ HOMOLOGADO — 3 CORRIGIDOS + pele | HOMOLOGADO | ✓ |
| 49 | ✅ PARECER — 1 CORRIGIDO | PARECER | ✓ |

Coerente com o README ("REVISAO itens 1–49: 47 HOMOLOGADO + 2 PARECER (46, 49)" — 44 anteriores + 45/47/48 = 47; PARECER = 46 e 49). A contradição interna (README × wiki × tracker) que motivou o REJECT está resolvida nos três lados.

## 3. Demais pontos da evidência F2 — re-confirmados sem pendência

- **Spot-check (127 nomes):** PASS original; nada a corrigir (nenhuma falha apontada).
- **Estrutura (7 arquivos 00–06, TOC, D0–D79/T1–T41, D74–D79/T22/T41):** PASS original.
- **Consistência (1353/1340/1/15, contagens históricas, S19–S42 × PRs, 23 arquivos pesados, 135 módulos):** PASS original.
- **Diff mínimo f5742d3 (2 arquivos, tom preservado):** PASS original.
- **task-19 (132/135 + 3 justificados; 136/136 testes):** conferido, PASS.
- **Observações menores (não-falhas) da leitura** (frase histórica "00–07 + revisoes/" em 00:15; quebra "9 correções" auto-consistente): mantidas como observações, sem ação requerida — nenhuma ficou sem tratamento.

## 4. Veredicto final (re-execução)

**VERDICT: APPROVE**

A única falha do gate F2 (contradição interna de status 46/49 entre README × wiki × REVISAO-INDICE.md) foi corrigida nas 3 ocorrências e alinhada ao tracker canônico; grep pós-edição mostra zero claim residual; nenhuma outra falha pendente. Wiki consistente, nenhum nome inventado, estrutura 00–06 preservada, diffs mínimos, cobertura task-19 conferida. (Revisão pura — nenhum doc editado por mim nesta re-execução; sem commit.)
