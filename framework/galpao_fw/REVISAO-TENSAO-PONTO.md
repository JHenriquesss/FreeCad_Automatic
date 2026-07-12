# Revisão — Verificação por tensões §5.5.2.3 no joelho (interação M-V)

Conferência do sênior. Fecha a **dívida (d)** do backlog do parecer 6.b: a alma
esbelta do joelho tapered vê o **momento e a cortante de pico juntos**, e as
checagens SEPARADAS de hoje — flexão (Anexo G/H) e cortante (5.4.3) — não capturam
a **tensão combinada no ponto** (junção mesa-alma). O `tensao_ponto.py` aplica a
verificação por **tensões da teoria da elasticidade** da NBR 8800 **§5.5.2.3**.
Fase 6.9. Criado 2026-07-12.

> **STATUS: 🟡 PENDENTE SÊNIOR** (2026-07-12). Aguarda parecer. Base **verbatim** do
> PDF (`nbr8800_2008_1.pdf`, pág 57). **Ponto de atenção honesto ao revisor:** a NBR
> **não** traz von Mises combinado `√(σ²+3τ²)` como equação explícita — §5.5.2.3 dá
> checagens **separadas** de σ e τ (a–d). O von Mises entra aqui **apenas como check
> suplementar conservador** (energia de distorção), sinalizado em `base_vm`. Se o
> revisor considerar o suplementar indesejado, é remoção de uma linha (as checagens
> a–d normativas ficam).

## Contexto — qual lacuna fecha

Hoje `check_nbr8800.verifica` reporta `u_M` (interação flexo-compressão §5.5.1.2) e
`u_V` (cortante §5.4.3) **independentes**: nunca a tensão combinada num mesmo ponto.
Para alma **compacta** isso é aceitável (cortante e flexão têm reservas amplas). Para
a **alma esbelta do joelho** (Anexo H), onde M **e** V picam no mesmo local e a alma
é fina, a interação σ–τ na junção mesa-alma pode governar. §5.5.2.3 é a cláusula
normativa exata para "seções quaisquer submetidas a momento fletor e força cortante".

## Base normativa (NBR 8800:2008 §5.5.2.3, pág 57 — verbatim)

> *"A tensão resistente de cálculo para os estados-limites últimos a seguir deve ser
> igual ou superior à tensão solicitante de cálculo, expressa em termos de tensão
> normal, σSd, ou de tensão de cisalhamento, τSd, determinadas pela teoria da
> elasticidade…"*

| Alínea | Estado-limite | Condição |
|---|---|---|
| **a** | escoamento sob tensão normal | `σSd ≤ fy/γa1` |
| **b** | escoamento sob cisalhamento | `τSd ≤ 0,60·fy/γa1` |
| **c** | instabilidade sob tensão normal | `σSd ≤ χ·fy/γa1` |
| **d** | instabilidade sob cisalhamento | `τSd ≤ 0,60·χ·fy/γa1` |

`χ` = fator de redução (§5.3.3), com `λ0=√(fy/σe)` para tensões normais e
`λ0=√(0,60·fy/τe)` para cisalhamento. No módulo, `χ_n` e `χ_v` são **INPUT**: o
consumidor (rodar) passa `χ_v` da esbeltez ao cisalhamento da própria alma esbelta
(`Vrd·γa1/(0,6·Aw·fy)`) e `χ_n=1,0` (a flambagem normal já é coberta pela FLT/FLM de
trecho do Anexo J/H). Checagens **a–d aplicadas SEPARADAS** (fiel à norma).

**Suplementar (não-NBR):** von Mises `√(σ²+3τ²) ≤ fy/γa1` — critério de energia de
distorção, sempre entre `max(σ, √3·τ)` e `σ+√3·τ`. Marcado `base_vm`.

## Pontos avaliados (I duplo-simétrico)

| Ponto | σ | τ |
|---|---|---|
| fibra extrema (`y=d/2`) | `N/A + M/Wx` | ≈ 0 |
| **junção mesa-alma** (`y=d/2−tf`) | `N/A + M·(d/2−tf)/Ix` | `V·Qf/(Ix·tw)`, `Qf=bf·tf·(d−tf)/2` |

A **junção** concentra σ alto **e** τ alto → ponto crítico para a interação
(mne-5: `τ` pela `Qf` real da mesa, **não** a simplificação `V/Aw` uniforme). A
fibra extrema (τ≈0) alimenta o σ maior das alíneas a/c.

## Integração (`rodar_galpao`, coluna tapered)

No bloco da coluna tapered, **após** a compressão global (J.3): se a seção do joelho
é esbelta (`alma_esbelta.e_esbelta`), avalia `verifica_5523` com `kN/kM` amplificados
por B2 e `kV` do joelho + `χ_v` da alma; `u_col_5523 = max(a,b,c,d,vm)` entra no
**envelope** `interacao_max_col`. Só dispara no ramo alma esbelta → **ref prismática
20×10 e mísulas de alma não-esbelta intocadas** (mne-4). Prova fim-a-fim (joelho
`h=0,95 m, tw=4 mm`, `h/tw≈230`): `u_col_mv_5523=0,18`, governante **von Mises**,
sem abortar.

## Não-regressão

- Ref prismática 20×10: **inalterada** (coluna prismática não entra no ramo tapered).
- Mísula de alma **não-esbelta** (ex.: `h_joelho=0,60 m, tw=8 mm`, `h/tw≈72<161`):
  `e_esbelta=False` → `u_col_5523=0`, `r5523=None` (suítes 6.4/6.6/6.b intocadas).
- `tensao_ponto` puro (sem FreeCAD, sem numpy) → importável no build headless.

## Checklist de testes (`tests/test_fase69_tensao_ponto.py`)

| Teste | Cobre |
|---|---|
| `test_sigma_juncao_formula` | σ da junção = `N/A + M·yj/Ix` (me-1) |
| `test_tau_juncao_usa_Qf_real` | τ pela `Qf` da mesa, **≠** `V/Aw` uniforme (mne-5) |
| `test_fibra_extrema_tau_zero` | fibra extrema: `σ=N/A+M/Wx`, τ≈0 |
| `test_5523_retorna_quatro_checks` | retorna a/b/c/d + vm + gov + OK (me-2) |
| `test_von_mises_envelope` | `max(σ,√3τ) ≤ vm ≤ σ+√3τ` |
| `test_von_mises_flag_nao_normativo` | von Mises marcado suplementar (mne-2) |
| `test_check_d_reduz_com_chi_v` | `χ_v<1` torna d) mais severa que b) |
| `test_sigma_isolado_reprova` | σ>fy/γ isolado → `OK=False` (mne-3) |
| `test_tau_governa_com_V_alto` | V alto, M~0 → governa cisalhamento (b/d) |
| `test_selftest_roda` | selftest do módulo |
| `test_joelho_esbelto_integra` | joelho esbelto → `u_vm` finito, sem abortar (me-3) |

11 testes verdes.

## Notas / backlog

- §5.5.2.3 usa `σ`/`τ` da **teoria da elasticidade**; para I duplo-simétrico a
  junção mesa-alma é o ponto crítico prático. Seções monossimétricas/abertas
  genéricas exigiriam varredura de pontos — fora do escopo (galpão I bissimétrico).
- Alívio de cortante das mesas inclinadas `V_alma = V − (M/h)·tanθ` (dívida **a**,
  economia) segue em backlog — ignorá-lo aqui é **conservador** (τ maior).
- von Mises suplementar pode ser desativado se o revisor preferir só a–d normativas.
