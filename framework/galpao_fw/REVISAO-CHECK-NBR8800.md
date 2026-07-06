# Revisão — Verificação de perfil (NBR 8800)

Conferência do sênior. Verifica um perfil I/H laminado sob **Nsd, Msd, Vsd**
(já amplificados por B1/B2 da 2ª ordem) pela **NBR 8800:2008** (Anexos F e G).

> Verifica a SEÇÃO, não a estabilidade global (essa é do pórtico/MAES).

Código: `check_nbr8800.py`. Norma: NBR 8800 (`pesquisa/aço/`).
Última atualização: 2026-07-06.

---

## 1. Compressão (5.3) — global χ + local Q

```python
def chi_compressao(lambda0):          # 5.3.3 / Tabela 4
    if lambda0 <= 1.5:
        return 0.658 ** (lambda0 ** 2)
    return 0.877 / lambda0 ** 2
```

`Ne = min(π²E·Ix/(Kx·L)², π²E·Iy/(Ky·Lb)²)` ;
`λ0 = √(Q·A·fy/Ne)` ; `Nc,Rd = χ·Q·A·fy/γa1` (γa1 = 1,10).

**Flambagem local Q = Qs·Qa** (Anexo F) — não assume Q = 1:

```python
def fator_Q(sec, fy):
    bf, tf, d, tw = sec["bf"], sec["tf"], sec["d"], sec["tw"]
    h = d - 2 * tf
    rE = math.sqrt(E / fy)
    # Qs - mesa (elemento AL, Grupo 4)
    bt_f = (bf / 2.0) / tf
    lim1, lim2 = 0.56 * rE, 1.03 * rE
    if bt_f <= lim1:
        Qs = 1.0
    elif bt_f < lim2:
        Qs = 1.415 - 0.74 * bt_f * math.sqrt(fy / E)
    else:
        Qs = 0.69 * E / (fy * bt_f ** 2)
    # Qa - alma (elemento AA, Grupo 2)
    bt_w = h / tw
    limw = 1.49 * rE
    if bt_w <= limw:
        Qa = 1.0
    else:                                  # F.3.2 largura efetiva (ca=0,34)
        bef = 1.92 * tw * rE * (1 - 0.34 / bt_w * rE)
        bef = min(bef, h)
        Aef = sec["A"] - (h - bef) * tw
        Qa = Aef / sec["A"]
    return Qs * Qa, Qs, Qa, bt_f, bt_w
```

---

## 2. Flexão (Anexo G, Tabela G.1) — menor Mn entre FLT, FLM, FLA

`Cw = Iy·(d−tf)²/4` ; `J = (2·bf·tf³ + (d−2tf)·tw³)/3` ; `σr = 0,3·fy`.

```python
def momento_resistente(sec, fy, Lb, Cb=1.0):
    Mpl = Zx * fy
    sr = 0.3 * fy
    rE = math.sqrt(E / fy)
    Cw, J = _cw_j(sec)
    # FLT
    lam = Lb / ry ; lamp = 1.76 * rE
    Mr_flt = (fy - sr) * Wx
    b1 = (fy - sr) * Wx / (E * J)
    lamr_flt = (1.38 * math.sqrt(Iy * J)) / (ry * J * b1) * \
        math.sqrt(1 + math.sqrt(1 + 27 * Cw * b1 ** 2 / Iy))
    Mcr_flt = (Cb * math.pi ** 2 * E * Iy / Lb ** 2) * \
        math.sqrt(Cw / Iy + 0.039 * J * Lb ** 2 / Iy)
    Mn_flt = _interp_M(lam, lamp, lamr_flt, Mpl, Mr_flt, Mcr_flt, Cb)
    # FLM (mesa)
    lam_m = (bf/2)/tf ; lamp_m = 0.38*rE ; lamr_m = 0.83*math.sqrt(E/(fy-sr))
    Mcr_m = 0.69 * E * Wx / lam_m ** 2
    Mn_flm = _interp_M(lam_m, lamp_m, lamr_m, Mpl, (fy-sr)*Wx, Mcr_m)
    # FLA (alma)
    lam_a = h/tw ; lamp_a = 3.76*rE ; lamr_a = 5.70*rE
    Mn_fla = _interp_M(lam_a, lamp_a, lamr_a, Mpl, fy*Wx, Mpl)
    Mn = min(Mn_flt, Mn_flm, Mn_fla)
```

Interpolação (G.2.1):

```python
def _interp_M(lam, lamp, lamr, Mpl, Mr, Mcr, Cb=1.0):
    if lam <= lamp:  return Mpl
    if lam <= lamr:  return min(Cb*(Mpl - (Mpl-Mr)*(lam-lamp)/(lamr-lamp)), Mpl)
    return min(Mcr, Mpl)
```

`Mrd = Mn/γa1`.

---

## 3. Cortante (5.4.3)

```python
Aw = d * tw                              # area de cisalhamento (laminado)
lamw = h / tw ; lamw_p = 1.10 * math.sqrt(5.0 * E / fy)   # kv=5 (sem enrijec.)
Vpl = 0.6 * Aw * fy
Vrd = Vpl/GA1 if lamw <= lamw_p else Vpl/GA1 * (lamw_p / lamw)
```

---

## 4. Interação flexo-compressão (5.5.1.2)

```python
n, m = Nsd/Nc_Rd, Msd/Mrd
if n >= 0.2:
    inter = n + (8.0/9.0)*m          # N/Nrd + 8/9·(M/Mrd)
else:
    inter = n/2.0 + m                # N/(2Nrd) + M/Mrd
OK = inter <= 1.0 and (Vsd/Vrd) <= 1.0
```

---

## 5. Pontos de conferência

1. **K = 1,0** (Kx = Ky = 1) — coerente com o MAES (4.9.6.2: a translação de nós
   já está no B2). Confirmar.
2. **Cb = 1,0** default (conservador) — o momento variável poderia elevar Cb.
3. **σr = 0,3·fy** (tensão residual) — valor da norma para laminados.
4. **Cw, J** calculados da geometria (não tabela) — conferir contra catálogo.
5. **Aw = d·tw** (área de cisalhamento) — laminado; confirmar.
6. `Lb` (comprimento destravado) vem da mão-francesa/terças — ver
   [REVISAO-MAO-FRANCESA.md](REVISAO-MAO-FRANCESA.md).

---

## 6. Onde revisar

| Assunto | Função | Item NBR |
|---|---|---|
| χ (curva) | `chi_compressao` | 5.3.3 / Tab.4 |
| Q local | `fator_Q` | Anexo F / F.3.2 |
| Cw, J | `_cw_j` | — |
| Mn FLT/FLM/FLA | `momento_resistente` | Anexo G / Tab. G.1 |
| Cortante | `verifica` (bloco Vrd) | 5.4.3 |
| Interação | `verifica` (bloco inter) | 5.5.1.2 |
