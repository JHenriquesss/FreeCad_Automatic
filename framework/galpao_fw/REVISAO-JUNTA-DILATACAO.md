# Revisão — Junta de dilatação / movimento térmico

> **STATUS: ✅ HOMOLOGADO (2026-07-08).** Sênior conferiu `L_max=120·(1−0,33−0,15)=
> 62,4 m`, `n_juntas=⌈100/62,4⌉−1=1`, `δ=12e-6·30·50=18 mm` (todos exatos), os
> fatores FCC Report 65, α=12e-6 e o caráter de **recomendação** (não cláusula
> fechada da NBR 8800) — "precisão absoluta". Duas diretrizes de log aplicadas
> (§4): δ/2 por lado + escolha furo-oblongo×pilar; significado de `rigidez_assimetrica`.

Verifica a **necessidade de junta de dilatação** no galpão (ação de temperatura)
e o **movimento térmico** longitudinal. Fecha a lacuna da ação de temperatura em
edifício longo. **Nível do edifício** (não por elemento).

Código: `junta_dilatacao.py`. Wire: `rodar_galpao.py` → `gate7-junta-dilatacao.txt`.
Última atualização: 2026-07-07.

---

## 1. Método (Bellei 4.5 / Federal Construction Council Report Nº65, via AISC 2005)

Referência extraída do PDF (`Edifícios de Múltiplos Andares em Aço`, Bellei, §4.5)
— não de memória.

### 1.1 Movimento térmico
```
delta = alpha · dT · L        (alongamento/encurtamento total)
```
`alpha = 12×10⁻⁶ /°C` (aço, NBR 8800/Bellei); `dT` = variação de temperatura
(Bellei: média Brasil **±15 °C = 30 °C**); `L` = comprimento do trecho.

### 1.2 Comprimento máximo entre juntas
Guia do FCC Report Nº65 (dT > 20 °C, condição normal no Brasil):
- **120 m** — edifício de **aço retangular**, vários pórticos com rigidez simétrica;
- **60 m** — qualquer material, forma **não retangular** (L, T, U).

Modificado pela **soma algébrica** dos fatores:

| Condição | Fator |
|---|---|
| Sem aquecimento interno | **−33 %** |
| AC + aquecimento + controle contínuo | **+15 %** |
| Bases **fixas** (engastadas) | **−15 %** |
| Maior rigidez lateral em um dos planos | **−25 %** |

(Aquecido + base rotulada ⇒ usa o máximo, sem redução.)

`L_max = base · (1 + Σ fatores)`.

---

## 2. Verificação

`verifica_junta(L_total, dT, retangular, aquecido, ar_condicionado, base_fixa,
rigidez_assimetrica)`:
- `precisa_junta = L_total > L_max`;
- `n_juntas = ⌈L_total/L_max⌉ − 1`; `n_segmentos = n_juntas + 1`;
- movimento do maior segmento `δ = α·dT·L_seg` (a junta/apoio absorve ~metade por lado).

**Ex.** galpão típico (retangular, **sem aquecimento**, **base engastada**):
`L_max = 120·(1 − 0,33 − 0,15) = 62,4 m`. Galpão 100 m → **1 junta**, 2 trechos de
50 m, `δ = 18 mm`. Galpão 40 m → não precisa.

---

## 3. Onde revisar / FLAGS

| Assunto | Função |
|---|---|
| Movimento térmico | `movimento_termico` |
| Comprimento máximo | `comprimento_max_junta` |
| Necessidade + segmentos | `verifica_junta` |

- `dT` e as condições (aquecimento, AC, base, rigidez) são **dados do projeto/sítio**
  — a skill confirma (`params.dT_termico`, `aquecido`, `ar_condicionado`,
  `base_fixed`).
- O **detalhe** da junta (linha dupla de pilares, apoio deslizante) é **projeto
  executivo**.
- O guia (120/60 m + fatores) é **recomendação** de literatura, não cláusula
  fechada da NBR 8800 — o responsável confirma o critério.

---

## 4. Diretrizes de log aplicadas (pós-parecer, 2026-07-08)

Duas recomendações do sênior, para o log não ser ambíguo no detalhamento:

1. **Restrição no apoio** — o `δ` do trecho é repartido: o relatório agora imprime
   **`~δ/2` por lado** e a **escolha executiva**: _furos oblongos / apoio deslizante_
   que absorvam esse `δ/2`, **OU** dimensionar os **pilares de extremidade** para o
   momento do deslocamento imposto no topo (ex. galpão 100 m → 18 mm/trecho →
   **~9 mm por lado**). Vale também no caso "sem junta" (o deslocamento vai todo
   para os apoios de extremidade).
2. **`rigidez_assimetrica` (−25 %)** — documentado no código: é o
   **contraventamento vertical (X) concentrado em UMA fachada/plano** (não
   distribuído) — a estrutura dilata contra o ponto rígido, ampliando a coação.
   Continua sendo **input** do sítio (a skill confirma).
