# Revisão — Ponte rolante estendida (rodas motoras + NBR 8400-1:2019)

Conferência do sênior. Estende a ponte rolante já homologada
([PONTE](REVISAO-PONTE.md): cargas + viga de rolamento + fadiga Anexo K) em três
pontos. Código: `ponte_rolante.py`, **novo** `nbr8400.py`, gate em
`projeto_spec.py`. Fase 4 do pipeline. Criado 2026-07-10.

> **STATUS: 🔁 PARECER 1 RESPONDIDO — REVER** (2026-07-11). Sênior validou Q2
> (Ψ e min(Vh,1.5)), Q3 (limite superior / B10) e Q4 (edição 2019). Apontou Q1
> (H_long) como erro de estática — **mas a fórmula está correta** (§6): `R_roda_max`
> é a reação POR RODA do trilho carregado (partilha igual), então
> `frac_long·R_roda_max·n_motoras = frac_long·ΣR_motoras ≤ frac_long·R_trilho_max`
> — não há superposição. Ψ-cap e B10 **já estavam implementados** (senior confirmou
> a matemática); só a doc induziu dúvida. Provas adicionadas ao selftest.

---

## 1. Frenagem longitudinal nas RODAS MOTORAS (NBR 8800)

Antes: a força longitudinal de frenagem incidia sobre **todas** as rodas do
trilho (`H_long = frac_long · R_roda_max · n_rodas_lado`). Fisicamente a frenagem
atua só nas **rodas motrizes**. Agora:

```
H_long = frac_long · R_roda_max · n_rodas_motoras     (n_motoras ≤ n_rodas_lado)
```

- `n_rodas_motoras` é **dado do fabricante** (gate); default = `n_rodas_lado`
  (todas motrizes ⇒ **idêntico ao comportamento anterior** — não-regressão).
- `frac_long` continua **A CONFIRMAR** (fabricante / NBR 8400); não foi inventado.
- Saturação: `n_rodas_motoras > n_rodas_lado` levanta erro (guard `mne-2`).

**[Q1]** Confirma o *basis* de que a frenagem longitudinal se distribui apenas
nas rodas motoras do caminho de rolamento (NBR 8800 / prática de ponte rolante),
com `frac_long` aplicado sobre `R_roda_max · n_motoras`?

> **RESPOSTA AO PARECER (§6):** o sênior objetou que `R_roda_max · n_motoras`
> superdimensiona (somaria o pico de uma roda em todas). **A objeção não procede**
> porque `R_roda_max` **não** é o pico isolado de uma roda: `cargas_de_roda`
> devolve `R_roda_max = R_trilho_max / n_rodas_lado` — a reação **por roda** do
> trilho carregado, com partilha igual. Então, nesse trilho, cada roda vale
> `R_roda_max` e a soma sobre as motoras é exatamente `ΣR_motoras`:
> `frac_long·R_roda_max·n_motoras = frac_long·ΣR_motoras`. Como
> `n_motoras ≤ n_rodas_lado` (guard), isso é **sempre ≤ `frac_long·R_trilho_max`**
> (a fração do trilho inteiro) → equilíbrio vertical preservado. Usar `R_roda_max`
> (trole na aproximação mínima) é o **envelope** conservador da carga aderente,
> não um erro. Igual à fórmula `H_long = μ·ΣR_motoras` que o próprio parecer pede.
> Doc reforçada e **teto provado no selftest** (`H_long ≤ frac_long·R_trilho_max`
> p/ todo `n_motoras ∈ [0, n_rodas_lado]`). Fórmula mantida.

---

## 2. Coeficiente dinâmico φ (Ψ) — NBR 8400-1:2019, Tabela 12 + §6.2.2.1

Antes: `phi` era input direto (1,10 típico). Agora, se a **classe de elevação**
`HC` e a **velocidade** `Vh` forem informadas, φ é calculado da norma:

```
Ψ = Ψmín + β2 · Vh            (Figura 4 / §6.2.2.1 ; Vh ≤ 1,5 m/s)
```

### Tabela 12 (verbatim, PDF p.20) — β2 e Ψmín por classe de elevação

| Classe | β2 | Ψmín |
|---|---|---|
| HC1 | 0,17 | 1,05 |
| HC2 | 0,34 | 1,10 |
| HC3 | 0,51 | 1,15 |
| HC4 | 0,68 | 1,20 |

`Vh` (velocidade de elevação em regime, m/s) **limitada a 1,5 m/s** (p.21: acima,
Ψ não aumenta). `HC` e `Vh` são **dado de projeto** (gate); sem classe, φ continua
input (retrocompatível). Fonte impressa no memorial (`phi_fonte`).

**[Q2]** A classe HC da ponte rolante típica (gancho, oficina geral) fica em
HC1–HC2. Concorda em deixar `HC` como **escolha do engenheiro** (Tabela 4 da norma
como orientação), sem default embutido?

---

## 3. Número de ciclos da fadiga — NBR 8400-1:2019, Tabela 9 (§6.1.4.2)

Antes: `n_ciclos` era input (2×10⁶ default). Agora, se a **classe de utilização
do componente** `B` for informada, N vem da Tabela 9:

### Tabela 9 (verbatim, PDF p.23) — classes B0…B10 (nº n de ciclos de tensão)

| Classe | n | Classe | n |
|---|---|---|---|
| B0 | < 16 000 | B6 | 500 000 – 1 000 000 |
| B1 | 16 000 – 32 000 | B7 | 1 000 000 – 2 000 000 |
| B2 | 32 000 – 63 000 | B8 | 2 000 000 – 4 000 000 |
| B3 | 63 000 – 125 000 | B9 | 4 000 000 – 8 000 000 |
| B4 | 125 000 – 250 000 | B10 | ≥ 8 000 000 |
| B5 | 250 000 – 500 000 | | |

O N adotado é o **limite superior** do intervalo da classe (conservador: mais
ciclos ⇒ faixa admissível de fadiga menor). Esse N alimenta o `verifica_fadiga`
(NBR 8800 Anexo K) **sem alterá-lo** — só troca a origem do N (input → norma).

**[Q3]** Aceita o **limite superior** da faixa da classe B como N representativo
(conservador), em vez da média/limite inferior?

**[Q4]** A NBR 8400-1:2019 é a edição harmonizada (ISO/EN). O φ dela (Ψ, ~1,05–1,88
conforme Vh) substitui a faixa "1,10 leve … 1,25 pesada" do texto antigo do módulo
quando a classe é informada. Confirma usar a **edição 2019** como fonte?

---

## 4. Gate de validação da ponte (ProjetoSpec)

`validar()` passa a **bloquear** quando `spec["ponte"]` é dict e falta dado do
fabricante: `Q, peso_ponte, peso_trole, aprox_min, n_rodas_lado, n_rodas_motoras,
frac_lateral, frac_long`, e `phi` **ou** `classe_hc`. `ponte=None` (sem ponte)
continua válido. Nada inventado: tudo é catálogo/projeto.

---

## 5. Não-regressão

- `ponte_rolante._selftest`, `projeto_spec._selftest`, `nbr8400._selftest` verdes.
- Caso `ponte` do `smoke_executivo` inalterado (n_motoras default = n_rodas_lado ⇒
  H_long idêntico; φ input mantido) — 14 pranchas.
- `tests/test_fase4_ponte_estendida.py`: 14 testes (8400 Tab.9/12, rodas motoras,
  gate, mapper).

---

## 6. Respostas ao parecer sênior (2026-07-11)

| Q | Parecer | Situação |
|---|---|---|
| Q1 | `R_roda_max·n_motoras` viola estática | **DEFENDIDO** — é `ΣR_motoras` do trilho carregado (partilha igual), ≤ `frac_long·R_trilho_max`. Fórmula mantida; teto provado no selftest. |
| Q2 | usar `min(Vh, 1,5)` (saturação) | **JÁ IMPLEMENTADO** — `coef_dinamico`: `v = max(0, min(Vh, VH_MAX))`; selftest `coef_dinamico("HC2",2.0)==coef_dinamico("HC2",1.5)`. Sênior validou a matemática. |
| Q3 | B10 sem limite superior → fixar 8×10⁶ | **JÁ IMPLEMENTADO** — `_TAB9_SUP["B10"] = 8_000_000` (absoluto, não aberto/`inf`); selftest `n_ciclos("B10") >= 8e6`. |
| Q4 | usar edição 2019 (Ψ/HC) | **CONFIRMADO** — módulo `nbr8400` é 100% NBR 8400-1:2019. |

Q2 e Q3 já estavam no código desde a fase 4; o parecer os sinalizou por leitura do
markdown. Nenhuma alteração de lógica foi necessária além do reforço de doc/prova
em Q1.

---

*Evidência: NBR 8400-1:2019 lida do PDF `pesquisa/pdfcoffee.com_abnt-nbr-8400-1...`
(Tab.9 p.23, Tab.12 p.20, verbatim). Fadiga Anexo K homologada em PONTE §9 — não
alterada. Selftests `ponte_rolante`, `nbr8400`, `projeto_spec` verdes.*
