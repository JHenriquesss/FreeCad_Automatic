# Revisão — Vento (NBR 6123)

Conferência do sênior. Ação do vento pela **NBR 6123/1988**: transversal
(α = 90°, atinge paredes longas) e longitudinal (α = 0°, atinge o oitão + força
de arrasto). Fornece as pressões; não analisa a estrutura.

Código: `vento_nbr6123.py`. Norma: NBR 6123 (`pesquisa/aço/`).
Última atualização: 2026-07-06.

---

## 1. Velocidade e pressão dinâmica

`Vk = V0·S1·S2·S3` ; `q = 0,613·Vk²` [N/m² → kN/m²].

**S2 = b·Fr·(z/10)^p** (Tabela 1):

```python
def s2_factor(cat, classe, z):
    Fr = {"A": 1.00, "B": 0.98, "C": 0.95}[classe]
    bp = {
        ("I","A"): (1.10,0.06),  ("I","B"): (1.10,0.065), ("I","C"): (1.10,0.07),
        ("II","A"):(1.00,0.085), ("II","B"):(1.00,0.09),  ("II","C"):(1.00,0.10),
        ("III","A"):(0.94,0.10), ("III","B"):(0.94,0.105),("III","C"):(0.94,0.115),
        ("IV","A"):(0.86,0.12),  ("IV","B"):(0.86,0.125), ("IV","C"):(0.86,0.135),
        ("V","A"): (0.74,0.15),  ("V","B"): (0.74,0.16),  ("V","C"): (0.74,0.175),
    }
    b, p = bp[(cat, classe)]
    return b, Fr, p, b * Fr * (z / 10.0) ** p
```

> **Conferir Tabela 1**: Cat II conferida contra a referência; **demais
> categorias A CONFIRMAR** contra o PDF. Fr aqui é o da Cat II por classe,
> aplicado a todas — verificar.

---

## 2. Coeficientes de forma (transversal, α = 90°)

```python
def cpe_paredes():        # Tabela 4, A/B (h/b=0,6 ; a/b=2)
    return {"parede_barlavento": +0.70, "parede_sotavento": -0.60}

def cpe_telhado(theta):   # Tabela 5, EF/GH (interpola 5-10 graus)
    ef = _interp(theta, 5.0, 10.0, -0.90, -1.10)
    gh = _interp(theta, 5.0, 10.0, -0.60, -0.60)
    return {"cobertura_barlavento": round(ef,2), "cobertura_sotavento": round(gh,2)}
```

**Cpi** (item 6.2.5-c, portão = abertura dominante):

```python
def cpi_cases():
    return {"portao_barlavento": +0.80,   # +0,1 a +0,8 conf. razao de areas
            "portao_sotavento": -0.60}    # = Cpe sotavento (Tab.4)
```

Pressão líquida por superfície: `(Cpe − Cpi)·q`.

---

## 3. Vento longitudinal (α = 0°) + força de arrasto (6.3)

```python
def cpe_paredes_longitudinal():   # Tabela 4, alpha=0 (a/b=2)
    return {"oitao_barlavento": +0.70, "oitao_sotavento": -0.30,
            "parede_lateral_A": -0.80, "parede_lateral_B": -0.50}

def forca_arrasto(q, area_frontal, ca):   # 6.3
    return ca * q * area_frontal          # Fa = Ca·q·Ae

# area frontal (empena) = retangulo + triangulo:
area = b * eave + b * (ridge - eave) / 2.0
```

`Fa` é dividido em 2 painéis de contraventamento (`Fa/2` por lado).

---

## 4. Pontos de conferência (FLAGS)

1. **Categoria/classe** e o par (b, p) das categorias ≠ II — A CONFIRMAR na
   Tabela 1.
2. **Fr** por classe aplicado a todas as categorias — verificar.
3. **S3 = 0,95** (galpão depósito, grupo 3) — confirmar o grupo.
4. **Cpi do portão = +0,80** (conservador, razão ≥ 6) — depende da razão real
   entre a área do portão e as demais aberturas sob sucção (6.2.5-c).
5. **Ca** (arrasto) vem da **Figura 4** (gráfico, baixa turbulência) — não é
   tabela; entra como parâmetro "A CONFIRMAR".
6. Mistura de colunas da Tabela 5: o código usa EF/GH (α = 90°) e alerta para
   NÃO misturar com EG/FH (α = 0°).

---

## 5. Onde revisar

| Assunto | Função | Item NBR |
|---|---|---|
| S2 | `s2_factor` | Tabela 1 |
| Cpe paredes | `cpe_paredes` / `_longitudinal` | Tabela 4 |
| Cpe telhado | `cpe_telhado` | Tabela 5 |
| Cpi | `cpi_cases` | 6.2.5-c |
| Arrasto | `forca_arrasto` | 6.3 / Fig. 4 |
