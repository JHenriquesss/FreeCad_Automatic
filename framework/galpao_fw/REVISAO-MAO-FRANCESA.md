# Revisão — Mão-francesa (contenção da mesa inferior)

Conferência do sênior. Espaçamento da mão-francesa (flange brace) que trava a
mesa inferior comprimida do rafter (sucção de vento / gravidade no joelho),
reduzindo o comprimento destravado `Lb`. **NBR 8800:2008** (Anexo G / 5.5.1.2).

Código: `mao_francesa.py` (reusa `check_nbr8800`).
Última atualização: 2026-07-07.

---

## 1. Método — inversão da interação (não heurística)

Reduzir `Lb` aumenta `Nc,Rd` (Ne do eixo fraco) e `Mrd` (FLT), logo a interação
flexo-compressão (5.5.1.2) é **monótona crescente em Lb**. Por bisseção acha-se
o **maior Lb** com interação ≤ 1,0 → espaçamento máximo entre braços.

Código **verbatim** (`mao_francesa.py`):

```python
def lb_maximo(sec, fy, L, Nsd, Msd, Vsd, Cb=1.0, alvo=1.0, Lb_min=0.10):
    _, _, d0 = ck.momento_resistente(sec, fy, Lb_min, Cb)
    info = {"Lp": d0["Lp"], "Lr_flt": d0["Lr_flt"],
            "interacao_travada": _interacao(sec, fy, L, Nsd, Msd, Vsd, Lb_min, Cb)}
    if info["interacao_travada"] > alvo:
        return None, info                      # nem totalmente travada passa
    lo, hi = Lb_min, Lb_min
    while _interacao(sec, fy, L, Nsd, Msd, Vsd, hi, Cb) <= alvo and hi < L:
        hi = min(hi * 1.5, L)                  # expande hi ate falhar (ou ate L)
        if hi >= L:                            # travada so pelas pontas ja passa
            break
    if _interacao(sec, fy, L, Nsd, Msd, Vsd, hi, Cb) <= alvo:
        info["interacao_no_Lbmax"] = _interacao(sec, fy, L, Nsd, Msd, Vsd, hi, Cb)
        return hi, info                        # ate o comprimento total passa
    for _ in range(80):                        # bissecao lo(passa)..hi(nao passa)
        mid = 0.5 * (lo + hi)
        if _interacao(sec, fy, L, Nsd, Msd, Vsd, mid, Cb) <= alvo:
            lo = mid
        else:
            hi = mid
    info["interacao_no_Lbmax"] = _interacao(sec, fy, L, Nsd, Msd, Vsd, lo, Cb)
    return lo, info
```

`lo, hi` **são** inicializados (`= Lb_min, Lb_min`) e `hi` é expandido por ×1,5
até a interação estourar (ou atingir `L`) antes da bisseção — o snippet anterior
deste doc estava resumido e induziu o parecer ao erro (ver §5.1).

`_interacao` chama exatamente `check_nbr8800.verifica` (K=1) — mesma equação do
check da seção, garantindo consistência.

---

## 2. Do Lb_max ao plano de braços

```python
def espacamento_terca_agua(span, slope, n_terca):
    meia = span / 2.0
    dev = meia * math.sqrt(1.0 + slope ** 2)   # comprimento inclinado da meia-agua
    return dev / n_terca                        # n_terca = VAOS (espacamentos)
```

`n_terca` é o número de **vãos** (espaçamentos) de terça na meia-água, não a
contagem de perfis — o comprimento desenvolvido é dividido pelo nº de intervalos
(ver §5.3). Dado o espaçamento real das terças, deriva o "passo" (a cada quantas
terças um braço) e o nº de braços por pórtico. Se nem totalmente travada passa →
travar não resolve, exige seção maior.

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

---

## 5. Resposta ao parecer do sênior (rodada 1 — 2026-07-07)

O parecer revisou o **snippet resumido** do Markdown (§1 antigo), não o código-fonte.
Os "erros de implementação" apontados são artefatos do resumo — o `.py` real está
completo e correto. Doc sincronizado com o código **verbatim** (§1).

### 5.1 — `lo`/`hi` não inicializadas — IMPROCEDENTE (artefato do doc)

O código real (linha 53) faz `lo, hi = Lb_min, Lb_min` e **expande `hi` por ×1,5
até a interação estourar** (linhas 54-57) antes da bisseção — exatamente a intenção
"expande hi até falhar". O snippet do doc omitia essas linhas; agora traz a função
inteira. **Nenhuma alteração de código.**

### 5.2 — 80 iterações "overkill" — mantido (correto e barato)

Verdade que 2⁻⁸⁰ é folga enorme; porém a bisseção só roda **depois** de bracketar
`lo`(passa)/`hi`(não passa), e cada `_interacao` é aritmética barata (ms). A folga
não custa e blinda contra vãos grandes; sem impacto de precisão ou desempenho
perceptível. Sem defeito → sem mudança. (O rewrite do parecer, além disso, **remove
a expansão de `hi`** e fixa `hi=L` — inferior ao código real, que bracketa o ponto
de falha antes de bissecionar. Rejeitado.)

### 5.3 — `n_terca` = vãos, não perfis — JÁ CORRETO (semântica documentada)

O parecer alerta, com razão, para o risco de off-by-one. O código **já** trata
`n_terca` como número de **vãos** (comentário na linha 75; selftest usa "3 vãos de
terça por água"). `s_terca = L_desenvolvido / n_terca` divide pelo nº de intervalos,
correto. Reforçado no doc (§2). Cabe ao orquestrador passar vãos (nº de terças − 1),
não a contagem de perfis — registrado como premissa de wiring.

### 5.4 — Confirmações do parecer (corretas)

- **Monotonicidade** da interação 5.5.1.2 em `Lb`: ↑Lb ⇒ ↓Nc,Rd (χ cai com λ₀) e
  ↓Mrd (FLT além de Lp) ⇒ ambos os quocientes sobem ⇒ interação não-decrescente;
  TVI garante convergência da bisseção. ✅ (o código usa o split 0,2 da NBR 8800,
  não o 8/9 do AISC que o parecer ilustrou — a monotonicidade vale nos dois.)
- **Interação completa** (viga-coluna), não FLT puro: a compressão "rouba"
  capacidade → exige Lb menor. ✅
- **Cb = 1,0** conservador entre pontos de travamento. ✅
- **Geometria** `L_inc = L_x·√(1+m²)` (Pitágoras) ✅.

### 5.5 — Não-regressão

Selftest `mao_francesa` OK (HEA180, sucção no joelho): 3 casos — passa com braços;
Msd maior ⇒ Lb_usado menor / mais braços; esforço absurdo ⇒ `Lb_max=None` (travar
não resolve). Sem alteração de código. Aguarda re-revisão.

---

## 6. Homologação (rodada 2 — 2026-07-07)

**Status: ✅ VALIDADO / HOMOLOGADO sob a NBR 8800:2008.**

Sênior retratou-se após ver o código verbatim: os "erros" eram do snippet resumido.
Confirmado: (1) **busca exponencial** (`hi ×1,5`) para bracketar a raiz antes da
bisseção — garante `[lo,hi]` contendo o ponto onde a interação cruza 1,0 (TVI);
(2) 80 iterações = folga proposital, custo em µs (aritmética, sem integral),
retorno de `lo` a favor da segurança (*safe side*), sem lógica de tolerância;
(3) `n_terca = vãos` elimina *fencepost error*; (4) interação flexo-compressão
completa (não FLT puro) — a compressão do vento de sucção no joelho "consome"
capacidade → exige Lb menor; (5) Cb=1,0 conservador dispensa ler o diagrama de
momentos em cada sub-trecho.

Módulo `mao_francesa.py` liberado. **Nenhuma alteração de código** (só sincronização
do doc com o verbatim).
