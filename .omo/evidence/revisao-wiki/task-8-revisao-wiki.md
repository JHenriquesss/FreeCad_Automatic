# Task 8 — Cross-check da árvore de testes (revisão-wiki)

**Data:** 2026-08-11
**Branch (worktree):** `docs/revisao-wiki-2026-08-11` (worktree `FreeCad_Automatic-wt`)
**Escopo:** cross-check de `wiki/02-test-tree.md` (129 linhas, seções por módulo + branches fase 3–5 + balde 4 + smoke + turnkey + sessões 2026-07-17/18/19 + S16–S19) contra os **136 arquivos** reais de `tests/` e os resultados da suíte (task-2).
**Entradas usadas (NÃO refeitas):** inventário + suíte `task-2-revisao-wiki.md` (1353 selecionados / 1340 passed / 1 failed F1-fitz / 15 skipped / 21 deselecionados; 17 arquivos build-marked, 18 ocorrências); ledger `task-5-revisao-wiki.md` (430 claims; seção 02-test-tree = linhas 146–185).
**Métodos:** (1) varredura de nomes `test_*.py` na wiki por regex vs. lista real do diretório; (2) contagens reais por arquivo via `pytest --collect-only -m "not build"` (SEM execução de testes) + contagem de `def test_` e `pytest.mark.build` por arquivo; (3) greps de nomes de módulos/funções no `framework/galpao_fw/`; (4) QA: 5 arquivos citados na wiki rodados ISOLADOS.
**python (QA):** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic\framework\galpao_fw\.venv\Scripts\python.exe` (venv do repo PRINCIPAL por caminho absoluto; cwd = worktree `framework\galpao_fw`).

---

## 1. Inventário: wiki × 136 arquivos de `tests/`

- **54 arquivos** são nomeados individualmente na wiki (via `test_<nome>.py`) → **TODOS existem** em `tests/` → **0 "obsoleto"** (nada descrito na wiki deixou de existir).
- **82 arquivos** existem em `tests/` e **NÃO** são citados na wiki → **faltante** (76 sem NENHUMA menção + 6 citados apenas como intervalo "`test_fase69` a `test_fase614`" na linha 125, sem nomear o arquivo).
- Os 6 do intervalo existem: `test_fase69_tensao_ponto.py`, `test_fase610_cortante_tapered.py`, `test_fase611_vento_zona_tesoura.py`, `test_fase612_dg25_crosscheck.py`, `test_fase613_enrijecedor_painel.py`, `test_fase614_dg25_full.py`.
- `smoke_executivo.py` é script (raiz `galpao_fw/`), não arquivo de teste — fora da contagem de 136.

### Tabela A — Arquivos NOVOS ausentes da wiki (veredito: faltante)

| arquivo (`tests/`) | ausência na wiki | veredito | evidência |
|---|---|---|---|
| test_galpao_concreto.py | não citado (seções param na Sessão 19) | faltante | existe; 21 testes; lane rápida |
| test_galpao_concreto_bim.py | não citado | faltante | existe; 7 testes |
| test_pilar_concreto.py | não citado | faltante | existe; 12 testes |
| test_viga_concreto.py | não citado | faltante | existe; 8 testes |
| test_desenho_concreto.py | não citado | faltante | existe; 8 testes |
| test_build_concreto.py | não citado | faltante | existe; 8 testes; build-marked |
| test_executivo_concreto.py | não citado | faltante | existe; 7 testes |
| test_techdraw_concreto.py | não citado | faltante | existe; 7 testes; build-marked |
| test_viga_protendida.py | não citado | faltante | existe; 11 testes |
| test_premoldado_nbr9062.py | não citado | faltante | existe; 14 testes |
| test_perdas_protensao_nbr6118.py | não citado | faltante | existe; 6 testes |
| test_fissuracao_nbr6118.py | não citado | faltante | existe; 8 testes |
| test_estabilidade_global_nbr6118.py | não citado | faltante | existe; 6 testes |
| test_torcao_nbr6118.py | não citado | faltante | existe; 8 testes |
| test_eletrico_bt.py | não citado | faltante | existe; lane rápida |
| test_eletrico_robustez.py | não citado | faltante | existe; lane rápida |
| test_eletrico_bim.py | não citado | faltante | existe; lane rápida |
| test_build_eletrico.py | não citado | faltante | existe; build-marked |
| test_executivo_eletrico.py | não citado | faltante | existe; build-marked |
| test_seguranca_incendio.py | não citado | faltante | existe; lane rápida |
| test_fogo_nbr15200.py | não citado | faltante | existe; lane rápida |
| test_hidrantes.py | não citado | faltante | existe; lane rápida |
| test_iluminacao_externa.py | não citado | faltante | existe; lane rápida |
| test_incendio_bim.py | não citado | faltante | existe; lane rápida |
| test_incendio_robustez.py | não citado | faltante | existe; lane rápida |
| test_hidraulica_predial.py | não citado | faltante | existe; lane rápida |
| test_esgoto_reuso.py | não citado | faltante | existe; lane rápida |
| test_galpao_hidraulica.py | não citado | faltante | existe; lane rápida |
| test_climatizacao.py | não citado | faltante | existe; lane rápida |
| test_fotovoltaico.py | não citado | faltante | existe; lane rápida |
| test_terraplenagem.py | não citado | faltante | existe; lane rápida |
| test_piso_industrial.py | não citado | faltante | existe; lane rápida |
| test_geotecnia_spt.py | não citado | faltante | existe; lane rápida |
| test_pacote_legal.py | não citado | faltante | existe; lane rápida |
| test_caderno_encargos.py | não citado | faltante | existe; lane rápida |
| test_orcamento.py | não citado | faltante | existe; lane rápida |
| test_cronograma.py | não citado | faltante | existe; lane rápida |
| test_compatibilizacao.py | não citado | faltante | existe; lane rápida |
| test_guardas_entrada.py | não citado | faltante | existe; lane rápida |
| test_saturacao_verdito.py | não citado | faltante | existe; lane rápida |
| test_turnkey.py | não citado | faltante | existe; lane rápida |
| test_turnkey_bim.py | não citado | faltante | existe; lane rápida |
| test_turnkey_clash.py | não citado | faltante | existe; lane rápida |
| test_caderno_turnkey.py | não citado | faltante | existe; build-marked |
| test_build_federado.py | não citado | faltante | existe; build-marked (2 marcas) |
| test_executivo_hidr_cli.py | não citado | faltante | existe; lane rápida |
| test_executivo_incendio.py | não citado | faltante | existe; build-marked |
| test_fase64_coluna_tapered.py | não citado (nem como intervalo) | faltante | existe; lane pesada; build-marked |
| test_fase65_zona_painel.py | não citado (nem como intervalo) | faltante | existe; lane pesada; build-marked |
| test_fase66_flt_misula.py | não citado (nem como intervalo) | faltante | existe; lane pesada |
| test_fase67_vento_tesoura.py | não citado (nem como intervalo) | faltante | existe; lane pesada |
| test_fase68_alma_esbelta.py | não citado (nem como intervalo) | faltante | existe; lane pesada |
| test_fase6a_calha_divisa.py | não citado (nem como intervalo) | faltante | existe; lane pesada |
| test_fase6b_alma_variavel.py | não citado (nem como intervalo) | faltante | existe; lane pesada; build-marked |
| test_fase6c_tesoura.py | não citado (nem como intervalo) | faltante | existe; lane pesada; build-marked |
| test_fase69_tensao_ponto.py | só como intervalo "test_fase69 a test_fase614" (wiki:125) | faltante | existe; 11 testes; lane pesada |
| test_fase610_cortante_tapered.py | só como intervalo (wiki:125) | faltante | existe; 14 testes; lane pesada |
| test_fase611_vento_zona_tesoura.py | só como intervalo (wiki:125) | faltante | existe; 11 testes; lane pesada |
| test_fase612_dg25_crosscheck.py | só como intervalo (wiki:125) | faltante | existe; 9 testes; lane pesada |
| test_fase613_enrijecedor_painel.py | só como intervalo (wiki:125) | faltante | existe; 16 testes; lane pesada |
| test_fase614_dg25_full.py | só como intervalo (wiki:125) | faltante | existe; 19 testes; lane pesada |
| test_calhas_robustez.py | não citado | faltante | existe; lane rápida |
| test_console_flt.py | não citado | faltante | existe; lane rápida |
| test_escada_patamar.py | não citado | faltante | existe; 10 testes; lane rápida |
| test_galpao_climatizacao.py | não citado | faltante | existe; lane rápida |
| test_gusset_espessura_3d.py | não citado | faltante | existe; lane rápida |
| test_ligacoes_pos_rotacao.py | não citado | faltante | existe; lane rápida |
| test_longarina_els.py | não citado | faltante | existe; lane rápida |
| test_n_terca_calc_3d.py | não citado | faltante | existe; lane rápida |
| test_pilar_biaxial.py | não citado | faltante | existe; lane rápida |
| test_prancha_selecao.py | não citado | faltante | existe; lane rápida |
| test_secao_por_ligacao.py | não citado | faltante | existe; lane rápida |
| test_takeoff_rotulos.py | não citado | faltante | existe; lane rápida |
| test_telha_tipo_mapper.py | não citado | faltante | existe; lane rápida |
| test_terca_alma_normal.py | não citado | faltante | existe; lane rápida |
| test_terca_trib_real.py | não citado | faltante | existe; lane rápida |
| test_frame2d_hardening.py | não citado | faltante | existe; lane rápida |
| test_carimbo_materiais.py | não citado | faltante | existe; lane rápida |
| test_coordenacao.py | não citado | faltante | existe; lane rápida |
| test_coluna_orientacao.py | não citado | faltante | existe; lane rápida |
| test_aco_classe.py | não citado | faltante | existe; lane rápida |
| test_baldrame_els.py | não citado | faltante | existe; lane rápida |

**Nota:** o prefixo `test_galpao_eletrico*.py` (lista prévia da tarefa) **NÃO existe** — a família elétrica real são os 5 arquivos acima (`test_eletrico_bt`, `test_eletrico_robustez`, `test_eletrico_bim`, `test_build_eletrico`, `test_executivo_eletrico`), todos ausentes da wiki. `test_saturacao_verdito.py` existe com essa grafia exata.

### Tabela B — Testes descritos na wiki que NÃO existem (veredito: obsoleto)

**NENHUM.** Os 54 nomes de arquivo citados individualmente na wiki foram todos confirmados em `tests/`. Nenhum arquivo a remover.

---

## 2. Contagens (claims do ledger × números reais)

Números reais de referência (task-2, 2026-08-11): **1353 selecionados** (1374 coletados; 21 deselecionados = 18 build + 3 crashes) · **1340 passed** · **1 failed** (test_validacao::test_dossie_unico, fitz) · **15 skipped** · build-marked atual: **18 ocorrências em 17 arquivos** · total `def test_` nos 136 arquivos: **1345** (itens coletados são mais, 1370, devido a `@pytest.mark.parametrize`/importorskip em 13 arquivos — coleta não-execução desta task).

### Tabela C — Contagens de teste citadas × real

| claim (wiki) | origem | wiki diz | real (2026-08-11) | veredito |
|---|---|---|---|---|
| Fase 3: `test_fase3_fundacao_profunda.py` (13 fast + 1 build) | 02-test-tree:30 | 14 | **16** (15 non-build + 1 build) | corrigir |
| Fase 4: `test_fase4_ponte_estendida.py` (14) | 02-test-tree:31 | 14 | 14 | ok |
| Fase 5: `test_fase5_corte_seccionado.py` (1 build) | 02-test-tree:32 | 1 build | 1 build (0 fast) | ok |
| 6.15 `test_fase615_props_mono.py` (11) | 02-test-tree:37 | 11 | 11 | ok |
| 6.16 `test_fase616_dg25_envelope.py` (13) | 02-test-tree:38 | 13 | 13 | ok |
| 6.17 `test_fase617_forcas_localizadas.py` (11) | 02-test-tree:39 | 11 | 11 | ok |
| 6.18 `test_fase618_viga_equilibrio.py` (13) | 02-test-tree:40 | 13 | 13 | ok |
| 6.19 `test_fase619_glifo_solda.py` (9) | 02-test-tree:41 | 9 | 9 | ok |
| `smoke_executivo.py` **7/7** (padrão, vao_maior, baixo_largo, ponte, estaca, alma_var, tesoura) | 02-test-tree:44 | 7 casos | 7 casos confirmados no arquivo (linhas 109–120); smoke não re-rodado (build — todo 18) | ok |
| `test_validacao.py` (17 testes puros, sem FreeCAD) | 02-test-tree:46-53 | 17 | 17 coletados (16 passed + 1 F1 fitz na suíte) | ok |
| Suíte completa `-m "not build"`: **256 passed** | 02-test-tree:53 | 256 | **1340 passed / 1 failed / 15 skipped** | corrigir |
| `test_validacao_coerencia.py` (49) | 02-test-tree:72 | 49 | **51** | corrigir |
| `test_wizard_robustez.py` (6) | 02-test-tree:73 | 6 | **8** | corrigir |
| `test_mao_francesa_geom.py` (5) | 02-test-tree:74 | 5 | **12** | corrigir |
| `test_tesoura_lby_inf.py` (3) | 02-test-tree:75 | 3 | 3 | ok |
| `test_estaca_ponta.py` (5) | 02-test-tree:80 | 5 | 5 | ok |
| `test_executivo_cleanup.py` (3) | 02-test-tree:81 | 3 | 3 | ok |
| `test_ship_build_src.py` (3) | 02-test-tree:82 | 3 | 3 | ok |
| `test_empocamento.py` (5) | 02-test-tree:101 | 5 | 5 | ok |
| `test_romaneio.py` (7) | 02-test-tree:102 | 7 | 7 | ok |
| `test_tipo_ligacao.py` (6) | 02-test-tree:103 | 6 | 6 | ok |
| `test_torcao.py` (7) | 02-test-tree:104 | 7 | 7 | ok |
| `test_marcas_peca.py` (6) | 02-test-tree:105 | 6 | 6 | ok |
| `test_tolerancias.py` (5) | 02-test-tree:106 | 5 | 5 | ok |
| `test_croquis_fabricacao.py` (5) | 02-test-tree:107 | 5 | 5 | ok |
| `test_diafragma.py` (8) | 02-test-tree:108 | 8 | 8 | ok |
| `test_montagem.py` (12) | 02-test-tree:113 | 12 | 12 | ok |
| S20: PROTENSÃO ... **60 testes**; fixtures Bastos/Araújo/Carvalho | 00-index:25-26 | 60 | grupo concreto atual = **153** testes (17 arquivos); protensão estrita (viga_protendida+perdas_protensao+premoldado) = **31**; nenhum agrupamento atual soma 60 | corrigir |
| Elétrico: suíte **1040 green** | 00-index:29 | 1040 | **1353 selecionados / 1340 passed** | corrigir |
| PR #152: suíte non-build **~1281 testes**; ~28 pesados `test_fase*`/`test_crashes_wiki07` | 00-index:53-55 | 1281 | **1353 selecionados** (1374 coletados); pesados reais = **23 arquivos** (22 test_fase* + test_crashes_wiki07) | corrigir |
| xdist S40: **1281 passed** | 00-index:55-57 | 1281 | **1340 passed** | corrigir |
| Regressão pós-#150: a-l **770**, m-z **511** | 00-index:61-62 | 1281 | 1353 selecionados (shards a-l/m-z não re-deriváveis sem xdist) | corrigir |
| S19: **831 testes verdes** | 00-index:66-67 | 831 | 1353 selecionados / 1340 passed | corrigir |
| S18: **723 testes verdes** | 00-index:78-79 | 723 | 1353/1340 | corrigir |
| PR #49: **714 testes verdes** (incl. 9 build 3D) | 00-index:83 | 714/9 | 1353/1340; build atual = **18 ocorrências** (17 arquivos) | corrigir |
| PR #48: build 7 passed + 2 failed → **9 passed em 9** | 00-index:85-88 | 9 | build-marked atual = **18** | corrigir |
| PR #47: **12 novos testes** em `test_montagem.py` | 00-index:107 | 12 | 12 (arquivo tem 12 `def test_`) | ok |
| S17: **702 testes verdes** | 00-index:110-111 | 702 | 1353/1340 | corrigir |
| S16: **643 testes** (652 − 9 build) | 00-index:129-130 | 643 | 1353/1340; build atual 18 | corrigir |
| PR #44: reconciliado (7 commits, **643 testes**) | 00-index:146-147 | 643 | 1353/1340 | corrigir |
| 2026-07-16: PR #12; suíte completa **256 passed** | 00-index:173 | 256 | 1340 passed | corrigir |
| 2026-07-14: pytest **245 passed**, smoke_executivo 7/7 | 00-index:213 | 245 | 1340 passed (smoke 7/7: casos confirmados, não re-rodado) | corrigir |
| Regressão 2026-08-04: **1281 passed** (-n auto, 11m14s) | 00-index:251-252 | 1281 | **1340 passed** (falha F1 fitz + 15 skipped) | corrigir |
| 2026-07-22: **723 testes non-build + 9 build** | 00-index:253-262 | 723+9 | 1353 non-build + 18 build | corrigir |
| Não-regressão: pytest **245 passed**; smoke 7/7 | 03-phases:49-50 | 245 | 1340 passed | corrigir |
| test_fase69..612 (**11+14+13+9=47**); **113 passed** | 03-phases:238-241 | 47 / 113 | **11+14+11+9=45** (fase611 tem 11, não 13); 113 → 1340 passed | corrigir |
| Job build 3D: **9 testes** @pytest.mark.build | 03-phases:266-269 | 9 | **18** ocorrências build (17 arquivos) | corrigir |
| PR #47: suíte não-build com **705 passed** | 03-phases:287 | 705 | 1340 passed | corrigir |
| PRs #45/#46: **702 testes verdes** | 03-phases:305 | 702 | 1340 passed | corrigir |
| PR #44: **643 testes** | 03-phases:307-310 | 643 | 1353/1340 | corrigir |
| Status: 17 módulos matemáticos + features (todos com selftest verde): 12 r2 + Junta + Sismo + Telha + Baldrame + Estaca profunda + Contenção lateral | 03-phases:324-325 | 12 r2 | módulos citados existem todos com `_selftest` (ver Tab. D) | ok |
| T40: suíte 100% verde: a-l **770**, m-z **511** | 06-open-threads:4 | 1281 | 1353/1340 | corrigir |
| T21: **723 testes non-build verdes** (+18) | 06-open-threads:9-10 | 723 | 1353/1340 | corrigir |
| T20: **714 testes verdes** (incl. 9 build 3D) | 06-open-threads:19-20 | 714 | 1353/1340; 18 build | corrigir |
| T19: **714 testes verdes** (705 pytest + 9 deselected build) | 06-open-threads:32-33 | 714 | 1353/1340; 21 deselecionados atuais | corrigir |
| T19: **12 novos testes** em test_montagem.py | 06-open-threads:45 | 12 | 12 | ok |
| T18: **702 testes verdes** | 06-open-threads:50-51 | 702 | 1353/1340 | corrigir |
| T17: **643 testes** (652 − 9 build) | 06-open-threads:69-70 | 643 | 1353/1340; 18 build | corrigir |
| T17: 7 commits/**643 testes** | 06-open-threads:79-80 | 643 | 1353/1340 | corrigir |
| T15: suíte cheia **304 passed** (17m53s); ~40 testes novos em 11 arquivos | 06-open-threads:144-155 | 304 | 1340 passed | corrigir |
| T14 FEITO e verificado (**256 passed**) | 06-open-threads:178-181 | 256 | 1340 passed | corrigir |
| T13: pytest tests não-build **239 passed** | 06-open-threads:205-217 | 239 | 1340 passed | corrigir |
| T13: **239 passed**; 642k DeprecationWarnings sumiram | 06-open-threads:218-225 | 239 | 1340 passed; warnings atuais 743.424 | corrigir |
| T12: pytest **245**, smoke 7/7 | 06-open-threads:243-248 | 245 | 1340 passed | corrigir |

**Vereditos de contagem: 64 claims verificados → 25 ok · 39 corrigir.**

**Claims de contagem não-testáveis por esta tarefa (registrados, sem veredito):** "caderno turnkey 26 páginas, 14 pranchas A1" (00-index:60-61), "IFC4 1,67 MB com 789 elementos" (00-index:70), "smoke ≥9 pranchas (13 s/ponte, 14 c/ponte)" (02-test-tree:44), "não-regressão coluna 0,42 / viga 0,68 / base C2_uplift_W2 −57,5" (02-test-tree:3) — dependem de artefatos build/render ou de selftests de módulos (todos 9/10/18), não da suíte non-build.

---

## 3. Módulos e funções citados no test-tree (Tabela D)

**Módulos (coluna "Por módulo" + Sessões):** todos os citados existem em `framework/galpao_fw/` — `fundacao_sapata`, `ligacoes`, `ponte_rolante`, `mao_francesa`, `contraventamento`, `redimensionamento`, `check_nbr8800`, `base_chumbador`, `junta_dilatacao`, `vento_nbr6123`, `telha_cobertura`, `viga_baldrame`, `sismo_nbr15421`, `estaca_profunda`, `gusset_ligacao`, `console_ponte`, `nbr8400`, `props_I_mono`, `dg25_ltb`, `forcas_localizadas`, `viga_equilibrio`, `mao_francesa_geom`, `perfis`, `validacao`, `wizard`, `projeto_spec`, `modelo_neutro`, `ifc_emit`, `ifc_map`, `modelo_analitico` → **veredito ok** (n = 30).

| função citada (origem) | real | veredito |
|---|---|---|
| `lb_maximo` (02-test-tree:11) | `mao_francesa.py:42` | ok |
| `_peso_rel` (02-test-tree:13) | **NÃO existe** — real: `_peso(cols_perfil, raf)` em `redimensionamento.py:66` | **corrigir** |
| `chi_compressao` (02-test-tree:23) | `check_nbr8800.py:26` | ok |
| `block_shear_linha` / `solda` / `solda_filete_minimo` (02-test-tree:23) | `ligacoes.py:137/247/268` | ok |
| `coef_dinamico` / `n_ciclos` (02-test-tree:25) | `nbr8400.py:44/57` | ok |
| `_secao_ligacao` + `VLIG_SEC_*` (02-test-tree:32) | `techdraw_exec.py:1214/1234` | ok |
| `_ridge_h(i)` (02-test-tree:64) | `galpao_portico.py:196` | ok |
| `cpe_telhado_1agua` (02-test-tree:66) | `vento_nbr6123.py:111` | ok |
| `cargas_parede` + `w_col`/`w_masonry`/`N_masonry_ext` (02-test-tree:59) | `projeto_spec.py:588` (retorna `w_col_kN_m`, `w_masonry_kN_m`, `N_masonry_ext_kN`) | ok |
| `_janela_band` (02-test-tree:60) | `projeto_spec.py:631` | ok |
| `segmentos` (02-test-tree:74) | `mao_francesa_geom.py:60` | ok |
| `_camada_na_ponta` (02-test-tree:80) | `estaca_profunda.py:116` | ok |
| `_matar_processo_freecad` (02-test-tree:81) | `rodar_projeto.py:331` | ok |
| `_ship_build_src` (02-test-tree:82) | `rodar_projeto.py:132` | ok |
| `validacao.rodar()` / `validacao_referencia` (02-test-tree:47) | `validacao.py:169/261` | ok |
| `wizard.construir_spec` / `rodar_tudo` (02-test-tree:49) | `wizard.py:221` / `rodar_projeto.py:479` | ok |
| `_codigo_prancha`/`_pos_notas`/`_cap_titulo`/`_fmt_terca`/`_quadro_fundacao`/`_pos_corte_ligacao`/`_callout_bloco` (02-test-tree:51-52) | `techdraw_exec.py:484/465/496/513/523/551/562` | ok |
| `montar_modelo` (02-test-tree:124) | `rodar_projeto.py:210` | ok |
| `_pr_croquis` (02-test-tree:107) | `techdraw_exec.py:1629` | ok |
| `_notas_do_modelo` (02-test-tree:95) | `techdraw_exec.py:1429` | ok |
| `cobertura.nao_cobertos`/`detalhes_edges`/`base_lig` (02-test-tree:44) | `smoke_executivo.py:189/194/197` | ok |
| "Cada módulo de cálculo tem `_selftest()`" (02-test-tree:3) | **107 módulos** com `def _selftest` + antigos via `__main__` (check_nbr8800, redimensionamento, estabilidade_b1b2, tercas_iteracao); exceções sem selftest: `perfis.py`, `mao_francesa_geom.py` (tabela/geometria, cobertos por pytest) | ok (ressalva registrada) |

**Funções que não conferem: 1 (`_peso_rel`).**

---

## 4. QA interno — 5 arquivos citados na wiki, rodados ISOLADOS

Comando por arquivo: `& <venv-principal>/python.exe -m pytest -p no:cacheprovider tests/test_X.py -q` (cwd = worktree `framework\galpao_fw`; timeout 300.000 ms).

| arquivo | citado em | resultado | confere com a wiki |
|---|---|---|---|
| test_empocamento.py | 02-test-tree:101 (5) | **5 passed** in 0.16s | sim (5) |
| test_romaneio.py | 02-test-tree:102 (7) | **7 passed** in 0.19s | sim (7) |
| test_tipo_ligacao.py | 02-test-tree:103 (6) | **6 passed** in 0.85s | sim (6) |
| test_marcas_peca.py | 02-test-tree:105 (6) | **6 passed** in 0.17s | sim (6) |
| test_diafragma.py | 02-test-tree:108 (8) | **8 passed** in 0.20s | sim (8) |

**5/5 arquivos passam isolados (32 testes, 0 falhas); nenhum arquivo descrito na wiki deixou de existir (0 "obsoleto").** Os 5 arquivos também passaram dentro da suíte completa do task-2 (1340 passed).

---

## 5. PATCH LIST

Convenção: para claims existentes no ledger usa-se `task-5:<linha>` (linha-original do ledger task-5); para arquivos ausentes (sem claim no ledger) usa-se `02-test-tree.md:<linha-alvo>` (linha 126 = fim das seções de sessão, onde as novas seções devem entrar — alimenta o todo 13).

### Corrigir (contagens e nomes)

| arquivo:linha | sujeito | veredito | origem |
|---|---|---|---|
| task-5:166 | fase3 (13 fast + 1 build) | corrigir | task-8 |
| task-5:176 | 256 passed | corrigir | task-8 |
| task-5:179 | validacao_coerencia (49) | corrigir | task-8 |
| task-5:179 | wizard_robustez (6) | corrigir | task-8 |
| task-5:179 | mao_francesa_geom (5) | corrigir | task-8 |
| task-5:153 | `_peso_rel` (nome — real `_peso`) | corrigir | task-8 |
| task-5:24 | 60 testes S20 | corrigir | task-8 |
| task-5:27 | 1040 green | corrigir | task-8 |
| task-5:41 | ~1281 testes | corrigir | task-8 |
| task-5:42 | 1281 passed (xdist) | corrigir | task-8 |
| task-5:44 | a-l 770, m-z 511 | corrigir | task-8 |
| task-5:45 | 831 testes verdes (S19) | corrigir | task-8 |
| task-5:52 | 723 testes verdes (S18) | corrigir | task-8 |
| task-5:55 | 714 testes verdes / 9 build | corrigir | task-8 |
| task-5:57 | 9 passed build (PR #48) | corrigir | task-8 |
| task-5:63 | 702 testes verdes (S17) | corrigir | task-8 |
| task-5:67 | 643 testes (652−9) S16 | corrigir | task-8 |
| task-5:71 | 643 testes PR #44 | corrigir | task-8 |
| task-5:78 | 256 passed (2026-07-16) | corrigir | task-8 |
| task-5:87 | 245 passed (2026-07-14) | corrigir | task-8 |
| task-5:93 | 1281 passed (2026-08-04) | corrigir | task-8 |
| task-5:94 | 723 non-build + 9 build | corrigir | task-8 |
| task-5:204 | 245 passed (03-phases) | corrigir | task-8 |
| task-5:253 | fase69..612 11+14+13+9=47 | corrigir | task-8 |
| task-5:253 | 113 passed | corrigir | task-8 |
| task-5:261 | 9 testes @pytest.mark.build | corrigir | task-8 |
| task-5:265 | 705 passed | corrigir | task-8 |
| task-5:270 | 702 testes verdes | corrigir | task-8 |
| task-5:271 | 643 testes (03-phases) | corrigir | task-8 |
| task-5:417 | T40 a-l 770, m-z 511 | corrigir | task-8 |
| task-5:420 | T21 723 (+18) | corrigir | task-8 |
| task-5:426 | T20 714 (9 build) | corrigir | task-8 |
| task-5:430 | T19 714 (705+9) | corrigir | task-8 |
| task-5:434 | T18 702 testes verdes | corrigir | task-8 |
| task-5:437 | T17 643 (652−9) | corrigir | task-8 |
| task-5:439 | T17 643 | corrigir | task-8 |
| task-5:445 | T15 304 passed | corrigir | task-8 |
| task-5:449 | T14 256 passed | corrigir | task-8 |
| task-5:452 | T13 239 passed | corrigir | task-8 |
| task-5:453 | T13 239 passed | corrigir | task-8 |
| task-5:455 | T12 245 | corrigir | task-8 |

### Faltante (arquivos de teste existentes não citados na wiki)

| arquivo:linha | sujeito | veredito | origem |
|---|---|---|---|
| 02-test-tree.md:126 | test_galpao_concreto.py | faltante | task-8 |
| 02-test-tree.md:126 | test_galpao_concreto_bim.py | faltante | task-8 |
| 02-test-tree.md:126 | test_pilar_concreto.py | faltante | task-8 |
| 02-test-tree.md:126 | test_viga_concreto.py | faltante | task-8 |
| 02-test-tree.md:126 | test_desenho_concreto.py | faltante | task-8 |
| 02-test-tree.md:126 | test_build_concreto.py | faltante | task-8 |
| 02-test-tree.md:126 | test_executivo_concreto.py | faltante | task-8 |
| 02-test-tree.md:126 | test_techdraw_concreto.py | faltante | task-8 |
| 02-test-tree.md:126 | test_viga_protendida.py | faltante | task-8 |
| 02-test-tree.md:126 | test_premoldado_nbr9062.py | faltante | task-8 |
| 02-test-tree.md:126 | test_perdas_protensao_nbr6118.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fissuracao_nbr6118.py | faltante | task-8 |
| 02-test-tree.md:126 | test_estabilidade_global_nbr6118.py | faltante | task-8 |
| 02-test-tree.md:126 | test_torcao_nbr6118.py | faltante | task-8 |
| 02-test-tree.md:126 | test_eletrico_bt.py | faltante | task-8 |
| 02-test-tree.md:126 | test_eletrico_robustez.py | faltante | task-8 |
| 02-test-tree.md:126 | test_eletrico_bim.py | faltante | task-8 |
| 02-test-tree.md:126 | test_build_eletrico.py | faltante | task-8 |
| 02-test-tree.md:126 | test_executivo_eletrico.py | faltante | task-8 |
| 02-test-tree.md:126 | test_seguranca_incendio.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fogo_nbr15200.py | faltante | task-8 |
| 02-test-tree.md:126 | test_hidrantes.py | faltante | task-8 |
| 02-test-tree.md:126 | test_iluminacao_externa.py | faltante | task-8 |
| 02-test-tree.md:126 | test_incendio_bim.py | faltante | task-8 |
| 02-test-tree.md:126 | test_incendio_robustez.py | faltante | task-8 |
| 02-test-tree.md:126 | test_hidraulica_predial.py | faltante | task-8 |
| 02-test-tree.md:126 | test_esgoto_reuso.py | faltante | task-8 |
| 02-test-tree.md:126 | test_galpao_hidraulica.py | faltante | task-8 |
| 02-test-tree.md:126 | test_climatizacao.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fotovoltaico.py | faltante | task-8 |
| 02-test-tree.md:126 | test_terraplenagem.py | faltante | task-8 |
| 02-test-tree.md:126 | test_piso_industrial.py | faltante | task-8 |
| 02-test-tree.md:126 | test_geotecnia_spt.py | faltante | task-8 |
| 02-test-tree.md:126 | test_pacote_legal.py | faltante | task-8 |
| 02-test-tree.md:126 | test_caderno_encargos.py | faltante | task-8 |
| 02-test-tree.md:126 | test_orcamento.py | faltante | task-8 |
| 02-test-tree.md:126 | test_cronograma.py | faltante | task-8 |
| 02-test-tree.md:126 | test_compatibilizacao.py | faltante | task-8 |
| 02-test-tree.md:126 | test_guardas_entrada.py | faltante | task-8 |
| 02-test-tree.md:126 | test_saturacao_verdito.py | faltante | task-8 |
| 02-test-tree.md:126 | test_turnkey.py | faltante | task-8 |
| 02-test-tree.md:126 | test_turnkey_bim.py | faltante | task-8 |
| 02-test-tree.md:126 | test_turnkey_clash.py | faltante | task-8 |
| 02-test-tree.md:126 | test_caderno_turnkey.py | faltante | task-8 |
| 02-test-tree.md:126 | test_build_federado.py | faltante | task-8 |
| 02-test-tree.md:126 | test_executivo_hidr_cli.py | faltante | task-8 |
| 02-test-tree.md:126 | test_executivo_incendio.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase64_coluna_tapered.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase65_zona_painel.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase66_flt_misula.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase67_vento_tesoura.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase68_alma_esbelta.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase6a_calha_divisa.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase6b_alma_variavel.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase6c_tesoura.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase69_tensao_ponto.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase610_cortante_tapered.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase611_vento_zona_tesoura.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase612_dg25_crosscheck.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase613_enrijecedor_painel.py | faltante | task-8 |
| 02-test-tree.md:126 | test_fase614_dg25_full.py | faltante | task-8 |
| 02-test-tree.md:126 | test_calhas_robustez.py | faltante | task-8 |
| 02-test-tree.md:126 | test_console_flt.py | faltante | task-8 |
| 02-test-tree.md:126 | test_escada_patamar.py | faltante | task-8 |
| 02-test-tree.md:126 | test_galpao_climatizacao.py | faltante | task-8 |
| 02-test-tree.md:126 | test_gusset_espessura_3d.py | faltante | task-8 |
| 02-test-tree.md:126 | test_ligacoes_pos_rotacao.py | faltante | task-8 |
| 02-test-tree.md:126 | test_longarina_els.py | faltante | task-8 |
| 02-test-tree.md:126 | test_n_terca_calc_3d.py | faltante | task-8 |
| 02-test-tree.md:126 | test_pilar_biaxial.py | faltante | task-8 |
| 02-test-tree.md:126 | test_prancha_selecao.py | faltante | task-8 |
| 02-test-tree.md:126 | test_secao_por_ligacao.py | faltante | task-8 |
| 02-test-tree.md:126 | test_takeoff_rotulos.py | faltante | task-8 |
| 02-test-tree.md:126 | test_telha_tipo_mapper.py | faltante | task-8 |
| 02-test-tree.md:126 | test_terca_alma_normal.py | faltante | task-8 |
| 02-test-tree.md:126 | test_terca_trib_real.py | faltante | task-8 |
| 02-test-tree.md:126 | test_frame2d_hardening.py | faltante | task-8 |
| 02-test-tree.md:126 | test_carimbo_materiais.py | faltante | task-8 |
| 02-test-tree.md:126 | test_coordenacao.py | faltante | task-8 |
| 02-test-tree.md:126 | test_coluna_orientacao.py | faltante | task-8 |
| 02-test-tree.md:126 | test_aco_classe.py | faltante | task-8 |
| 02-test-tree.md:126 | test_baldrame_els.py | faltante | task-8 |

**Obsoleto: nenhum (0 linhas).**

---

## 6. Escopo respeitado

- NENHUM arquivo da wiki editado; NENHUM arquivo de teste corrigido; NENHUM commit (`git status` limpo exceto `?? .omo/`).
- Suíte completa NÃO re-rodada — apenas: (a) `--collect-only` (coleta, sem execução de testes) para contagens por arquivo; (b) 5 arquivos isolados no QA (32 testes, todos passaram).
- Ledger task-5 NÃO editado — PATCH LIST acima será aplicado na atualização serializada (todo posterior).
- Artefatos brutos: `%TEMP%\opencode\collect_task8.log` (coleta), `%TEMP%\opencode\test_counts.csv`, `%TEMP%\opencode\test_per_file.csv`.
