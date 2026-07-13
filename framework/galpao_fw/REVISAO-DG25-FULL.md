# Revisão — DG25 full: Cb tapered + Mn nominal completo (VALIDAÇÃO)

Conferência do sênior. Estende o cross-check DG25 (item 42, elástico) para o
**momento nominal de FLT completo** do AISC Design Guide 25 §5.4 (Rpc, Rpg, F_L, três
regiões 5.4-16/17/18) e o **Cb tapered por tensões** (5.4-1/5.4-2). Fecha o refino
listado no backlog do item 42. Fase 6.14. Criado 2026-07-13.

> **STATUS: ⏳ AGUARDA PARECER.** Método lido **verbatim** do AISC DG25 §5.4.1–5.4.3
> (pág 58–62, imagens renderizadas). Continua **INFORMATIVO** — não altera o
> dimensionamento, que segue a **NBR 8800 Anexo J** (item 36). A novidade frente ao
> item 42: agora o Cb **NÃO cancela** na razão (entra não-linearmente pelas três
> regiões), e a comparação é de **capacidade nominal** (Mn), não só do `Mcr` elástico.

## O que muda frente ao item 42 (cross-check elástico)

| | Item 42 (`cross_check_flt`) | Item 43/6.14 (`cross_check_capacidade`) |
|---|---|---|
| Compara | `M_eLTB` **elástico** × `Mcr` NBR | **Mn nominal** DG25 × **Mn nominal** NBR |
| Cb | cancela (mesmo Cb dos 2 lados) | **não cancela** (não-linear nas regiões) |
| Fatores | — | `Rpc`, `Rpg`, `F_L`, 3 regiões (inelástica) |
| Prismático | 0,998 (fórmulas ≡) | **0,951** (curvas inelásticas diferem ~5%) |

O item 42 permanece **intocado** (back-compat, mne). Esta fase **acrescenta**
funções e um segundo cross-check.

## Base normativa (AISC DG25 §5.4 — verbatim das imagens, pág 58–62)

### §5.4.1 Cb tapered (5.4-1 / 5.4-2), método Yura-Helwig/AASHTO por **tensões**

```
Se fmid/f2 >= 1, ou f2 = 0, ou balanço:   Cb = 1,0
senão:   Cb = 1,75 − 1,05·(f1/f2) + 0,3·(f1/f2)²  ≤ 2,3        (5.4-1)
```
`f2` = |maior tensão de compressão| numa extremidade (compressão +, tração −);
`f1` por **5.4-2**: se `|fmid| < |(f0+f2)/2|` → `f1 = f0`; senão `f1 = 2·fmid − f2 ≥ f0`.

### §5.4.1 Rpc — plastificação da alma / compressão (5.4-4 / 5.4-5, Spec F4-9a/b)

```
hc/tw ≤ λpw:              Rpc = Mp/Myc                                  (5.4-4)
λpw < hc/tw < λrw:        Rpc = [Mp/Myc − (Mp/Myc − 1)·(λ−λpw)/(λrw−λpw)] ≤ Mp/Myc  (5.4-5)
hc/tw ≥ λrw  ou Iyc/Iy ≤ 0,23:   Rpc = 1,0 ≤ Mp/Myc
```
`Mp = Fy·Zx ≤ 1,6·Fy·Sxc` ; `Myc = Fy·Sxc` ; `λ = hc/tw` ;
`λpw = 3,76·√(E/Fy)` (duplo-sim, Spec Tab. B4.1) ; `λrw = 5,70·√(E/Fy)`.

### §5.4.1 Rpg — flambagem por flexão da alma / bend buckling (5.4-6 / 5.4-7, Spec F5-6)

```
hc/tw ≤ λrw:   Rpg = 1,0
hc/tw > λrw:   Rpg = 1 − aw/(1200 + 300·aw)·(hc/tw − 5,70·√(E/Fy)) ≤ 1,0     (5.4-6)
```
`aw = hc·tw/(bfc·tfc) ≤ 10,0` (5.4-7, **com** o cap de 10, ao contrário do `rt`).

### §5.4.2 Escoamento da mesa comprimida — CFY (5.4-8)

`Mn = Rpc·Rpg·Myc = Rpc·Rpg·Fy·Sxc` — **teto** do estado de FLT.

### §5.4.3 FLT — três regiões

**Chave algébrica:** `γ_eLTB = F_eLTB/f_r` (5.4-13) ⇒ `γ_eLTB·f_r = F_eLTB`. O `f_r`
(tensão de compressão no ponto) **cancela** em 5.4-16/17/18 — o Mn nominal depende só
de `F_eLTB`, `F_L`, `Fy`, `Rpc`, `Rpg`. Regiões via `F_eLTB/Fy` vs `π²/1,1² = 8,2`:

| Região | Condição | Mn |
|---|---|---|
| **(a)** | `F_eLTB/Fy ≥ 8,2` | FLT não se aplica → `Mn = Rpc·Rpg·Myc` (CFY) |
| **(b)** | `8,2 > F_eLTB/Fy > F_L/Fy` | `Rpg·Rpc·Myc·[1 − (1 − F_L/(Rpc·Fy))·(π√(Fy/F_eLTB)−1,1)/(π√(Fy/F_L)−1,1)] ≤ Rpg·Rpc·Myc` (5.4-16) |
| **(c)** | `F_eLTB/Fy ≤ F_L/Fy` | esbelta: `Rpg·F_eLTB·Sxc` (5.4-17) ; senão `F_eLTB·Sxc` (5.4-18) |

`F_L = 0,7·Fy` (5.4-14, duplo-simétrico `Sxt/Sxc = 1 ≥ 0,7`).
`F_eLTB`, `rt`, `J` como no item 42 (5.4-10/11/12).

Coeficientes `1,75 / 1,05 / 0,3 / 2,3 / 3,76 / 5,70 / 8,2 / 0,7 / 1,6 / 0,23` verbatim (mne-2).

## Módulo `dg25_ltb.py` (funções novas)

`myc`, `mp_dg`, `_lam_pw`, `_lam_rw`, `rpc`, `rpg`, `f_L`, `m_cfy`,
`mn_ltb_dg(sec, fy, Lb, Cb)` → `{Mn, M_cfy, regiao, Rpc, Rpg, F_L, F_eLTB, ...}`,
`cb_tapered(f0, fmid, f2)`,
`cross_check_capacidade(segs, fy, Lb, Cb, tol=0,20)` →
`{Mn_dg, Mn_nbr, razao, converge, regiao_dg, Rpc, Rpg, sec_meio, sec_funda}`.
Puro (sem numpy — importável no build). `_selftest` estendido.

## Resultados (smoke, Cb ilustrativo = 1,30)

| Membro | Região | Rpc | Rpg | Mn_DG (meio) | Mn_NBR (funda) | razão cap. | razão elást. (item 42) |
|---|---|---|---|---|---|---|---|
| **Prismático** (base sã) | b | — | 1,00 | 477,2 | 501,9 | **0,951** | 0,998 |
| Rafter 0,90→0,45 | b | 1,110 | 1,00 | 543,0 | 888,1 | **0,611** | 0,726 |
| Coluna 0,90→0,35 | b | 1,105 | 1,00 | 504,2 | 888,1 | **0,568** | 0,662 |

## Interpretação (SEM falso alarme)

- **Prismático 0,951 (não 1,0):** o `M_eLTB` **elástico** é idêntico (0,998, item 42 —
  F4-5 ≡ F2), mas a **capacidade nominal** difere ~5% porque a **curva inelástica** do
  DG25 (região b, White & Kim, ancorada em `Rpc·Myc` e `F_L`) **não é** a interpolação
  do NBR Anexo G (ancorada em `Mp`/`Mr` com `λ = Lb/ry`). São **dois pacotes de
  cálculo diferentes** no regime inelástico — a divergência de 5% é a **assinatura**
  dessa diferença de formulação, não erro.
- **Tapered ~0,6:** soma a diferença inelástica (~5%) à diferença **geométrica** da
  seção de referência (meio × funda, o achado do item 42). O DG25 (seção do meio) é
  **mais conservador** que o Anexo J (seção funda) no momento nominal para tapers
  fortes.
- **Nada muda no dimensionamento.** A utilização segue **100% NBR Anexo J** (item 36),
  auto-consistente (demanda e resistência na mesma seção). O cross-check entrega ao
  sênior um **número AISC independente de capacidade** para sanity-check.

## Integração (`rodar_galpao`) — informativa

Ao lado do cross-check elástico (item 42), o **cross-check de capacidade** do rafter:
`[CROSS-CHECK DG25 CAPACIDADE (informativo)] Mn nominal completo (Rpc/Rpg/3 regiões,
região X): Mn_DG(meio)=… ; Mn_NBR(funda)=… → razão=… CONVERGE/DIVERGE`.
`res["alma_variavel"]`: `dg25_cap_razao_raf`, `dg25_cap_regiao_raf`,
`dg25_cap_converge_raf`. **Utilização intocada** (só reporta) (mne-1).

## Não-regressão

- `cross_check_flt` (item 42) **byte-idêntico** — só foram acrescentadas funções.
- Nenhuma utilização/`interacao_max_*` muda.
- Ref prismática 20×10 não entra (só ramo tapered).
- Suítes fase-6 + build verdes.

## Checklist de testes (`tests/test_fase614_dg25_full.py`)

| Teste | Cobre |
|---|---|
| `test_rpc_compacta_igual_mp_myc` | Rpc = Mp/Myc (compacta, 5.4-4) |
| `test_rpc_slender_um` | alma esbelta → Rpc=1 |
| `test_rpc_noncompact_interpola` | Rpc interpola (5.4-5) |
| `test_rpg_nao_esbelta_um` | Rpg=1 (não esbelta) |
| `test_rpg_slender_menor_que_um` | Rpg<1 verbatim 5.4-6 (aw cap 10) |
| `test_fL_duplo_simetrico` | F_L = 0,7Fy (5.4-14) |
| `test_mn_positivo_e_bounded_por_cfy` | 0 < Mn ≤ CFY |
| `test_mn_cresce_quando_Lb_diminui` | Mn↑ com Lb↓ |
| `test_mn_regiao_a_quando_muito_curto` | Lb→0 → região (a), Mn=CFY |
| `test_mn_regiao_c_quando_muito_longo` | Lb grande → região (c) elástica |
| `test_cb_uniforme_um` | fmid/f2≥1 ou f2=0 → Cb=1 |
| `test_cb_gradiente_maior_que_um_limitado_23` | Cb ∈ [1 ; 2,3] |
| `test_cb_formula_verbatim` | 5.4-1/5.4-2 verbatim |
| `test_capacidade_cb_nao_cancela` | Cb **altera** a razão (≠ item 42) |
| `test_capacidade_prismatico_finito` | prismático finito, região definida |
| `test_selftest_roda` | selftest |
| `test_integra_reporta_capacidade` | rodar reporta razão de capacidade; util intacta (mne-1) |

17 testes verdes.

## FLAGs / backlog

- **FLB (flambagem local da mesa, §5.4.4)** e **TFY/ruptura da mesa tracionada
  (§5.4.5/5.4.6)** do DG25 não implementados — o cross-check foca o estado de **FLT**,
  que é o que o Anexo J tapered governa. Refino futuro se o sênior quiser o envelope
  DG25 completo dos 5 estados-limite (§5.4 lista 1–5).
- **Cb tapered aplicado no rodar:** `cb_tapered` está disponível, mas a integração usa
  o `cb_raf`/`cb_col` já calculados (Anexo J, item 36) para manter a comparação
  ancorada na NBR. Trocar para o Cb-tensão do DG25 seria **decisão de método** do
  sênior — fora do escopo (informativo).
- **Divergência meio×funda + inelástica:** decisão de método, não bug. Documentada,
  não aplicada.
