# Revisão — Zona de painel do joelho (cisalhamento + doubler/enrijecedores)

Conferência do sênior. Fecha o **Q3 do parecer da alma variável** (fase 6.b), que
ficou no backlog: verificação do **painel de alma do pilar no nó rígido viga-coluna
(joelho)** e a decisão de chapa de reforço (doubler) e/ou enrijecedores. Fase 6.5.
Criado 2026-07-11.

> **STATUS: A REVISAR (parecer 1 respondido).** Módulo novo `zona_painel.py`. Base
> normativa lida **verbatim** do PDF `pesquisa/aço/nbr8800_2008_1.pdf`. Aplica a
> **todo pórtico de nó rígido** (prismático + alma variável); a tesoura não dispara.

## Parecer sênior 1 — respostas

| Pt | Alegação | Veredito / ação |
|---|---|---|
| A | `FSd = M/dm` deveria abater `V_col` (equilíbrio do painel nodal) | **PROCEDENTE — implementado.** `FSd = M/dm − V_col` (V_col = cortante do pilar no nó, já disponível = `kV`). NBR 5.7.7.1 define FSd como força das mesas (M/dm); o abatimento de `V_col` é o refino mecânico (AISC J10.6/Bellei), a favor da economia. Ponte: 1053→989 kN, u 1,27→1,19. |
| B | Capacidade + redução axial | **Correto** (sênior confirmou). Sem ação. |
| C | Falta o **enrugamento da alma** (web crippling) | **PROCEDENTE — adicionado §5.7.4.** (O sênior citou "§5.7.5" e coef "0,80"; no PDF **§5.7.4** e coef **0,66** interior / 0,33 extremidade — `Ff = 0,66·tw²[1+3(ln/d)(tw/tf)^1,5]√(E·fy·tf/tw)/γa1`.) |
| D | Doubler pode flambar por cisalhamento (esbeltez) | **PROCEDENTE — implementado por critério NBR.** A fórmula `hw/418√fy` do parecer é **AISC imperial** (não normativa na NBR); usei a esbeltez de **§5.4.3.1.1**: `t ≥ dc/λp`, `λp = 1,10√(kv·E/fy)`, kv=5. `dimensiona_doubler` retorna `max(t_força, t_esbeltez)`. Ponte: doubler 3→8 mm. |

## Base normativa (NBR 8800:2008, lida do PDF)

| Cláusula | Estado-limite | Fórmula (verbatim) |
|---|---|---|
| **§5.7.7.1** | Cisalhamento do painel de alma | `N_Sd ≤ 0,4·Npl` → `F_Rd = V_Rd` ; `N_Sd > 0,4·Npl` → `F_Rd = V_Rd·(1,4 − N_Sd/Npl)` |
| **§5.4.3.1.2** | Cortante do painel `V_Rd` | `Vpl = 0,60·fy·Aw`, `Aw = dc·tw` (pilar), `V_Rd = Vpl/γa1` (+redução por esbeltez §5.4.3.1.1, kv=5,0) |
| **§5.7.2.2** | Flexão local da mesa | `F_Rd = 6,25·tf²·fy/γa1` (metade se extremidade, §5.7.2.3) |
| **§5.7.3.2** | Escoamento local da alma | `F_Rd = 1,10·(5k + ln)·fy·tw/γa1` (interior) / `2,5k` (extremidade) |
| **§5.7.6.2** | Flambagem da alma por compressão | `F_Rd = 24·tw³·√(E·fy)/(h·γa1)` (metade se perto da extremidade, §5.7.6.3) |
| **§5.7.7.2** | Doubler (chapa de reforço) | dois lados da alma, dimensionada por §5.4 p/ o excesso; estende +150 mm além do painel |

`Npl = Ag·fy` (§5.7.7.1). **Demanda** `FSd = M_Sd/dm`, `dm = d_viga − tf_viga`
(binário das mesas da viga) — mecânica (Bellei, *Edifícios Industriais em Aço*),
não coeficiente de norma.

## 1. Módulo `zona_painel.py`

- `forca_das_mesas(M_Sd, d_viga, tf_viga)` → `FSd`.
- `cisalhamento_painel(caso)` → §5.7.7 com redução por axial; `V_Rd` via §5.4.3
  (esbeltez da alma do pilar, kv=5,0).
- `dimensiona_doubler(FSd, F_Rd, dc, fy)` → espessura total (mm, arredonda ↑) tal
  que `0,6·fy·dc·t/γa1 ≥ FSd − F_Rd` (§5.7.7.2, §5.4).
- `estados_locais(caso)` → §5.7.2/§5.7.3/§5.7.6; governante + `precisa_enrijecedor`.
- `verifica_painel(caso)` consolida: `u_painel`, `precisa_reforco`, `t_doubler_mm`,
  `precisa_enrijecedor`, `u_max`. `relatorio_pt`. `_selftest`.

## 2. Integração (rodar_galpao, gate7)

Após o gusset: monta o caso do joelho com `kM/kN/kV` (de `_esforcos_base_joelho`) +
a seção do pilar (`res["perfil_col"]` ou, no tapered, `props_I(h_joelho)`) + a viga
(`sc["perfil_raf"]` ou `h_joelho`). Salva `gate-zona-painel.txt` e popula
`res["zona_painel"]`. **Prismático e alma variável**; a **tesoura pula** (sem nó
rígido). No tapered, a seção do joelho é a **mais funda** (`h_joelho`) — pilar e
viga.

## 3. Build 3D (build_galpao)

`joelho()` já desenha enrijecedores de continuidade (padrão do nó de momento). O
elemento **novo condicional** é a **chapa de reforço de alma (doubler)**: duas
chapas paralelas à alma do pilar (uma de cada lado, §5.7.7.2), cobrindo o painel +
150 mm, desenhadas **só quando** `REFORCO_JOELHO.t_doubler > 0` (vindo do cálculo
via `to_build_kwargs → reforco_joelho`). Prefixo `CONEX_JOELHO_*_DOUBLER_L/R` →
tratado como elemento de conexão (fora da checagem de interferência primário-primário).
Verificado ao vivo: gatilho de 16 mm → 20 doublers (2 por joelho × 10 joelhos),
**0 interferências**.

## 4. Não-regressão

Sem gatilho → build não cria `DOUBLER_*` (mne-2). Tesoura sem `zona_painel` (mne-3).
Redução por axial ativa (`N_Sd > 0,4·Npl`, mne-4). Ref/prismático/alma-var/tesoura
inalterados; smoke 7/7.

## Checklist de testes (`tests/test_fase65_zona_painel.py`)

| Teste | Cobre |
|---|---|
| `test_forca_das_mesas` | `FSd = M/dm` |
| `test_painel_sem_axial_igual_Vrd` | §5.7.7 sem axial (`F_Rd = V_Rd`) + `V_Rd` §5.4.3 |
| `test_axial_alto_reduz_Frd` | redução `(1,4 − N_Sd/Npl)` (mne-4) |
| `test_alma_fina_exige_doubler` | doubler cobre o excesso §5.7.7.2 |
| `test_alma_espessa_passa` | `u_painel < 1`, sem reforço |
| `test_estados_locais_mesa_fina` | §5.7.2/§5.7.6 → enrijecedor |
| `test_selftest_roda` | selftest |
| `test_rodar_prismatico/alma_var_tem_zona_painel` | integração (gate + res) |
| `test_rodar_tesoura_sem_zona_painel` | tesoura pula (mne-3) |
| `test_build_sem_reforco_nao_cria_doubler` | build ref sem doubler, 0 interf. (mne-2) |

11 testes (10 fast + 1 build). Doubler condicional verificado ao vivo (0 interf.).

## Notas / limites de escopo

- Enrijecedor **diagonal** (§5.7.7.3, alternativa ao doubler) não desenhado — o
  doubler é a solução adotada. Refino de detalhamento.
- Enrijecedores de continuidade seguem sempre desenhados no `joelho()` (padrão do
  nó rígido); o flag `precisa_enrijecedor` do cálculo é reportado no gate para
  registro/ART.
