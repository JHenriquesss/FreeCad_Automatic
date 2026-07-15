# 07 — Discovered Bugs

Este documento registra as inconformidades, inconsistências e erros de método ou lógica encontrados durante a auditoria do código-fonte do framework **FreeCAD Automatic (Steel Warehouse Design Framework)**, bem como a verificação de suas resoluções.

> [!NOTE]
> **Status Geral: ✅ TODOS OS BUGS VERIFICADOS E RESOLVIDOS (2026-07-15)**
> Todos os 9 itens listados abaixo foram auditados no código-fonte e tiveram sua resolução confirmada no commit mais recente. Os testes correspondentes passaram sem regressão.

---

## 1. Erros Críticos de Dimensionamento Estrutural (Risco à Segurança)

### Bug 1.1: [estaca_profunda.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estaca_profunda.py) — Subdimensionamento de 50% da Armadura do Tirante de Blocos de 4 Estacas
* **Arquivo:** [estaca_profunda.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estaca_profunda.py#L396)
* **Descrição Original:** A força de tração no tirante para blocos de $N$ estacas usava `P_est = N_pilar / n_est` em sua fórmula (`T = P_est * braco / d`), o que causava um subdimensionamento de 50% para blocos de 4 estacas. A teoria de Blévot exige que o tirante em cada direção resista ao empuxo das estacas do mesmo lado da linha neutra, ou seja, $T_x = T_y = \frac{N_{pilar}}{2} \cdot \frac{e}{d}$.
* **Status:** **✅ RESOLVIDO E VERIFICADO.** 
  O cálculo foi atualizado para:
  ```python
  T = (N_pilar / 2.0) * braco / d
  ```
  Isso garante a força de tração correta nas duas direções da malha do bloco.

---

## 2. Erros de Lógica de Cálculo e Inconsistências de Geometria

### Bug 2.1: [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) — Inversão Lógica de L_fixo e B_foot com Erro de Cálculo da Excentricidade
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L55-L58)
* **Descrição Original:** Ao fornecer `L_fixo`, o código trocava as variáveis (`B_foot = L_fixo`), misturando as dimensões paralelas e perpendiculares à divisa e distorcendo a excentricidade `e_fixo` e a reação da sapata.
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  O código foi corrigido para manter `B_foot` na direção perpendicular (onde atua a excentricidade `e`) e aplicar `L_fixo` estritamente na direção paralela:
  ```python
  B = B_foot
  if L_fixo:
      L = L_fixo
  else:
      L = R_divisa / sig / B_foot
  ```

### Bug 2.2: [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) — Inconsistência da Fórmula de Momento Fletor da Viga Alavanca com viga_equilibrio.py
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L86) vs [viga_equilibrio.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/viga_equilibrio.py#L76)
* **Descrição Original:** A sapata de divisa superficial usava `M_viga = R_divisa * e`, enquanto o módulo profundo de divisa usava `M_viga = P_divisa * e`, gerando momentos divergentes.
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  Ambos os módulos agora calculam o momento com base na estática exata (corte no centroide da sapata de divisa, onde atua apenas o pilar de divisa):
  ```python
  M_viga = P_divisa * e
  ```

### Bug 2.3: [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) — Falso Positivo (OK) no Status de Flexão da Viga Alavanca em Caso de Falha
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L126)
* **Descrição Original:** A chave `"ok_flexao"` retornava `ok if As_viga else True`. Se o concreto esmagasse por superarmadura (`As_viga` retornava `None`, redefinido como `0.0`), a chave avaliava para `True`.
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  O retorno foi alterado para mapear diretamente o status de ductilidade:
  ```python
  "ok_flexao": ok
  ```

### Bug 2.4: [viga_baldrame.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/viga_baldrame.py) — Omissão de Armadura de Apoio para Flexão Negativa em Vigas Contínuas
* **Arquivo:** [viga_baldrame.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/viga_baldrame.py#L98-L112)
* **Descrição Original:** Sob continuidade, a viga baldrame sofria redução do momento positivo, mas a armadura superior nos apoios (momentos negativos) era omitida (deixando apenas armadura construtiva mínima).
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  Adicionou-se o dimensionamento automático para flexão negativa nos apoios sob continuidade (`M_d_neg = GF * (1/10) * w * L^2`), aplicando a taxa mínima `As_min` e a armadura necessária:
  ```python
  As_sup = max(As_flex_neg + As_tie / 2.0, As_sup_piso)
  ```

---

## 3. Desvios Normativos e Limites de Escopo Omitidos

### Bug 3.1: [estaca_profunda.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estaca_profunda.py) — Cálculo Incorreto do N Médio de Fuste em Decourt-Quaresma
* **Arquivo:** [estaca_profunda.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estaca_profunda.py#L144-L147)
* **Descrição Original:** O limite $3 \le N \le 50$ do método era aplicado à média final, e não a cada camada individualmente antes da média, o que inflava a capacidade com camadas muito duras (N > 50).
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  A média ponderada agora limita o SPT de cada camada individualmente:
  ```python
  N_cam = max(3.0, min(cam["N"], N_LIMITE))
  somaNz += N_cam * dz
  ```

### Bug 3.2: [tercas_nbr14762.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/tercas_nbr14762.py) — Ausência de Validação de Altura Limite do Anexo F sob Continuidade
* **Arquivo:** [tercas_nbr14762.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/tercas_nbr14762.py#L84-L87)
* **Descrição Original:** Quando `continua = True`, o fator $R$ era retornado sem checar se a altura da alma excedia o limite de validade de 292 mm.
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  A validação do escopo do Anexo F foi incluída no fluxo de continuidade:
  ```python
  if continua:
      if bw_mm > 292:
          return None
      return 0.70 if secao == "Z" else 0.60
  ```

### Bug 3.3: [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) — Ausência de Dimensão Limite Mínima
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L59-L61)
* **Descrição Original:** O comprimento paralelo $L$ não tinha limite inferior, permitindo sapatas de divisa com menos de 60 cm para cargas pequenas, infringindo a NBR 6122.
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  A dimensão mínima de 60 cm foi imposta para ambos os lados:
  ```python
  L = max(L, 0.60)
  B = max(B, 0.60)
  ```

---

## 4. Inconformidades nos Relatórios e Apresentação de Resultados

### Bug 4.1: [calhas.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/calhas.py) — Erro de Exibição de Área da Regra de Bellei no Relatório
* **Arquivo:** [calhas.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/calhas.py#L80-L82)
* **Descrição Original:** O relatório exibia a área de lâmina de água `s['As_cm2']` no texto comparativo, gerando contradições visuais como `30 >= 51 cm2 OK`.
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  O memorial foi corrigido para imprimir a área total da seção da calha `B_base * H_max`, exibindo a área molhada util de forma secundária:
  ```python
  f"    Bellei A_secao>=A_contrib: {s['B_base_m']*s['H_max_m']*1e4:.0f} >= {r['area_contrib_m2']:.0f} cm2 (lamina util {s['As_cm2']:.0f} cm2)"
  ```

### Bug 4.2: [vento_nbr6123.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/vento_nbr6123.py) — Hardcoding do Coeficiente 'b' no Memorial de S2
* **Arquivo:** [vento_nbr6123.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/vento_nbr6123.py#L289-L299)
* **Descrição Original:** O relatório imprimia a equação de $S_2$ fixando o coeficiente $b$ em `1,00`, ignorando a variação por categoria de solo da Tabela 1.
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  O dicionário de retorno agora exporta o `b` do solo e a impressão o lê dinamicamente:
  ```python
  L.append(f"  S2 = {r['b']:.2f}*{r['Fr']:.2f}*({r['z']:.1f}/10)^{r['p']:.3f} = {r['s2']:.3f}")
  ```

### Bug 4.3: [fogo_nbr14323.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/fogo_nbr14323.py) — Não-monotonicidade da Tabela de Pintura Intumescente
* **Arquivo:** [fogo_nbr14323.py](file:///C:/Users/joseh/OneDrive/%C3%81rea%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/fogo_nbr14323.py#L151-L155)
* **Descrição Original:** A tabela de espessuras continha valores inconsistentes que diminuíam a proteção para massividades mais altas (ex: $1.27 \to 0.88$ mm).
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  Os dados foram corrigidos a partir das cartas de cobertura Nulifire S605 para garantir um comportamento puramente não-decrescente em $u/A$:
  ```python
  tabela = [
      (55,  0.49, 1.27, 1.73, 3.96),
      (240, 0.49, 1.27, 2.31, 5.94),
      (334, 0.49, 2.23, None, None),
  ]
  ```
