# Revisão — Fundação (sapata isolada)

Documento para revisão do engenheiro sênior. Descreve o **método** de
dimensionamento da sapata, com as **citações exatas da NBR 6118:2014**
(PDF em `pesquisa/aço/`), a lógica do **envelope de combinações**, e as
**limitações/pendências** deixadas explícitas no memorial.

> CONCEITUAL — o framework calcula e dimensiona; o engenheiro responsável
> revisa e assina (ART). Nada aqui é projeto executivo.

Código: `framework/galpao_fw/fundacao_sapata.py`
Fluxo: `rodar_galpao.py` Gate 7 (`_casos_base_envelope` → `fs.dimensiona_sapata_env`).

Última atualização: 2026-07-07.

---

## 1. Escopo

Sapata **isolada** sob a reação de base de um pilar de galpão (N, V, M),
dividida em duas partes por rigor de método:

- **Parte A** — geotecnia/estabilidade (estática pura, independe de norma de
  concreto).
- **Parte B** — concreto armado, **método extraído da NBR 6118:2014**.

Fora de escopo (marcado PENDENTE): bloco sobre estacas/tubulão, sapata
flexível (punção), detalhamento executivo da armadura.

---

## 2. Parte A — geotecnia / estabilidade

Entrada: reação (N, V, M) por combinação; `sigma_solo_adm` (**input da
sondagem** — não é inventado, bloqueia o cálculo se não informado); `mu`,
`coesão`, peso específico do solo/concreto.

### 2.1 Tensão no solo (flexão composta)

Excentricidade `e = |M| / N`.

- **Núcleo** (`e ≤ L/6`) — contato total:
  `σ_max,min = N/(B·L) · (1 ± 6e/L)`
- **Borda** (`e > L/6`) — levantamento parcial, diagrama triangular:
  comprimento de contato `x = 3·(L/2 − e)`; `σ_max = 2N/(B·x)`.

Critério: `σ_max ≤ σ_solo,adm`.

### 2.2 Estabilidade

N estabilizante inclui o **peso próprio** da sapata + pedestal + reaterro.

- **Tombamento**: `FS = M_estab / M_tomb`, com
  `M_estab = N_tot · L/2` e `M_tomb = |V|·h_total + |M|`. Mínimo usual **1,5**.
- **Deslizamento**: `FS = (N_tot·μ + c·A) / |V|`. Mínimo usual **1,5**.

> Os fatores 1,5 são prática usual (ELU geotécnico) — **confirmar** com o
> critério adotado no projeto. Ficam como parâmetro do caso.

---

## 3. Parte B — concreto armado (NBR 6118:2014)

Todas as referências abaixo foram extraídas do PDF da norma.

### 3.1 Rigidez — item 22.6.1

Sapata **rígida** se, nas duas direções:
`h ≥ (a − a_p)/3` (a = dimensão da sapata; a_p = dimensão do pilar).

O código **aumenta h** até satisfazer a rigidez (só ajuda a Parte A). Sendo
rígida, o item **22.6.2.2** dispensa a verificação de **punção** (a sapata
fica dentro do cone) — resta a **compressão diagonal** (19.5.3.1).

> Se a geometria for **flexível** (`h < (a−a_p)/3`), a Parte B agora **verifica a
> punção** (19.5) no contorno C' a 2d — ver §10. A flexão não-uniforme (22.6.4.1.3)
> permanece simplificada (conservadora).

### 3.2 Flexão — itens 22.6.3 (modelo de flexão) + 17.2.2 (bloco retangular)

Momento na **face do pilar**, balanço `c = (a − a_p)/2`, pressão de cálculo
(conservadora) `σ_d` uniforme sobre o balanço:
`M_d = σ_d · largura · c²/2` (uma direção por vez).

Armadura por **bloco retangular** (17.2.2, fck ≤ 50 MPa → `λ = 0,8`,
`α_c = 0,85`):

```
μ    = M_d / (b·d²·α_c·f_cd)
x/d  = (1 − √(1 − 2μ)) / λ          (limite de ductilidade x/d ≤ 0,45, 14.6.4.3)
z    = d·(1 − 0,5·λ·x/d)
A_s  = M_d / (f_yd·z)
```

Altura útil `d = h − cobrimento − φ`. Armadura mínima `A_s,min = ρ_min(fck)·b·h`
com `ρ_min` da **Tabela 17.3** (piso 0,15% até fck 30; sobe para fck>30 —
0,164% em 35 … 0,208% em 50). Adota o valor de **viga** (mais exigente que o de
laje 2-direções `0,67·ρ_min`, 19.3.3.2/Tab.19.1) — cobre as duas classificações.
Ver §8.

### 3.3 Compressão diagonal — item 19.5.3.1

No **perímetro do pilar** `u0 = 2·(a_p,L + a_p,B)`:

```
τ_Sd  = F_d/(u0·d) + K·M_d/(Wp0·d)         (parcela de momento, 19.5.2.2)
τ_Rd2 = 0,27·α_v·f_cd ,   α_v = (1 − f_ck/250)  [f_ck em MPa]
```

`K` da **Tabela 19.2** (função de C1/C2, interpolado). `Wp0 = C1²/2 + C1·C2`
(módulo plástico do contorno do pilar). Critério `τ_Sd ≤ τ_Rd2`.

---

## 4. Envelope de combinações (por elemento)

**Fecha o gap** de usar uma única combinação. Cada verificação pega a
combinação ELU que a governa:

- **bearing (σ_solo)** → combinação de **N máximo** (gravitacional);
- **tombamento / deslizamento** → **N mínimo** com **M/V máximo** (uplift);
- **flexão** → maior `A_s` entre as combinações (adota o maior);
- **compressão diagonal** → maior `τ_Sd`.

Código: `_casos_base_envelope()` devolve todas as combinações ELU na base
(cruzamento W1/W2, com/sem ponte); `dimensiona_sapata_env()` adota a **menor
geometria da escada que passa TODAS as combinações**, e o memorial imprime a
combinação governante de cada verificação.

Exemplo (nf982, 20×10, ponte 100 kN): bearing governado por `C4_ponte`
(N = +205 kN, o caso que a abordagem antiga de “só max |M|” perdia, pois lá
N ≈ 1,3 kN); tombamento por `C2_uplift`. Sapata adotada 2,0 × 2,5 × 0,75 m,
rígida, util 0,27.

---

## 4a. Detalhamento das barras de flexão (arranjo)

Traduz o `A_s` requerido (por largura) num arranjo comercial: escolhe a bitola
cujo espaçamento cai na faixa prática [10; 20] cm; entre as válidas, prefere a
**menor bitola** (mais barras, melhor fissuração). `n = ⌈A_s/A_barra⌉` (≥ 2).

```python
_BITOLAS = [6.3, 8.0, 10.0, 12.5, 16.0, 20.0, 25.0]   # mm, CA-50
S_MIN = 0.10 ; S_MAX = 0.20        # faixa pratica (m) - A CONFIRMAR (18.3.2.2)

def detalha_barras(As_req, largura, cobrimento=0.05):
    b_util = max(largura - 2 * cobrimento, 0.0)
    if As_req <= 0 or b_util <= 0:
        return None
    melhor = None
    for phi in _BITOLAS:
        A1 = math.pi * (phi/1000)**2 / 4.0
        n = max(2, math.ceil(As_req / A1))
        s = b_util / (n - 1)
        if S_MIN - 1e-9 <= s <= S_MAX + 1e-9:      # na faixa
            if melhor is None or phi < melhor["phi"]:
                melhor = {"phi": phi, "n": n, "s": s, "As_ef": n*A1, "na_faixa": True}
    # fallback: se nenhuma na faixa, a menor bitola que ainda cabe (s <= S_MAX)
    return melhor or _fallback(...)
```

Ex. nf982: dir L → 19 φ12,5 c/11 cm ; dir B → 23 φ12,5 c/11 cm. Se o espaçamento
sair da faixa, o memorial emite `[!] espacamento fora de [10;20]cm - revisar`.

> **A CONFIRMAR**: S_MIN/S_MAX práticos e o espaçamento máximo normativo da
> armadura de flexão da sapata (detalhamento NBR 6118 18.3.2 / 20.1) — o código
> flaga em vez de fixar um s_max possivelmente incorreto.

## 4b. Quantitativo (concreto + aço)

`quantitativo(rA, rB, n_sapatas)` — por sapata × nº de sapatas
(`2 pilares × nº de pórticos`):

- **Concreto** (m³): `B·L·h` do bloco + pedestal.
- **Aço** (kg): `(A_s,L·(B−0,10) + A_s,B·(L−0,10)) · 7850` — A_s é área total
  por largura (já integra a quantidade de barras); comprimento aproximado das
  barras. Indicador `taxa` em kg/m³.

Aparece no memorial `gate7-fundacao.txt` e no DXF (nota sob o detalhe da base).
Ex. nf982: 10 sapatas, 38,0 m³ de concreto, 865 kg de aço (taxa ~23 kg/m³).

> Aproximação de **anteprojeto** (não substitui o detalhamento executivo, que
> define bitolas, espaçamentos, ganchos e traspasses).

## 5. Limitações / pendências (FLAGS no memorial)

1. `sigma_solo,adm` e parâmetros do solo (μ, coesão, γ) — **relatório de
   sondagem** (geotecnia). Bloqueia se não informado.
2. Sapata **flexível** — punção (19.5) **implementada** (§10): a Parte B verifica o
   contorno C' a 2d em vez de só flagar. A rígida dispensa (22.6.2.2). Flexão
   não-uniforme (22.6.4.1.3) segue simplificada (conservadora).
3. `A_s,min` = `ρ_min(fck)` da Tabela 17.3 (§8) — **resolvido** (era fixo 0,15%).
4. **Detalhamento/ancoragem** da armadura (gancho face a face 22.6.4.1.1;
   arranque 22.6.4.1.2) — projeto executivo.
5. Fatores de segurança 1,5 (tombamento/deslizamento) — confirmar critério.

---

## 5b. Representação no modelo 3D (FreeCAD)

`build_galpao` desenha a sapata (bloco B×L×h de concreto) + o pedestal sob cada
placa de base, parametrizados pelo spec (`SAPATA_MODEL`, via
`to_build_kwargs → configurar(sapata=...)`). O concreto entra no take-off com
**densidade própria** (2500 kg/m³) e **categoria separada** ("Sapatas/Pedestais
(concreto)") — não soma na tonelagem de aço. O auditor geométrico
(`verifica_conexoes`) confirma que a placa de base assenta sobre o pedestal/sapata.

Validado ao vivo (nf982): 10 sapatas + 10 pedestais, volume 3,75 m³/sapata,
0 conexões suspeitas, aço 16,7 t (concreto à parte, 93,75 t = 10×3,75×2,5).

## 6. Onde revisar no código

| Assunto | Função | Item NBR |
|---|---|---|
| Tensão no solo | `tensoes_solo` | flexão composta |
| Estabilidade | `estabilidade` | — |
| Escolha da geometria | `dimensiona_sapata_env` | — |
| Rigidez | `dimensiona_sapata_B` (bloco rigidez) | 22.6.1 / 22.6.2.2 |
| Flexão / armadura | `_armadura_flexao` | 22.6.3 / 17.2.2 / 14.6.4.3 |
| Compressão diagonal | `dimensiona_sapata_B` (bloco compr_diag) | 19.5.3.1 / Tab. 19.2 |
| Combinações na base | `rodar_galpao._casos_base_envelope` | `_combos_elu` |

---

## 7. Código-fonte das rotinas de cálculo (conferência matemática)

Cópia **verbatim** de `fundacao_sapata.py` (mantida em sincronia a cada
alteração). Unidades SI: m, kN (fck/fyk/σ em kN/m²). Confira aqui a matemática.

### Constantes

```python
FS_TOMB_MIN = 1.5          # tombamento (pratica usual p/ ELU geotecnico)
FS_DESL_MIN = 1.5          # deslizamento
GAMMA_C_CONCRETO = 25.0    # peso especifico concreto armado (kN/m3) - NBR 6120
GAMMA_SOLO = 18.0          # reaterro (kN/m3) - INPUT (sondagem); default flag

LAMBDA_BLOCO = 0.80        # 17.2.2 (fck<=50 MPa)
ALPHA_C = 0.85             # 17.2.2 (fck<=50 MPa)
XD_LIM = 0.45              # 14.6.4.3 limite de ductilidade x/d (fck<=50)
RHO_MIN = 0.0015           # piso absoluto 0,15% (17.3.5.2.1); rho_min(fck) p/ fck>30
_RHO_MIN_TAB = {20: 0.00150, 25: 0.00150, 30: 0.00150, 35: 0.00164,   # Tabela 17.3
                40: 0.00179, 45: 0.00194, 50: 0.00208}                 # (viga, CA-50)
RHO_ACO = 7850.0           # massa especifica do aco (kg/m3)

def rho_min(fck_MPa):
    """Tabela 17.3: piso 0,15% ate fck 30; interpola p/ fck>30 (a favor da seg.)."""
    pts = sorted(_RHO_MIN_TAB.items())
    if fck_MPa <= pts[0][0]:  return pts[0][1]
    if fck_MPa >= pts[-1][0]: return pts[-1][1]
    for (f0, r0), (f1, r1) in zip(pts, pts[1:]):
        if f0 <= fck_MPa <= f1:
            return r0 + (r1 - r0) * (fck_MPa - f0) / (f1 - f0)
    return pts[-1][1]
_K_TAB = [(0.5, 0.45), (1.0, 0.60), (2.0, 0.70), (3.0, 0.80)]  # Tabela 19.2
```

### Parte A — tensão no solo (flexão composta)

```python
def tensoes_solo(N, M, B, L):
    A = B * L
    if N <= 0:
        return None, None, "sem compressao (N<=0)", 0.0
    e = abs(M) / N
    if e <= L / 6.0 + 1e-12:                       # dentro do nucleo: contato total
        sig_max = N / A * (1.0 + 6.0 * e / L)
        sig_min = N / A * (1.0 - 6.0 * e / L)
        return sig_max, sig_min, "nucleo (contato total)", L
    # fora do nucleo: parte da sapata levanta, diagrama triangular.
    # comprimento de contato x = 3*(L/2 - e); sigma_max = 2N/(B*x).
    x = 3.0 * (L / 2.0 - e)
    if x <= 0:
        return None, 0.0, "instavel (resultante fora da base)", 0.0
    sig_max = 2.0 * N / (B * x)
    return sig_max, 0.0, "borda (levantamento parcial)", x
```

### Parte A — peso próprio e estabilidade

```python
def peso_proprio(B, L, h, h_reaterro=0.0, d_ped=0.0, b_ped=0.0, h_ped=0.0):
    p_sapata = B * L * h * GAMMA_C_CONCRETO
    a_ped = (d_ped * b_ped) if (d_ped and b_ped) else 0.0
    p_ped = a_ped * h_ped * GAMMA_C_CONCRETO
    p_solo = max(B * L - a_ped, 0.0) * h_reaterro * GAMMA_SOLO
    return p_sapata + p_ped + p_solo, {...}


def estabilidade(N, V, M, B, L, h, mu, coesao=0.0, h_reaterro=0.0,
                 d_ped=0.0, b_ped=0.0, h_ped=0.0):
    Pp, det = peso_proprio(B, L, h, h_reaterro, d_ped, b_ped, h_ped)
    N_tot = N + Pp
    h_tot = h + h_ped                              # altura ate o topo do pedestal
    M_tomb = abs(V) * h_tot + abs(M)
    M_est = N_tot * L / 2.0
    fs_tomb = (M_est / M_tomb) if M_tomb > 0 else float("inf")
    # atrito ~ N_tot; ADESAO (coesao) so na area de contato efetiva B*x (uplift)
    e = abs(M) / N_tot if N_tot > 0 else 0.0
    x_cont = L if e <= L / 6.0 else max(3.0 * (L / 2.0 - e), 0.0)
    A_ef = B * min(x_cont, L)                       # = B*L com contato total
    resist = N_tot * mu + coesao * A_ef
    fs_desl = (resist / abs(V)) if abs(V) > 0 else float("inf")
    return {"N_tot": N_tot, "Pp": Pp, "M_tomb": M_tomb, "M_est": M_est, "A_ef": A_ef,
            "fs_tomb": fs_tomb, "fs_desl": fs_desl, "h_tot": h_tot, ...}
```

Critérios (em `verifica_sapata_A`): `ok_solo = σ_max ≤ σ_adm` ;
`ok_tomb = fs_tomb ≥ 1,5` ; `ok_desl = fs_desl ≥ 1,5` ;
`ok_contato = x_contato ≥ L/3` (resultante no terço médio).

### Parte B — coeficiente K (Tabela 19.2) e armadura de flexão

```python
def _K_puncao(c1_c2):
    if c1_c2 <= _K_TAB[0][0]:
        return _K_TAB[0][1]
    if c1_c2 >= _K_TAB[-1][0]:
        return _K_TAB[-1][1]
    for (r0, k0), (r1, k1) in zip(_K_TAB, _K_TAB[1:]):
        if r0 <= c1_c2 <= r1:
            return k0 + (k1 - k0) * (c1_c2 - r0) / (r1 - r0)
    return _K_TAB[-1][1]


def _armadura_flexao(M_d, b, d, fck, fyk):
    fcd = fck / 1.4
    fyd = fyk / 1.15
    if M_d <= 0:
        return 0.0, 0.0, d, True
    mu = M_d / (b * d * d * ALPHA_C * fcd)
    disc = 1.0 - 2.0 * mu
    if disc < 0:                                  # secao insuficiente a flexao
        return None, 1.0 / LAMBDA_BLOCO, 0.0, False
    x_d = (1.0 - math.sqrt(disc)) / LAMBDA_BLOCO
    z = d * (1.0 - 0.5 * LAMBDA_BLOCO * x_d)
    As = M_d / (fyd * z)
    return As, x_d, z, (x_d <= XD_LIM + 1e-9)
```

### Parte B — verificação completa (rigidez + flexão + compressão diagonal)

```python
def dimensiona_sapata_B(caso, r_A):
    B, L, h = r_A["B"], r_A["L"], r_A["h"]
    ap_L = caso.get("d_ped") or caso.get("ap_L") or 0.30    # pilar // L
    ap_B = caso.get("b_ped") or caso.get("ap_B") or 0.30    # pilar // B
    fck, fyk = caso["fck"], caso["fyk"]
    fck_MPa = fck / 1000.0
    cob = caso.get("cobrimento", 0.05)             # contato c/ solo: >= 5 cm (7.4)
    phi = caso.get("phi_barra", 0.0125)
    gf = caso.get("gamma_f", 1.4)
    d = h - cob - phi                              # altura util (2 camadas ort.)

    # 1) RIGIDEZ (22.6.1): h >= (a - ap)/3 nas duas direcoes
    rig_L = h >= (L - ap_L) / 3.0 - 1e-9
    rig_B = h >= (B - ap_B) / 3.0 - 1e-9

    # esforcos de calculo (ELU); pressao de flexao = so a reacao do pilar.
    N_d, V_d, M_d0 = gf * caso["N"], gf * caso["V"], gf * caso["M"]
    sig_max_d, _, _, _ = tensoes_solo(N_d, M_d0, B, L)
    if sig_max_d is None:
        sig_max_d = N_d / (B * L)

    # 2) FLEXAO (22.6.3 + 17.2.2): balanco a partir da face do pilar
    c_L = max((L - ap_L) / 2.0, 0.0)               # balanco na direcao L
    c_B = max((B - ap_B) / 2.0, 0.0)               # balanco na direcao B
    M_dL = sig_max_d * B * c_L ** 2 / 2.0          # momento (barras // L), largura B
    M_dB = sig_max_d * L * c_B ** 2 / 2.0          # momento (barras // B), largura L
    As_L, xdL, zL, okL = _armadura_flexao(M_dL, B, d, fck, fyk)
    As_B, xdB, zB, okB = _armadura_flexao(M_dB, L, d, fck, fyk)
    rho = rho_min(fck_MPa)                          # Tabela 17.3 (sobe p/ fck>30)
    As_min_L = rho * B * h                          # As,min por largura (17.3.5.2)
    As_min_B = rho * L * h
    # As_adot = max(As_flexao, As_min)  em cada direcao

    # 3) COMPRESSAO DIAGONAL no perimetro do pilar (19.5.3.1)
    fcd = fck / 1.4
    alpha_v = 1.0 - fck_MPa / 250.0
    tau_rd2 = 0.27 * alpha_v * fcd
    u0 = 2.0 * (ap_L + ap_B)                        # perimetro do pilar
    C1, C2 = ap_L, ap_B                             # C1 // excentricidade (plano do M)
    K = _K_puncao(C1 / C2 if C2 > 0 else 1.0)
    Wp0 = C1 ** 2 / 2.0 + C1 * C2                   # modulo plastico do contorno u0
    tau_sd = N_d / (u0 * d) + (K * abs(M_d0) / (Wp0 * d) if Wp0 > 0 else 0.0)
    # OK_B = rigida and (x/d<=lim nas 2 dir) and (tau_sd <= tau_rd2)
```

### Envelope de combinações (núcleo do laço)

```python
def dimensiona_sapata_env(caso_base, casos, escada=None):
    # ... para cada geometria (B,L,h0) da escada:
    h = max(h0, math.ceil(max(L - ap_L, B - ap_B) / 3.0 / 0.05) * 0.05)  # rigida
    # Parte A: pior u_solo / menor FS entre TODAS as combinacoes
    for (nm, N, V, M) in casos:
        c = dict(caso_base); c.update(N=N, V=V, M=M, B=B, L=L, h=h)
        rA = verifica_sapata_A(c)
        # guarda o maior u_solo (bearing = N max), menor fs_tomb, menor fs_desl
    # Parte B: pior utilizacao e MAIOR As entre TODAS as combinacoes
    for (nm, N, V, M) in casos:
        rB = dimensiona_sapata_B({**caso_base, "N": N, "V": V, "M": M},
                                 {"B": B, "L": L, "h": h})
        As_L = max(As_L, rB["flexao_L"]["As_adot"])   # adota o MAIOR As
        As_B = max(As_B, rB["flexao_B"]["As_adot"])
        # guarda o maior tau_sd (compr. diagonal)
    # adota a MENOR geometria cujo (todosA and okB) for verdadeiro.
```

### Quantitativo (concreto + aço)

```python
def quantitativo(rA, rB, n_sapatas=1, h_ped=0.5):
    B, L, h = rA["B"], rA["L"], rA["h"]
    ap_L = rB.get("ap_L", 0.30); ap_B = rB.get("ap_B", 0.30)
    vol_conc = B * L * h + ap_L * ap_B * h_ped     # bloco + pedestal
    As_L = rB["flexao_L"]["As_adot"]               # m2 (por largura B)
    As_B = rB["flexao_B"]["As_adot"]               # m2 (por largura L)
    vol_aco = As_L * (B - 0.10) + As_B * (L - 0.10)   # As x comprimento das barras
    massa_aco = vol_aco * RHO_ACO
    # taxa = massa_aco / vol_conc  (kg/m3, indicador)
```

---

## 8. Resposta ao parecer do sênior (rodada 1 — 2026-07-07)

Parecer **sem erro de método** — Parte A e Parte B corretas. Um ponto acionável
(`ρ_min` × fck) e três notas conservadoras aceitas. Todos os pontos duros
conferidos contra o **PDF da NBR 6118:2014** e cruzados com Carvalho & Figueiredo
(Quadro 4.2 = Tabela 17.3) — **não de memória**.

### 8.1 — `RHO_MIN` fixo em 0,15% — PARCIALMENTE procedente → MELHORIA APLICADA

O parecer alega que `RHO_MIN = 0,0015` subdimensiona a armadura mínima para
fck>30 MPa. Verificado contra a norma:

- **17.3.5.2.1** (vigas): piso absoluto **0,15%**; **Tabela 17.3** sobe com fck.
  Valores conferidos na fonte: fck 20/25/30 → **0,150%**; 35 → **0,164%**;
  40 → **0,179%**; 45 → **0,194%**; 50 → **0,208%** (CA-50, γc=1,4, d/h=0,8).
- **19.3.3.2 + Tabela 19.1** (lajes): a sapata rígida flexiona nas **duas
  direções** → "armadura positiva de lajes armadas nas duas direções:
  **ρs ≥ 0,67·ρ_min**". Mesmo em fck 50: 0,67×0,208% = **0,139% < 0,15%**. Ou
  seja, **como laje** o código já era conservador em toda a faixa 20–50 (o parecer
  erra ao supor subdimensionamento nesta classificação).
- **Como viga** (ρ_min cheio): 0,15% fica **abaixo** para fck>30 — real canto
  não-conservador.

**Fix (strict-safe):** `RHO_MIN` vira `rho_min(fck)` pela **Tabela 17.3** (valor de
viga, o mais exigente das duas classificações). Para **fck≤30 devolve 0,0015**
(idêntico ao anterior → **sem regressão**, o exemplo fck 25 mantém As_L=18,0 cm²
porque ali a flexão governa, não o mínimo); para **fck>30 sobe** conforme a tabela,
com interpolação linear entre os pontos tabelados. Remove o único canto
não-conservador seja qual for a classificação adotada pelo revisor. Selftest #10
adicionado (piso 0,15% até 30; 0,164% em 35; 0,208% em 50; extremos e interpolação).

> Projeto real do galpão usa fck 25–30 → 0,15% é **exato** (piso absoluto),
> logo **nenhum quantitativo já emitido muda**. A melhoria blinda fck>30 futuro.

### 8.2 — Pressão σ_max uniforme no balanço (flexão) — conservador, mantido

O parecer nota (§2) que a pressão sob o balanço é **trapezoidal** na presença de
M, e o código usa `σ_max_d` **uniforme** sobre todo o balanço (`M_dL = σ_max_d·B·c²/2`).
Correto: é simplificação **a favor da segurança** (integra o trapézio pelo seu
valor máximo) → leve superdimensionamento de As em sapatas de grande
excentricidade. Escolha válida e comum para envelope de anteprojeto. Sem alteração.

### 8.3 — Quantitativo de aço sem gancho (~10–15% baixo) — nota de orçamento, mantido

O parecer aponta (§3) que `vol_aco` conta barras retas (desconta só 5 cm de
cobrimento/lado), sem o comprimento dos **ganchos/ancoragem** (22.6.4.1.1) →
quantitativo ~10–15% subestimado. Verdade, e **já sinalizado** no memorial como
"Aproximação de anteprojeto" (§4b). Detalhamento executivo define ganchos,
traspasses e o consumo final. É indicador, não lista de corte. Sem alteração de
método (registrado como margem de orçamento).

### 8.4 — Confirmações verificadas contra o PDF

- **Núcleo** `σ = N/A·(1±6e/L)` (e≤L/6) e **borda** triangular `x=3·(L/2−e)`,
  `σ_max=2N/(B·x)` — flexão composta exata (Alonso). ✅
- **Estabilidade**: braço de tombamento com `h_tot = h + h_ped` (inclui V);
  FS 1,5 usual (ELU geotécnico / NBR 6122). ✅
- **Rigidez 22.6.1** `h ≥ (a−a_p)/3` → dispensa punção (22.6.2.2). ✅
- **Bloco retangular 17.2.2** (λ=0,8, α_c=0,85, fck≤50); x/d ≤ 0,45 (14.6.4.3);
  `_armadura_flexao` reversível (selftest #5). ✅
- **Compressão diagonal 19.5.3.1** `τ_Rd2 = 0,27·α_v·f_cd`, `α_v = 1−fck/250`;
  parcela de M por `K` (Tabela 19.2) e `Wp0`. ✅
- **S_MAX = 0,20 m** (20.1: menor de 20 cm ou 2h; sapata rígida tem h alto →
  20 cm governa). ✅

### 8.5 — Não-regressão

Selftest `fundacao_sapata` OK (10 casos, +#10 `rho_min`, +#3b coesão/A_ef).
Exemplo fck 25 → sapata 2,00×2,00×0,60 m, As_L=As_B=18,0 cm², compr.diag u=0,18,
FS_desl=2,79 — **inalterado**. Envelope mantém governantes.

---

## 9. Homologação (rodada 2 — 2026-07-07)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 6118:2014 (+ estabilidade geotécnica).**

Sênior homologou a Parte A e a Parte B, confirmando: flexão composta (núcleo +
triangular exato de Alonso), rigidez 22.6.1, bloco retangular 17.2.2, compressão
diagonal 19.5.3.1 (`Wp0`, `K` Tab.19.2), e a correção do `ρ_min(fck)` (§8.1).

**Ponto novo levantado na homologação (§1, deslizamento) — MELHORIA APLICADA:**
o sênior notou que `resist = N_tot·μ + coesao·(B·L)` usa a **área total** mesmo
sob levantamento parcial (e>L/6), quando só `B·x` toca o solo — otimista se
`c>0`. Aceitou como abstração, mas por ser canto **não-conservador** real, foi
corrigido (strict-safe): o termo de **atrito** segue `N_tot·μ` (independe de área,
a resultante normal passa pelo bulbo de contato), e a **adesão** passa a atuar só
na **área efetiva** `A_ef = B·min(x,L)` (Velloso & Lopes). Contato total (e≤L/6):
`x=L` → `A_ef=B·L` → **idêntico ao anterior** (sem regressão; exemplo coesão=0
inalterado). Sob uplift com `c>0`: reduz a resistência ao deslizamento → a favor
da segurança. Selftest #3b adicionado.

Notas conservadoras aceitas sem alteração: pressão σ_max uniforme no balanço
(§8.2), `d = h − cob − φ` (centroide na interface das camadas cruzadas),
quantitativo de aço sem ganchos (~10–15%, marcador de anteprojeto, §8.3).

Módulo `fundacao_sapata.py` liberado. **1 melhoria de código nesta rodada**
(adesão na área efetiva) + a de r1 (`ρ_min(fck)`).

---

## 10. Punção da sapata flexível (NBR 6118 19.5) — feature adicionada 2026-07-07

> **STATUS: ✅ HOMOLOGADO (2026-07-07)** — sênior conferiu: contorno C' = soma de
> Minkowski (`u=2(C1+C2)+4πd`, `A_C'=C1·C2+4d(C1+C2)+4πd²` — "cálculo exato"),
> alívio `F_Sd,ef=N_d−σ·A_C'` correto, e o isolamento de unidades híbridas da
> `τ_Rd1` (d→cm via `d*100`, fck→MPa via `/1000`, ×1000 devolve ao SI) — "lógica
> brilhante". Sem vício de modelagem. Liberado.

Fecha a pendência FLAG 2 (antes: código forçava rígida e só emitia flag). Agora a
Parte B, quando a sapata é **flexível** (`h < (a−a_p)/3`), **verifica a punção** no
contorno crítico C' a **2d** do pilar; a **rígida** continua dispensada (22.6.2.2 —
fica dentro do cone, a compressão diagonal 19.5.3.1 já a cobre).

Fórmulas extraídas do PDF (não de memória):

- **19.5.2.1** — `τ_Sd = F_Sd,ef / (u·d)`, `u` = perímetro de C' a 2d
  (`u = 2(C1+C2) + 2π·2d`, cantos arredondados).
- **19.5.3.2** — `τ_Rd1 = 0,13·(1+√(20/d))·(100·ρ·f_ck)^(1/3) + 0,10·σ_cp`
  (`d` em cm, `f_ck` em MPa; `ρ = √(ρ_x·ρ_y)`; `σ_cp = 0` sem protensão/normal →
  conservador).

**Modelo de sapata (alívio da reação):** a reação do solo **dentro de C'** não
atravessa a superfície crítica, então alivia a força de punção:
`F_Sd,ef = N_d − σ·A_C'`, com `σ = N_d/(B·L)` (pressão média, equilíbrio) e
`A_C' = C1·C2 + 2(C1+C2)·2d + π·(2d)²` (soma de Minkowski do pilar com disco de raio
2d). `ρ_x = As_L/(B·d)`, `ρ_y = As_B/(L·d)` (a largura da faixa cancela).

```python
def puncao_sapata(N_d, B, L, ap_L, ap_B, d, fck, As_L, As_B):
    C1, C2 = ap_L, ap_B
    u = 2.0*(C1+C2) + 2.0*math.pi*(2.0*d)                 # contorno C' a 2d
    A_cp = C1*C2 + 2.0*(C1+C2)*(2.0*d) + math.pi*(2.0*d)**2
    sig = N_d/(B*L)                                       # pressao media
    F_ef = max(N_d - sig*min(A_cp, B*L), 0.0)            # alivio da reacao em C'
    tau_sd = F_ef/(u*d)
    rho = math.sqrt(max(As_L/(B*d),0)*max(As_B/(L*d),0))
    tau_rd1 = 0.13*(1+math.sqrt(20/(d*100)))*(100*rho*fck/1000.0)**(1/3)*1000.0
    return {"tau_sd": tau_sd, "tau_rd1": tau_rd1, "u_punc": tau_sd/tau_rd1,
            "ok": tau_sd <= tau_rd1 + 1e-9, ...}
```

Integração em `dimensiona_sapata_B`: `if rigida: OK_B = flexao and compr_diag ;
else: OK_B = flexao and compr_diag and puncao`. Selftest #11 confere `u`, `τ_Rd1`,
o alívio `0 < F_ef < N_d`, e que uma sapata flexível roda a punção (não só flag).

**Nota de escopo:** o auto-sizer (`dimensiona_sapata_env`) **ainda sobe h até a
rígida** — a punção é o caminho de verificação para geometrias flexíveis (uso
direto, ou quando h for limitado), não a preferência do envelope. Não-regressivo: o
exemplo de referência (rígido) mantém As e utilização inalterados.

---

## 11. Recalque da sapata (ELS geotécnico, NBR 6122) — feature adicionada 2026-07-07

> **STATUS: ✅ HOMOLOGADO (2026-07-07)** — sênior confirmou a solução analítica de
> fundação rasa sobre semiespaço elástico (Perloff 1975) e que rodar a verificação
> **apenas** com `Es_solo` consistente "evita fabricação de parâmetros e preserva a
> premissa Ask, Do Not Invent". Liberado.

Fecha a lacuna do **deslocamento** da fundação (o módulo só tinha capacidade de
carga + estabilidade, não deformação). A NBR 6122 exige a verificação de recalque
mas **remete a métodos geotécnicos** — usou-se o **recalque imediato/elástico pela
Teoria da Elasticidade** (Veloso & Lopes; Perloff 1975), extraído do PDF:

```
rho = q_liq · B · (1 − ν²) · Iw / Es
```

- `q_liq` = pressão **líquida de serviço** (kN/m²) = N_serv/(B·L) − sobrecarga;
- `B` = **menor** dimensão da sapata; `Es` = módulo de deformabilidade do solo
  (INPUT sondagem); `ν` = Poisson do solo; `Iw` = fator de forma/rigidez.
- **Iw (Tab. 5.1 Perloff, lido do PDF):** rígido — círculo **0,79**, quadrado
  **0,88**; retângulo cresce com L/B (o engenheiro confirma pela relação L/B).

**Ask, Do Not Invent:** `Es_solo`, `nu_solo`, `Iw`, `recalque_adm_mm` são dados
geotécnicos — **INPUT**. Sem `Es_solo`, o recalque **não é calculado** (FLAG,
informativo), e o `OK_A` não é afetado; **com** `Es_solo`, entra no `OK_A` (só
reprova se exceder o admissível). Carga de **serviço**: usa `N_serv` (senão `N`,
com o envelope ELU sendo conservador — o engenheiro passa a combinação de serviço).

Ex. (sapata 2,0×2,0, N_serv 49 kN, Es 20 MPa, ν 0,3, Iw 0,88): `q=12,3 kN/m²` →
`ρ=0,98 mm ≤ 25 mm` (OK). Selftest #12 confere a fórmula, `Es=0→None`, e o
gate por `Es_solo`. Não-regressivo: exemplo sem `Es_solo` inalterado.

> **Limites:** (1) recalque **imediato/elástico** (meio homogêneo, espessura
> infinita) — solos estratificados pedem **Steinbrenner** (soma de camadas) e o
> **adensamento** (argilas) fica fora; (2) `recalque_adm` (default 25 mm total) e
> o **diferencial entre pilares** (≤15 mm, Tabela C.1 da NBR 8800, já no módulo de
> ponte) dependem da sensibilidade da estrutura — confirmar. Es via SPT (correlações)
> é do relatório de sondagem, não inventado aqui.
