# Revisão — Enrijecedores transversais da alma (painel do joelho)

Conferência do sênior. Fecha a **dívida (e)** do backlog do parecer 6.b: o cap
`h/tw ≤ 260` do Anexo H valia só para almas **sem** enrijecedores; com enrijecedores
transversais no painel do joelho (comum em pórtico tapered) a NBR 8800 **§5.4.3.1**
admite almas mais esbeltas e eleva a **força cortante resistente** via `kv`. Fase 6.13.
Criado 2026-07-13.

> **STATUS: ✅ PARECER RESPONDIDO (aguarda confirmação)** (2026-07-13). Escrutínio
> matemático **validou** curva de cisalhamento (1,10/1,37; continuidade
> `1,24·(1,10/1,37)² ≈ 1,10/1,37 ≈ 0,80`), condições de `kv` e `Aw=d·tw`. **3
> apontamentos:** (1) nomenclatura `a_min→a_max` **ACOLHIDA** (bug real de nome); (2)
> eixo de inércia singelo×par — **norma REFUTADA** (NBR §5.4.3.1.3c diz *plano médio*
> para AMBOS, verbatim; o eixo-na-face é AISC 360 G2.2), **mérito mecânico ACOLHIDO**
> (adicionado `ist_singelo` no eixo-da-face como conservador); (3) campo de tração —
> **REFUTADO** (§5.4.3.2 é *"Seções tubulares retangulares e caixão"*, não tension
> field; NBR 8800:2008 **não tem** cláusula de campo de tração; redação refinada).

## Parecer sênior — respostas

| Pt | Apontamento | Veredito / ação |
|---|---|---|
| **Acertos** | Curva cisalhamento (1,10/1,37, continuidade ≈0,80), travas de `kv`, `Aw=d·tw` | **CONFIRMADOS.** Sem ação. |
| **1 (nome)** | `a_min_para_vsd` retorna o espaçamento **máximo** (maior `a` com `V_Rd≥V_Sd`); nome contraria a física | **ACOLHIDO — bug de nomenclatura.** Renomeado `a_max_para_vsd` (módulo, `rodar_galpao`, teste). Docstring reforça "limite superior admissível". |
| **2 (eixo I)** | "Divergência normativa": singelo deveria ter I em relação à **face** da alma, não ao plano médio | **NORMA REFUTADA + MÉRITO ACOLHIDO.** NBR 8800:2008 §5.4.3.1.3c, **verbatim** (pág 51): *"inércia da seção de um enrijecedor singelo **ou** de um par… **em relação ao eixo no plano médio da alma**"* — a NBR usa **plano médio para AMBOS**. O eixo-na-face para singelo é **AISC 360 G2.2**, não a NBR. Porém o mérito mecânico é válido (plano médio superestima I no singelo assimétrico): adicionado `ist_singelo` = `t·b³/3` (eixo na face, **conservador**), selecionável por `disposicao='singelo'`. Ficar mais conservador que a NBR é sempre admissível. |
| **3 (tração)** | "NBR não inclui" seria falsa premissa; campo de tração estaria em §5.4.3.2 | **REFUTADO.** NBR 8800:2008 **§5.4.3.2** (verbatim, pág 51) = *"Seções tubulares retangulares e caixão"*, **não** campo de tração. A NBR 8800:2008 **não possui** cláusula de tension field em §5.4.3 (.1 I/H/U · .2 tubular · .3 T · .4 cantoneiras · .5 I/H/U eixo-mesas · .6 tubular circular) — ao contrário do **AISC 360 G3**. FLAG mantido; **redação refinada** para "a NBR 8800:2008 não contempla campo de tração (≠ AISC G3)". |

## Contexto — o TODO que esta fase fecha

`alma_esbelta._valida` (item 38) trazia:

> *"O limite 260 vale para almas SEM enrijecedores transversais. TODO: com
> enrijecedores no painel (comum no joelho), o limite depende de a/h — expandir
> quando um módulo de enrijecimento do painel tapered for adicionado."*

Este é o módulo. A alma esbelta do joelho, quando o `V_Sd` de pico excede o `V_Rd`
sem enrijecedor (`kv=5`), pode ser reforçada com enrijecedores transversais espaçados
de `a`, elevando `kv` e portanto `V_Rd`.

## Base normativa (NBR 8800:2008 §5.4.3.1 — verbatim das imagens, pág 50–51)

### §5.4.3.1.1 — V_Rd (três domínios de λ = h/tw)

| Domínio | V_Rd |
|---|---|
| `λ ≤ λp` | `Vpl / γa1` |
| `λp < λ ≤ λr` | `(λp/λ)·Vpl / γa1` |
| `λ > λr` | `1,24·(λp/λ)²·Vpl / γa1` |

com `λp = 1,10·√(kv·E/fy)` , `λr = 1,37·√(kv·E/fy)` e

```
kv = 5,0               para almas SEM enrijecedores transversais,
                       para a/h > 3  ou  a/h > [260/(h/tw)]²
kv = 5 + 5/(a/h)²      para todos os outros casos
```

`a` = distância entre linhas de centro de dois enrijecedores adjacentes;
`h` = distância entre faces internas das mesas (perfil soldado) = `d − 2tf`.

### §5.4.3.1.2 — Vpl

`Vpl = 0,60·Aw·fy`, com `Aw = d·tw` (**altura total `d`**).

### §5.4.3.1.3 — requisitos do enrijecedor (quando necessário)

| Alínea | Requisito |
|---|---|
| **a** | soldado à alma e às mesas; interrupção do lado tracionado entre `4tw` e `6tw` |
| **b** | (largura/espessura) do enrijecedor `≤ 0,56·√(E/fy)` |
| **c** | `I_st ≥ a·tw³·j`, com `j = [2,5/(a/h)²] − 2 ≥ 0,5`. NBR **verbatim**: inércia do enrijecedor **singelo OU par** em relação ao eixo no **plano médio da alma** (para ambos). Módulo adota, para o singelo, o eixo **na face** (`t·b³/3`, conservador — AISC 360 G2.2) como *safe-side* opcional |

Coeficientes `5 / 5 / 260 / 0,56 / 2,5 / 4tw / 6tw` lidos verbatim (mne-1).

## Módulo `enrijecedor_painel.py`

| Função | Faz |
|---|---|
| `kv(sec, a)` | §5.4.3.1.1 — `a=None` ⇒ 5; `a/h>3` ou `a/h>(260/(h/tw))²` ⇒ 5; senão `5+5/(a/h)²` |
| `vpl(sec, fy)` | §5.4.3.1.2 — `0,60·d·tw·fy` |
| `vrd(sec, fy, a)` | §5.4.3.1.1 — três domínios; `a=None` reproduz o cortante de `check_nbr8800` (kv=5) |
| `j_rigidez(a_h)` | §5.4.3.1.3c — `[2,5/(a/h)²]−2 ≥ 0,5` |
| `ist_req(sec, a)` | §5.4.3.1.3c — `a·tw³·j` |
| `ist_par(sec, b_st, t_st)` | par (um de cada lado), eixo **plano médio** = `t·(2b+tw)³/12` (NBR verbatim) |
| `ist_singelo(sec, b_st, t_st)` | singelo (um lado), eixo **na face** = `t·b³/3` (conservador, AISC-aligned — safe-side vs NBR) |
| `requisitos_enrijecedor(..., disposicao)` | §5.4.3.1.3 a/b/c → `OK`; `disposicao='par'\|'singelo'` |
| `a_max_para_vsd(sec, fy, Vsd)` | **maior** `a` admissível (espaçamento **máximo**, menos enrijecedores) com `V_Rd(a) ≥ V_Sd` |

Puro (sem numpy — importável no build headless). `_selftest`.

## Relaxamento do cap 260 do Anexo H (`alma_esbelta._valida`)

`_valida(sec, a=None)`: quando `a` é fornecido **e** `a/h ≤ 3`, o cap `h/tw ≤ 260` é
**substituído** pelo provimento dos enrijecedores (§5.4.3.1.1 admite `kv>5`); o limite
`Aw/Afc ≤ 10` **continua valendo** (independe de `a`). `mrd_alma_esbelta(..., a=None)`
propaga o parâmetro.

## Integração (`rodar_galpao`) — informativa/opt-in

No bloco da **zona de painel** do joelho: se a alma do joelho for esbelta E o `V_Sd`
de pico exceder `V_Rd(kv=5)`, o módulo **sugere** o maior espaçamento `a` que atende e
reporta em `res["zona_painel"]`: `enrij_a_sug_mm`, `enrij_kv`, `enrij_Vrd_kN`,
`enrij_Vrd_sem_kN`, `enrij_Ist_req_cm4`. **Não altera a utilização** — é
dimensionamento do reforço, adotado pelo engenheiro (mne-2).

## Não-regressão

- `a=None` ⇒ `kv=5` ⇒ `V_Rd` **byte-idêntico** ao `check_nbr8800` atual (mne-3).
- Ref prismática 20×10 intocada (só dispara em joelho tapered esbelto).
- Suítes fase-6 + build verdes.

## Checklist de testes (`tests/test_fase613_enrijecedor_painel.py`)

| Teste | Cobre |
|---|---|
| `test_kv_sem_enrijecedor` | `a=None` → 5 |
| `test_kv_a_igual_h` | `a/h=1` → 10 |
| `test_kv_a_h_maior_que_3_cai_para_5` | `a/h>3` → 5 |
| `test_kv_a_h_acima_do_limite_260` | `a/h>(260/(h/tw))²` → 5 |
| `test_vrd_sobe_com_enrijecedor` | `V_Rd(enrij) > V_Rd(kv=5)` |
| `test_vrd_a_none_reproduz_kv5` | `a=None` reproduz check_nbr8800 (mne-3) |
| `test_j_rigidez` | `j=2,5/(a/h)²−2 ≥ 0,5` |
| `test_ist_req_formula` | `I_st ≥ a·tw³·j` verbatim |
| `test_requisitos_ok_e_reprova` | b/t + I_st passa/reprova |
| `test_bt_limite_verbatim` | `0,56√(E/fy)` |
| `test_anexo_h_cap_260_relaxado_com_enrijecedor` | cap 260 dispensado com `a/h≤3` |
| `test_aw_afc_ainda_limita` | `Aw/Afc>10` reprova mesmo com `a` |
| `test_a_max_para_vsd` | espaçamento **máximo** admissível (a maior falha) |
| `test_ist_singelo_conservador_vs_par` | singelo (face) < par (plano médio); `disposicao` |
| `test_selftest_roda` | selftest |
| `test_integra_reporta_enrijecedor_quando_esbelto` | rodar reporta reforço; util intacta (mne-2) |

16 testes verdes.

## FLAGs / backlog

- **Enrijecedores de apoio** (bearing stiffeners sob cargas concentradas, §5.7.4) não
  cobertos aqui — escopo é o enrijecedor **intermediário** de cisalhamento do painel.
- Contribuição de **campo de tração** (tension field action) NÃO adotada. Motivo: a
  **NBR 8800:2008 não contempla campo de tração** em §5.4.3 (ao contrário do **AISC
  360 G3**) — §5.4.3.1 dá apenas os ramos de flambagem elástica/inelástica por
  cisalhamento, e os subitens seguintes (§5.4.3.2 tubular/caixão, §5.4.3.3 T, etc.)
  tratam de **outras seções**, não da parcela pós-flambagem de tração diagonal. `V_Rd`
  fica no ramo convencional (conservador). Refutado o apontamento de que §5.4.3.2
  seria tension field.
- Espaçamento `a` **sugerido**, não imposto: a decisão de adotar (e o desenho do
  enrijecedor) é do engenheiro.
