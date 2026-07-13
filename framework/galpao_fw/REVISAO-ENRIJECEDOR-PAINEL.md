# Revisão — Enrijecedores transversais da alma (painel do joelho)

Conferência do sênior. Fecha a **dívida (e)** do backlog do parecer 6.b: o cap
`h/tw ≤ 260` do Anexo H valia só para almas **sem** enrijecedores; com enrijecedores
transversais no painel do joelho (comum em pórtico tapered) a NBR 8800 **§5.4.3.1**
admite almas mais esbeltas e eleva a **força cortante resistente** via `kv`. Fase 6.13.
Criado 2026-07-13.

> **STATUS: ⏳ AGUARDA PARECER.** Módulo `enrijecedor_painel.py` novo; método lido
> **verbatim** da NBR 8800:2008 §5.4.3.1 (pág 50–51, imagens renderizadas). Cortante
> com `kv = 5 + 5/(a/h)²`, requisitos do enrijecedor §5.4.3.1.3, relaxamento do cap
> 260 do Anexo H quando `a/h ≤ 3`. **INFORMATIVO/opt-in** — não muda a utilização a
> menos que o engenheiro adote os enrijecedores.

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
| **c** | `I_st ≥ a·tw³·j`, com `j = [2,5/(a/h)²] − 2 ≥ 0,5` (inércia da seção do enrijecedor — singelo ou par — em relação ao eixo no plano médio da alma) |

Coeficientes `5 / 5 / 260 / 0,56 / 2,5 / 4tw / 6tw` lidos verbatim (mne-1).

## Módulo `enrijecedor_painel.py`

| Função | Faz |
|---|---|
| `kv(sec, a)` | §5.4.3.1.1 — `a=None` ⇒ 5; `a/h>3` ou `a/h>(260/(h/tw))²` ⇒ 5; senão `5+5/(a/h)²` |
| `vpl(sec, fy)` | §5.4.3.1.2 — `0,60·d·tw·fy` |
| `vrd(sec, fy, a)` | §5.4.3.1.1 — três domínios; `a=None` reproduz o cortante de `check_nbr8800` (kv=5) |
| `j_rigidez(a_h)` | §5.4.3.1.3c — `[2,5/(a/h)²]−2 ≥ 0,5` |
| `ist_req(sec, a)` | §5.4.3.1.3c — `a·tw³·j` |
| `ist_par(sec, b_st, t_st)` | inércia de um par de enrijecedores em relação ao plano médio (conservador) |
| `requisitos_enrijecedor(...)` | §5.4.3.1.3 a/b/c → `OK` global |
| `a_min_para_vsd(sec, fy, Vsd)` | maior `a` (menos enrijecedores) que faz `V_Rd(a) ≥ V_Sd` |

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
| `test_a_min_para_vsd` | busca do `a` que atende `V_Sd` |
| `test_selftest_roda` | selftest |
| `test_integra_reporta_enrijecedor_quando_esbelto` | rodar reporta reforço; util intacta (mne-2) |

15 testes verdes.

## FLAGs / backlog

- **Enrijecedores de apoio** (bearing stiffeners sob cargas concentradas, §5.7.4) não
  cobertos aqui — escopo é o enrijecedor **intermediário** de cisalhamento do painel.
- Contribuição de **campo de tração** (tension field action) NÃO adotada — a NBR
  8800 §5.4.3.1 não a inclui; `V_Rd` fica no ramo de flambagem por cisalhamento
  (conservador). Documentado.
- Espaçamento `a` **sugerido**, não imposto: a decisão de adotar (e o desenho do
  enrijecedor) é do engenheiro.
