# Revisão — Pórtico (análise 1ª + 2ª ordem)

Conferência do engenheiro sênior. Análise do pórtico transversal (1 vão, 2
águas): esforços de 1ª ordem por rigidez direta e amplificação de 2ª ordem
pelo **MAES — NBR 8800:2008, Anexo D**.

> CONCEITUAL — calcula esforços; o engenheiro revisa e assina (ART).

Código: `frame2d.py` (solver), `estabilidade_b1b2.py` (MAES),
`galpao_portico.py` (geometria, cargas, combinações). Norma: NBR 8800 (PDF em
`pesquisa/aço/`). Última atualização: 2026-07-06.

---

## 1. Solver de 1ª ordem — `frame2d.py`

Método da **rigidez direta**, elemento de viga-coluna (Euler-Bernoulli), 3 GDL
por nó (u, v, θ). Aceita cargas nodais e UDL de membro em componentes globais.

**Validado** contra solução fechada (`python frame2d.py`): balanço `δ = PL³/3EI`
e `M = PL`; viga biapoiada `M = wL²/8`. É análise matricial padrão — COMPUTA,
não certifica.

### Matriz de rigidez local (6×6)

```python
def _k_local(self, e, L):
    E, A, I = e["E"], e["A"], e["I"]
    EA_L = E * A / L
    EI = E * I
    k = np.zeros((6, 6))
    k[0, 0] = k[3, 3] = EA_L
    k[0, 3] = k[3, 0] = -EA_L
    a = 12 * EI / L**3
    b = 6 * EI / L**2
    c = 4 * EI / L
    d = 2 * EI / L
    k[1, 1] = k[4, 4] = a
    k[1, 4] = k[4, 1] = -a
    k[1, 2] = k[2, 1] = b
    k[1, 5] = k[5, 1] = b
    k[2, 4] = k[4, 2] = -b
    k[4, 5] = k[5, 4] = -b
    k[2, 2] = k[5, 5] = c
    k[2, 5] = k[5, 2] = d
    return k
```

### Cargas equivalentes de UDL (fixed-end forces, em eixo local)

```python
def _fef_local(self, e, L, cs, sn):
    wx, wy = self.member_udl.get(self._eidx(e), (0.0, 0.0))
    w_ax = wx * cs + wy * sn        # ao longo da barra
    w_pp = -wx * sn + wy * cs       # perpendicular
    f = np.zeros(6)
    f[0] = f[3] = w_ax * L / 2.0
    f[1] = f[4] = w_pp * L / 2.0
    f[2] = w_pp * L**2 / 12.0
    f[5] = -w_pp * L**2 / 12.0
    return f
```

### Montagem, solução e reações

```python
# global: k_glob = T.T @ k_loc @ T ; F -= T.T @ fef  (cargas equivalentes)
d[free] = np.linalg.solve(Kff, Ff)          # deslocamentos
# esforcos de barra (local): f = k_loc @ (T @ d_e) + fef
# reacoes: R = K @ d - F  (nao-nulo nos apoios; inclui contencoes ficticias)
```

Convenção: `mf[e] = [N_i, V_i, M_i, N_j, V_j, M_j]` = forças que a barra exerce
nos nós; normal interno (tração +) = `-N_i = +N_j`.

---

## 2. Combinações ELU — `galpao_portico._combos_elu`

Cruza cada combinação com os dois casos de vento (W1 = portão a barlavento,
W2 = a sotavento); Q favorável = 0 no uplift.

```python
for wc in ("W1", "W2"):
    combos[f"C1_grav_{wc}"]   = {"G": 1.25, "Q": 1.50, wc: 0.6 * 1.40}
    combos[f"C2_uplift_{wc}"] = {"G": 1.00, wc: 1.40}            # sem Q (favor.)
    combos[f"C3_Gdesf_{wc}"]  = {"G": 1.25, wc: 1.40, "Q": 0.8 * 1.50}
    combos[f"C3_Gfav_{wc}"]   = {"G": 1.00, wc: 1.40}           # sem Q (favor.)
    if ponte:
        combos[f"C4_ponte_{wc}"]       = {"G": 1.25, "PONTE": 1.50, wc: 0.6*1.40, "Q": 0.8*1.50}
        combos[f"C5_vento_ponte_{wc}"] = {"G": 1.25, wc: 1.40, "PONTE": 0.7*1.50, "Q": 0.8*1.50}
```

> **Conferir**: coeficientes de ponderação γ e fatores de combinação ψ0
> (NBR 8800 Tab. 1 / NBR 8681). ψ0·γq = 0,6·1,4 no vento secundário, 0,8·1,5 na
> sobrecarga secundária.

---

## 3. 2ª ordem — MAES — `estabilidade_b1b2.py` (NBR 8800 Anexo D)

```
Msd = B1·Mnt + B2·Mlt        Nsd = Nnt + B2·Nlt        (D.2.1)
B1  = Cm/(1 − Nsd1/Ne) ≥ 1   (P-δ local, por barra)    Cm = 1,0 (carga transversal)
B2  = 1/(1 − (1/Rs)·(Δh·ΣN)/(H·ΣH))   (P-Δ global)     Rs = 0,85 (nós rígidos)
Ne  = π²·E·I / L²                                       (flambagem no plano)
```

Decomposição **nt/lt**: `nt` = beirais travados por contenção fictícia (→ Mnt,
Nnt e a reação lateral fictícia); `lt` = mesma estrutura sem fictícias, carregada
com as reações fictícias **invertidas** (→ Mlt, Nlt, deslocamento Δh).

### Força nocional (imperfeição geométrica, 4.9.7.1.1)

```python
FN_FRAC = 0.003     # 0,3% da carga gravitacional do andar
def _forca_nocional(combo):
    return FN_FRAC * (combo.get("G",0)*GVERT + combo.get("Q",0)*QVERT
                      + combo.get("PONTE",0)*PVERT)   # vento NAO entra
```

### B1 por barra (amplificação local) e combinação nt/lt

```python
def _combina_grupo(mf_nt, mf_lt, elems, B2, sec, Efac=1.0):
    # Nsd1 = normal interno MAIS COMPRIMIDO (mais negativo) do grupo
    Nsd1 = 0.0
    for e in elems:
        for Nint in (-(mf_nt[e][0] + mf_lt[e][0]), (mf_nt[e][3] + mf_lt[e][3])):
            if Nint < Nsd1:
                Nsd1 = Nint
    Ne = math.pi ** 2 * (E * Efac) * sec["I"] / sec["L"] ** 2
    Cm = 1.0                     # ha cargas transversais na barra (D.2.2)
    B1 = max(Cm / (1.0 - abs(Nsd1) / Ne), 1.0) if Nsd1 < 0 else 1.0
    Msd = Nsd = Vsd = 0.0
    for e in elems:
        for im, iN, iV, sgn in ((2, 0, 1, -1.0), (5, 3, 4, +1.0)):
            m = B1 * mf_nt[e][im] + B2 * mf_lt[e][im]
            n = sgn * (mf_nt[e][iN] + B2 * mf_lt[e][iN])
            v = mf_nt[e][iV] + mf_lt[e][iV]      # Vsd nao amplificado (D.2.4)
            Msd = max(Msd, abs(m)); Nsd = max(Nsd, abs(n)); Vsd = max(Vsd, abs(v))
    return {"B1": B1, "Ne": Ne, "Msd": Msd, "Nsd": Nsd, "Vsd": Vsd, ...}
```

### B2 global (P-Δ, D.2.3) e classificação de deslocabilidade

```python
if sumH < 1e-9:            # sem forca lateral liquida
    B2 = 1.0
else:
    B2 = 1.0 / (1.0 - (1.0 / RS) * (dh * sumN) / (H_STORY * sumH))
# sumN = reacoes verticais nas bases (carga gravitacional do andar)
# sumH = reacao lateral ficticia total ; dh = deslocamento lt no beiral
```

```python
def _classe(B2max):
    if B2max <= 1.1: return "pequena deslocabilidade (2a ordem dispensavel)"
    if B2max <= 1.4: return "media deslocabilidade (B1/B2 com rigidez reduzida 80%)"
    return "GRANDE deslocabilidade (exige P-Delta rigoroso)"
```

### Rigidez reduzida (média deslocabilidade, 4.9.7.1.2)

`analyse()`: 1º passo com rigidez integral → classifica por B2. Se B2 > 1,1,
refaz com `EA` e `EI × 0,8` (Efac = 0,8) → esforços FINAIS. Se ≤ 1,1, mantém
rigidez integral.

---

## 4. Pontos de conferência (possíveis problemas de método)

1. **Rs = 0,85** — adotado fixo (D.2.3, nós rígidos). Confirmar aplicabilidade
   à base rotulada.
2. **Cm = 1,0** — assumido para barras com carga transversal (D.2.2). Para barras
   sem carga transversal entre apoios, Cm menor seria menos conservador.
3. **Ne = π²EI/L²** com `L` = comprimento real da barra e `K = 1` (4.9.6.2).
   Conferir o comprimento efetivo adotado (coluna L = pé-direito; viga L =
   comprimento inclinado da água).
4. **Força nocional** só de G/Q/ponte (não do vento), somada no sentido do vento.
5. **Vsd não amplificado** (D.2.4) — confirmar.
6. **B2 por andar único** (galpão térreo) com ΣN = reações verticais de base.

---

## 5. Onde revisar no código

| Assunto | Arquivo / função | Item NBR |
|---|---|---|
| Rigidez / solução | `frame2d._k_local`, `solve` | análise matricial |
| Cargas de UDL | `frame2d._fef_local` | — |
| Combinações ELU | `galpao_portico._combos_elu` | Tab.1 / NBR 8681 |
| Decomposição nt/lt | `estabilidade_b1b2._analisa_combo` | An. D |
| B1 / Ne | `_combina_grupo` | D.2.1 / D.2.2 |
| B2 / classe | `_analisa_combo`, `_classe` | D.2.3 |
| Força nocional | `_forca_nocional` | 4.9.7.1.1 |
| Rigidez reduzida | `analyse`, `_scale_E` | 4.9.7.1.2 |

---

## 6. Resposta ao parecer do sênior (rodada 1 — 2026-07-06)

Parecer recebido confrontado, item a item, com o **texto autêntico da NBR
8800:2008** (PDF `pesquisa/aço/nbr8800_2008_1.pdf`). Verificação de método,
nunca de memória. Os 3 pontos acionáveis do parecer foram **rejeitados**: o
código já segue a norma. Citações abaixo para re-revisão.

### 6.1 — Vsd = Vnt + Vlt (parecer: "recompor por equilíbrio com M amplificado")

**Veredito: REJEITADO. Código correto (segue D.2.4).**

NBR 8800 **D.2.4** (pág. 129 do PDF), literal:
> "A força cortante solicitante de cálculo **pode ser tomada igual à da análise
> elástica de primeira ordem** [...] igual a: **Vsd = Vnt + Vlt**."

`estabilidade_b1b2._combina_grupo`, linha 141:
```python
v = mf_nt[e][iV] + mf_lt[e][iV]   # Vsd = Vnt + Vlt (D.2.4, sem amplificar)
```
Corresponde exatamente à norma (sem B2 no Vlt). O argumento do parecer (o
cortante em equilíbrio com os momentos amplificados cresce, Vsd = V_transv +
(M_A+M_B)/L) é fisicamente verdadeiro, porém é **conservadorismo além do exigido**;
a NBR 8800 dispensa explicitamente. **Não é erro de método.**
DECISÃO DO ENG.: adotar a recomposição por equilíbrio (mais conservadora) ou
manter D.2.4. Recomendação: **manter D.2.4** (norma; e Vsd não governa o perfil
neste galpão — flexão+normal governa).

### 6.2 — Rs = 0,85 → 1,0 (parecer: "sem pilares escorados, logo Rs = 1,0")

**Veredito: REJEITADO. Código correto. Mudar para 1,0 seria contra a norma e
a favor da insegurança (B2 menor).**

NBR 8800 **D.2.3** (pág. 129), literal:
> "Rs é um coeficiente de ajuste, igual a **0,85 nas estruturas onde o sistema
> resistente a ações horizontais é constituído apenas por subestruturas de
> contraventamento formadas por pórticos nos quais a estabilidade lateral é
> assegurada pela rigidez à flexão das barras e pela capacidade de transmissão
> de momentos das ligações** e igual a 1,0 para todas as outras estruturas."

O galpão é justamente um **pórtico de nós rígidos** (estabilidade lateral pela
rigidez à flexão das barras + ligações que transmitem momento) → **Rs = 0,85 é
o caso literal da norma**. `estabilidade_b1b2.RS = 0.85` (linha 35) está correto.
O parecer confundiu o **Rs da NBR 8800** (0,85 fixo para pórtico rígido) com o
**R_M do AISC 360** (fator de pilares escorados, R_M = 1 − 0,15·ΣP_escorado/ΣP_total).
São coeficientes distintos. A fórmula de leaning columns do parecer **não pertence
à NBR 8800**.

### 6.3 — ψ0 de Q com vento (parecer: "cobertura → ψ0 = 0, não combina com vento")

**Veredito: REJEITADO. Código correto.**

NBR 8800 **Tabela 2** (pág. 28), linha "Bibliotecas, arquivos, depósitos,
oficinas e garagens e **sobrecargas em coberturas (ver B.5.1)**": **ψ0 = 0,8**
(vento: ψ0 = 0,6).

`estabilidade_b1b2.COMBOS`, linha 42:
```python
"C3_vento_Gdesf": {"G": 1.25, "W2": 1.40, "Q": 0.8 * 1.50},   # γq·ψ0 = 1,50 × 0,8
```
γq·ψ0 = 1,50 × 0,8, exatamente a Tabela 2 para sobrecarga de cobertura como ação
secundária. Verificado **B.5.1** (pág. 121): define apenas a sobrecarga mínima
de 0,25 kN/m² — **não há** cláusula de não-simultaneidade com vento. O parecer
confundiu com a regra ASCE/AISC ("roof live não combina com vento"), que **não
existe na NBR 8800**.

### 6.4 — Confirmações do parecer (corretas, já implementadas)

- Solver de 1ª ordem (matriz de rigidez 6×6, FEF de UDL wL²/12): correto.
- B1 com **K = 1** e L real da barra: correto (D.2.2 + **4.9.6.2**, pág. 37 —
  "adoção do coeficiente de flambagem K igual a 1,0").
- Força nocional só de G/Q/ponte (vento não gera imperfeição de prumo), somada
  no sentido do vento: correto (**4.9.7.1.1**, pág. 37).
- B2 por andar único (galpão térreo): correto.

### 6.5 — Ações de código desta rodada

**Nenhuma alteração de código.** Os 3 pontos acionáveis contrariam a NBR 8800;
implementá-los introduziria erro (2×) ou conservadorismo não-normativo (1×,
item 6.1, à escolha do eng.). Itens da seção 4 "Pontos de conferência" #1
(Rs=0,85) e #5 (Vsd não amplificado) ficam **confirmados pela norma** acima.
Aguarda re-revisão do parecer com estas citações.

---

## 7. Homologação (rodada 2 — 2026-07-06)

**Status: ✅ APROVADO / HOMOLOGADO sob a NBR 8800:2008.**

O sênior confrontou a resposta da §6 com o texto literal da norma e homologou os
três itens contestados, mantendo o código original:

- **7.1 Vsd** — mantém `v = mf_nt[e][iV] + mf_lt[e][iV]`. D.2.4 dispensa a 2ª
  ordem no cortante; recompor por equilíbrio (V=M/L) seria rigor acima do legal.
- **7.2 Rs = 0,85** — mantém. D.2.3 fixa 0,85 para pórtico rígido não
  contraventado. 1,0 daria B2 irrealmente conservador e violaria a norma.
- **7.3 ψ0 = 0,8** — mantém `"Q": 0.8 * 1.50`. Tabela 2 crava ψ0=0,8 para
  sobrecarga de cobertura como ação secundária; NBR não abre a exceção do ASCE 7.

**Módulos homologados:** `frame2d.py`, `galpao_portico.py`, `estabilidade_b1b2.py`.
MAES (Anexo D) traduzido com rigor. Liberado para detalhamento e emissão de ART.
