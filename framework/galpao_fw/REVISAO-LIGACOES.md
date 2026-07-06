# Revisão — Ligações (parafusos e solda)

Conferência do sênior. Verifica ligações parafusadas e soldadas pela
**NBR 8800:2008** (6.2 solda / 6.3 parafusos / 6.1.5 força mínima). Genérico:
joelho viga-coluna, emenda, contravento, chapa de terça.

Código: `ligacoes.py`. Última atualização: 2026-07-06.

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

def fw_rd_base(t_base, Lw, fy):         # metal-base ao cisalhamento
    AMB = t_base * Lw
    return 0.60 * fy * AMB / GA1
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
| Solda filete | `fw_rd_filete` / `_base` | 6.2.5 |
| Força mínima | `forca_minima` | 6.1.5.2 |
