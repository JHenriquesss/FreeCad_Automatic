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

## Convenção de não-regressão
Selftest imprime valores de referência; alteração de código deve manter os valores do galpão de referência salvo quando a mudança normativa os corrige de propósito (ex.: redim H/300 muda perfil adotado — mudança intencional, documentada [[04-decisions#D5]]).
