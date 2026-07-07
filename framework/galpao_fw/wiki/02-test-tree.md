# 02 — Árvore de testes

Cada módulo de cálculo tem `_selftest()` no `if __name__=="__main__"`. Rodar: `python <modulo>.py`. Sem framework de teste externo — asserts inline + print de valores de referência. Não-regressão = valores do galpão de referência (nf982) inalterados.

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
| `vento_nbr6123` | (ver REVISAO-VENTO) |

## Convenção de não-regressão
Selftest imprime valores de referência; alteração de código deve manter os valores do galpão de referência salvo quando a mudança normativa os corrige de propósito (ex.: redim H/300 muda perfil adotado — mudança intencional, documentada [[04-decisions#D5]]).
