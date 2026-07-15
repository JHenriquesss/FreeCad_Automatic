# 07 — Discovered Bugs

Este documento registra as inconformidades, inconsistências e erros de método ou lógica encontrados durante a auditoria minuciosa do código-fonte do framework **FreeCAD Automatic (Steel Warehouse Design Framework)**.

---

## STATUS DE RESOLUÇÃO (2026-07-15)

Os 12 apontamentos foram revisados **um a um** contra o notebook *"Diretrizes Técnicas
para Revisão de Projetos de Engenharia"* (fontes normativas: NBR 6118/6122/6123/14323/14762,
Blévot, Alonso, Velloso & Lopes, Décourt-Quaresma). **Veredito: todos os 12 procedem** e
**todos foram corrigidos** (selftests dos módulos passam).

> ⚠️ **Reclassificação do Bug 1.1:** numa análise preliminar por estática pura, o 1.1 havia
> sido considerado *falso positivo* (a força **por tirante de borda** vale de fato
> `N(2s−a_p)/16d`). A fonte autoritativa, porém, mostrou que o bloco de 4 estacas é armado
> **em malha**, cujo esquema é igual ao do bloco de 2 estacas: a força de projeto **por
> direção** é `N(2s−a_p)/8d` (empuxo das **duas** estacas de um lado da linha neutra). Como o
> código reportava `As` **por direção** usando `N/4`, subdimensionava a malha em 50%. **Bug
> real, corrigido.**

| # | Arquivo | Correção aplicada |
|---|---------|-------------------|
| 1.1 | `estaca_profunda.py` | `T = (N/2)·braço/d` (era `N/n_est` = `N/4` p/ 4 estacas) |
| 2.1 | `sapata_divisa.py` | `e` sempre da dim. perpendicular (B); sem trocar B↔L |
| 2.2 | `sapata_divisa.py` | `M_viga = P_divisa·e` (era `R_divisa·e`) — alinhado a `viga_equilibrio.py` |
| 2.3 | `sapata_divisa.py` | `ok_flexao = ok` (não retorna mais `True` em falha) |
| 2.4 | `viga_baldrame.py` | dimensiona `As_sup` p/ momento negativo (M⁻ ~ wL²/10) quando contínua |
| 3.1 | `estaca_profunda.py` | limite 3≤N≤50 aplicado **por camada antes** da média |
| 3.2 | `tercas_nbr14762.py` | retorna `None` se `bw>292 mm` também no ramo contínuo |
| 3.3 | `sapata_divisa.py` | clamp L,B ≥ 0,60 m (NBR 6122 7.7.1) |
| 4.1 | `calhas.py` | exibe área da seção (coerente com `ok_bellei`) + lâmina útil |
| 4.2 | `vento_nbr6123.py` | relatório usa `b` real da Tab.1 (era `1,00` hardcoded) |
| 4.3 | `fogo_nbr14323.py` | tabela S605 correta (monotônica) + fallback seguro (era mistura S605/S607/Calatherm) |

---

## 1. Erros Críticos de Dimensionamento Estrutural (Risco à Segurança)

### Bug 1.1: [estaca_profunda.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estaca_profunda.py) — Subdimensionamento Crítico de 50% da Armadura do Tirante de Blocos de 4 Estacas
* **Arquivo:** [estaca_profunda.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estaca_profunda.py#L384-L393)
* **Descrição:** No método `bloco_coroamento`, a força de tração no tirante para blocos de $N$ estacas é calculada pela fórmula:
  ```python
  P_est = N_pilar / n_est
  braco = espacamento / 2.0 - a_pilar / 4.0
  T = P_est * braco / d
  ```
  Se o bloco tem 4 estacas (`n_est = 4`), a carga em cada estaca é `P_est = N_pilar / 4`. No entanto, pela teoria de bielas e tirantes de Blévot para blocos de 4 estacas em malha quadrada, o tirante em cada direção ($x$ e $y$) deve resistir à componente horizontal da biela de **duas estacas** de um mesmo lado da linha neutra. Portanto, a força total do tirante em cada direção deve ser:
  $$T_x = T_y = 2 \cdot P_{est} \cdot \frac{e}{d} = \frac{N_{pilar}}{2} \cdot \frac{e}{d}$$
  O código calcula apenas $T = P_{est} \cdot \frac{e}{d}$ (que equivale a $\frac{N_{pilar}}{4} \cdot \frac{e}{d}$), o que resulta em **exatamente metade (50%) da força de tração e da área de aço ($As$) necessárias** em cada direção.
* **Impacto:** Altíssimo risco estrutural de colapso por tração/fissuração excessiva na base do bloco de coroamento de 4 estacas.

---

## 2. Erros de Lógica de Cálculo e Inconsistências de Geometria

### Bug 2.1: [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) — Inversão Lógica de L_fixo e B_foot com Erro de Cálculo da Excentricidade
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L47-L50)
* **Descrição:** Quando o usuário fornece `L_fixo` (comprimento da sapata paralelo à divisa), o código inverte as variáveis:
  ```python
  if L_fixo:
      B_foot, L_fixo = L_fixo, None
  ```
  Isso faz com que o valor de `L_fixo` passe a ser usado como a dimensão perpendicular à divisa (`B_foot`). Posteriormente, a excentricidade é calculada como:
  ```python
  e_fixo = max((B_foot - b_col_div) / 2.0, 0.0)
  ```
  Onde `b_col_div = 2.0 * dist_divisa` (dimensão perpendicular da coluna). Subtrair `b_col_div` (perpendicular) de `B_foot` (que agora é o `L_fixo` paralelo) é um erro dimensional e geométrico. A excentricidade perpendicular real deveria ser calculada com base na largura perpendicular calculada `L` (que o código inverteu para ser a variável de área).
* **Impacto:** O dimensionamento com comprimento paralelo fixo gera sapatas com geometria incorreta e excentricidade de projeto errônea.

### Bug 2.2: [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) — Inconsistência da Fórmula de Momento Fletor da Viga Alavanca com viga_equilibrio.py
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L77) vs [viga_equilibrio.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/viga_equilibrio.py#L76)
* **Descrição:** Em `sapata_divisa.py` o momento máximo na viga alavanca é calculated como `M_viga = R_divisa * e`. No entanto, na revisão sênior do módulo profundo correspondente (`viga_equilibrio.py`, Parecer Item 48), ficou demonstrado por estática exata que o momento fletor correto no centroide é `M_viga = P_divisa * e` (já que a única força à direita da seção do centroide é a carga do pilar, não a reação amplificada).
* **Impacto:** O momento fletor na viga de equilíbrio superficial é sobredimensionado em relação ao módulo profundo.

### Bug 2.3: [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) — Falso Positivo (OK) no Status de Flexão da Viga Alavanca em Caso de Falha
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L117)
* **Descrição:** A chave `"ok_flexao"` no dicionário de retorno da viga alavanca é definida como:
  ```python
  "ok_flexao": ok if As_viga else True
  ```
  Se a rotina `_armadura_flexao` falhar por compressão excessiva do concreto (quando a viga não tem capacidade e `As_viga` retorna `None`), o código define `ok = False` e `As_viga = 0.0`. Devido à expressão ternária, como `As_viga` é `0.0` (avaliado como `False`), a expressão retorna `True`.
* **Impacto:** O programa reporta que o dimensionamento à flexão passou (`ok_flexao: True`), escondendo uma falha grave de esmagamento do concreto.

### Bug 2.4: [viga_baldrame.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/viga_baldrame.py) — Omissão de Armadura de Apoio para Flexão Negativa em Vigas Contínuas
* **Arquivo:** [viga_baldrame.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/viga_baldrame.py#L96)
* **Descrição:** Quando o baldrame é definido como contínuo (`continuidade = "continua"`), o coeficiente de momento positivo é reduzido para `1.0/10.0`. Porém, vigas contínuas geram momentos fletores negativos nos apoios (sobre as sapatas). O código não calcula esses momentos negativos e assume que a armadura superior `As_sup` precisa apenas resistir à tração de amarração e porta-estribo:
  ```python
  As_sup = max(As_tie / 2.0, AS_CONSTRUTIVA_SUP)
  ```
* **Impacto:** Risco severo de fissuração incontrolável ou ruptura por flexão negativa sobre os apoios (sapatas) em vigas de baldrame contínuas.

---

## 3. Desvios Normativos e Limites de Escopo Omitidos

### Bug 3.1: [estaca_profunda.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estaca_profunda.py) — Cálculo Incorreto do N Médio de Fuste em Decourt-Quaresma
* **Arquivo:** [estaca_profunda.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estaca_profunda.py#L143-L146)
* **Descrição:** A rotina `capacidade_decourt_quaresma` calcula o $N_{med}$ fazendo a média ponderada simples dos valores de $N$ das camadas e, em seguida, limita a média a $[3, 50]$. Todavia, o método de Décourt-Quaresma (1978) exige que os limites de $3 \le N \le 50$ sejam aplicados a **cada camada individualmente** antes do cálculo da média.
* **Impacto:** Camadas profundas com SPT muito alto (ex: N = 60 ou 80) elevam indevidamente a média do fuste, resultando em uma capacidade lateral calculada superestimada (contra a segurança).

### Bug 3.2: [tercas_nbr14762.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/tercas_nbr14762.py) — Ausência de Validação de Altura Limite do Anexo F sob Continuidade
* **Arquivo:** [tercas_nbr14762.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/tercas_nbr14762.py#L84-L85)
* **Descrição:** No método `fator_R_anexoF`, quando a viga é contínua (`continua = True`), a função retorna o fator diretamente:
  ```python
  if continua:
      return 0.70 if secao == "Z" else 0.60
  ```
  Isso ignora a verificação de limite de altura da alma $b_w \le 292$ mm. Para vigas biapoiadas, o limite é verificado e retorna `None` se excedido.
* **Impacto:** Terças contínuas com altura superior a 292 mm são incorretamente aceitas no escopo do Anexo F.

### Bug 3.3: [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) — Ausência de Dimensão Limite Mínima
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L54)
* **Descrição:** A norma NBR 6122 exige que nenhuma dimensão de sapata isolada ou associada seja inferior a 60 cm. No dimensionamento da sapata de divisa, a dimensão paralela $L$ é calculada de forma direta por equilíbrio de pressões, podendo resultar em valores impraticáveis e proibidos (ex: $L = 0.40$ m) para cargas leves.
* **Impacto:** Geração de geometrias de fundação que violam a dimensão mínima regulamentar da NBR 6122.

---

## 4. Inconformidades nos Relatórios e Apresentação de Resultados

### Bug 4.1: [calhas.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/calhas.py) — Erro de Exibição de Área da Regra de Bellei no Relatório
* **Arquivo:** [calhas.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/calhas.py#L80)
* **Descrição:** No relatório impresso em `relatorio_pt`, o programa exibe a área molhada calculada `s['As_cm2']` (área da lâmina d'água) na comparação da Regra de Bellei (1 cm² de calha / m² de telhado):
  ```python
  f"    Bellei As>=A_contrib: {s['As_cm2']:.0f} >= {r['area_contrib_m2']:.0f} cm2"
  ```
  A verificação de aprovação interna (`ok_bellei`) usa corretamente a área total da seção da calha `B_base * H_max * 10000`. Isso gera textos contraditórios como:
  `Bellei As>=A_contrib: 30 >= 51 cm2 OK` (onde 30 é menor que 51, mas o status exibe OK porque a área total de 120 cm² é de fato maior que 51).
* **Impacto:** Confusão e desconfiança na leitura do memorial descritivo por auditores humanos.

### Bug 4.2: [vento_nbr6123.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/vento_nbr6123.py) — Hardcoding do Coeficiente 'b' no Memorial de S2
* **Arquivo:** [vento_nbr6123.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/vento_nbr6123.py#L299)
* **Descrição:** No método `relatorio_pt`, o texto explicativo da fórmula do fator $S_2$ fixa o coeficiente $b$ em `1,00`:
  ```python
  L.append(f"  S2 = 1,00*{r['Fr']:.2f}*({r['z']:.1f}/10)^{r['p']:.3f} = {r['s2']:.3f}")
  ```
  No entanto, o coeficiente $b$ varia conforme a categoria do solo (Tabela 1 da NBR 6123). Ele é `1.00` apenas para a Categoria II. Para a Categoria III, por exemplo, ele vale `0.94`.
* **Impacto:** O memorial descritivo exibe uma equação matematicamente errada para terrenos que não sejam de Categoria II.

### Bug 4.3: [fogo_nbr14323.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/fogo_nbr14323.py) — Não-monotonicidade da Tabela de Pintura Intumescente
* **Arquivo:** [fogo_nbr14323.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/fogo_nbr14323.py#L147-L153)
* **Descrição:** A tabela de espessuras de tinta intumescente necessária apresenta variações não-monótonas absurdas com o fator de massividade $u/A$. Perfis com maior massividade (que aquecem mais rápido) teoricamente necessitam de maior espessura de tinta, porém o código estabelece espessuras menores em faixas superiores (ex: para TRRF 60 min, passa de $1.27$ mm para $u/A \le 55$ para $0.88$ mm para $u/A \le 105$).
* **Impacto:** Geração de espessuras de proteção ineficientes e perigosas sob o ponto de vista da segurança ao fogo.
