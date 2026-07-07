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
    if lam_a > lamr_a:                 # alma esbelta: fora do escopo (Tabela G.1)
        raise ValueError("... Alma esbelta -> viga de alma cheia (Anexo H)")
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

## 3. Cortante (5.4.3.1.1) — três domínios, kv=5 (alma sem enrijecedores)

```python
Aw = d * tw                              # area de cisalhamento (laminado)
lamw = h / tw
lamw_p = 1.10 * math.sqrt(5.0 * E / fy)  # escoamento (plastificacao)
lamw_r = 1.37 * math.sqrt(5.0 * E / fy)  # flambagem elastica
Vpl = 0.6 * Aw * fy
if lamw <= lamw_p:
    Vn = Vpl                                 # plastificacao da alma
elif lamw <= lamw_r:
    Vn = Vpl * (lamw_p / lamw)               # flambagem inelastica
else:
    Vn = Vpl * 1.24 * (lamw_p / lamw) ** 2   # flambagem elastica
Vrd = Vn / GA1
```

Forma literal da norma (5.4.3.1.1): `Vrd = 1,24·(λp/λ)²·Vpl/γa1` para `λ > λr`.
Equivale à forma expandida `1,24·1,10²·kv·E/(fy·λ²) ≈ 1,50·kv·E/(fy·λ²)`.

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
| Cortante | `verifica` (bloco Vrd) | 5.4.3.1.1 |
| Interação | `verifica` (bloco inter) | 5.5.1.2 |

---

## 7. Resposta ao parecer do sênior (rodada 1 — 2026-07-06)

Parecer confrontado com o texto autêntico da NBR 8800:2008 (PDF
`pesquisa/aço/nbr8800_2008_1.pdf`). **Dois achados procedentes → código corrigido.**

### 7.1 — Cortante (5.4.3.1.1): faltava o 3º domínio (flambagem elástica)

**Veredito: PROCEDE. CORRIGIDO.**

O código anterior tinha só 2 ramos e aplicava a flambagem **inelástica** (`λp/λ`)
para qualquer alma acima de `λp`, superestimando o cortante em almas muito
esbeltas. NBR 8800 **5.4.3.1.1** (pág. 59 do PDF) prescreve **três** domínios:

- `λ ≤ λp` → `Vrd = Vpl/γa1`
- `λp < λ ≤ λr` → `Vrd = (Vpl/γa1)·(λp/λ)`
- `λ > λr` → `Vrd = (Vpl/γa1)·1,24·(λp/λ)²`   ← **domínio adicionado**

com `λ = h/tw`, `λp = 1,10√(kv·E/fy)`, `λr = 1,37√(kv·E/fy)`, `kv = 5`.
A fórmula do parecer (`1,51·kv·E/(fy·λw²)`) é a forma expandida equivalente
(`1,24·1,10² = 1,50`). Adotada a **forma literal da norma** `1,24·(λp/λ)²`.
Ver §3. Impacto prático: nulo para perfis I laminados (alma sempre no domínio 1;
run de referência confirma `alma compacta: True`, Vrd inalterado), mas o código
fica correto para almas esbeltas.

### 7.2 — FLA (Anexo G): guardrail p/ alma esbelta

**Veredito: PROCEDE. CORRIGIDO.**

`_interp_M(lam_a, ..., Mpl, fy·Wx, Mpl)` retornava `Mpl` mesmo com
`λa > λr,a = 5,70√(E/fy)` (alma esbelta), silenciosamente inseguro. Perfis com
alma esbelta saem do escopo deste verificador (perfil laminado compacto) e devem
ir para **viga de alma cheia (Anexo H)**. Adicionado `raise ValueError` (fail-loud)
quando `λa > λr,a`, conforme sugestão do parecer. Ver §2. Não dispara em nenhum
perfil laminado do galpão (run de referência OK, sem raise).

### 7.3 — Confirmações do parecer (corretas, sem alteração)

Compressão global χ (5.3.3) e local Qs/Qa (Anexo F, incl. `bef` com ca=0,34) ✓ ·
FLT/FLM e Mcr (Anexo G) ✓ · interação flexo-compressão (5.5.1.2) ✓ ·
K=1 (4.9.6.2) · Cw/J por geometria (conservador) · Aw = d·tw (laminado). ✓

### 7.4 — Verificação de não-regressão

`check_nbr8800.py` selftest OK. `rodar_galpao.py` (galpão 20×10 referência):
interação coluna = 0,67 e viga = 0,93 — **idênticas à referência**. Sem raise,
sem traceback. Aguarda re-revisão.

---

## 8. Homologação (rodada 2 — 2026-07-06)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 8800:2008.**

O sênior confrontou as correções da §7 com o texto autêntico da norma e homologou:

- **8.1 Cortante** — 3 domínios (5.4.3.1.1) corretos; forma literal `1,24·(λp/λ)²`
  confirmada equivalente a `1,51·kv·E/(fy·λw²)`. Sanou a única vulnerabilidade.
- **8.2 FLA** — `raise ValueError` para `λa > 5,70√(E/fy)` homologado; perfis de
  alma esbelta exigem Anexo H (campo de tração), fora do escopo deste verificador.
- **8.3 Confirmados** — compressão global/local (5.3, Anexo F, bef ca=0,34),
  FLT/FLM e Mcr (Anexo G, ≡ G.12), interação (5.5.1.2, eq. 5.25/5.26).

Módulo `check_nbr8800.py` liberado para produção. Robusto contra falso-positivo
(cisalhamento) e extrapolação fora de escopo (alma esbelta).
