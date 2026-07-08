# Revisão — Base (placa + chumbadores)

Conferência do sênior. Liga o pilar à fundação: placa de base + chumbadores sob
**N, V, M**. Base rotulada (M = 0) ou engastada (M ≠ 0). **NBR 8800** (6.3/6.6)
+ **AISC Design Guide 1** (método da excentricidade / espessura da placa).

Código: `base_chumbador.py`. Última atualização: 2026-07-06.
Ver também a fundação de concreto: [REVISAO-FUNDACAO.md](REVISAO-FUNDACAO.md).

---

## 1. Pressão de contato no concreto (NBR 8800 6.6.5)

```python
GC = 1.40 ; GN = 1.40
def sigma_c_rd(fck, A1, A2):
    val = fck / (GC * GN) * math.sqrt(A2 / A1)
    return min(val, fck)
```

---

## 2. Placa sob N+M — método da excentricidade (AISC DG1)

`e = M/N`. Pequena excentricidade (`e ≤ L/6`): sem tração. Grande: bloco de
compressão **plastificado** em σc,Rd; equilíbrio resolve o comprimento Y do
bloco e a tração T nos chumbadores.

```python
# C·(d_anchor − Y/2) = N·(d_anchor − L/2) + M ;  C = sig_rd·B·Y
q = sig_rd * B
a = -q / 2.0
b = q * d_anchor
c = -(N * (d_anchor - L / 2.0) + abs(M))
disc = b * b - 4 * a * c
Y = (-b + math.sqrt(disc)) / (2 * a)      # (ou a outra raiz se 0<Y<=L)
C = q * Y ; T = C - N
```

Uplift puro (N ≤ 0): `T = |N| + |M|/d_anchor`. Critério geométrico: `Y ≤ L`.

---

## 3. Chumbadores (NBR 8800 6.3.3)

`Ft,Rd = Abe·fub/γa2` (6.3.3.1) ; `Fv,Rd = 0,4·Ab·fub/γa2` (6.3.3.2, rosca no
plano) ; interação `(Ft/FtRd)² + (Fv/FvRd)² ≤ 1` (6.3.3.4). γa2 = 1,35 ;
Abe = 0,75·Ab.

```python
Ft_sd = T / n_t          # tracao por chumbador tracionado
Fv_sd = |V| / n          # cisalhamento distribuido em todos
interacao = (Ft_sd/Ft_rd)**2 + (Fv_sd/Fv_rd)**2
```

---

## 4. Espessura da placa (AISC DG1 3.1.3) — maior dos dois lados

**Lado comprimido** (bloco de contato Y em balanço até a face da mesa):

```python
x_face = max(L/2 - d_col/2, 0.0)
if Ybear >= x_face:  m_comp = p * x_face**2 / 2.0
else:                m_comp = p * Ybear * (x_face - Ybear/2.0)
t_comp = math.sqrt(4 * m_comp * GA1 / fy_p)      # GA1 = 1,10
```

**Lado tracionado** (linha de dobra, braço do chumbador até a mesa):

```python
m_trac = (T / beff) * x_t
t_trac = math.sqrt(4 * m_trac * GA1 / fy_p)
t_req = max(t_comp, t_trac)
```

`dimensiona_base` varia (B, L, db, n) na escada e **deriva a espessura** de
t_req (chapa padrão ≥ t_req) — a espessura não entra na escada porque crescer a
placa aumenta o balanço e o próprio t_req.

---

## 5. Pontos de conferência (FLAGS)

1. **Bloco plastificado** em σc,Rd na grande excentricidade (u_concreto = 1,0 por
   construção; o critério real é geométrico Y ≤ L) — conferir a hipótese.
2. **Cone de arrancamento / ancoragem** do chumbador no concreto (NBR 6118/ACI
   318) — **NÃO** verificado aqui (é do projeto de fundação) — FLAG.
3. **Abe = 0,75·Ab** ; **γa2 = 1,35**.
4. Cisalhamento distribuído em **todos** os chumbadores; tração só nos tracionados.
5. Usa o par de esforços que governa a placa (max |M|) — ver nota de envelope na
   [REVISAO-FUNDACAO.md](REVISAO-FUNDACAO.md) §5.

---

## 6. Onde revisar

| Assunto | Função | Item |
|---|---|---|
| Pressão concreto | `sigma_c_rd` | NBR 8800 6.6.5 |
| Placa N+M | `placa_sob_NM` | AISC DG1 |
| Chumbador | `ft_rd_chumbador` / `fv_rd_chumbador` | 6.3.3 |
| Espessura | `verifica_base` (bloco t) | AISC DG1 3.1.3 |
| Escada | `dimensiona_base` | — |

---

## 7. Resposta ao parecer do sênior (rodada 1 — 2026-07-06)

### 7.1 — Pressão no concreto: fator 0,85 e teto — IMPROCEDENTE

**Veredito: REJEITADO. Código já correto (segue NBR 8800 6.6.5 literal).**

O parecer pediu inserir `0,85` e trocar o teto de `fck` por `2×0,85·fck/(γc·γn)`,
alegando 17 % de superestimativa. Confrontado com o texto autêntico da
**NBR 8800:2008 item 6.6.5** ("Apoios de concreto", pág. 100 do PDF), literal:

> "A tensão resistente de cálculo à pressão de contato, na área A1 da região
> carregada sob placas de apoio [...]:
> **σc,Rd = (fck)/(γc·γn)·√(A2/A1) ≤ fck** ; γn = 1,40"

Não há fator 0,85, e o teto é **fck** (não 2×). O código:
```python
val = fck / (GC * GN) * math.sqrt(A2 / A1)   # GC=γc=1,40 ; GN=γn=1,40
return min(val, fck)
```
corresponde **exatamente** à norma (denominador γc·γn = 1,96). O parecer confundiu
a NBR 8800 6.6.5 com a **compressão localizada da NBR 6118** (que traz 0,85·fcd e
teto 3·fcd/√ etc.) ou com o **AISC** (0,85·f'c·√(A2/A1) ≤ 1,7·f'c). São normas e
filosofias distintas — a NBR 8800 já embute o conservadorismo nos dois γ (1,40 ×
1,40). O item "6.6.5.2" citado no parecer não existe (6.6.5 tem alíneas a/b).
**Nenhuma alteração de código.**

### 7.2 — Confirmações do parecer (corretas, verificadas contra o PDF)

- **Placa N+M** (AISC DG1): equilíbrio `C·(d_anchor − Y/2) = N·(d_anchor − L/2)
  + |M|`, quadrática `a=−q/2, b=q·d_anchor, c=−(...)`, menor raiz positiva de Y.
  Uplift `N≤0`: `T=|N|+|M|/d_anchor` (conservador). ✅
- **Chumbadores** (NBR 8800 6.3.3): `Ft,Rd = 0,75·Ab·fub/γa2`, `Fv,Rd =
  0,4(ou 0,5)·Ab·fub/γa2`, γa2=1,35; interação `(Ft/FtRd)²+(Fv/FvRd)² ≤ 1`. ✅
- **Espessura** (AISC DG1 3.1.3): `t = √(4·m·γa1/fy)` (reverte Z=t²/4). ✅

### 7.3 — Pergunta do parecer (export para a equipe de concreto)

O cone de arrancamento / ancoragem (NBR 6118 / ACI 318) já é **FLAG delegada à
fundação** (§5.2). `verifica_base` retorna a **tração T por chumbador** e a
geometria (B, L, d_anchor, bitola, disposição) — dados que alimentam o
detalhamento da armadura de fretagem / comprimento de embutimento no pedestal
(módulo `fundacao_sapata`). Integração explícita fica registrada como pendência
de projeto (sem alteração de método nesta rodada).

### 7.4 — Não-regressão

`base_chumbador` selftest OK; sem alteração de código. Aguarda re-revisão.

---

## 8. Homologação (rodada 2 — 2026-07-07)

**Status: ✅ VALIDADO / HOMOLOGADO sob NBR 8800:2008 + AISC DG1.**

Sênior concordou com a rejeição do 0,85 — reconhecido como "vício comum de
projetistas que aplicam a NBR 6118 (concreto armado puro) ou o ACI 318 diretamente
em bases metálicas". Confirmado: a NBR 8800 6.6.5 embute o conservadorismo no
denominador `γc·γn = 1,40 × 1,40 = 1,96`; o `min(val, fck)` é ~2 % mais conservador
que o teto normativo real (√(A2/A1) ≤ 2 → 1,02·fck), boa prática. **Nenhuma
alteração de código.**

Confirmados contra o método:
- **Placa N+M** (grande excentricidade): equilíbrio de momentos na linha de
  chumbadores tracionados → quadrática `a=−q/2, b=q·d_anchor`, menor raiz positiva
  de Y (bloco de contato real). Uplift `N≤0`: `T=|N|+|M|/d_anchor` envoltória
  conservadora padrão. ✅
- **Chumbadores** (6.3.3.4): interação quadrática `(Ft/FtRd)²+(Fv/FvRd)² ≤ 1`. ✅
- **Espessura** (AISC DG1 3.1.3): reverte `Z=t²/4` → `t=√(4·m·γa1/fy)`; braços
  `x_face` (aba comprimida em balanço) e `x_t` (lado tracionado). ✅

Módulo `base_chumbador.py` liberado.

---

## 9. Ancoragem do chumbador no concreto (NBR 6118 9.4.2) — feature adicionada 2026-07-07

> **STATUS: ✅ HOMOLOGADO (2026-07-07)** — sênior refez o exemplo (HEA200,
> Ft,Sd=63,2 kN, φ20 liso, fck25): `fctm=2,565 → fctk,inf=1,795 → fctd=1,282 →
> fbd=1,28 MPa` (exato); `lb=(φ/4)(fyd/fbd)` com `fyd=250/1,15=217,4 MPa` → 848 mm;
> `lb,nec=0,7·848=593 mm` (todos batem). Confirmou o **caráter informativo** (barra
> lisa tem aderência ruim; transferência real é mecânica pela porca/arruela no
> fundo → cone ACI 318 Ch.17) como a decisão madura. Sem erro. Liberado.

Fecha a lacuna do **lado do concreto** (o módulo só tinha aço/placa/bearing). A
ligação de base agora calcula o **comprimento de ancoragem por aderência** do
chumbador — o embutimento reto que desenvolve a tração `Ft,Sd`. Fórmulas do PDF
(não de memória):

- **9.3.2.1** — `f_bd = η1·η2·η3·f_ctd`, `f_ctd = f_ctk,inf/γc`,
  `f_ctk,inf = 0,7·f_ctm`, `f_ctm = 0,3·f_ck^(2/3)` [MPa]. `η1 = 1,0` (barra
  **lisa** = chumbador liso; nervurada seria 2,25), `η3 = 1,0` (φ<32 mm).
- **9.4.2.4** — `lb = (φ/4)·(f_yd/f_bd)` (ancoragem básica).
- **9.4.2.5** — `lb,nec = α·lb·(A_s,cal/A_s,ef) ≥ lb,min`; `α = 0,7` com gancho
  (tracionada, cobrimento normal ao gancho ≥ 3φ); `lb,min = max(0,3·lb; 10φ; 100 mm)`.

**Saída = requisito de projeto** (como `t_req` da placa): `lb,nec` é o embutimento
reto requerido. **Informativo por default** — não reprova o OK (só com
`gate_ancoragem=True` + `h_embed` insuficiente). Razão: a aderência de **barra
lisa** é conservadora e **subestima** o gancho/placa, que transferem por
**mecânica** (cone/bearing). Esse cone de arrancamento e o efeito de **grupo**
(ACI 318 Ch.17) são agora **calculados** em separado — ver **§10**.

Ex. (base HEA200, Ft,Sd=63,2 kN, d20 liso, fck25): `f_bd=1,28 MPa`, `lb=848 mm`,
`lb,nec=593 mm` (α=0,7) — ou seja, chumbador liso reto precisaria de ~59 cm de
embutimento por aderência (na prática o gancho/placa reduz isso via mecânica).
Selftest #5 confere `f_bd`, `lb`, `lb,nec ≥ lb,min`, α gancho×sem-gancho, e o gate
por `h_embed`. Não-regressivo: auto-sizer segue adotando a base (ancoragem
informativa).

> **Limite honesto:** esta verificação é a ancoragem por **aderência** (NBR 6118).
> O modo que costuma **governar** o chumbador — **cone de arrancamento do
> concreto** e **grupo** — está agora em **§10** (ACI 318 Ch.17, método CCD).

---

## 10. Cone de arrancamento do concreto — grupo (ACI 318 Ch.17, método CCD)

> **STATUS: ✅ HOMOLOGADO (2026-07-08)** — sênior cruzou com Nilson 15ª ed. cap.21:
> `Nb` (kc=24 cast-in), `A_Nco=9hef²`, `A_Nc` (expansão 1,5hef limitada pela borda),
> `ψed,N`/`ψc,N` (Tab.21.4/21.5), pullout de gancho `0,9·f'c·eh·da` (3da≤eh<4,5da) e
> os selftests Ex.21.3 (`Ncbg`=33,7 kip=149,8 kN) + Ex.21.6 (`Npng`=141,4 kip=628,9
> kN) — "espelhamento primoroso", sem erro. Aprovou o isolamento de unidades e o
> opt-in/informativo (segregação de disciplinas metálica↔fundação). Liberado.

Fecha o modo de ruptura do **concreto** que a aderência (§9) não cobre. Como **não
há ACI 318 no acervo** `pesquisa/aço/`, a fonte é **Nilson, _Design of Concrete
Structures_, 15ª ed., cap. 21**, que **reproduz o ACI 318 Ch.17** (método CCD) —
lido do PDF, **não de memória**. O ACI é escrito em **unidades US** (lb, in, psi);
para preservar as **constantes exatas** (`kc=24`, `A_Nco=9h_ef²`, `N_p=8·A_brg·f'c`,
`N_sb=160…`, `1,9·f_ya`) a rotina **converte a entrada SI → US no contorno**,
calcula, e devolve kN (mesmo padrão de isolamento da punção da fundação).

**Modos de ruptura na tração** (o menor governa; o aço já é coberto pela NBR 8800):

- **Breakout do grupo (21.6):**
  - `N_b = k_c·λ_a·√f'c·h_ef^1,5` (Eq. 21.1; `k_c=24` cast-in); alternativa profunda
    `N_b = 16·λ_a·√f'c·h_ef^(5/3)` para `11 ≤ h_ef ≤ 25 in` (21.2);
  - `A_Nco = 9·h_ef²` (21.9b); `A_Nc` = área projetada do grupo (expande o retângulo
    dos ancoras por `min(1,5h_ef; borda)` em cada face — Fig. 21.10);
  - `ψ_ec,N = 1/(1+2e'_N/(3h_ef)) ≤ 1` (Tab. 21.6); `ψ_ed,N = 1` se `c_a,min ≥ 1,5h_ef`
    senão `0,7+0,3·c_a,min/(1,5h_ef)` (Tab. 21.5); `ψ_c,N = 1,0` fissurado / `1,25`
    não-fissurado cast-in (Tab. 21.4); `ψ_cp,N = 1,0` (cast-in);
  - `N_cbg = (A_Nc/A_Nco)·ψ_ec·ψ_ed·ψ_c·ψ_cp·N_b` (21.6).
- **Pullout (21.9/10/11):** headed `N_p = 8·A_brg·f'c`; **gancho J/L** `N_p =
  0,9·f'c·e_h·d_a` (`3d_a ≤ e_h < 4,5d_a`); `ψ_c,p = 1,0` fissurado / `1,4` não;
  `N_pn = ψ_c,p·N_p`.
- **Side-face blowout (21.12):** `N_sb = 160·c_a1·√A_brg·λ_a·√f'c`, só quando
  `h_ef > 2,5·c_a1` (embutimento profundo perto da borda), com modificador de canto.

**φ (Tab. 21.1):** breakout cast-in Cond. B (**sem** armadura suplementar) **0,70**,
Cond. A (**com**) 0,75; pullout/side-face 0,70. `cap = φ·N` de cada modo; governa o
menor. Demanda `N_ua = Ft,Sd,ancora · n_tração`.

**Validação (selftest #6, entrada SI reproduzindo Nilson):** Ex. 21.3 — 6 studs
½″, `h_ef=4″`, `s1=5″`, `s2=4,5″`, `c_a1=8″` (>1,5h_ef), fissurado, 5000 psi →
`N_b=13,58 kip (60,4 kN)`, `A_Nc/A_Nco=357/144=2,479`, **`N_cbg`nom `= 33,7 kip
(149,7 kN)`**. Ex. 21.6 — `A_brg=0,589 in²` → **`N_png = 141,4 kip (628,9 kN)`**.
Ambos batem → **isolamento de unidades provado**.

**Opt-in / informativo:** só roda com `caso["cone_geom"]` (`h_ef`, `n_x/n_y`,
`s_x/s_y`, `c_a1/c_a2`, fissuração, reforço) — a geometria do bloco/pedestal e o
detalhe da cabeça/gancho são **do projeto de fundação** (Ask, Do Not Invent). Não
gateia o `OK` por default (só com `gate_cone=True`).

> **Nota física:** para **chumbador de gancho** (nosso caso) o `N_p = 0,9·f'c·e_h·d_a`
> costuma **governar** e dar baixa capacidade — é o próprio recado do ACI: gancho
> tem pullout ruim; capacidade real de tração vem de **cabeça/placa de ancoragem**
> ou **armadura de ancoragem** (17.4.2.9), que transfere a carga por barras. O
> exemplo HEA200 reprova por pullout (u=3,3), sinalizando exatamente isso.
>
> **Limites:** o cortante (breakout/pryout na direção do V) fica como refinamento;
> a **armadura de ancoragem** (que dispensa o breakout, 17.4.2.9) e a interação
> tração-cortante (21.16) não estão automatizadas. Fonte é Nilson/CCD (equivalente
> ao ACI 318M SI); o responsável confirma a geometria e o detalhe do gancho/cabeça.
