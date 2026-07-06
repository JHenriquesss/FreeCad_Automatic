# Revisão — Mão-francesa (contenção da mesa inferior)

Conferência do sênior. Espaçamento da mão-francesa (flange brace) que trava a
mesa inferior comprimida do rafter (sucção de vento / gravidade no joelho),
reduzindo o comprimento destravado `Lb`. **NBR 8800:2008** (Anexo G / 5.5.1.2).

Código: `mao_francesa.py` (reusa `check_nbr8800`).
Última atualização: 2026-07-06.

---

## 1. Método — inversão da interação (não heurística)

Reduzir `Lb` aumenta `Nc,Rd` (Ne do eixo fraco) e `Mrd` (FLT), logo a interação
flexo-compressão (5.5.1.2) é **monótona crescente em Lb**. Por bisseção acha-se
o **maior Lb** com interação ≤ 1,0 → espaçamento máximo entre braços.

```python
def lb_maximo(sec, fy, L, Nsd, Msd, Vsd, Cb=1.0, alvo=1.0, Lb_min=0.10):
    info["interacao_travada"] = _interacao(sec, fy, L, Nsd, Msd, Vsd, Lb_min, Cb)
    if info["interacao_travada"] > alvo:
        return None, info          # nem totalmente travada passa -> secao maior
    # expande hi ate falhar (ou ate L) ; depois bisseciona lo(passa)..hi(nao)
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if _interacao(sec, fy, L, Nsd, Msd, Vsd, mid, Cb) <= alvo:
            lo = mid
        else:
            hi = mid
    return lo, info
```

`_interacao` chama exatamente `check_nbr8800.verifica` (K=1) — mesma equação do
check da seção, garantindo consistência.

---

## 2. Do Lb_max ao plano de braços

```python
def espacamento_terca_agua(span, slope, n_terca):
    meia = span / 2.0
    dev = meia * math.sqrt(1.0 + slope ** 2)   # comprimento inclinado da meia-agua
    return dev / n_terca
```

Dado o espaçamento real das terças, deriva o "passo" (a cada quantas terças um
braço) e o nº de braços por pórtico. Se nem totalmente travada passa → travar
não resolve, exige seção maior.

---

## 3. Pontos de conferência

1. `Lb_max` pela interação completa (5.5.1.2), não FLT puro — mais rigoroso.
2. Nsd/Msd/Vsd vêm amplificados de 2ª ordem (ver [REVISAO-PORTICO.md](REVISAO-PORTICO.md)).
3. Cb = 1,0 default (conservador).
4. A força de estabilização do braço (2% da mesa) é verificada em
   [REVISAO-CONTRAVENTAMENTO.md](REVISAO-CONTRAVENTAMENTO.md).

---

## 4. Onde revisar

| Assunto | Função | Item NBR 8800 |
|---|---|---|
| Lb máximo | `lb_maximo` | 5.5.1.2 / Anexo G |
| Interação | `_interacao` → `check.verifica` | 5.5.1.2 |
| Espaçamento terça | `espacamento_terca_agua` | — |
| Plano de braços | `plano_mao_francesa` | — |
