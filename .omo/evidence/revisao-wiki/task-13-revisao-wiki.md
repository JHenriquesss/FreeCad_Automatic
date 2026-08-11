# Task 13 — Atualização serializada de `02-test-tree.md` (revisão-wiki)

**Data:** 2026-08-11
**Branch (worktree):** `docs/revisao-wiki-2026-08-11` (worktree `FreeCad_Automatic-wt`)
**Arquivo editado (ÚNICO):** `framework/galpao_fw/wiki/02-test-tree.md` (129 → 280 linhas; UTF-8 sem BOM, validação estrita ok)
**Entradas usadas (NÃO refeitas):** inventário + suíte `task-2-revisao-wiki.md` (136 arquivos; 1353 sel / 1340 passed / 1 failed F1-fitz / 15 skip; runner `tools/run_tests.py`; 23 lane pesada); cross-check `task-8-revisao-wiki.md` (82 faltantes + PATCH LIST + 41 correções); ledger `task-5-revisao-wiki.md` (vereditos).
**Extração de conteúdo (nova, nesta task):** docstrings + nomes `def test_*` + docstrings de teste dos 82 arquivos lidos direto de `tests/` (script `%TEMP%\opencode\extract_test_docs.py` → `extracted_test_docs.txt`) — nenhuma redação inventada, tudo derivado dos arquivos.
**Nenhum commit; nenhum outro arquivo editado.**

---

## 1. Linha de abertura (02:3) — atualizada

Mantido o conteúdo verificado (selftest por módulo + valores de não-regressão coluna 0,42 / viga 0,68 / base −57,5) e APENDADO ao parágrafo:

- comando real do runner: `python tools/run_tests.py` (lane rápida `tests/` exceto `test_fase*`/`test_crashes_wiki07` + lane pesada `test_fase*.py`/`test_crashes_wiki07.py`; xdist `-n auto` quando instalado, senão fallback 2 lanes sequenciais);
- contagem real da suíte (task-2): **1353 selecionados / 1340 passed / 1 failed / 15 skipped** (2026-08-11);
- nota do finding F1: falha única = `test_validacao::test_dossie_unico` — PyMuPDF `fitz` ausente no venv (dependência de instalação, não regressão).

## 2. Correções aplicadas nas seções existentes (task-8, 02-test-tree)

| linha (nova) | claim antigo | corrigido para | fonte |
|---|---|---|---|
| 13 | `_peso_rel` | `_peso` (função real `_peso(cols_perfil, raf)` em `redimensionamento.py:66`) | task-8 Tab. D |
| 30 | fase3 `(13 fast + 1 build)` | `(15 fast + 1 build)` = 16 | task-8 Tab. C |
| 53 | suíte `-m "not build"`: **256 passed** | **1340 passed / 1 failed / 15 skipped** (1353 sel; falha = `test_dossie_unico`, fitz) | task-8 Tab. C |
| 72 | `test_validacao_coerencia.py` (49) | (51) | task-8 Tab. C |
| 73 | `test_wizard_robustez.py` (6) | (8) | task-8 Tab. C |
| 74 | `test_mao_francesa_geom.py` (5) | (12) | task-8 Tab. C |

**6 correções** (as 41 do PATCH LIST que pertencem a 02-test-tree; as demais são de 00-index/03-phases/06-open-threads → outros todos). Verificado por `git diff`: **7 deleções no total** = linha 3 + as 6 correções; nenhum outro conteúdo de S3–S19 alterado (aço não reescrito). A correção `fase611 13→11` (origem 03-phases:238) refletida no novo registro S32: `test_fase611_vento_zona_tesoura.py` (11).

## 3. Seções APENDADAS — 82 arquivos novos, um por linha, com o que assere

Todas as redações derivadas de docstring/nomes de teste lidos dos arquivos (sem inventar). Contagens entre parênteses = confirmadas pelo collect-only do task-8; os demais arquivos ficaram SEM contagem (não verificada por coleta).

### Sessão 20 — Concreto armado/pré-moldado (8)
| arquivo | assere (1 linha) |
|---|---|
| test_galpao_concreto.py (21) | orquestrador `galpao_concreto` stateless (pilares engastados + viga biapoiada + sapata): vão grande→protensão, gate cálice/icamento, TRRF (isento c/ nota / 1 face / multiface→Anexo E), interferências e sobreposição de sapatas |
| test_galpao_concreto_bim.py (7) | BIM IFC4 do galpão de concreto: IfcColumn/IfcBeam/IfcFooting, material Concreto Cxx + Pset de armadura, sem FreeCAD |
| test_pilar_concreto.py (12) | pilar em flexão composta NBR 6118 aferido em 3 exemplos de Bastos (Md,tot e As); γn Tab.13.1, λ1 35–90, curvatura limitada |
| test_viga_concreto.py (8) | viga retangular NBR 6118 aferida em Araújo e Carvalho & Figueiredo; biela de cortante, ELS L/250 (alvenaria L/500), As_min |
| test_desenho_concreto.py (8) | formas + armação em SVG puro: bem-formado E cabe no canvas (regressão de escala de metros) |
| test_build_concreto.py (8) | build 3D do concreto: caixas()/_takeoff() puros (orientação/volume) + camada build headless sem interferência |
| test_executivo_concreto.py (7) | executivo de concreto: quadro de aço (dobramento) + resumo + memorial; quantidades escalam com nº de pórticos |
| test_techdraw_concreto.py (7) | pranchas A1 TechDraw do concreto: cfg/quadros por tipo, carimbo não vaza aço; build gera PDF |

### Sessão 21 — Protensão e pré-moldado (6)
| test_viga_protendida.py (11) | viga pré-tracionada NBR 6118 aferida em Bastos (tensões de borda); ato 17.2.4.3.2, serviço nível 2, ELU, cortante protendida |
| test_premoldado_nbr9062.py (14) | NBR 9062:2017: cálice Tab.15 (embutimento 1,2–2,0h, min 40cm), γn=1,2, içamento (σ≤0,5fyk, ponto 0,207L), fckj |
| test_perdas_protensao_nbr6118.py (6) | perdas pré-tração NBR 6118 9.6.3: encurtamento elástico SEM fator (n−1)/2n; progressivas RB 9.6.3.4.3 |
| test_fissuracao_nbr6118.py (8) | ELS-W 17.3.3.2: wk = menor das duas fórmulas; η1=2,25; limites Tab.13.4 por CAA |
| test_estabilidade_global_nbr6118.py (6) | α = H·√(Nk/(Ecs·Ic)) vs α1 (0,2+0,1n / 0,6); γz 15.5.3 com majoração 0,95γz |
| test_torcao_nbr6118.py (8) | torção 17.5: seção vazada equiv., biela TRd2, estribo/longitudinal, interação V+T |

### Sessão 22 — Elétrico (5)
| test_eletrico_bt.py (27) | núcleo BT (cargas/condutores/curto/proteção/FP) aferido em Mamede/Creder; ICC 300kVA, DPS/SPDA, malha, subestação |
| test_eletrico_robustez.py (13) | luminotécnica (lúmens), condutores em paralelo 900A, varredura de galpões sem quebrar, queda em alim. longo |
| test_eletrico_bim.py (6) | membros_bim neutro + emissão IFC4 retrocompatível (skip sem ifcopenshell) |
| test_build_eletrico.py (7) | build 3D elétrico: caixas/cilindros puros; build headless sem clash |
| test_executivo_eletrico.py (11) | unifilar SVG (NBR 5410 4.2.5.5; regressão '<' cru), quadro de cargas, planta; pranchas A1 build-gated |

### Sessão 23 — Segurança contra incêndio (7)
| test_seguranca_incendio.py (15) | SCI: iluminação de emergência, sinalização, detecção pontual×linear, sprinklers (risco/vazão/pressão), gates |
| test_fogo_nbr15200.py (9) | concreto em incêndio NBR 15200:2024: Tab.4 vigas, Tab.12 pilar 1 face, Tab.13 pilar-parede; protendido +c1 |
| test_hidrantes.py (16) | NBR 13714: tipo por ocupação, 2 jatos, reserva V=Q·t, nº hidrantes, override, 5º gate do SCI |
| test_iluminacao_externa.py (6) | NBR 5101: classes/níveis, espaçamento de postes, método dos lúmens p/ vias |
| test_incendio_bim.py (7) | BIM/IFC da SCI count-driven; mangotinho→IfcHoseReel; tanque pela maior reserva |
| test_incendio_robustez.py (13) | harness adversarial SCI/iluminação/clima: teto alto→detector linear, monotonicidade, invariantes |
| test_executivo_incendio.py (15) | planta de segurança/rotas (SVG), pontos cortam em n, notas citam hidrantes/AVCB; pranchas build-gated |

### Sessão 24 — Hidráulica (4)
| test_hidraulica_predial.py (25) | NBR 5626/8160/10844: pesos Tab.A1, FWH, UHC/DN, calha Tab.3, pluvial Tab.4; saturação flagada nunca silenciosa |
| test_esgoto_reuso.py (12) | fossa NBR 7229 (V=1000+N(C·T+K·Lf)), sumidouro, reuso por Rippl (≤100%) |
| test_galpao_hidraulica.py (18) | vertical hidráulica: dimensiona por ponto de drenagem, default FLAGADO sem aparelhos, BIM de tubos, turnkey + clash |
| test_executivo_hidr_cli.py (11) | executivo A1 hidráulica+climatização: SVG sem vírgula, cfg + bootstrap (build-gated) |

### Sessão 25 — Climatização + fotovoltaico (3)
| test_climatizacao.py (12) | NBR 16401: carga térmica, capacidade TR/kW/BTU, renovação, duto Tab.1, reprova velocidade excessiva |
| test_galpao_climatizacao.py (9) | vertical HVAC: rodar (capacidade+dutos), membros_bim (tronco/ramais/UTA), turnkey (5ª disciplina), clash duto×estrutura |
| test_fotovoltaico.py (11) | on-grid: área→potência→geração (CRESESB)→compensação; HSP/catálogo A CONFIRMAR; SVG válido |

### Sessão 26 — Terraplenagem, piso, geotecnia (3)
| test_terraplenagem.py (10) | corte/aterro por grade, greide de equilíbrio com empolamento; drenagem (racional + Manning) |
| test_piso_industrial.py (15) | placa sobre Winkler, Westergaard (interior/borda/canto), f't 8.2.5, juntas 24h/teto 6m, k por CBR |
| test_geotecnia_spt.py (14) | σadm=N/50, Terzaghi (fatores do PDF), recalque, recomendador sapata×estaca; integra galpao_concreto |

### Sessão 27 — Legal e gestão (5)
| test_pacote_legal.py (9) | índice de pranchas, memorial consolidado, ART/RRT, checklists PPCI-AVCB e LOD-BIM, manual O&M |
| test_caderno_encargos.py (9) | cláusulas por disciplina (material+execução+controle+normas), ordem canônica; turnkey acrescenta fundação/piso |
| test_orcamento.py (11) | planilha + BDI, curva ABC, preços de referência A CONFIRMAR, override do usuário, volume de concreto |
| test_cronograma.py (9) | rede CPM (caminho crítico), curva S até 100%, WBS default do galpão |
| test_compatibilizacao.py (10) | clash federado → pendências BCF-like (GUID estável), matriz de coordenação simétrica |

### Sessão 28 — Guardas + saturação (2)
| test_guardas_entrada.py (12) | entrada degenerada (≤0) → ValueError LIMPO (nunca ZeroDivisionError) em incêndio/elétrico/concreto |
| test_saturacao_verdito.py (2) | trava a saturação silenciosa (S40): terça saturada por flecha e placa saturada REPROVAM o veredito global |

### Sessão 29 — Turnkey federado (5)
| test_turnkey.py (11) | orquestrador-mestre: consolida verticais, ATENDE global = AND, aço pulado sem out_dir, falha isolada |
| test_turnkey_bim.py (8) | IFC por disciplina + turnkey_federado.ifc no frame comum (concreto transformado + elétrico + incêndio) |
| test_turnkey_clash.py (15) | clash federado AABB: m/mm por disciplina, só pares DIFERENTES, ordenado por volume, triagem esperado×revisar |
| test_caderno_turnkey.py (17) | caderno único: mescla PDFs multidisciplina (capa com veredito/índice), apêndice de clash; merge c/ PDFs sintéticos |
| test_build_federado.py (7) | sólidos das 4 disciplinas no frame comum (caixa/prisma/cilindro); OCCT build-gated |

### Sessão 30 — Fase 6.4–6.8 (5)
| test_fase64_coluna_tapered.py (10) | coluna tapered: seção variável, joelho casa rafter, verificação por segmento < compressão global, mapper h_col_base |
| test_fase65_zona_painel.py (14) | forças das mesas, axial alto reduz Frd, alma fina exige doubler; presente em prismático/alma var, ausente na tesoura |
| test_fase66_flt_misula.py (9) | FLT da mísula: Cb (uniforme/gradiente/teto 3), usa seção de maior altura, cita Anexo J |
| test_fase67_vento_tesoura.py (7) | sucção automática negativa, envelope 2 direções, uplift reverte banzo inferior |
| test_fase68_alma_esbelta.py (11) | Anexo H: kc/kpg reduzem Mrd, FLM inelástico, compacta usa Anexo G inalterado |

### Sessão 31 — Fase 6.a–6.c (3)
| test_fase6a_calha_divisa.py (9) | chuva I default + divisa None, gates não bloqueiam, calcular roda calha/divisa |
| test_fase6b_alma_variavel.py (9) | tipo_portico default/inválido bloqueia, verificação por segmento, build rafter tapered |
| test_fase6c_tesoura.py (8) | treliça por equilíbrio, banzo inferior traciona, build com barras |

### Sessão 32 — Fase 6.9–6.14 (intervalo da S19 nomeado) (6)
| test_fase69_tensao_ponto.py (11) | §5.5.2.3: σ/τ na junção (Qf real), fibra extrema τ=0, von Mises envelope (flag não-normativo) |
| test_fase610_cortante_tapered.py (14) | ΔV de dh/dx, haunch alívio, favorável NÃO credita, adverso SEMPRE conta (braço h0) |
| test_fase611_vento_zona_tesoura.py (11) | zonas iguais→escalar, envelope simétrico, zona ≤ aço, cpe Tab.5, back-compat (**11, não 13**) |
| test_fase612_dg25_crosscheck.py (9) | rt, J compacta/esbelta, M_eltb decresce com Lb, razão independe de Cb |
| test_fase613_enrijecedor_painel.py (16) | §5.4.3.1: kv (5,34/a=h/5), VRd sobe, J/ist, Anexo H cap 260 relaxado, a_max |
| test_fase614_dg25_full.py (19) | Rpc/Rpg, fL mono (½Fy), Mn regiões A/B/C, Cb fórmula verbatim (teto 2,3) |

### Sessão 33 — Secundários (6)
| test_n_terca_calc_3d.py (6) | n_terca do cálculo chega ao build (guarda AST anti-hardcode); espaçamento respeita vão máx da telha |
| test_terca_alma_normal.py (5) | tilt derivado do SLOPE (sinais opostos nas águas), beiral sem tilt |
| test_terca_trib_real.py (4) | trib derivada da geometria, reconfigurar DEPOIS de fixar n_terca (bug de ordem), amostra 2,022 |
| test_telha_tipo_mapper.py (6) | tipo→perfil com vão máx ordenado; peso/perfil do usuário vencem e tiram flag ilustrativo |
| test_longarina_els.py (4) | ELS Tab.C.1: L/120 vento e L/180 peso; ELS governa mesmo com ELU ok |
| test_calhas_robustez.py (5) | h_max absurdo → ValueError imediato (anti-trava), dimensão negativa falha alto |

### Sessão 34 — Ligações/3D (5)
| test_console_flt.py (8) | FLT da chapa do console (Anexo G Tab.G.1, gap A3): reproduz Pfeil, nunca supera o plástico |
| test_gusset_espessura_3d.py (7) | espessura dimensionada chega ao 3D; gussets usam GUSSET_T, bracket do console não herda, reset entre projetos |
| test_ligacoes_pos_rotacao.py (7) | nervura na face em d, enrijecedor do joelho X=bf/Y=d, doubler desloca em X, calha livra a girt |
| test_secao_por_ligacao.py (6) | eixo do corte por ligação: clipe de girt corta em planta (normal z), origem não deslocada (anti-travamento) |
| test_prancha_selecao.py (6) | snap escolhe o pórtico mais próximo (bug de nº ímpar de vãos); sem pórtico devolve centro; aviso não derruba as 12 |

### Sessão 35 — Estrutural geral (6)
| test_pilar_biaxial.py (7) | oblíqua NBR 6118 17.2.5: interação α=1,2, biaxial pede mais aço, degenerado→uniaxial |
| test_escada_patamar.py (10) | multi-lance com patamar (gap C5): desnível >3,2m divide em N lances (Blondel), NR-18 parametrizável |
| test_frame2d_hardening.py (6) | NaN/nó coincidente/mecanismo → erro explícito; UDL em membros idênticos vai ao certo |
| test_aco_classe.py (10) | classe por fy/fu conferida na fonte; 'AR300' NÃO existe; wizard pergunta, validar bloqueia |
| test_coluna_orientacao.py (5) | coluna roll=90, rafter sem roll, calha afastada por DERIVAÇÃO (GUT_Y fixo colidia) |
| test_baldrame_els.py (5) | ELS sob alvenaria Tab.13.3: flecha diferida (fluência) pós-construção; dimensiona sobe altura |

### Sessão 36 — Takeoff/carimbo/coordenação (3)
| test_takeoff_rotulos.py (5) | rótulos derivados do parâmetro: bocal acompanha o condutor (+30), porca casa com o chumbador (mesmo db) |
| test_carimbo_materiais.py (10) | carimbo segue fck/fyk, nome do aço por fy (tabela conferida), sem fck remete ao memorial (não mente) |
| test_coordenacao.py (9) | prancha de coordenação: SVG por disciplina + clash, exige 2 disciplinas; build-gated |

**Total apendado: 82 arquivos** (8+6+5+7+4+3+3+5+2+5+5+3+6+6+5+6+3 = 82), distribuídos em 17 seções novas (## Sessão 20 … ## Sessão 36).

## 4. QA interno (registrado)

1. **Cobertura 136/136**: script `qa_wiki.py` varreu `tests/` (136 `*.py`) × wiki: **MISSING = 0** (todo arquivo de teste aparece ≥1 vez); **PHANTOM = 0** (nenhum nome `test_*.py` citado na wiki sem arquivo real — os 4 nomes citados como `tests/test_X.py`/intervalo foram confirmados individualmente).
2. **Redações verificadas por extração real**: todos os 82 arquivos tiveram docstring de módulo, nomes `def test_*` e docstrings de testes lidos do disco (nada de memória); contagens entre parênteses apenas onde o collect-only do task-8 confirmou.
3. **Aço intacto**: `git diff` mostra 7 deleções = linha 3 + 6 correções do task-8; nenhum conteúdo de S3–S19 removido/reescrito além delas.
4. **UTF-8 explícito**: validação estrita `UTF8Encoding(false, throwOnInvalid:true)` → ok, sem BOM.

## 5. Escopo respeitado

- Único arquivo editado: `framework/galpao_fw/wiki/02-test-tree.md`. Nenhuma outra wiki (00/01/03/04/05/06) tocada; nenhum código/teste modificado; nenhum arquivo novo criado além desta evidência; nenhum commit.
- Notepad `learnings.md` não escrito (instrução).
- Artefatos brutos: `%TEMP%\opencode\extract_test_docs.py`, `extracted_test_docs.txt`, `qa_wiki.py`; diff conferido via `git diff` (sem commit).
