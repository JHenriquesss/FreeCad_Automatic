# Task 2 — Inventário de testes + suíte non-build (revisão-wiki)

**Data:** 2026-08-11
**Branch (worktree):** `docs/revisao-wiki-2026-08-11` (worktree `FreeCad_Automatic-wt`, commit base `6358157`)
**cwd de execução:** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic-wt\framework\galpao_fw`
**python (caminho absoluto):** `C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic\framework\galpao_fw\.venv\Scripts\python.exe`
**pytest:** 9.1.1 · **pytest-xdist:** NÃO instalado → runner usou fallback de 2 lanes sequenciais

## Nota de dependências (regra do plano)

O `.venv` do projeto **não existe no worktree** (é gitignored e não é carregado em worktrees).
Usado o `.venv` do **repo PRINCIPAL por caminho absoluto** (`...\FreeCad_Automatic\framework\galpao_fw\.venv\Scripts\python.exe`).
A venv resolve `site-packages` via `pyvenv.cfg`, funcionando com cwd no worktree — verificado em execução (suíte coletou e rodou os 136 arquivos de teste do worktree).

## Inventário de arquivos de teste

- **Total: 136 arquivos** `tests\*.py` (o diretório tem 137 entradas, incluindo `__pycache__/`, criado pela própria suíte durante a execução).
- **17 arquivos com `pytest.mark.build`** (18 ocorrências; `test_build_federado.py` tem 2) — contêm testes build **e** testes fast:
  `test_bloco_fundacao.py`, `test_build_concreto.py`, `test_build_eletrico.py`, `test_build_federado.py`, `test_caderno_turnkey.py`, `test_carga_parede.py`, `test_executivo_eletrico.py`, `test_executivo_incendio.py`, `test_fase3_fundacao_profunda.py`, `test_fase5_corte_seccionado.py`, `test_fase64_coluna_tapered.py`, `test_fase65_zona_painel.py`, `test_fase6b_alma_variavel.py`, `test_fase6c_tesoura.py`, `test_ifc_secundarios_xcheck.py`, `test_shed.py`, `test_techdraw_concreto.py`
- **119 arquivos fast** (sem marcador build).
- **23 arquivos da lane pesada** (22 `test_fase*` + `test_crashes_wiki07.py`) — end-to-end que rodam `rodar_projeto.calcular` completo, ~20 s cada.
- **113 arquivos da lane rápida.**

Lista completa dos 136 arquivos com classificação na seção "Anexo A".

## Execução da suíte (non-build)

Hierarquia do plano respeitada: **runner → espelho manual 2 lanes** (o runner falhou na lane 2 — ver Finding F2).

**Run primário** (`tools/run_tests.py`, sem xdist):
```
& "C:\Users\joseh\OneDrive\Área de Trabalho\dev\FreeCad_Automatic\framework\galpao_fw\.venv\Scripts\python.exe" tools/run_tests.py
```
- Lane 1 (interna do runner): `pytest -p no:cacheprovider -m not build tests/ --ignore-glob=*/test_fase* -k not crashes_wiki07` → **rodou completa, 213.55s**
- Lane 2 (interna do runner): `pytest -p no:cacheprovider -m not build tests/test_fase*.py tests/test_crashes_wiki07.py` → **ERRO**: `ERROR: file or directory not found: tests/test_fase*.py` (glob não expandido pelo PowerShell — passado literal ao pytest) → `no tests ran in 0.00s`

**Fallback manual — lane 2 (lista de arquivos EXPANDIDA explicitamente, 23 arquivos):**
```
& "C:\...\FreeCad_Automatic\framework\galpao_fw\.venv\Scripts\python.exe" -m pytest -p no:cacheprovider -m "not build" <23 caminhos explícitos: 22 tests\test_fase*.py + tests\test_crashes_wiki07.py>
```
→ **rodou completa, 489.71s**

## Contagens reais

| Métrica | Lane 1 (rápida, runner) | Lane 2 (pesada, manual) | **Total** |
|---|---|---|---|
| Coletados | 1125 | 249 | **1374** |
| Deselecionados | 15 | 6 | **21** |
| Selecionados | 1110 | 243 | **1353** |
| **passed** | 1097 | 243 | **1340** |
| **failed** | 1 | 0 | **1** |
| **skipped** | 15 | 0 | **15** |
| errored | 0 | 0 | **0** |
| warnings | 50688 | 692736 | 743424 |
| Duração pytest | 213.55s (0:03:33) | 489.71s (0:08:09) | **703.26s (0:11:43)** |

- **Duração total (wall, incl. ~15s de overhead entre lanes): ~11m58s**
- Exit codes: runner = **5** (lane 1 rc 5 por 1 falha | lane 2 rc 4 por erro de uso — OR binário); lane 2 manual = **0**
- Linhas-resumo verbatim:
  - Lane 1: `= 1 failed, 1097 passed, 15 skipped, 15 deselected, 50688 warnings in 213.55s (0:03:33) =`
  - Lane 2: `======= 243 passed, 6 deselected, 692736 warnings in 489.71s (0:08:09) ========`
- Header de coleta lane 1: `collected 1125 items / 15 deselected / 3 skipped / 1110 selected` (os "15 skipped" do resumo incluem skips em runtime)
- Deselecionados (21) = 18 testes marcados `build` + 3 testes de `test_crashes_wiki07.py` excluídos via `-k not crashes_wiki07` na lane 1 (o arquivo tem 4 `def test_`; os demais rodaram na lane 2)

## Comparação com o claim da wiki

| Claim da wiki | Real medido (2026-08-11) | Delta |
|---|---|---|
| ~1281 testes (suíte non-build, `-n auto` no S40) | **1353 selecionados** (1374 coletados) | **+72 selecionados** |
| 1281 passed com xdist (S40) | 1340 passed / 1 failed / 15 skipped | +59 passed, 1 falha nova |
| README `tools/`: 1038 rápidos + 243 pesados = 1281 | lane 1 = 1110 selecionados + lane 2 = 243 selecionados | lane rápida +72 |

Leitura: a suíte **cresceu desde S40** (~72 testes novos na lane rápida — consistente com os waves S42 de `pacote-legal`/`caderno-encargos` no log git). Os 243 da lane pesada batem exatamente. Dados brutos para o todo 5 (claims) e todo 8 (cross-check test-tree).

## Findings — falhas pré-existentes (NENHUMA corrigida)

- **F1 — `tests/test_validacao.py::test_dossie_unico` (FAILED)**: `ModuleNotFoundError: No module named 'fitz'` (em `import fitz`, `dossie.py:105`). Causa: módulo PyMuPDF (`fitz`) **não instalado** no `.venv`. Falha pré-existente de dependência, não corrigida.
- **F2 — `tools/run_tests.py` lane 2 do fallback quebrada em shell Windows**: globs `tests/test_fase*.py` passados literalmente ao pytest (PowerShell/cmd não expandem glob) → `ERROR: file or directory not found: tests/test_fase*.py` + `no tests ran in 0.00s`. O caminho xdist (`-n auto`, passa `tests/` sem glob) não sofre isso; o fallback só funciona via shell com expansão de glob (ex.: git-bash). Bug de ferramenta pré-existente, não corrigido (contornado na execução com lista explícita de arquivos).
- Warnings (743.424 total): dominados por `DeprecationWarning` do `pycufsm` (numpy <1.25, "Conversion of an array with ndim > 0 to a scalar") e warnings de `test_validacao.py` (640) — não contam como falha; registrados para auditoria de escopo.

## Escopo respeitado

- Suíte rodada **apenas no worktree** (`FreeCad_Automatic-wt`) — nada rodado na pasta do repo principal.
- Nenhum teste corrigido, nenhum arquivo de código/teste modificado (`git status` limpo, exceto `?? .omo/` — evidência desta revisão).
- Nenhum commit.
- `-m build` / `smoke_executivo.py` NÃO rodados (todo 18 / Wave 5).
- Nenhum diretório `saida_*` foi criado por esta execução da suíte non-build (verificado no worktree root e em `framework/galpao_fw`; `saida_*` devem ser artefatos de execuções build/smoke de outros todos) — registrado para a auditoria de escopo.
- Logs brutos: `%TEMP%\opencode\suite_task2.log` (runner — lane 1) e `%TEMP%\opencode\suite_task2_lane2.log` (lane 2 manual).

## QA interno (registrado)

- Happy path não atingido (exit 0) — **1 falha pré-existente** (F1) registrada na íntegra acima; suíte 100% executada nas 2 lanes com contagens completas.
- Contagens da evidência conferem com as linhas-resumo verbatim dos logs.
- Inventário de 136 arquivos gerado por varredura do diretório, classificação build por grep de `pytest.mark.build`; cruzado com a contagem de deselecionados (18 build + 3 crashes = 21) — consistente.

## Anexo A — Lista completa dos 136 arquivos `tests\*.py` classificados

| Arquivo | Marcador build | Lane |
|---|---|---|
| test_aberturas_janela.py | fast | rápida |
| test_aco_classe.py | fast | rápida |
| test_baldrame_els.py | fast | rápida |
| test_bloco_fundacao.py | build-marked | rápida |
| test_build_concreto.py | build-marked | rápida |
| test_build_eletrico.py | build-marked | rápida |
| test_build_federado.py | build-marked | rápida |
| test_caderno_encargos.py | fast | rápida |
| test_caderno_turnkey.py | build-marked | rápida |
| test_calha_calc_3d.py | fast | rápida |
| test_calhas_robustez.py | fast | rápida |
| test_cantoneira_geom.py | fast | rápida |
| test_carga_parede.py | build-marked | rápida |
| test_carimbo_materiais.py | fast | rápida |
| test_climatizacao.py | fast | rápida |
| test_coluna_orientacao.py | fast | rápida |
| test_compatibilizacao.py | fast | rápida |
| test_console_flt.py | fast | rápida |
| test_contencao_lateral.py | fast | rápida |
| test_coordenacao.py | fast | rápida |
| test_crashes_wiki07.py | fast | pesada |
| test_cronograma.py | fast | rápida |
| test_croquis_fabricacao.py | fast | rápida |
| test_desenho_concreto.py | fast | rápida |
| test_diafragma.py | fast | rápida |
| test_eletrico_bim.py | fast | rápida |
| test_eletrico_bt.py | fast | rápida |
| test_eletrico_robustez.py | fast | rápida |
| test_empocamento.py | fast | rápida |
| test_escada_patamar.py | fast | rápida |
| test_esgoto_reuso.py | fast | rápida |
| test_estabilidade_global_nbr6118.py | fast | rápida |
| test_estaca_ponta.py | fast | rápida |
| test_executivo_cleanup.py | fast | rápida |
| test_executivo_concreto.py | fast | rápida |
| test_executivo_eletrico.py | build-marked | rápida |
| test_executivo_hidr_cli.py | fast | rápida |
| test_executivo_incendio.py | build-marked | rápida |
| test_fase3_fundacao_profunda.py | build-marked | pesada |
| test_fase4_ponte_estendida.py | fast | pesada |
| test_fase5_corte_seccionado.py | build-marked | pesada |
| test_fase610_cortante_tapered.py | fast | pesada |
| test_fase611_vento_zona_tesoura.py | fast | pesada |
| test_fase612_dg25_crosscheck.py | fast | pesada |
| test_fase613_enrijecedor_painel.py | fast | pesada |
| test_fase614_dg25_full.py | fast | pesada |
| test_fase615_props_mono.py | fast | pesada |
| test_fase616_dg25_envelope.py | fast | pesada |
| test_fase617_forcas_localizadas.py | fast | pesada |
| test_fase618_viga_equilibrio.py | fast | pesada |
| test_fase619_glifo_solda.py | fast | pesada |
| test_fase64_coluna_tapered.py | build-marked | pesada |
| test_fase65_zona_painel.py | build-marked | pesada |
| test_fase66_flt_misula.py | fast | pesada |
| test_fase67_vento_tesoura.py | fast | pesada |
| test_fase68_alma_esbelta.py | fast | pesada |
| test_fase69_tensao_ponto.py | fast | pesada |
| test_fase6a_calha_divisa.py | fast | pesada |
| test_fase6b_alma_variavel.py | build-marked | pesada |
| test_fase6c_tesoura.py | build-marked | pesada |
| test_fissuracao_nbr6118.py | fast | rápida |
| test_fogo_nbr15200.py | fast | rápida |
| test_fotovoltaico.py | fast | rápida |
| test_frame2d_hardening.py | fast | rápida |
| test_frame2d_sinal.py | fast | rápida |
| test_galpao_climatizacao.py | fast | rápida |
| test_galpao_concreto.py | fast | rápida |
| test_galpao_concreto_bim.py | fast | rápida |
| test_galpao_hidraulica.py | fast | rápida |
| test_geotecnia_spt.py | fast | rápida |
| test_guardas_entrada.py | fast | rápida |
| test_gusset_espessura_3d.py | fast | rápida |
| test_hidrantes.py | fast | rápida |
| test_hidraulica_predial.py | fast | rápida |
| test_ifc_emit.py | fast | rápida |
| test_ifc_map.py | fast | rápida |
| test_ifc_secundarios_xcheck.py | build-marked | rápida |
| test_iluminacao_externa.py | fast | rápida |
| test_incendio_bim.py | fast | rápida |
| test_incendio_robustez.py | fast | rápida |
| test_ligacoes_pos_rotacao.py | fast | rápida |
| test_longarina_els.py | fast | rápida |
| test_mao_francesa_cantoneira.py | fast | rápida |
| test_mao_francesa_geom.py | fast | rápida |
| test_marcas_peca.py | fast | rápida |
| test_modelo_analitico.py | fast | rápida |
| test_modelo_neutro.py | fast | rápida |
| test_montagem.py | fast | rápida |
| test_montar_headless.py | fast | rápida |
| test_multivao_hetero.py | fast | rápida |
| test_n_terca_calc_3d.py | fast | rápida |
| test_notas_prancha_x_modelo.py | fast | rápida |
| test_orcamento.py | fast | rápida |
| test_pacote_legal.py | fast | rápida |
| test_pecas_conexao_encaixe.py | fast | rápida |
| test_perdas_protensao_nbr6118.py | fast | rápida |
| test_pilar_biaxial.py | fast | rápida |
| test_pilar_concreto.py | fast | rápida |
| test_pipeline_bim.py | fast | rápida |
| test_piso_industrial.py | fast | rápida |
| test_prancha_selecao.py | fast | rápida |
| test_premoldado_nbr9062.py | fast | rápida |
| test_quadro_materiais_prancha.py | fast | rápida |
| test_relatorio_x_calculo.py | fast | rápida |
| test_romaneio.py | fast | rápida |
| test_saturacao_verdito.py | fast | rápida |
| test_secao_por_ligacao.py | fast | rápida |
| test_seguranca_incendio.py | fast | rápida |
| test_shed.py | build-marked | rápida |
| test_ship_build_src.py | fast | rápida |
| test_ship_cache_modulo.py | fast | rápida |
| test_takeoff_rotulos.py | fast | rápida |
| test_takeoff_x_modelo.py | fast | rápida |
| test_techdraw_concreto.py | build-marked | rápida |
| test_telha_tipo_mapper.py | fast | rápida |
| test_terca_alma_normal.py | fast | rápida |
| test_terca_assento_3d.py | fast | rápida |
| test_terca_trib_real.py | fast | rápida |
| test_terraplenagem.py | fast | rápida |
| test_terreno_mapper.py | fast | rápida |
| test_tesoura_lby_inf.py | fast | rápida |
| test_tipo_ligacao.py | fast | rápida |
| test_tolerancias.py | fast | rápida |
| test_torcao.py | fast | rápida |
| test_torcao_nbr6118.py | fast | rápida |
| test_turnkey.py | fast | rápida |
| test_turnkey_bim.py | fast | rápida |
| test_turnkey_clash.py | fast | rápida |
| test_validacao.py | fast | rápida |
| test_validacao_alonso.py | fast | rápida |
| test_validacao_coerencia.py | fast | rápida |
| test_vento_uplift.py | fast | rápida |
| test_viga_concreto.py | fast | rápida |
| test_viga_protendida.py | fast | rápida |
| test_viga_rolamento_3d.py | fast | rápida |
| test_wizard_robustez.py | fast | rápida |
