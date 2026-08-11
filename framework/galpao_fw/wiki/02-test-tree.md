# 02 — Árvore de testes

Cada módulo de cálculo tem `_selftest()`. Rodar: `python <modulo>.py --selftest` (módulos novos) ou `python <modulo>.py` (antigos). Sem framework externo — asserts inline + print de referência. Não-regressão = valores do galpão de referência 20×10 inalterados (coluna 0,42 / viga 0,68 / base C2_uplift_W2 −57,5). Suíte pytest: `python tools/run_tests.py` (lane rápida `tests/` exceto `test_fase*`/`test_crashes_wiki07` + lane pesada `test_fase*.py`/`test_crashes_wiki07.py`; xdist `-n auto` quando instalado, senão fallback 2 lanes sequenciais) — **1353 selecionados / 1340 passed / 1 failed / 15 skipped** (2026-08-11; falha única = `test_validacao::test_dossie_unico`, PyMuPDF `fitz` ausente no venv — dependência de instalação, não regressão).

## Por módulo (o que assere)
| Módulo | Asserts-chave |
|---|---|
| `fundacao_sapata` | (1) núcleo σ=N/A·(1±6e/L); (2) borda x=3(L/2−e), σ=2N/Bx; (3) estabilidade FS_tomb/desl c/ peso próprio; (3b) **coesão só na área efetiva** B·x sob uplift; (4) escada escolhe menor que passa; (5) bloco retangular reversível As→M; (6) compr. diagonal α_v/τ_rd2 (19.5.3.1); (7) rigidez 22.6.1; (8) envelope bearing=N máx / tombamento=N mín+M; (9) detalha barras; (10) **rho_min(fck)** Tab.17.3 (piso 0,15% até 30; 0,164% em 35; 0,208% em 50; interpola) |
| `ligacoes` | metal-base solda filete: min(escoamento 0,60·fy·Ag/γa1, ruptura 0,60·fu·Anv/γa2) **6.5.5**; interação parafuso quadrática c/ gate `min(Fvrd,Fcrd)` esmagamento; contravento A36 escoamento 261,8 governa |
| `ponte_rolante` | cargas de roda Rmax/Rmin; momento móvel Barré (2P/L)(L/2−d/4)² → PL/4 em d>0,586L; flecha 2 rodas δ=Pa(3L²−4a²)/24EI; limites flecha Tab.C.1; override Wy_top/Zy_top (fallback Wy/2) |
| `mao_francesa` | `lb_maximo` busca exponencial (hi×1,5) + bisseção 80it; monotonicidade interação em Lb; HEA180 Lb_max 4,64m; n_terca=vãos |
| `contraventamento` | Nt,Rd=min(Ag·fy/1,10; 0,75·Ag·fu/1,35); N=F/cosθ; r=d/4; esbeltez L/r≤300 dispensada p/ pré-tensionada (5.2.8.1); 2% Msd/braço |
| `redimensionamento` | roda escada completa; sob **H/300** adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez); `_peso` não altera seleção (ordem da escada) |
| `check_nbr8800` | flexo-compressão 5.5.1.2 split 0,2; FLT Anexo G; K=1 |
| `base_chumbador` | tração/corte/interação chumbador; bearing 6.6.5; placa AISC DG1; **ancoragem 9.4.2** (fbd, lb, lb,nec) |
| `junta_dilatacao` | δ=α·dT·L; L_max 120/60 × fatores (galpão típico 62,4m); n_juntas; 100m→1 junta |
| `vento_nbr6123` | S2 Tab.1; q=0,613Vk²; Cpe global; **§8 Cpe local**: parede −1,1 (Tab.4), cobertura envoltória −2,0 (Tab.5 4 zonas interp θ), sucção local (cpe_medio−cpi)·q |
| `telha_cobertura` | M_Rd=Wef·fy/γ; flecha L/180 grav, L/120 vento; vão máx inverte ELU/ELS; combos 1,25G+1,50Q e 1,40W−0,90G (W=sucção local §8) |
| `viga_baldrame` | M_d=γf·cM·w·L²; flexão (reusa fs._armadura_flexao); amarração As=Nd/fyd (N=max\|V\| base); As_min; b≥12cm (13.2.2); estribo 0,6d≤300 (18.3.3.2) |
| `sismo_nbr15421` | espectro Sa(T) 4 trechos; Cs=2,5ags0/(R/I); Ta=CT·hn^x; **θ=Px·Δx/(Hx·hsx·Cd)** (9.6), δx=Cd·δxe/I (9.5); **100/30** (8.5) |
| `estaca_profunda` | **Aoki-Velloso** (K/α Tab.12.6, F1/F2 Tab.12.7); **Décourt** (C Tab.12.12, r_l=N/3+1, FS partido 1,3/4,0); **Teixeira** (α Tab.12.16, β); tração=R_lat/FS; grupo Converse-Labarre; atrito neg U·Σf·dz; recalque radier equiv; bloco: biela 22.3.2 (fcd1/fcd3), ancoragem 9.3.2, punção pilar/estaca |
| `ligacoes` (novos) | furos 6.3.9/10/11 (s≥2,7db, lf da geometria); **Tab.14** furo-borda + máx 6.3.12; **block shear 6.5.6**; **T-stub EN 1993-1-8** (3 modos) |
| `gusset_ligacao` | chapa de gusset compondo primitivos: tração escoamento/ruptura na **largura de Whitmore** (espalhamento 30° AISC, FLAG não-NBR análogo T-stub); compressão da faixa efetiva (reusa `check_nbr8800.chi_compressao`); block shear (reusa `ligacoes.block_shear_linha`); solda filete (reusa `ligacoes.solda`, perna mín `solda_filete_minimo`); esforço=tração da diagonal de contravento; adota {t_mm, bw_mm} |
| `console_ponte` | console/mísula do trilho (só ponte): **grupo de solda elástico** f=√(fv²+fh²+fb²), fv=Rv/L, fh=Ht/L, fb=6·M/L², M=Rv·ecc, Sw=L²/6 (mecânica/AISC FLAG); **dimensiona a perna** (first-fit 6/8/10/12mm, adota 12+FLAG se nenhuma passa); cortante da chapa V_Rd=0,6·fy·t·L/γa1 (5.4); adota {t_mm, perna_solda_mm} |
| `nbr8400` (novo, fase 4) | NBR 8400-1:2019 verbatim do PDF: `coef_dinamico(HC,Vh)`=Ψmín+β2·Vh (**Tab.12** HC1-4, cap Vh 1,5) → impacto φ vertical; `n_ciclos(B0-B10)` (**Tab.9**, limite superior conservador) → N da fadiga Anexo K. Classe HC/B = dado de projeto (gate) |

## Branches por fase (3–5, 2026-07-10)
| fase | arquivo de teste | assere |
|---|---|---|
| 3 fundação profunda | `tests/test_fase3_fundacao_profunda.py` (15 fast + 1 build) | gate `fundacao.tipo`/SPT bloqueia; `to_rodar_params`/`to_build_kwargs` estaca (exclusiva sapata); `calcular` grava adotados; build headless ESTACA/BLOCO/BALDRAME, 0 interferências, sem SAPATA; ref sapata não-regride |
| 4 ponte estendida | `tests/test_fase4_ponte_estendida.py` (14) | `nbr8400` Tab.9/12; `forcas_horizontais` rodas motoras (½ com 1 de 2; erro se >lado); `analisa` φ da classe HC/Vh + N da classe B; gate ponte (`ponte=None` ok, incompleta bloqueia); mapper passa n_rodas_motoras |
| 5 corte seccionado | `tests/test_fase5_corte_seccionado.py` (1 build) | `_secao_ligacao` gera `VLIG_SEC_*` com arestas>0 (DrawViewSection headless FreeCAD 1.1) |

## Branches balde 4 (fases 6.15–6.19, 2026-07-13/14)
| fase | arquivo de teste | assere |
|---|---|---|
| 6.15 props_I_mono | `test_fase615_props_mono.py` (11) | reduz exato ao duplo-sim (`props_I`); Wxc=Wxt no simétrico; centroide sobe c/ mesa comp maior; Zx>S_min; Cw→Iy·ho²/4; **rt usa h livre hw, não hc (5.4-11)**; F_L clampa 0,5Fy / rampa 5.4-15; Mn roda em mono |
| 6.16 DG25 envelope | `test_fase616_dg25_envelope.py` (13) | FLB compacta/não-compacta/esbelta; **kc usa hw não hc (5.4-24)** + dupl-sim inalterado; **teto Mp do Rpt usa Sxc não Sxt (5.4-28)**; TFY só se Sxt<Sxc; TFR só c/ furos; envelope=min |
| 6.17 forças localizadas | `test_fase617_forcas_localizadas.py` (11) | valores verbatim 501,8/552/414/163,4 kN (`K_REF=20mm`,`LN_REF=100mm`); dispensa 5.7.2.1; ramos enrugamento; flamb. lateral razão≤2,30 + Cr 32E/16E; geometria 5.7.9.5; enrijecedor barra comprimida Lb=0,75h faixa 12tw; `precisa_enrijecedor` |
| 6.18 viga equilíbrio | `test_fase618_viga_equilibrio.py` (13) | R'=P·l/(l−e); e maior amplifica; nº estacas cobre R'; alívio 50%; **M=P·e não R'·e (estática)**; **cisalhamento V=ΔP (biela VRd2+estribo)**; **peso próprio ~5%**; **pele h>60cm / dispensada h≤60cm**; wiring escolhe estaca |
| 6.19 glyph solda | `test_fase619_glifo_solda.py` (9) | SVG bem-formado; perna+triângulo+linha ref; círculo all-around; bandeira campo; sem perna omite texto; **arrow-side triângulo abaixo**; **other-side acima**; **both espelhado**; **default=arrow** |

## Smoke end-to-end — `smoke_executivo.py`
4 geometrias headless (padrão, vão>comp, baixo-largo, ponte) calc→3D(freecadcmd)→pranchas(freecad.exe)→PDF. Assere por caso: `atende`; **cfg tem joelho+gusset (sempre) e console (só ponte)** = callout rastreia ao cálculo; ≥9 pranchas (13 s/ponte, 14 c/ponte); `cobertura.nao_cobertos`=∅ (todo TIPO de sólido desenhado); `detalhes_edges` todos ≥15 (anti-silhueta) + base_lig presente (cumeeira/gusset_cob/gusset_par/clipe + console p/ ponte); memorial PDF >2KB. Pré-flight sem freecad: carimbo anti-`__PENDENTE__`. **7/7** (casos: padrão, vao_maior, baixo_largo, ponte, estaca, alma_var, tesoura; fase 5 assere `detalhes_secoes`≥1 e nenhuma vazia). Não rodar freecad foreground/`taskkill` durante o smoke em background. Ver [[03-phases#FECHADA — Detalhe de ligação nível fabricação (A+B) — 2026-07-09]].

## Turnkey/validação — `tests/test_validacao.py` (17 testes puros, sem FreeCAD)
Cobre a camada turnkey (sessão 2026-07-16): `validacao.rodar()` (7 benchmarks núcleo, todos
PASS) + `validacao_referencia` (CBCA sistema <1%); `escopo` (envelope+ART); `wizard`
(construir_spec sapata/estaca, faixas, coerência, presets); `rodar_tudo` veredito global +
`res["atende_global"]`; `dossie` (PDF capa+ART, faltando≠quebra); multi-vão (mappers `spans`);
neve (gate+escopo+`_quadro`); helpers de pranchas puros (`_codigo_prancha`, `_pos_notas`,
`_cap_titulo`, `_fmt_terca`, `_quadro_fundacao`, `_pos_corte_ligacao`, `_callout_bloco`) —
regressão dos 6 defeitos de layout. Suíte completa `-m "not build"`: **1340 passed / 1 failed / 15 skipped** (1353 selecionados, 2026-08-11; falha = `test_dossie_unico`, fitz ausente — dependência, não regressão).

## Correções+features+validação — sessão 2026-07-17 (ver [[06-open-threads#T15]])
| arquivo | assere |
|---|---|
| `test_frame2d_sinal.py` | UDL p/ baixo → desloca p/ baixo + reação +10 (não invertida); UDL e nodal equivalente dão MESMA reação; gravidade no pórtico comprime a base (D52) |
| `test_carga_parede.py` | `cargas_parede`: leve→coluna (`w_col`), alvenaria→fundação/baldrame (`N_masonry_ext`, `w_masonry`), NÃO na coluna; integração build-marked |
| `test_aberturas_janela.py` | `_janela_band` (L,H)→(z_base,z_topo) altura POSITIVA; mapper converte janela do wizard; portão fica (L,H) |
| `test_terreno_mapper.py` | mapper passa `params[terreno]`; gate área-only TO/CA/TP; reprova TO excedido; polígono ainda checa recuos |
| `test_crashes_wiki07.py` | reprovação não crasha (E); ponte sem `Hvr` (C); solo inválido bloqueia no validar (D); rótulo de vão desigual no dossiê (K) |
| `test_vento_uplift.py` | vento 1 vão SUCÇÃO no telhado (uplift) + equilíbrio; referência detecta uplift de base; `abertura_dominante` muda Cpi (vedada<portão) |
| `test_multivao_hetero.py` | `_ridge_h(i)` cumeeira por vão, inclinação constante; vãos iguais sem regressão; equilíbrio heterogêneo |
| `test_bloco_fundacao.py` | β≥60° (NBR 6122 7.8.2); `fund_tipo='bloco'` válido; 3D bloco alto; pipeline build-marked |
| `test_shed.py` | `cpe_telhado_1agua` sucção; frame shed 2 colunas alturas diferentes/sem cumeeira; gravidade+vento equilíbrio+uplift; 1 vão valida / multi-vão bloqueia; pipeline 2 colunas distintas |
| `test_validacao_alonso.py` | **VALIDAÇÃO DE SISTEMA**: sapata σ_solo 0,5% (Alonso 18º); B×L exato (cap.9); bloco h/β/σt exato; pilar NBR 8800 N_Rd 0,1% (Bellei A.6); vento q exato (D57) |

## Caça de bugs — sessão 2026-07-18 (ver [[06-open-threads#T16]])
| arquivo | assere |
|---|---|
| `test_validacao_coerencia.py` (51) | `validar` BLOQUEIA todo input degenerado: span<0, ridge≤eave, slope≤0, aguas∉{1,2}, V0<30/>60, abertura>fachada, sigma_solo∉[30,2000], span>120, ponte (Q/vão>0, aprox_min<vão, n_rodas, frações, phi≥1), tesoura (h>0, n_paineis par&≥2), fundação (fck/fyk>0, mu≥0, gamma_f≥1), vento-enums (cat I-V, classe A/B/C), estaca (tipo AokiVelloso, D/L>0, SPT N≥0/dz>0), baldrame b/h>0, terreno frações [0,1], opcionais (neve/fogo/escada/plataforma); **AVISO** z<ridge (não bloqueia) (D58/D61) |
| `test_wizard_robustez.py` (8) | `_ask_one` não trava em entrada vazia/EOF (RuntimeError, cap 100); `construir_spec` ValueError claro p/ obrigatório faltando |
| `test_mao_francesa_geom.py` (12) | **guarda permanente**: `mao_francesa_geom.segmentos` liga mesa inf→terça com componente X≠0 (fora do plano); Y constante; sobe da mesa inf à terça; ângulo 20–70° (D59) |
| `test_tesoura_lby_inf.py` (3) | `Lb_y_inf=None` back-compat; espaçamento real do travamento do banzo inferior PENALIZA a util sob uplift (0,52→3,18) (D60) |

## Revisão continuada — sessão 2026-07-19 (ver [[06-open-threads#T16]])
| arquivo | assere |
|---|---|
| `test_estaca_ponta.py` (5) | `_camada_na_ponta` (camada de L, boundary→cima, além→última); Aoki/Décourt/Teixeira usam N da ponta a L (estaca curta na argila << estaca longa na areia); `N_ponta` override; L=profundidade sem regressão (D63) |
| `test_executivo_cleanup.py` (3) | `_matar_processo_freecad`: proc morto=no-op; kill resolve sem escalar; nunca propaga exceção (D64) |
| `test_ship_build_src.py` (3) | fonte shipada de build_galpao prepende `sys.path` com o dir; todo irmão importado existe no dir; `_result_ = run()` removido (D65) |

## Sessão 16 — mão-francesa + 4 varreduras (2026-07-21, ver [[06-open-threads#T17]], [[04-decisions#D67]])
| arquivo | assere |
|---|---|
| `test_contencao_lateral.py` | 4.11.3.4 nodal (0,02/10) ≠ relativa 4.11.3.3 (0,008/4); γr=1,35; Cd dobra; D16 reprova (esbeltez+resistência); força/rigidez pelo ângulo; gate ligado ao `rodar_galpao`; sem numpy no `res` |
| `test_cantoneira_geom.py` | `perfis.cantoneira` (A=t(2b−t); Ix=Iy; eixos 45°) vs **integração de polígono (Green) a 1e-9**; r_min governa; razão r_min/b estável; geometria inválida levanta |
| `test_mao_francesa_cantoneira.py` | Qs Tab. F.1 Grupo 3 (0,45); degrau 0,2% é da NORMA; **E.1.4.2 MAIS conservador** que r_min; secao dispara E.1.4 por rx1; eng. escolhe (b,t) → 3D+gate mesmo par; L50x50x5 8 faces, área 475=t(2b−t) |
| `test_terca_assento_3d.py` | filtro de vigas casa `PORTICO_\d+_V\d+` (não `"_VIGA_"` morto); beiral não afirma EAVE_H; chapa segue inclinação; ordem chapa→terça; T_CLIPE única |
| `test_ship_cache_modulo.py` | bootstrap DESCARTA módulos irmãos do cache (antes do `build`); cobre irmãos reais; não derruba `os`/`FreeCAD`; DIAM_BRACO compartilhado |
| `test_pecas_conexao_encaixe.py` | gap de graute realizado (pbot−GROUT_GAP); porca cabe no gap; esticadores `FRAC_ESTIC`≠0,5; gusset nasce abaixo da escora |
| `test_takeoff_x_modelo.py` | mísula = chapas soldadas (alma+mesa inf.), não bloco; rótulo deriva do rafter; sem vírgula (é CSV); arruela T_ARRUELA; teto de espessuras cravadas |
| `test_relatorio_x_calculo.py` | quadro inclui a mão-francesa; API `atende`=global (não pórtico); expõe `atende_portico`/`falhas`; massa vem do modelo |
| `test_notas_prancha_x_modelo.py` | notas MEDIDAS (`_notas_do_modelo`); nenhuma medida cravada em mm; ⌀ por Volume/eixo; fallback sem número |
| `test_quadro_materiais_prancha.py` | takeoff vazio → aviso + "NÃO DISPONÍVEL" na folha (era meia folha em branco silenciosa) |

## Sessão 17 — Gaps Nível A/C + Fabricação 3D/2D + Diafragma (2026-07-22, PRs #45 e #46)
| arquivo | assere |
|---|---|
| `test_empocamento.py` (5) | declividade $\ge 3\%$ dispensa ($OK=True$); $<3\%$ reprova exigindo análise adicional ($OK=False$, flag "9.3"); limite exato inclusivo; `incl_pct_de_theta` converte $\theta$ rad |
| `test_romaneio.py` (7) | agrupa peças primárias $C1, V1..Vn$; quantidade $(n_{vãos}+1) \times n_{pórticos}$ colunas; massa linear $A \cdot 7850$; multi-vão com vãos diferentes gera marcas $V1, V2$ distintas |
| `test_tipo_ligacao.py` (6) | `wizard` pergunta `tipo_ligacao` (default soldada); normaliza para minúsculas; `projeto_spec.validar` rejeita tipo inválido (ex. `solda`); propaga para `rodar_params` |
| `test_torcao.py` (7) | $J$ de perfil I duplo-simétrico; torção nula $\rightarrow$ desprezível; $\tau_t > 0,20\tau_{Rd} \rightarrow$ exige análise de flexo-torção ($OK=False$); tubo retangular $T_{rd}$ 3 regimes + interação quadrtica |
| `test_marcas_peca.py` (6) | prefixos determinsticos por categoria ($C, V, T, TP, PB, CH...$); 1 marca por perfil distinto; mesmo grupo mesma marca; determinstico na ordenação |
| `test_tolerancias.py` (5) | folga do furo-padrão $d_b<24\rightarrow +1,5\text{ mm}$, $d_b\ge 24\rightarrow +2,0\text{ mm}$ (NBR 8800 Tab. 12); linhas contêm grupos FABRICAÇÃO/MONTAGEM/FURAÇÃO com fontes |
| `test_croquis_fabricacao.py` (5) | `_pr_croquis` registrada no pipeline de executivo (PE14); localiza peças no 3D pela propriedade `Marca`; projeta vistas em 3 colunas A1; rotula $C1, V1, MI1$ |
| `test_diafragma.py` (8) | classifica diafragma (deflexão no plano $>2\times\text{drift}_{médio}\rightarrow$ FLEXÍVEL); distribuição flexível por largura tributária; distribuição rígida por rigidez + torção por excentricidade |

## Sessão 18 — Plano de Montagem e Escoramento (2026-07-22, PR #47)
| arquivo | assere |
|---|---|
| `test_montagem.py` (12) | tolerância de prumo $\max(H/500, 5\text{ mm})$ com teto 25 mm; peça mais pesada considera rafter pré-montado no solo (2 meias-águas); guindaste momento de carga $M_{carga} = \text{peso}\cdot\gamma_{imp}\cdot\text{raio}$ ($t\cdot m$) cita 4.2.6; estaiamento tração $T=F/(n\cdot\cos\alpha)$, compressão na coluna e arrancamento $T\cdot\sin\alpha$; $\gamma$ de construção 1,30 (4.9.6.5); sequência 10 passos estaiia antes de desacoplar guindaste; fallback gracioso "A CONFIRMAR"; pórtico multi-vão considera colunas internas |

## Sessão 19 — Interoperabilidade BIM & IFC4 (2026-07-23, PRs #55–#61)
| arquivo | assere |
|---|---|
| `test_modelo_neutro.py` | constrói modelo neutro de dados (`modelo_neutro.py`); valida hierarquia de edifícios, pórticos, membros primários e secundários sem dependência de FreeCAD |
| `test_ifc_emit.py` | emissor IFC4 puro-Python (`ifc_emit.py` via `ifcopenshell`); emite arquivo IFC4 físico com schemas `IfcColumn`, `IfcBeam`, `IfcMember`, `IfcPlate`, `IfcFooting` |
| `test_ifc_map.py` | mapeamento semântico `ifc_map.py` (marcas $C1, V1... \rightarrow$ entidades IFC4 correspondentes); valida propriedades e materiais |
| `test_ifc_secundarios_xcheck.py` | cross-check entre membros secundários (terças, girts, tirantes, contraventamento) e entidades `IfcMember` no modelo IFC puro |
| `test_modelo_analitico.py` | gerador de BIM estrutural (`modelo_analitico.py`); valida emissão de `IfcStructuralAnalysisModel`, `IfcStructuralPointConnection`, `IfcStructuralCurveMember`, condições de contorno e casos de carga |
| `test_pipeline_bim.py` | pipeline fim-a-fim de emissão BIM (integração entre cálculo, `build_galpao.export()` e arquivo `galpao.ifc`) |
| `test_montar_headless.py` | auto-fallback headless (`montar_modelo` $\rightarrow$ `freecadcmd`) se o bridge da porta 9875 não estiver ativo |
| `test_fase69` a `test_fase614` | suítes de validação de tensão pontual (§5.5.2.3), cortante tapered, vento por zona, cross-check DG25, enrijecedor de painel (§5.4.3.1) e DG25 envelope full |
| `test_calha_calc_3d.py`, `test_viga_rolamento_3d.py` | integridade geométrica 3D e validações pontuais de folgas em calhas e vigas de rolamento |

## Sessão 20 — Concreto armado/pré-moldado (onda pós-S19)
| arquivo | assere |
|---|---|
| `test_galpao_concreto.py` (21) | orquestrador `galpao_concreto` (pilares engastados + viga de cobertura biapoiada + sapata, stateless): vão grande roteia p/ protensão, vão pequeno fica CA, gate cálice/icamento, TRRF (isento c/ nota, 1 face atende, multiface exige Anexo E), interferências (sapatas sobrepostas pegam, toque de face não) |
| `test_galpao_concreto_bim.py` (7) | BIM IFC4 do galpão de concreto: `membros_bim` → `IfcColumn`/`IfcBeam`/`IfcFooting` com seção retangular, material Concreto Cxx e Pset de armadura — sem FreeCAD (via `ifc_emit`) |
| `test_pilar_concreto.py` (12) | pilar em flexão composta NBR 6118 aferido contra 3 exemplos resolvidos de Bastos (Md,tot e As: Ex.1 le=280→10,84 cm²; Ex.2 le=480→31,03 cm²; Ex.5 extremidade αb/γn); γn Tab.13.1, λ1 faixa 35–90, curvatura limitada, seção insuficiente reprova |
| `test_viga_concreto.py` (8) | viga retangular NBR 6118 aferida em Araújo (15×40→As=2,98) e Carvalho & Figueiredo (dom.2, As=1,46); cortante reprova biela fina, ELS L/250 (alvenaria L/500) governa e sobe altura, As_min |
| `test_desenho_concreto.py` (8) | desenho de formas + armação (SVG puro): bem-formado E cabe no canvas (guarda de bounding-box — sapata em metros estourava e cobria a viga); planta de formas completa |
| `test_build_concreto.py` (8) | build 3D do galpão de concreto em 2 camadas: `caixas()`/`_takeoff()` puros (orientação/posição/volume, pilar em X apoia no topo, sapata no nível zero) + camada `build` headless gera FCStd/IFC sem interferência |
| `test_executivo_concreto.py` (7) | executivo de concreto: quadro de aço (dobramento) cobre pilar/viga/sapata, quantidades escalam com nº de pórticos, pilar longitudinal inclui ancoragem, peso bate com fórmula, memorial compõe todas as disciplinas |
| `test_techdraw_concreto.py` (7) | pranchas A1 TechDraw do concreto: cfg/quadros por tipo (sapata/estaca/viga protendida), carimbo não vaza aço do template de steel, bootstrap injeta sys.path; camada `build` gera PDFs (skip sem freecad.exe) |

## Sessão 21 — Protensão e pré-moldado (NBR 9062/6118)
| arquivo | assere |
|---|---|
| `test_viga_protendida.py` (11) | viga pré-tracionada NBR 6118 aferida no exemplo resolvido de Bastos (tensões de borda, núcleo e ep_máx); limites no ato 17.2.4.3.2, serviço nível 2 (ELS-F/ELS-D, Tab.13.4) e ELU; cortante protendida (biela + majoração, estribo mín. 1,70) |
| `test_premoldado_nbr9062.py` (14) | pré-moldado NBR 9062:2017: cálice Tab.15 (embutimento lisa/rugosa 1,5→2,0h, chaves 1,2→1,6h, min 40 cm), γn=1,2 (7.7.1.2), situações transientes (içamento limita σ≤0,5fyk, ponto ótimo 0,207L), fckj NBR 6118 12.3.3 |
| `test_perdas_protensao_nbr6118.py` (6) | perdas de protensão pré-tração NBR 6118 9.6.3: encurtamento elástico SEM fator (n−1)/2n (é da pós-tração 9.6.3.3.2.1); progressivas RB 9.6.3.4.3 literal; mais fluência/fck novo → mais perda |
| `test_fissuracao_nbr6118.py` (8) | ELS-W NBR 6118 17.3.3.2: wk = MENOR das duas fórmulas (3σs/fctm vs 4/ρri+45), η1=2,25 nervurada, limites Tab.13.4 por CAA (0,2/0,3/0,4 mm), mais armadura/barra fina reduz |
| `test_estabilidade_global_nbr6118.py` (6) | estabilidade global NBR 6118 15.5: α=H·√(Nk/(Ecs·Ic)) vs α1=0,2+0,1n (0,6 p/ n≥4; balanço 0,3); γz=1/(1−ΔMtot,d/M1,tot,d) com majoração 0,95γz |
| `test_torcao_nbr6118.py` (8) | torção de viga NBR 6118 17.5: seção vazada equivalente (he=A/u≥2c1, 17.5.1.4.1), biela TRd2=0,50αv2·fcd·Ae·he·sen(2θ) (17.5.1.5), estribo/longitudinal (17.5.1.6a/b), interação V+T; `viga_concreto` roda torção |

## Sessão 22 — Elétrico (NBR 5410)
| arquivo | assere |
|---|---|
| `test_eletrico_bt.py` (27) | núcleo BT (cargas, condutores, curto, proteção, fator de potência, orquestrador) aferido em Mamede/Creder: demanda motor 75cv, condutor chuveiro 6 mm², ICC trafo 300kVA, disjuntor/DPS/SPDA (níveis e descidas), malha de terra, subestação 225kVA, média tensão >300 |
| `test_eletrico_robustez.py` (13) | robustez elétrica: luminotécnica (método dos lúmens, iluminância/índice, alimenta cargas), condutores em paralelo (900 A) e seções até 300, varredura de galpões variados sem quebrar, queda de tensão em alimentador longo governa |
| `test_eletrico_bim.py` (6) | BIM/IFC do elétrico: `membros_bim` neutro (contagem, coords em mm, seção em m, perímetro fecha) + emissão IFC4 retrocompatível (skip sem ifcopenshell); extensão não quebra BIM de aço |
| `test_build_eletrico.py` (7) | build 3D elétrico: camada pura (`caixas`/`_takeoff`/classificador de conexão — haste cilíndrica, eletrocalha ao longo do comprimento, board centrado) + `build` headless sem clash |
| `test_executivo_eletrico.py` (11) | executivo elétrico: unifilar SVG (NBR 5410 4.2.5.5 circuitos separados; regressão '<' cru que malformava XML), quadro de cargas, planta de ilum/tomadas; pranchas A1 `build`-gated |

## Sessão 23 — Segurança contra incêndio (NBR 10898/16820/17240/13714/15200)
| arquivo | assere |
|---|---|
| `test_seguranca_incendio.py` (15) | vertical SCI: iluminação de emergência (níveis/espaçamento, fluxo insuficiente reprova), sinalização (distância/nº placas), detecção pontual×linear e cobertura por viga (exemplo NBR 12×23), sprinklers (classifica risco, projeto do galpão, vazão/pressão), gates (galpão alto → detector linear) |
| `test_fogo_nbr15200.py` (9) | concreto em incêndio NBR 15200:2024 tabular: Tabela 4 vigas biapoiadas (bmin/c1 alternativos, bw,min por TRRF), Tabela 12 pilar 1 face, Tabela 13 pilar-parede por μfi; protendido acrescenta c1; TRRF inválido levanta |
| `test_hidrantes.py` (16) | hidrantes NBR 13714: tipo por ocupação (Tab.1), 2 jatos simultâneos, reserva V=Q·t, nº mínimo 2 por hidrante, cobertura por malha 5.3.2, override de tipo (inválido = ValueError), 5º gate do vertical SCI |
| `test_iluminacao_externa.py` (6) | iluminação externa/vias NBR 5101/Mamede: classes e níveis, espaçamento de postes, método dos lúmens para vias, projeto de via interna |
| `test_incendio_bim.py` (7) | BIM/IFC da SCI count-driven (mesmas contagens do resumo/pranchas), mangotinho tipo 1 → IfcHoseReel, tanque elevado pela maior reserva, IFC4 gated no ifcopenshell |
| `test_incendio_robustez.py` (13) | harness adversarial SCI/iluminação/climatização: teto alto → detector linear, detectores/reserva monotônicos, sprinklers de estoque alto recusam sem inventar, postes respeitam faixa 3H–5H, invariantes (gate bool, sem crash, contagens não-negativas) |
| `test_executivo_incendio.py` (15) | executivo SCI: planta de segurança/rotas de fuga (SVG puro, desenha contagens da norma, pontos cortam em n, grade proporcional), cfg da prancha citando hidrantes/AVCB, carimbo não vaza campos estruturais; pranchas A1 `build`-gated |

## Sessão 24 — Hidráulica predial (NBR 5626/8160/10844)
| arquivo | assere |
|---|---|
| `test_hidraulica_predial.py` (25) | dimensionamento hidráulico: água fria NBR 5626 (pesos Tab.A1, Fair-Whipple-Hsiao, comprimento equivalente Tab.A3, verifica pressão), esgoto NBR 8160 (UHC/DN, ventilação Tab.8/D1, declividade mínima obrigatória), pluvial NBR 10844 (Tab.3/4, i default flagado); saturação flagada nunca silenciosa |
| `test_esgoto_reuso.py` (12) | saneamento do lote sem rede: fossa NBR 7229 (V=1000+N(C·T+K·Lf), mín. 1000 L, coeficiente ausente → A CONFIRMAR), sumidouro, reuso de chuva por Rippl (12 meses, atendimento limitado a 100%) |
| `test_galpao_hidraulica.py` (18) | vertical hidráulica do galpão: `rodar` dimensiona por ponto de drenagem, sem aparelhos cai em default comercial FLAGADO (nunca norma inventada), override de diâmetro vence, BIM de tubos, turnkey (6ª disciplina) + clash tubo×estrutura/duto/cabo |
| `test_executivo_hidr_cli.py` (11) | executivo A1 de hidráulica + climatização: SVG sem vírgula nas coordenadas e XML bem-formado, cfg da prancha + bootstrap; geração real da prancha `build`-gated |

## Sessão 25 — Climatização (NBR 16401) + fotovoltaico
| arquivo | assere |
|---|---|
| `test_climatizacao.py` (12) | climatização NBR 16401: carga térmica (condução + pessoas), capacidade TR/kW/BTU, vazão de renovação, duto (seção/aspecto, velocidade Tab.1), galpão reprova velocidade excessiva |
| `test_galpao_climatizacao.py` (9) | vertical HVAC do galpão: `rodar` (capacidade + rota de dutos), membros_bim (tronco/ramais/UTA), turnkey (5ª disciplina), clash federado pega duto×estrutura (conflito real a revisar) |
| `test_fotovoltaico.py` (11) | fotovoltaico on-grid: área→potência→geração (fórmula CRESESB)→compensação do consumo; limitado por área E por consumo; HSP/catálogo A CONFIRMAR (nunca inventados); gráfico SVG XML válido |

## Sessão 26 — Terraplenagem, piso industrial e geotecnia SPT
| arquivo | assere |
|---|---|
| `test_terraplenagem.py` (10) | terraplenagem: corte/aterro por grade, greide de equilíbrio (empolamento >1 baixa a plataforma), movimento de terra com saldo; drenagem superficial (método racional + Manning, canaleta insuficiente reprova) |
| `test_piso_industrial.py` (15) | piso industrial: placa sobre solo de Winkler (D, raio relativo), espessura por Westergaard (interior/borda/canto; raio de contato corrigido a<1,724h), tração na flexão NBR 6118 8.2.5, juntas (24h, teto 6m), k por CBR, UDL verifica contra o solo |
| `test_geotecnia_spt.py` (14) | ponte SPT→σadm: σadm=N/50 (N≥20), faixas (8≤N<20 presumido c/ alerta, N<8→profunda), Terzaghi (fatores do PDF Tab.4.1), recalque elástico, recomendador sapata×estaca, N médio no bulbo pondera camadas, integra `galpao_concreto` (explicito vence recomendação) |

## Sessão 27 — Legal e gestão (pacote legal, encargos, orçamento, cronograma)
| arquivo | assere |
|---|---|
| `test_pacote_legal.py` (9) | pacote legal/gestão: índice de pranchas (códigos únicos), memorial consolidado, ART/RRT por conselho (dados do RT A CONFIRMAR), checklists PPCI-AVCB e LOD-BIM, manual O&M, gera pacote markdown |
| `test_caderno_encargos.py` (9) | caderno de encargos: cláusulas completas (material+execução+controle+normas) por disciplina, ordem canônica, subconjunto, disciplina inválida, normas referenciadas ordenadas e únicas; caderno do turnkey acrescenta fundação/piso |
| `test_orcamento.py` (11) | orçamento 5D: planilha + BDI, rejeita negativo, curva ABC (ordena/acumula, item dominante classe A), preços de REFERÊNCIA A CONFIRMAR, override do usuário vence, volume de concreto (rect+caixas), extrai piso do turnkey |
| `test_cronograma.py` (9) | cronograma físico-financeiro 4D: rede CPM (caminho crítico série/paralelo com folga, ciclo/precedência inválida, ids duplicados), curva S monótona até 100%, WBS default do galpão, SVG XML válido |
| `test_compatibilizacao.py` (10) | relatório formal de compatibilização: clash federado → pendências BCF-like (GUID estável entre execuções, severidade por volume, status/responsável), matriz de coordenação simétrica, resumo sem conflitos |

## Sessão 28 — Guardas de entrada e saturação silenciosa
| arquivo | assere |
|---|---|
| `test_guardas_entrada.py` (12) | revisão total de gaps: entrada DEGENERADA (geometria/tensão/área/fator = 0 ou negativa) vira ValueError LIMPO no padrão da casa, nunca ZeroDivisionError — em incêndio, elétrico (tensão, curto, aterramento, SPDA, condutores, motores) e concreto |
| `test_saturacao_verdito.py` (2) | trava a caça de SATURAÇÃO SILENCIOSA (S40): terça saturada por flecha e placa de sinalização saturada → veredito global REPROVA (tabela não entrega o último item como se atendesse) |

## Sessão 29 — Turnkey (vertical-mestre) e modelo federado
| arquivo | assere |
|---|---|
| `test_turnkey.py` (11) | orquestrador-mestre `galpao_turnkey`: consolida os verticais num único `rodar(spec)`, geometria comum propaga (dialeto LWH), ATENDE global = AND, aço pulado sem out_dir, falha de disciplina fica ISOLADA (não derruba as demais) |
| `test_turnkey_bim.py` (8) | BIM/IFC federado: `emitir_bim` escreve um IFC por disciplina + `turnkey_federado.ifc` no frame comum (concreto transformado + elétrico + incêndio), footprint coerente, aço federa via spec enriquecido |
| `test_turnkey_clash.py` (15) | clash federado ENTRE disciplinas (AABB puro): dims estrutural em m / instalações em mm, barra orientada não engorda o eixo, painel ignorado, toque de face = 0, só pares DIFERENTES, ordenado por volume, relatório cita triagem esperado×revisar |
| `test_caderno_turnkey.py` (17) | caderno executivo ÚNICO: mescla PDFs de pranchas multidisciplina (capa com veredito global/índice/divisórias; capa mostra reprovação), apêndice de clash, PNG inválido degrada sem crash; merge testado com PDFs sintéticos (PyMuPDF) |
| `test_build_federado.py` (7) | build 3D federado: `solidos()` decompoõe membros neutros das 4 disciplinas no frame comum (caixa/prisma orientado/cilindro), barra de comprimento zero ignorada, 3D vivo consistente com AABB; OCCT `build`-gated |

## Sessão 30 — Fase 6.4–6.8 (onda alma variável/tesoura)
| arquivo | assere |
|---|---|
| `test_fase64_coluna_tapered.py` (10) | coluna tapered: seção variável, joelho casa o rafter, análise retorna segmentos da coluna, verificação POR SEGMENTO < compressão global, h_col_base maior que joelho avisa, mapper passa h_col_base (lane pesada) |
| `test_fase65_zona_painel.py` (14) | zona de painel: forças das mesas, painel sem axial = VRd, axial alto reduz Frd, alma fina exige doubler (trava esbeltez), Fsd abate Vcol, enrugamento presente; roda em pórtico prismático E alma var, ausente na tesoura |
| `test_fase66_flt_misula.py` (9) | FLT da mísula: Cb momento uniforme/gradiente/teto 3, usa a seção de maior altura, Cb reduz util, demanda σ máx; relatório cita Anexo J; `rodar_coluna_tapered` recebe Cb |
| `test_fase67_vento_tesoura.py` (7) | vento por zona na tesoura: sucção automática negativa, override honrado, gate cita NBR 6123, combo uplift×gravidade, uplift REVERTE o banzo inferior, prismático sem vento automático |
| `test_fase68_alma_esbelta.py` (11) | alma esbelta Anexo H: web esbelta detectada, kc dentro de limites, kpg≤1 reduz Mrd, FLM inelástico presente, guarda validade aw/afc, compacta usa Anexo G INALTERADO, mísula de alma fina calcula |

## Sessão 31 — Fase 6.a–6.c (calha/divisa, alma variável, tesoura)
| arquivo | assere |
|---|---|
| `test_fase6a_calha_divisa.py` (9) | novidades do spec: chuva I com default + divisa None, gates não bloqueiam, mapper passa divisa/chuva (sem divisa não passa), `calcular` roda calha e divisa quando setado; métodos têm estaca+calha+divisa |
| `test_fase6b_alma_variavel.py` (9) | pórtico alma variável: tipo_portico default / inválido BLOQUEIA, mapper passa tapered, verificação por segmento, prismático inalterado; build rafter tapered |
| `test_fase6c_tesoura.py` (8) | tesoura: resolve a treliça por equilíbrio (nº de esforços = nº de barras), banzo inferior TRACIONA, verificação de util, tipo inválido bloqueia, mapper passa treliça; build com barras |

## Sessão 32 — Fase 6.9–6.14 (intervalo citado em S19, agora nomeado)
| arquivo | assere |
|---|---|
| `test_fase69_tensao_ponto.py` (11) | tensão pontual §5.5.2.3: σ na junção (fórmula), τ usa Qf real, fibra extrema τ=0, §5.5.2.3 retorna 4 checks, von Mises envelope (flag não-normativo), check D reduz com χv |
| `test_fase610_cortante_tapered.py` (14) | cortante tapered: ΔV de dh/dx, haunch dá alívio, M=0 sem efeito, favorável NÃO credita (conservador), adverso SEMPRE conta (braço exato h0), prismático sem efeito; relatório reporta reserva, crédito não piora util |
| `test_fase611_vento_zona_tesoura.py` (11) | vento por zona: zonas iguais reproduzem escalar, zonas diferentes dão cargas diferentes, envelope 2 direções simétrico, zona ≤ aço, pressão dead desfavorável, cpe longitudinal Tab.5, back-compat escalar |
| `test_fase612_dg25_crosscheck.py` (9) | cross-check DG25: rt (fórmula), J compacta positiva / esbelta zero, M_eltb positivo e decresce com Lb, razão independe de Cb, prismático converge; taper forte sinaliza sem exceção |
| `test_fase613_enrijecedor_painel.py` (16) | enrijecedor de painel §5.4.3.1: kv sem enrijecedor / a=h / cai p/ 5 quando a/h>3, VRd sobe com enrijecedor, J e ist requisitos, bt limite verbatim, Anexo H cap 260 relaxado c/ enrijecedor, a_max para Vsd, ist singelo conservador vs par |
| `test_fase614_dg25_full.py` (19) | DG25 envelope full: Rpc compacta=1/não-compacta interpola/esbelta, Rpg, fL duplo-simétrico vs monossimétrico (piso ½Fy), Mn positivo limitado por Cfy e regiões A/B/C, Cb fórmula verbatim (teto 2,3), capacidade prismática finita |

## Sessão 33 — Secundários: terças, telha, longarina, calhas
| arquivo | assere |
|---|---|
| `test_n_terca_calc_3d.py` (6) | n_terca do CÁLCULO chega ao build: `configurar()` expõe o parâmetro (sem hardcode — guarda por AST na fonte), back-compat sem a chave, espaçamento do calc respeita o vão máx da telha (3 hardcoded NÃO cabia) |
| `test_terca_alma_normal.py` (5) | terça com alma normal ao plano: tilt DERIVADO do SLOPE (não número fixo), águas com sinais OPOSTOS, beiral sem tilt (apoia no topo do pilar, superfície horizontal) |
| `test_terca_trib_real.py` (4) | largura tributária real da terça: derivada da geometria, reconfigurar DEPOIS de fixar n_terca (bug de ORDEM), 1,675 do params_ref documentado (vao 10/ridge-eave 0,5/n=3), amostra vão 20→trib 2,022 |
| `test_telha_tipo_mapper.py` (6) | mapper telha.tipo→perfil: vão máx ordenado (ondulada<trapezoidal<sanduíche), peso do usuário sobrepõe, perfil de fabricante com Wef vence e tira o flag ILUSTRATIVO |
| `test_longarina_els.py` (4) | ELS da longarina NBR 8800 Tab.C.1: L/120 perpendicular (vento) e L/180 paralelo (peso, entre tirantes) — antes só ELU biaxial; ELS governa e reprova mesmo com ELU ok |
| `test_calhas_robustez.py` (5) | guardas da calha: h_max absurdo → ValueError IMEDIATO (antes range gigante travava o processo), h_max em metros continua funcionando (faixa útil intacta), dimensão negativa falha alto (contra-segurança) |

## Sessão 34 — Ligações, console e prancha 3D
| arquivo | assere |
|---|---|
| `test_console_flt.py` (8) | FLT da chapa do console (NBR 8800 Anexo G, Tab. G.1 — gap A3): reproduz exemplo de Pfeil, seção sólida sem flambagem local (G.1.2), balanço curto plastifica, longo esbelto → regime elástico, FLT nunca supera o plástico |
| `test_gusset_espessura_3d.py` (7) | espessura DIMENSIONADA do gusset chega ao 3D: gussets de contravento (cobertura e parede) usam o global GUSSET_T, bracket do console NÃO herda (peça diferente), takeoff deriva o rótulo, reset entre projetos na mesma sessão |
| `test_ligacoes_pos_rotacao.py` (7) | posições pós-rotação das ligações: nervura parte da face em d, girt encosta na face em d, enrijecedor do joelho X=bf e Y=d, doubler desloca em X (uma chapa de cada lado da alma), calha livra a GIRT (não só a coluna) |
| `test_secao_por_ligacao.py` (6) | eixo do corte por ligação: tabela de LIGACOES carrega a normal do corte, clipe de girt corta EM PLANTA (normal z — 25 arestas vs 14 do histórico), demais ligações mantêm histórico, origem do corte não deslocada (regressão: deslocar travava o TechDraw 1200s) |
| `test_prancha_selecao.py` (6) | seleção de pórtico na prancha (PE04/PE07): faixa do pórtico sempre pega um pórtico — snap escolhe o MAIS PRÓXIMO (bug do nº ÍMPAR de vãos), sem pórtico devolve o centro, aviso registra e não derruba as outras 12 pranchas |

## Sessão 35 — Estrutural geral (pilar biaxial, escada, frame2d, aço)
| arquivo | assere |
|---|---|
| `test_pilar_biaxial.py` (7) | flexão composta OBLÍQUA NBR 6118 17.2.5/15.8.3.3.5: interação (Mx/Mrd,xx)^α+(My/Mrd,yy)^α≤1 com α=1,2 retangular, Mrd uniaxiais do solver aferido em Bastos (As em 4 cantos), biaxial pede mais aço, degenerado reduz ao uniaxial |
| `test_escada_patamar.py` (10) | escada multi-lance com patamar (gap C5): desnível >3,2 m divide em N lances (cada ≤ limite) com N−1 patamares — antes ABORTAVA e não gerava escada em pé-direito >6 m; Blondel por lance, NR-18 parametrizável, patamar default = largura |
| `test_frame2d_hardening.py` (6) | hardening do frame2d: carga NaN, nó coincidente e mecanismo (apoio insuficiente) → erro EXPLÍCITO (não NaN silencioso); UDL em dois membros idênticos vai para o membro certo (eidx por identidade, não dict-equal) |
| `test_aco_classe.py` (10) | classe de aço por fy/fu: propriedades conferidas na fonte (Pfeil), 'AR300' NÃO existe (guarda contra erro cometido), classe desconhecida falha ALTO (não adivinha), wizard pergunta e `validar` bloqueia typo (não cai no default MR250) |
| `test_coluna_orientacao.py` (5) | orientação de coluna no 3D: coluna prismática E tapered roll=90 (i_member _C{j}), rafter SEM roll (já está no plano), calha afastada por DERIVAÇÃO (GUT_Y fixo colidia com a coluna que virou d/2 em Y) |
| `test_baldrame_els.py` (5) | ELS da viga de baldrame sob alvenaria NBR 6118 Tab.13.3: flecha DIFERIDA (fluência) pós-construção da parede — esbelto reprova no ELS mesmo com ELU ok; dimensiona sobe a altura até atender; sem alvenaria não checa |

## Sessão 36 — Takeoff, carimbo e coordenação
| arquivo | assere |
|---|---|
| `test_takeoff_rotulos.py` (5) | rótulos do takeoff derivados do parâmetro (não literais): bocal acompanha o condutor (cond+30 na MESMA conta da geometria), porca casa com o chumbador (mesmo db — barra 32 com porca M20 era o caso visível) |
| `test_carimbo_materiais.py` (10) | carimbo de materiais segue o projeto: fck/fyk, nome do aço por fy (tabela conferida no PDF — 1ª versão tinha 'AR300' que não existe), cobrimento e proteção de corrosão do spec vão para a nota, sem fck remete ao memorial em vez de mentir 25 MPa |
| `test_coordenacao.py` (9) | prancha de COORDENAÇÃO do modelo federado: SVG planta+elevação coloridas por disciplina + clash, cfg computa clash se None, bootstrap injeta entry, exige 2 disciplinas (senão erro limpo); geração real `build`-gated |

## Convenção de não-regressão
Selftest imprime valores de referência; alteração de código deve manter os valores do galpão de referência salvo quando a mudança normativa os corrige de propósito (ex.: redim H/300 muda perfil adotado — mudança intencional, documentada [[04-decisions#D5]]).
