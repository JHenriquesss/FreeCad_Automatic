# 02 — Árvore de testes

Cada módulo de cálculo tem `_selftest()`. Rodar: `python <modulo>.py --selftest` (módulos novos) ou `python <modulo>.py` (antigos). Sem framework externo — asserts inline + print de referência. Não-regressão = valores do galpão de referência 20×10 inalterados (coluna 0,42 / viga 0,68 / base C2_uplift_W2 −57,5).

## Por módulo (o que assere)
| Módulo | Asserts-chave |
|---|---|
| `fundacao_sapata` | (1) núcleo σ=N/A·(1±6e/L); (2) borda x=3(L/2−e), σ=2N/Bx; (3) estabilidade FS_tomb/desl c/ peso próprio; (3b) **coesão só na área efetiva** B·x sob uplift; (4) escada escolhe menor que passa; (5) bloco retangular reversível As→M; (6) compr. diagonal α_v/τ_rd2 (19.5.3.1); (7) rigidez 22.6.1; (8) envelope bearing=N máx / tombamento=N mín+M; (9) detalha barras; (10) **rho_min(fck)** Tab.17.3 (piso 0,15% até 30; 0,164% em 35; 0,208% em 50; interpola) |
| `ligacoes` | metal-base solda filete: min(escoamento 0,60·fy·Ag/γa1, ruptura 0,60·fu·Anv/γa2) **6.5.5**; interação parafuso quadrática c/ gate `min(Fvrd,Fcrd)` esmagamento; contravento A36 escoamento 261,8 governa |
| `ponte_rolante` | cargas de roda Rmax/Rmin; momento móvel Barré (2P/L)(L/2−d/4)² → PL/4 em d>0,586L; flecha 2 rodas δ=Pa(3L²−4a²)/24EI; limites flecha Tab.C.1; override Wy_top/Zy_top (fallback Wy/2) |
| `mao_francesa` | `lb_maximo` busca exponencial (hi×1,5) + bisseção 80it; monotonicidade interação em Lb; HEA180 Lb_max 4,64m; n_terca=vãos |
| `contraventamento` | Nt,Rd=min(Ag·fy/1,10; 0,75·Ag·fu/1,35); N=F/cosθ; r=d/4; esbeltez L/r≤300 dispensada p/ pré-tensionada (5.2.8.1); 2% Msd/braço |
| `redimensionamento` | roda escada completa; sob **H/300** adota HEB200/IPE300 (HEA200/HEA180 reprova por rigidez); _peso_rel não altera seleção (ordem da escada) |
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
| 3 fundação profunda | `tests/test_fase3_fundacao_profunda.py` (13 fast + 1 build) | gate `fundacao.tipo`/SPT bloqueia; `to_rodar_params`/`to_build_kwargs` estaca (exclusiva sapata); `calcular` grava adotados; build headless ESTACA/BLOCO/BALDRAME, 0 interferências, sem SAPATA; ref sapata não-regride |
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
regressão dos 6 defeitos de layout. Suíte completa `-m "not build"`: **256 passed**.

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
| `test_validacao_coerencia.py` (49) | `validar` BLOQUEIA todo input degenerado: span<0, ridge≤eave, slope≤0, aguas∉{1,2}, V0<30/>60, abertura>fachada, sigma_solo∉[30,2000], span>120, ponte (Q/vão>0, aprox_min<vão, n_rodas, frações, phi≥1), tesoura (h>0, n_paineis par&≥2), fundação (fck/fyk>0, mu≥0, gamma_f≥1), vento-enums (cat I-V, classe A/B/C), estaca (tipo AokiVelloso, D/L>0, SPT N≥0/dz>0), baldrame b/h>0, terreno frações [0,1], opcionais (neve/fogo/escada/plataforma); **AVISO** z<ridge (não bloqueia) (D58/D61) |
| `test_wizard_robustez.py` (6) | `_ask_one` não trava em entrada vazia/EOF (RuntimeError, cap 100); `construir_spec` ValueError claro p/ obrigatório faltando |
| `test_mao_francesa_geom.py` (5) | **guarda permanente**: `mao_francesa_geom.segmentos` liga mesa inf→terça com componente X≠0 (fora do plano); Y constante; sobe da mesa inf à terça; ângulo 20–70° (D59) |
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

## Convenção de não-regressão
Selftest imprime valores de referência; alteração de código deve manter os valores do galpão de referência salvo quando a mudança normativa os corrige de propósito (ex.: redim H/300 muda perfil adotado — mudança intencional, documentada [[04-decisions#D5]]).
