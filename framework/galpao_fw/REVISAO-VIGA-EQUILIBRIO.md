# Revisão — Viga de equilíbrio de divisa sobre estacas (variante profunda)

Novo módulo `viga_equilibrio.py`: variante **PROFUNDA** (estaca) da fundação de
divisa. Quando o pilar está na divisa do lote **e** a fundação é profunda, o grupo
de estacas não pode ser centrado sob o pilar (a divisa impede); o bloco fica
excêntrico e uma **viga de equilíbrio** (viga alavanca) o liga a um bloco interno.
Fecha o backlog "viga de equilíbrio de divisa excêntrica (estaca)". Fase 6.18.
Criado 2026-07-13.

> **STATUS: ⏳ AGUARDANDO PARECER** (2026-07-13). Unidades SI (m, kN). Saídas PT.

## Mecânica (corpo rígido — a MESMA já validada em `sapata_divisa`)

```
R' = P_divisa · l / (l − e)          reação amplificada no bloco de divisa
Delta_P = R' − P_divisa              acréscimo -> ALIVIA o pilar interno (praxe 50%)
M_viga = R' · e                      momento na viga (tração na face SUPERIOR)
V_viga = Delta_P
```
`l` = vão da viga (entre eixos dos pilares); `e` = excentricidade do eixo do pilar
ao centroide do grupo de estacas. **Não é norma nova** — é a estática de alavanca
de Alonso/Velloso & Lopes, já validada contra o exemplo trabalhado no
`sapata_divisa._selftest` (P=1400, e=0,79, l=5,5 → R=1635 kN).

## O que muda frente à sapata de divisa (variante rasa, já existente)

| | `sapata_divisa` (rasa) | `viga_equilibrio` (profunda) |
|---|---|---|
| Fundação de divisa | sapata excêntrica | **bloco sobre estacas** |
| Dimensiona | B×L da sapata (σ_solo) | **nº de estacas** = ⌈R'/P_adm⌉ |
| Capacidade | tensão admissível do solo | **P_adm da estaca** (sondagem, `estaca_profunda`) |
| Viga | alavanca (tração superior) | equilíbrio (tração superior) — **igual** |
| Alívio interno | 50% ΔP | 50% ΔP — **igual** |

## O que revisar

1. **Estática da alavanca** — `R'=P·l/(l−e)`, `ΔP`, `M=R'·e`, `V=ΔP`, alívio 50%.
   Idêntica ao `sapata_divisa` (homologado no item 34/D45).
2. **Grupo de estacas** — `n = estaca_profunda.n_estacas(R', P_adm)["n"]`;
   carga/estaca ≤ P_adm. `P_adm` vem da sondagem (Ask-Do-Not-Invent).
3. **Excentricidade `e`** — default geométrico `excentricidade_estimada`:
   2 estacas ⊥ à divisa, `x_centroide = D/2 + folga_borda + s/2`,
   `e = x_centroide − dist_divisa` (`s=3D` praxe). **Arranjo A CONFIRMAR** (depende
   do diâmetro/arranjo real); `e` pode ser passado explicitamente.
4. **Viga de equilíbrio** — RC tracionada na face superior; armadura por
   `fundacao_sapata._armadura_flexao` (NBR 6118, já homologado); itera `h` (l/7)
   até passar; `As_min` por `rho_min`.
5. **Wiring (`rodar_galpao`)** — o gate de divisa **ramifica**: com `params["estaca"]`
   → `viga_equilibrio` (usa a `P_adm` da estaca já calculada); senão →
   `sapata_divisa` (rasa). Corrigido shadowing de aliases (`est`→`est_res`,
   `ve`→`veq`) que colidiam com locais de `rodar`. Runtime end-to-end confirmado
   (`res["divisa"]["tipo"]` ∈ {estaca, sapata}).

## Cobertura de teste (fase 6.18)

`tests/test_fase618_viga_equilibrio.py` — 8 testes: reação amplificada (fórmula do
braço); e maior amplifica mais; nº de estacas cobre R'; alívio 50% no interno; viga
passa à flexão; excentricidade geométrica; relatório PT; wiring escolhe a variante
estaca.

## Escopo (FLAGs — Ask-Do-Not-Invent)

- `P_adm` da estaca (sondagem), cargas reais dos pilares (envelope do pórtico) e o
  arranjo/excentricidade do grupo na divisa = **entradas**; bloqueiam se não
  informados. Detalhamento (ancoragem, estribos da viga) = executivo.
