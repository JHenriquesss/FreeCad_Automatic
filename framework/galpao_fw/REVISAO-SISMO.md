# Revisão — Ação sísmica (NBR 15421:2023)

> **STATUS: ✅ HOMOLOGADO — PRONTO PARA PRODUÇÃO (2026-07-08).** Sênior refez o
> cálculo (zona 3, D, hn=8): `ags0=0,225`, `Sa,max=0,5625 g`, `Cs=0,5625/3,5=0,1607`
> (< cap 0,185 → governado pelo platô), `H=160,7 kN` — todos exatos; interpolação
> `Ca(0,125)=1,55` validada; triagem 0/1/2-4 "tradução brilhante" da 7.3.2. Sem
> erro. Ressalvas (confirmar `I` e a dupla interpolação Ca/Cv com a skill) são
> lembretes de input, já cobertos pelos FLAGS. Liberado.

Fecha a lacuna da **ação sísmica** — a última grande pendência do projeto completo.
Método e constantes **extraídos do PDF** `NBR 15421:2023` (em `pesquisa/aço/`), não
de memória. Nível do **edifício**. Código: `sismo_nbr15421.py`. Wire:
`rodar_galpao.py` → `gate7-sismo.txt`.

---

## 1. Triagem por zona (Tabelas 1 e 5)

| Zona | ag (Tab.1) | Categoria (Tab.5) | Requisito |
|---|---|---|---|
| 0 | 0,025 g | A | **Nenhum** (7.3.2) — dispensado |
| 1 | ≤0,05 g | A | Simplificado `Fx = 0,01·wx` (7.3.2) |
| 2 | ≤0,10 g | B | Forças horizontais equivalentes (Seção 9) |
| 3 | ≤0,15 g | C | idem |
| 4 | 0,15 g | C | idem |

A maior parte do Brasil é **Zona 0** → dispensado (default do código).

## 2. Espectro de resposta de projeto Sa(T) (6.3)

`ags0 = Ca·ag` ; `ags1 = Cv·0,75·ag` (em fração de g). `Ca`, `Cv` da **Tabela 3**
por classe do terreno (A..E) e `ag` (interpola 0,10↔0,15 g). Quatro trechos (T em s):
```
0 ≤ T ≤ 0,04·Cv/Ca :  Sa = ags0·(37,5·T·Ca/Cv + 1)
0,04 ≤ T ≤ 0,30·Cv/Ca :  Sa = 2,5·ags0                (platô)
0,30 ≤ T ≤ 2,0·Cv/Ca :  Sa = ags1/T
T ≥ 2,0·Cv/Ca :  Sa = 2·(Cv/Ca)·ags1/T²
```

## 3. Força horizontal total (9.1)

```
H = Cs·W        Cs = 2,5·ags0/(R/I)  ≤  ags1/(T·(R/I))  ≥  0,01
```
`W` = peso efetivo (8.7.2, **input**). `R` = coef. de modificação de resposta
(**Tabela 6**: aço momento **3,5**; aço treliçado 3,25; pêndulo invertido/pilar em
balanço 2,5; …). `I` = fator de importância (**Tabela 4**: 1,0/1,25/1,50).

**Período aproximado (9.2):** `Ta = C_T·hn^x` — aço momento `C_T=0,0724, x=0,8`;
aço treliçado `0,0731, x=0,75`; outras `0,0488, x=0,75`. (`Cup` da Tab.10 só limita
o T de extração modal; usa-se `Ta` direto.)

**Distribuição vertical (9.3):** `Fx = Cvx·H`, `Cvx = wx·hx^k/Σwi·hi^k`;
`k=1` (T<0,5 s) / `(T+1,5)/2` (0,5–2,5 s) / `2` (T>2,5 s). **Galpão de 1 nível** →
tudo no topo (trivial).

## 4. Validação (selftest)

- **Espectro:** platô = `2,5·ags0`; trecho `ags1/T`; `Ca/Cv` classe D em `ag=0,15`
  → 1,5/2,2, e interpolação em 0,125 g → `Ca=1,55`.
- **Cs:** zona 3, `ag=0,15`, classe D, aço momento, `hn=8 m` → `Ta=0,382 s`,
  `Cs=2,5·(1,5·0,15)/3,5 = 0,1607` (platô < cap 0,185), ≥0,01.
- **Triagem:** zona 0 → `H=0` (dispensado); zona 1 → `H=0,01·W`; zona 3 →
  `H=Cs·W`. Ex.: W=1000 kN → **H=160,7 kN** (16 % do peso, zona alta + solo mole).

## 5. Onde revisar / FLAGS

| Assunto | Função | Item |
|---|---|---|
| Espectro Sa(T) | `espectro_sa` | 6.3 |
| Ca, Cv | `coef_ca_cv` | Tab.3 |
| Cs | `coef_resposta_cs` | 9.1 |
| Período | `periodo_aproximado` | 9.2 |
| Força total + distribuição | `verifica_sismo` | 9.1/9.3 |

- **`ag`/zona** (mapa de zoneamento), **classe do terreno** (Vs30/SPT, Tab.2),
  **R** (sistema, Tab.6), **I** (categoria de utilização, Tab.4) e **W** (peso
  efetivo, 8.7.2) são **dados do sítio/projeto** — a skill confirma (`params.sismo`).
- Combinação última **EXCEPCIONAL** (NBR 8681: `γq=1,0`; vento/recalque/retração
  não entram nessa combinação).

> **Limites (escopo):** método **estático** das forças horizontais equivalentes
> (Seção 9) — a análise modal espectral (Seção 10) e a histórica (Seção 11) ficam
> fora. Torção acidental (9.4.2), efeitos P-Δ/θ (9.6) e deslocamentos relativos
> (9.5, Tab.9) não automatizados. Detalhamento sismorresistente (ductilidade,
> ligações) é do projeto do material. `Ω0`/`Cd` (Tab.6) tabelados, não aplicados.

---

## 6. Sismo → ENVELOPE do pórtico (combinação excepcional) — feature 2026-07-08

> **STATUS: ✅ HOMOLOGADO (2026-07-09).** Antes o sismo era **calculado mas não
> redimensionava** nada (H isolado no memorial). Agora entra no envelope do
> pórtico, da base e do joelho como **combinação última excepcional**.

### 6.1 — Combinação (NBR 15421:2023 §5.4, lida VERBATIM do PDF)

A ação sísmica é **excepcional** (§5.2). §5.4 remete à **NBR 8681:2003 5.1.3.3**:

- **γg** (Tab.1/2 NBR 8681): para edificações com ações variáveis de utilização
  **≤ 5 kN/m²**, quando o efeito permanente for **desfavorável**, `γg = 1,2`
  (favorável `γg = 1,0`).
- **γq = 1,0** (Tab.4/5) para as ações variáveis na combinação excepcional.
- **γexc = 1,0** (5.1.4.3) para a ação sísmica.
- **"os efeitos de vento, recalques de apoio e retração dos materiais NÃO precisam
  ser considerados na combinação última excepcional"** — vento **fora**.

Sobrecarga de cobertura tem **ψ2 = 0** (NBR 8800 Tab.2, coberturas) → a Q vertical
**não acompanha** a combinação sísmica. Resultam as combinações (reversíveis ±E):

```
C6_sismo_Gdesf_P/N: 1,20·G ± 1,00·SISMO
C6_sismo_Gfav_P/N : 1,00·G ± 1,00·SISMO     (sem vento, sem Q)
```

### 6.2 — Força sísmica no pórtico

`H = Cs·W` (total do edifício, §9.1) → cortante de piso atribuído a **um pórtico
transversal** pela largura tributária: `E = H·(vão / comprimento)`. Aplicada no
**nível do beiral** (galpão 1 nível), dividida nos dois beirais (`case_sismo`). A
reversibilidade vem do fator ±1,0 nas combinações C6.

```python
# rodar_galpao.py
H_sismo = rs.get("H", 0.0)
E_frame = H_sismo * g["bay"] / g["comprimento"]
gp.configurar(sismo={"E": E_frame} if E_frame > 1e-9 else False)
```

O `SISMO` entra em `galpao_portico` (`case_sismo`, combos C6), em
`estabilidade_b1b2` (`_apply_case` cs="SISMO", nt/lt automático — a contenção
fictícia do beiral captura a força lateral, idêntico ao vento) e no envelope de
**base** e **joelho** (`_casos_mf_reac` + `_combos_elu(PONTE, SISMO)`).

### 6.3 — FLAGS / limites

1. **`E = H·vão/comprimento`** (distribuição por largura tributária) — pórtico
   interno típico. Empenas/pórticos de extremidade têm ½ da largura; o valor é
   **conservador** para o interno. FLAG para o engenheiro confirmar a distribuição.
2. **Peso efetivo W** (8.7.2) = entrada do sítio; a força escala linearmente nele.
3. **P-Δ sísmico (θ, 9.6) implementado** — `deslocamento_theta` calcula δx=Cd·δxe/I
   (9.5) e θ=Px·Δx/(Hx·hsx·Cd) (9.6): θ<0,10 dispensa 2ª ordem; 0,1<θ≤θmax=0,5/Cd≤0,25
   amplifica por 1/(1−θ); θ>θmax = instável. δxe = drift do beiral sob o caso sísmico
   característico (do pórtico). Ref zona 4/pêndulo: θ=0,022 → dispensada.
4. **Direção**: análise no plano do pórtico (transversal). A combinação ortogonal
   **100/30** (8.5) está disponível em `combinacao_ortogonal(Ex, Ey)` =
   max(|Ex|+0,3|Ey|; |Ey|+0,3|Ex|), **exigida só p/ cat. C com irregularidade de
   plano Tipo 3** — não se aplica ao galpão regular (sem acoplamento); a resposta
   longitudinal (Ey) vem da análise dos contraventos, fornecida pelo engenheiro.
5. Reversível ±E cobre os dois sentidos; o pior entra no envelope.

### 6.4 — Não-regressão

Referência 20×10 é **zona 0** (dispensado) → `E=0` → `gp.SISMO=None` → envelope
**idêntico** ao anterior (coluna 0,42 / viga 0,68 / base C2_uplift_W2 −57,5 kNm
inalterados). Teste zona 4 / classe E / pêndulo invertido / I=1,25 / W=1500:
`Cs=0,394`, `H=590,6 kN`, `E=147,7 kN/pórtico` → **C6_sismo_Gdesf_P governa a
base** (M=261,7 kNm) e sobe a coluna a 0,91. Aguarda revisão.
