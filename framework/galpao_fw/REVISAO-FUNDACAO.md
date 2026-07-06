# Revisão — Fundação (sapata isolada)

Documento para revisão do engenheiro sênior. Descreve o **método** de
dimensionamento da sapata, com as **citações exatas da NBR 6118:2014**
(PDF em `pesquisa/aço/`), a lógica do **envelope de combinações**, e as
**limitações/pendências** deixadas explícitas no memorial.

> CONCEITUAL — o framework calcula e dimensiona; o engenheiro responsável
> revisa e assina (ART). Nada aqui é projeto executivo.

Código: `framework/galpao_fw/fundacao_sapata.py`
Fluxo: `rodar_galpao.py` Gate 7 (`_casos_base_envelope` → `fs.dimensiona_sapata_env`).

Última atualização: 2026-07-06.

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

> Se a geometria não puder ser rígida, o memorial emite FLAG exigindo punção
> (19.5) e flexão não-uniforme (22.6.4.1.3) — **PENDENTE**.

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

Altura útil `d = h − cobrimento − φ`. Armadura mínima `A_s,min = 0,15%·b·h`
(17.3.5.2 — **confirmar** para o fck adotado).

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
2. Sapata **flexível** exige punção (19.5) — PENDENTE (o código força rígida).
3. `A_s,min` = 0,15% (17.3.5.2) — confirmar para o fck.
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
RHO_MIN = 0.0015           # 17.3.5.2 taxa minima (fck<=~30) - A CONFIRMAR p/ fck
RHO_ACO = 7850.0           # massa especifica do aco (kg/m3)
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
    resist = N_tot * mu + coesao * (B * L)
    fs_desl = (resist / abs(V)) if abs(V) > 0 else float("inf")
    return {"N_tot": N_tot, "Pp": Pp, "M_tomb": M_tomb, "M_est": M_est,
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
    As_min_L = RHO_MIN * B * h                     # As,min por largura (17.3.5.2)
    As_min_B = RHO_MIN * L * h
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
