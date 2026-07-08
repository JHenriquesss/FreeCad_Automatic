# Revisão — Ligações (parafusos e solda)

Conferência do sênior. Verifica ligações parafusadas e soldadas pela
**NBR 8800:2008** (6.2 solda / 6.3 parafusos / 6.1.5 força mínima). Genérico:
joelho viga-coluna, emenda, contravento, chapa de terça.

Código: `ligacoes.py`. Última atualização: 2026-07-07.

---

## 1. Parafusos (6.3.3)

```python
GA2 = 1.35
def _area(db):
    Ab = math.pi * db ** 2 / 4.0
    return Ab, 0.75 * Ab            # bruta, efetiva (rosqueada)

def fv_rd(db, fub, rosca_no_plano=True, n_planos=1):   # 6.3.3.2
    Ab, _ = _area(db)
    c = 0.4 if rosca_no_plano else 0.5
    return c * Ab * fub / GA2 * n_planos

def ft_rd(db, fub):                                     # 6.3.3.1
    _, Abe = _area(db)
    return Abe * fub / GA2

def fc_rd(db, t, fu, lf):                               # 6.3.3.3 esmagamento
    return min(1.2 * lf * t * fu, 2.4 * db * t * fu) / GA2
```

Interação tração + corte (6.3.3.4):
`(Nsd/Ft,Rd)² + (Vsd/Fv,Rd)² ≤ 1` ; corte limitado por `min(Fv,Rd, Fc,Rd)`.

```python
Fv_lim = min(Fvrd, Fcrd)
inter = (Nsd/Ftrd)**2 + (Vsd/Fvrd)**2 if Nsd > 0 else Vsd / Fv_lim
```

---

## 2. Solda de filete (6.2.5)

```python
GW2 = 1.35 ; GA1 = 1.10
def fw_rd_filete(perna, Lw, fw):        # metal da solda; garganta = 0,707·perna
    Aw = 0.707 * perna * Lw
    return 0.60 * fw * Aw / GW2, Aw

def fw_rd_base(t_base, Lw, fy, fu=None):   # metal-base (Tabela 8 -> 6.5.5)
    AMB = t_base * Lw
    Fesc = 0.60 * fy * AMB / GA1           # escoamento 6.5.5-a
    if fu is None:
        return Fesc
    Frup = 0.60 * fu * AMB / GA2           # ruptura 6.5.5-b (Anv=Ag ao longo da solda)
    return min(Fesc, Frup)
# Fw,Rd = min(metal da solda, metal-base)
```

---

## 3. Força mínima de ligação (6.1.5.2)

```python
FORCA_MIN = 45.0   # kN
def forca_minima(Fsd, excecao=False):
    if excecao:                 # tirantes redondos, travessas, TERCAS, travejamento
        return Fsd, False
    if abs(Fsd) < FORCA_MIN:
        return FORCA_MIN, True
    return Fsd, False
```

---

## 4. Dimensionamento do joelho (escada)

Escolhe (n parafusos, db, t_chapa) mais leve com interação ≤ 1 sob N (tração da
mesa = M/(d−tf) + N/2) e V. Escada `ESCADA_JOELHO` de M20/4 → M30/8.

---

## 5. Pontos de conferência (FLAGS)

1. **Área efetiva = 0,75·Ab** (rosca no plano de corte) — uso comum; confirmar.
2. `fc_rd` cobre **esmagamento/rasgamento** local; **NÃO** cobre rasgamento em
   bloco nem flexão da chapa de topo — FLAG.
3. **Força mínima 45 kN** com as exceções da norma (terça marcada `excecao`).
4. N de tração da mesa do joelho = `M/(d−tf) + N/2` (modelo de binário) — vem do
   orquestrador; conferir o braço.
5. Solda: `fw` (resistência do eletrodo) e `fy_base` — entradas.

---

## 6. Onde revisar

| Assunto | Função | Item NBR |
|---|---|---|
| Corte parafuso | `fv_rd` | 6.3.3.2 |
| Tração parafuso | `ft_rd` | 6.3.3.1 |
| Esmagamento | `fc_rd` | 6.3.3.3 |
| Interação | `parafusos` | 6.3.3.4 |
| Solda filete | `fw_rd_filete` / `_base` | 6.2.5 / 6.5.5 |
| Força mínima | `forca_minima` | 6.1.5.2 |

---

## 7. Resposta ao parecer do sênior (rodada 1 — 2026-07-07)

### 7.1 — Interação parafuso "exclui esmagamento da chapa" — IMPROCEDENTE

**Veredito: REJEITADO. Esmagamento (Fc,Rd) já entra no critério de aprovação.**

O parecer alega que o `if Nsd > 0` calcula só a curva do parafuso e **exclui** o
gargalo de esmagamento `Fc,Rd`, aprovando ligação com `Vsd > Fc,Rd`. Leitura
incorreta do código. Linhas 61-62:
```python
Fv_lim = min(Fvrd, Fcrd)
inter = (Nsd/Ftrd)**2 + (Vsd/Fvrd)**2 if Nsd > 0 else Vsd / Fv_lim
```
e o `OK` (linha 66):
```python
"OK": inter <= 1.0 and (Vsd / Fv_lim) <= 1.0
```
O esmagamento **sempre** entra pelo gate `(Vsd/Fv_lim) ≤ 1`, com `Fv_lim =
min(Fvrd, Fcrd)`. Se `Vsd > Fc,Rd`, então `Vsd/Fv_lim > 1` e a ligação **reprova**
— exatamente o cenário que o parecer temia. A separação (interação do conector
6.3.3.4 no `inter`; esmagamento da chapa 6.3.3.3 no gate) é **fisicamente correta**:
a superfície quadrática 6.3.3.4 é do **material do parafuso**; misturar `Fc,Rd`
(estado-limite da **chapa**) dentro da quadrática seria errado. O `max(...)` que
o parecer propõe é funcionalmente equivalente ao `AND` de dois gates já existente.
**Nenhuma alteração de código.**

### 7.2 — Metal-base da solda de filete: falta ruptura — PROCEDE

**Veredito: CORRIGIDO.** O `fw_rd_base` só trazia o escoamento
`0,60·fy·AMB/γa1`. A **Tabela 8** da NBR 8800 (pág. 81) manda o metal-base do
filete sob cisalhamento **"atender a 6.5"**; o **item 6.5.5** ("Elementos
submetidos a cisalhamento", pág. 87) exige o **menor** de:

> a) escoamento: `0,60·fy·Ag/γa1`
> b) ruptura: `0,60·fu·Anv/γa2`

Ao longo da solda não há furos → `Anv = Ag = AMB`. Fix:
```python
Fesc = 0.60*fy*AMB/GA1 ; Frup = 0.60*fu*AMB/GA2 ; return min(Fesc, Frup)
```
(fu opcional, retrocompatível). Observação: o `0,60·fy·AMB/γa1` original é, na
verdade, a linha de **penetração total** da Tabela 8 — para filete faltava o par
de 6.5.5. Para aço A36 (fy=250/fu=400) o **escoamento governa** (0,60·250/1,10 =
136 < 0,60·400/1,35 = 178 ·AMB), então o caso de referência não muda de valor; a
ruptura passa a governar em aços com `fu < 1,227·fy`. Correção de robustez, a
favor da segurança.

### 7.3 — Confirmações do parecer (corretas, verificadas contra o PDF)

- `Ft,Rd = 0,75·Ab·fub/γa2` (6.3.3.1) ✅ ; `Fv,Rd = 0,4/0,5·Ab·fub/γa2` (6.3.3.2) ✅
- `Fc,Rd = min(1,2·lf·t·fu ; 2,4·db·t·fu)/γa2` (6.3.3.3, deformação limitante) ✅
- Metal da solda `0,60·fw·Aw/γw2`, garganta `0,707·perna` (6.2.5, Tabela 8, γw2=1,35) ✅
- Força mínima 45 kN (6.1.5.2) com exceções (tirantes/travessas/terças/travejamento) ✅
- Binário do joelho `N_mesa = M/(d−tf) + N/2` (método clássico, Fakury/Pfeil) — vem
  do orquestrador, não de `ligacoes.py`; braço `d−tf` confere ✅

### 7.4 — Pendências mantidas como FLAG (parecer §4, corretas)

- **Efeito alavanca (prying)** na chapa de topo (T-stub / EN 1993-1-8 método do
  perfil T equivalente) — **fora do escopo** desta rotina; permanece FLAG 2.
- **Rasgamento em bloco** (6.5.6, `Frd = 0,60·fu·Anv + Cts·fu·Ant ≤ 0,60·fy·Agv +
  Cts·fu·Ant`) — **fora do escopo**; permanece FLAG 2. (Rotina de T-stub e block
  shear = módulo futuro, não bloqueia este verificador de esforços diretos.)

### 7.5 — Não-regressão

Selftest `ligacoes` OK (inclui asserts de 6.5.5 escoamento×ruptura). Exemplos:
joelho M20/6 inter 0,09; chapa terça M12 0,30; contravento solda filete metal-base
261,8 (escoamento governa) / util 0,21. Aguarda re-revisão.

---

## 8. Homologação (rodada 2 — 2026-07-07)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 8800:2008.**

Sênior concedeu razão na separação de estados-limite (§7.1): interação 6.3.3.4 =
critério de von Mises no **material do parafuso**; esmagamento = estado-limite da
**chapa**, gate independente `(Vsd/Fv_lim) ≤ 1`. Correção do metal-base (§7.2)
validada — escoamento + ruptura (Tabela 8 → 6.5.5), `Anv=Ag=AMB` correto para
plano de corte paralelo à solda contínua (sem furos). Confirmados γa1=1,10,
γa2=1,35, γw2=1,35 e o binário do joelho `M/(d−tf)+N/2`.

Módulo `ligacoes.py` liberado para o orquestrador. FLAGs mantidas e documentadas
para módulos futuros: **efeito alavanca (T-stub)** e **rasgamento em bloco (6.5.6)**.

---

## 9. Detalhamento dos furos (6.3.9/6.3.10/6.3.11) — feature adicionada 2026-07-08

> **STATUS: 🆕 PENDENTE SÊNIOR** — feature nova. A conferir: `s ≥ 2,7db`, distância
> livre `≥ db` (6.3.9), `s_max ≤ min(24t; 300)` (6.3.10) e o **`lf` derivado da
> geometria** que alimenta o esmagamento 6.3.3.3.

Antes o `lf` do esmagamento era **input solto**; agora, quando o caso traz a
geometria (`s_furos`, `e_borda`), o `lf` é **derivado** dela — coerente com o
layout — e os mínimos de detalhamento são checados. Regras **lidas do PDF**:

- **6.3.9** — distância entre centros `≥ 2,7·db` (pref. `3·db`); distância **livre**
  entre bordas de furos consecutivos `≥ db`.
- **6.3.10 a)** — espaçamento máximo (chapa pintada) `≤ min(24·t; 300 mm)`.
- **`lf` (6.3.3.3):** `min(e_borda − d_h/2; s_furos − d_h)` (distância livre do furo à
  extremidade / ao furo vizinho), `d_h = db + 1,5 mm` (furo-padrão, Tabela 12).
  Alimenta `Fc,Rd = min(1,2·lf·t·fu; 2,4·db·t·fu)/γa2` (já existente).

**Tabela 14 (distância furo-borda) fica FLAG:** a extração tabular é ambígua
(colunas borda cortada × laminada) e a **nota (a) da própria Tabela 14** remete ao
**6.3.3.3** como estado-limite de resistência — que já é calculado. O engenheiro
confirma a coluna de borda. Selftest: `db20`, `s=60 mm ≥ 2,7·20=54` OK, livre
`60−21,5=38,5 ≥ 20` OK, `lf=min(35−10,75; 60−21,5)=24,25 mm`; `s=45<54` reprova.
Não-regressivo: sem `s_furos`/`e_borda`, usa o `lf` explícito (ex. da terça).
