# Revisão — Contraventamento e barras tracionadas

Conferência do sênior. Barras tracionadas pela **NBR 8800:2008** (5.2):
contraventamento (diagonais redondas só-tração que levam o arrasto do vento
longitudinal à fundação), tirantes de terça (sag rods) e a barra da mão-francesa.

Código: `contraventamento.py`. Última atualização: 2026-07-07.

---

## 1. Barra tracionada (5.2)

```python
GA1 = 1.10 ; GA2 = 1.35
def tracao_barra_Rd(d, fy, fu, ct=1.0, k_rosca=0.75):
    Ag = math.pi * d ** 2 / 4.0
    An = k_rosca * Ag                       # area efetiva na rosca (~0,75 Ag)
    esc = Ag * fy / GA1                      # escoamento da secao bruta
    rup = ct * An * fu / GA2                 # ruptura da secao liquida
    return min(esc, rup), esc, rup
```

`Nt,Rd = min(Ag·fy/1,10 ; Ct·An·fu/1,35)`.

---

## 2. Força na diagonal e esbeltez (5.2.8)

```python
def n_diagonal(F_painel, dx, dy):
    L = math.hypot(dx, dy)
    cos_t = dx / L
    return F_painel / cos_t, L               # N = F_painel / cos(theta)

# esbeltez:
r_gir = d / 4.0                              # raio de giracao da secao cheia
lam = L / r_gir
esbeltez_ok = pretensionada or lam <= 300.0  # barra so-tracao pre-tensionada dispensa
```

---

## 3. Força de estabilização da mão-francesa (2%)

```python
def forca_estabilizacao_2pct(Msd, braco):
    return 0.02 * Msd / braco                # 2% da forca da mesa (Msd/braco)
```

---

## 4. Pontos de conferência (FLAGS)

1. **An = 0,75·Ag** na rosca ; **Ct = 1,0** (barra redonda).
2. **Esbeltez L/r ≤ 300** dispensada para barra só-tração **pré-tensionada**
   (esticador/turnbuckle) — reportado e sinalizado.
3. `F_painel` (arrasto por painel) vem de `Fa` do vento longitudinal — ver
   [REVISAO-VENTO.md](REVISAO-VENTO.md); fração por diagonal = arranjo (A CONFIRMAR).
4. Regra dos 2% = **resistência** do braço (proxy de literatura). **Rigidez** do
   travamento é da análise global com imperfeição equivalente (4.9.3.2), não deste
   módulo — a NBR 8800 não tem βbr fechado (isso é AISC App 6). Ver §6.2.

---

## 5. Onde revisar

| Assunto | Função | Item NBR 8800 |
|---|---|---|
| Nt,Rd | `tracao_barra_Rd` | 5.2 |
| Diagonal | `n_diagonal` | — |
| Esbeltez | `verifica_barra` | 5.2.8 |
| Estabilização 2% | `forca_estabilizacao_2pct` | lit. / 4.9.3.2 |

---

## 6. Resposta ao parecer do sênior (rodada 1 — 2026-07-07)

Parecer **sem erro de código** — só elogios + um alerta com **citação normativa
equivocada**. Pontos duros conferidos contra o PDF da NBR 8800.

### 6.1 — Confirmações verificadas contra o PDF

- **5.2.8.1** (esbeltez), literal: "Recomenda-se que o índice de esbeltez das barras
  tracionadas … **excetuando-se tirantes de barras redondas pré-tensionadas** ou
  outras barras montadas com pré-tensão, não supere 300." → `esbeltez_ok =
  pretensionada or lam <= 300` é **exato**. ✅
- **Barra rosqueada**: 5.2.2 exclui "barras redondas com extremidades rosqueadas"
  do min genérico e remete a **6.3.3.1** (`Ft,Rd = 0,75·Ab·fub/γa2`). O código usa
  `rup = 0,75·Ag·fu/γa2` (mesma expressão) e **ainda adiciona** o escoamento do
  fuste `Ag·fy/γa1` no `min` — gate extra conservador (para MR250 a ruptura na rosca
  governa: 222·Ag < 227·Ag, então o resultado não muda). ✅
- **Raio de giração** seção cheia `r = d/4` (I=πd⁴/64, A=πd²/4) ✅.
- **Diagonal** `N = F_painel/cos θ`, `cos θ = dx/hypot(dx,dy)` ✅.
- γa1=1,10, γa2=1,35 ✅.

### 6.2 — Alerta de rigidez (βbr) / "Anexo L" — citação IMPROCEDENTE, ponto de fundo registrado

O parecer alerta que a regra dos 2% cobre a **resistência** da contenção mas não a
**rigidez** (βbr), citando o "Anexo L da NBR 8800 – Contenção Nodal".

**A citação está errada:** o **Anexo L da NBR 8800 trata de VIBRAÇÕES** (conforto
de piso, caminhar de pessoas — ver 11.4.1), não de contenção nodal. O critério
resistência-**e**-rigidez com `Pbr`/`βbr` é do **AISC 360 Apêndice 6**, não da
NBR 8800. A NBR 8800 **não** traz fórmula fechada de rigidez de contenção; trata a
estabilização por **imperfeição geométrica equivalente** (item **4.9.3.2**: global
L/500, local L/1000) embutida na **análise de 2ª ordem do pórtico** — ou seja, a
rigidez do sistema de travamento é capturada no modelo global (P-Δ/P-δ com
imperfeições), não numa checagem por-braço.

**Fundo (correto):** um braço muito esbelto pode não travar de fato. Registrado como
FLAG: a `forca_estabilizacao_2pct` dimensiona o braço à **resistência**; a
**rigidez** do travamento é responsabilidade da análise global com imperfeições
(4.9.3.2), não deste módulo. Sem alteração de código.

### 6.3 — Não-regressão

Selftest `contraventamento` OK: contravento d20 (pré-tens., u<1), tirante d16,
mão-francesa d16 (2% de Msd=61,3/braço 0,171). Sem alteração de código. Aguarda
re-revisão.

---

## 7. Homologação (rodada 2 — 2026-07-07)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 8800:2008.**

Sênior aceitou a contra-argumentação: (1) `Nt,Rd` com γa1=1,10/γa2=1,35 e o gate
extra de escoamento do fuste (rosca por 6.3.3.1 governa, sem erro contra a
segurança); (2) `r=d/4`, `N=F/cosθ` exatos; (3) esbeltez 5.2.8.1 com dispensa de
pré-tensionada, literal; (4) **Anexo L = vibrações** (não contenção) — confusão do
1º parecer com AISC 360 App 6 (`Pbr`/`βbr`); a NBR 8800 delega a **rigidez** de
contenção à **imperfeição geométrica equivalente 4.9.3.2** na análise de 2ª ordem,
e a `forca_estabilizacao_2pct` cuida da **resistência** do braço.

Módulo `contraventamento.py` liberado. **Nenhuma alteração de código.**
