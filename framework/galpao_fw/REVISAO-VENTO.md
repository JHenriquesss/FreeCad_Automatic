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
        ("I","A"): (1.10,0.06),  ("I","B"): (1.11,0.065), ("I","C"): (1.12,0.07),
        ("II","A"):(1.00,0.085), ("II","B"):(1.00,0.09),  ("II","C"):(1.00,0.10),
        ("III","A"):(0.94,0.10), ("III","B"):(0.94,0.105),("III","C"):(0.93,0.115),
        ("IV","A"):(0.86,0.12),  ("IV","B"):(0.85,0.125), ("IV","C"):(0.84,0.135),
        ("V","A"): (0.74,0.15),  ("V","B"): (0.73,0.16),  ("V","C"): (0.71,0.175),
    }
    b, p = bp[(cat, classe)]
    return b, Fr, p, b * Fr * (z / 10.0) ** p
```

> **Tabela 1 conferida integralmente** contra o PDF (pág. 8). Ver §6. Fr é o da
> Cat II por classe (A=1,00; B=0,98; C=0,95), aplicado a todas as categorias
> (5.3.3: "Fr é sempre o correspondente à categoria II").

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

1. **Categoria/classe** e o par (b, p) — ✅ Tabela 1 conferida integralmente
   contra o PDF (ver §6.1); classes B/C de I/III/IV/V corrigidas.
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

---

## 6. Resposta ao parecer do sênior (rodada 1 — 2026-07-06)

Parecer confrontado com o texto autêntico da NBR 6123/1988 (PDF
`pesquisa/aço/crr_nbr_6123_forcasvento.pdf`).

### 6.1 — Fator b da Tabela 1: classes B/C erradas — CORRIGIDO (mais que o parecer)

**Veredito: PROCEDE, e auditoria própria achou MAIS erros que o parecer.**

O parecer apontou só a Categoria I. Auditoria completa do dicionário `bp`
contra a **Tabela 1** autêntica (pág. 8 do PDF) revelou que as classes B e C
foram copiadas da classe A em **quatro** categorias (I, III, IV, V). Valores
de `p` estavam todos corretos. Tabela 1 verbatim:

| Cat | b (A/B/C) — norma | Código antes | Corrigido |
|---|---|---|---|
| I   | 1,10 / **1,11** / **1,12** | 1,10/1,10/1,10 | ✅ |
| II  | 1,00 / 1,00 / 1,00 | 1,00/1,00/1,00 | (já ok) |
| III | 0,94 / 0,94 / **0,93** | 0,94/0,94/0,94 | ✅ |
| IV  | 0,86 / **0,85** / **0,84** | 0,86/0,86/0,86 | ✅ |
| V   | 0,74 / **0,73** / **0,71** | 0,74/0,74/0,74 | ✅ |

O parecer afirmou "Cat II–V exatas" — **incorreto** para III/IV/V; o confronto
com o PDF prevaleceu (regra: verificar método na norma, nunca de memória/parecer).

### 6.2 — Conversão de q (N/m² vs kN/m²) — IMPROCEDENTE

**Veredito: REJEITADO. Código já correto.**

O parecer alertou erro de 1000×, mas leu apenas o comentário resumido
(`q = 0,613·Vk²`). A linha de cálculo real (`vento_nbr6123.py:109` e `:181`)
sempre teve `q = 0.613 * vk**2 / 1000.0` → saída em **kN/m²**. Confirmado no
selftest: `q = 0,787 kN/m²` (valor fisicamente coerente). Adicionado comentário
explícito `# ... /1000 -> kN/m2` para não induzir novo mal-entendido.

### 6.3 — Confirmações do parecer (corretas)

- Área frontal da empena `A_e = b·h_eave + b·(h_ridge−h_eave)/2`: correta.
- Fr por classe (A=1,00; B=0,98; C=0,95) aplicado a todas as categorias: correto
  (5.3.3, pág. 8: "Fr é sempre o correspondente à categoria II").
- S3=0,95 (Grupo 3, galpão): confirmado (Tabela 3). Cpi=+0,8 conservador
  (6.2.5-c) e Ca "A CONFIRMAR" (Fig. 4 depende de h/l1, l1/l2): mantidos como
  premissas registradas.

### 6.4 — Não-regressão

Galpão de referência usa **Cat II Classe B** (b=1,00, inalterado) → S2=0,943,
q=0,787 kN/m², Fa=59,0 kN — **idênticos**. Interação coluna 0,67 / viga 0,93
inalteradas. A correção afeta apenas terrenos Cat I/III/IV/V (fora da referência).
Aguarda re-revisão.

---

## 7. Homologação (rodada 2 — 2026-07-06)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 6123/1988.**

O sênior confrontou as correções da §6 com o texto autêntico da norma e homologou:

- **7.1 Tabela 1 (b, p)** — correção das classes B/C em I/III/IV/V confirmada;
  reconhecido que o aval anterior ("II–V exatas") foi falho. `s2_factor` correto.
- **7.2 q** — falso positivo do parecer (leu comentário, não linhas 109/181);
  `/1000 → kN/m²` íntegro, `q=0,787 kN/m²` de ordem de grandeza correta.
- **7.3 Confirmados** — Vk=V0·S1·S2·S3, S2=b·Fr·(z/10)^p, Fr sempre da Cat II
  (5.3.3), Fa=Ca·q·Ae (6.3), área frontal da empena (retângulo+triângulo),
  Cpi=+0,8 (máx. 6.2.5-c), S3=0,95 (Grupo 3), Ca "A CONFIRMAR" (Fig. 4).

Módulo `vento_nbr6123.py` liberado para alimentar o dimensionamento da estrutura
principal. Auditoria cruzada elogiada como mais rigorosa que a revisão inicial.

---

## 8. Cpe médio / local de borda e canto (Tabelas 4 e 5) — feature adicionada 2026-07-08

> **STATUS: ✅ HOMOLOGADO (2026-07-09)** — Cpe médio local §8. Conferido: a
> coluna **"cpe médio"** das Tabelas 4 (paredes) e 5 (telhado), as zonas de alta
> sucção de borda/canto e a sucção líquida local que dimensiona **telha, terça e
> fixadores**.

### 8.1 — O que faltava

O módulo só entregava o **Cpe global** (faces inteiras) que alimenta o **pórtico**.
A NBR 6123 traz, na coluna **"cpe médio"** das Tabelas 4 e 5, coeficientes de
sucção **muito mais severos**, aplicados em **faixas estreitas de borda e canto**.
Esses valores **não** governam o pórtico, mas **governam** o dimensionamento da
**telha**, da **terça** e — o crítico — dos **fixadores** (parafuso auto-atarraxante
telha→terça e ligação terça→pórtico), que arrancam por sucção nos cantos.

### 8.2 — Valores lidos VERBATIM do PDF (págs. 14-15)

**Tabela 4 — paredes, coluna "cpe médio"** (faixa de barlavento das paredes
paralelas ao vento, largura = **min(0,2b ; h)**, nota c):

| bloco h/b | 1≤a/b≤3 | 2≤a/b≤4 |
|---|---|---|
| h/b ≤ 1/2 | −0,9 | −1,0 |
| 1/2 < h/b ≤ 3/2 | −1,1 | −1,1 |
| 3/2 < h/b ≤ 6 | −1,2 | −1,2 |

**Tabela 5 — telhado 2 águas, coluna "cpe médio"** (4 zonas hachuradas; faixa
**y = min(h ; 0,15b)**; dimensão da zona **min(max(b/3 ; a/4) ; 2h)**). Transcrição
integral em `_CPE_MEDIO_COB` (3 blocos h/b × θ × 4 zonas; `None` = célula em branco
= zona ausente naquele ângulo). Notas: **c) lanternins cpe médio = −2,0**;
b) saliências (chaminé/torre) Ce=1,2 até meia-diagonal.

Para o galpão de referência (h/b=0,6 → bloco 1/2<h/b≤3/2; θ=5,71°): a envoltória
das 4 zonas dá **−2,0** (zona de canto). Sucção líquida local (Cpi=+0,8 de arranque):
`p = (−2,0 − 0,8)·q = −2,80·q = −2,203 kN/m²` na cobertura — **62 % acima** da global
de barlavento (−1,362 kN/m²). Parede: `(−1,10 − 0,8)·q = −1,495 kN/m²`.

### 8.3 — Código (verbatim)

```python
_CPE_MEDIO_PAREDE = {("<=1/2","1-3"):-0.9, ("<=1/2","2-4"):-1.0,
    ("1/2-3/2","1-3"):-1.1, ("1/2-3/2","2-4"):-1.1,
    ("3/2-6","1-3"):-1.2, ("3/2-6","2-4"):-1.2}

def cpe_local_parede(a=20.0, b=10.0, h=6.0):
    bloco_h, hb = _bloco_hb(h, b); bloco_a, ab = _bloco_ab(a, b)
    cpe = _CPE_MEDIO_PAREDE[(bloco_h, bloco_a)]
    faixa = min(0.2*b, h)                     # nota c
    return {"cpe_medio": cpe, "faixa_m": round(faixa,2), ...}

def cpe_local_cobertura(theta_graus=5.71, b=10.0, h=6.0, a=20.0):
    # envoltória (mais negativa) das 4 zonas, interpolada em theta;
    # y = min(h, 0.15*b) ; dim_zona = min(max(b/3, a/4), 2*h)
    ...
    envoltoria = min(v for v in zonas if v is not None)

def sucao_local_fixacao(q, cpe_medio, cpi=+0.80):
    return round((cpe_medio - cpi)*q, 3)      # negativo = arranque
```

### 8.4 — FLAGS / limites de escopo

1. **Envoltória conservadora** — retorno-chave é a zona **mais severa** das 4
   (dimensionar o fixador pelo pior canto). As 4 zonas ficam disponíveis em
   `zonas` para quem quiser mapear faixa-a-faixa.
2. **Interpolação só em θ** (nota a da Tab.5). a/b entra apenas no bloco (Tab.4);
   a interpolação a/b 3/2..2 da nota (a) da Tab.4 **não** altera a coluna cpe médio
   (constante dentro do bloco h/b) — sem perda.
3. **Cpi de arranque = +0,8** (portão a barlavento, máx. de 6.2.5-c) — mesmo FLAG
   de razão de aberturas da §6/§3; o engenheiro confirma a razão real.
4. Não dimensiona o parafuso da telha em si (bitola/arranque do fixador) — entrega
   a **sucção de projeto**; o cálculo do fixador é do fabricante da telha/terça.

### 8.5 — Não-regressão

`python vento_nbr6123.py --selftest` → **PASSED**. Cpe global, S2, q e Fa
**inalterados** (feature é aditiva: nova chave `local` no dict, novo bloco no
relatório). Orquestrador roda limpo; `gate5-vento.txt` traz o bloco local.
Selftest cobre: parede −1,1 (bloco/faixa), cobertura envoltória −2,0
(faixa y=1,5 / zona=5,0), interpolação θ no bloco h/b≤1/2, sucção −2,8·q.
Aguarda revisão.
