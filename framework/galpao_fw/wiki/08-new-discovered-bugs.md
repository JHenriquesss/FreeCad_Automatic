# 08 — New Discovered Bugs (Auditoria com Base em Diretrizes Técnicas)

Este documento registra as novas inconformidades, inconsistências e riscos estruturais identificados no framework **FreeCAD Automatic (Steel Warehouse Design Framework)** durante a auditoria baseada no caderno de *"Diretrizes Técnicas para Revisão de Projetos de Engenharia"*, bem como a verificação de suas resoluções.

> [!NOTE]
> **Status Geral (2026-07-15):**
> - **Fase 1 (bugs 8.1–8.4):** ✅ 4/4 verificados e corrigidos — commit `dad7b87`.
> - **Fase 9 (bugs 8.5–8.13):** ✅ 7 reais corrigidos (8.5, 8.6, 8.7, 8.8, 8.10, 8.12, 8.13) + ⚪ 2 falsos positivos (8.9, 8.11) — commit `06130c0`.
> - **Fase 10 (bugs 8.14–8.17):** ✅ 3 reais corrigidos (8.15, 8.16, 8.17) + ⚪ 1 falso positivo (8.14) — verificados no notebook *"Diretrizes Técnicas para Revisão de Projetos de Engenharia"*.

---

## Índice das Inconformidades

| ID | Nível de Risco | Módulo Afetado | Descrição do Problema | Referência Normativa | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bug 8.1** | 🔴 Crítico | [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) | Omissão total da verificação de esforço cortante na viga alavanca superficial. | NBR 6118 (Item 17.4) | **✅ Resolvido** |
| **Bug 8.2** | 🔴 Crítico | [galpao_portico.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/galpao_portico.py) | Inclusão de sobrecarga variável ($Q$) atuando como estabilizadora em combinações de arrancamento por vento (uplift). | NBR 8681 e NBR 8800 | **✅ Resolvido** |
| **Bug 8.3** | 🟡 Alto | [check_nbr8800.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/check_nbr8800.py) | Esforço axial de tração atuando de forma a reduzir/subtrair a utilização na interação de flexo-tração. | NBR 8800 (Item 5.5.1) | **✅ Resolvido** |
| **Bug 8.4** | 🟡 Médio | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Ausência de travamento transversal (baldrame ortogonal) para blocos apoiados sobre 1 ou 2 estacas. | NBR 6122 (Item 8.4.1) | **✅ Resolvido** |
| **Bug 8.5** | 🔴 Crítico | [escada.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/escada.py) | Dupla multiplicação por largura no peso próprio permanente. | NBR 6120 / NBR 8800 | **✅ Resolvido** |
| **Bug 8.6** | 🟡 Médio | [escada.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/escada.py) | Variável de flecha delta morta com inércia fixa fictícia de 1e-8. | NBR 8800 (Item C.1) | **✅ Resolvido** |
| **Bug 8.7** | 🟡 Médio | [plataforma.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/plataforma.py) | Bypass rígido não-normativo na verificação de vibração para L <= 4.0m. | NBR 8800 (Anexo L.1.2) | **✅ Resolvido** |
| **Bug 8.8** | 🟡 Médio | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da elevação vertical na chamada de cálculo hidráulico da calha. | NBR 10844 | **✅ Resolvido** |
| **Bug 8.9** | 🟡 Médio | [junta_dilatacao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/junta_dilatacao.py) | Vulnerabilidade em acúmulo aditivo de fatores de redução de junta térmica. | FCC Report 65 | **⚪ Falso positivo** |
| **Bug 8.10** | 🟡 Baixo | [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) | Parâmetro orfão b_col_paralela e largura de viga alavanca hardcoded. | NBR 6122 / NBR 6118 | **✅ Resolvido** |
| **Bug 8.11** | 🔴 Crítico | [gusset_ligacao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/gusset_ligacao.py) | Definição de comprimento de flambagem L_livre padrão incorreta usando Lc. | AISC DG29 / Thornton | **⚪ Falso positivo** |
| **Bug 8.12** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Esforço do tirante de terça Nsd_tirante hardcoded em 8.0 kN sem cálculo real. | NBR 8800 | **✅ Resolvido** |
| **Bug 8.13** | 🟡 Médio | [fogo_nbr14323.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/fogo_nbr14323.py) | Espessura de tinta intumescente é ignorada no cálculo incremental de temperatura do aço. | NBR 14323 | **✅ Resolvido** |
| **Bug 8.14** | 🔴 Crítico | [estabilidade_b1b2.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estabilidade_b1b2.py) | Omissão do fator $B_2$ na amplificação do esforço cortante de translação lateral $V_{lt}$. | NBR 8800 (Item D.2.4) | **⚪ Falso positivo** |
| **Bug 8.15** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Erro de "fencepost" no cálculo do vão de flambagem superior do rafter ($Lb_{terca}$). | NBR 8800 (Anexo J.4.2) | **✅ Resolvido** |
| **Bug 8.16** | 🟡 Médio | [estabilidade_b1b2.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estabilidade_b1b2.py) | Ausência de salvaguardas para $B_2$ negativo ou excessivo (instabilidade de 2ª ordem). | NBR 8800 (Item 4.9.7) | **✅ Resolvido** |
| **Bug 8.17** | 🟡 Médio | [console_ponte.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/console_ponte.py) | Omissão do momento horizontal $M_z$ (surto lateral) na flexão da raiz da chapa do console. | NBR 8800 (§5.4) | **✅ Resolvido** |


---

## 1. Detalhes das Correções e Verificação

### Bug 8.1: Omissão de Cisalhamento na Viga Alavanca da Sapata de Divisa
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L96-L118)
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  O módulo agora importa `viga_baldrame as vb` e realiza a verificação de cisalhamento da viga de equilíbrio chamando a função `vb._verifica_cortante(V_d, b_viga, d_viga, fck, fyk)`. O loop de otimização de dimensões foi atualizado para incrementar a altura da viga ($h_{viga}$) de forma iterativa até que passe tanto nos critérios de flexão quanto de biela/estribos de cisalhamento.
  ```python
  cr = vb._verifica_cortante(V_d, b_viga, d_viga, fck, fyk)
  ok_flex = ok and As_viga is not None
  ok_cort = cr["ok_biela"] and cr["ok_min"]
  ```

---

### Bug 8.2: Sobrecarga Variável Estabilizando Combinações de Uplift (Vento)
* **Arquivo:** [galpao_portico.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/galpao_portico.py#L363-L366)
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  A combinação favorável de projeto (`"Gfav"`) na rotina de geração de combinações matriciais do pórtico teve o fator da sobrecarga variável ($Q$) ajustado para `0.00`:
  ```python
  # Gfav: G FAVORAVEL (gamma_g=1,0) com vento principal (uplift). A sobrecarga Q
  # (variavel gravitacional) NAO pode estabilizar o arrancamento -> gamma_q=0
  for tag, gf, qf, wf in [("grav", 1.25, 1.50, 0.6 * 1.40),
                           ("uplift", 1.00, 0.00, 1.40),
                           ("Gdesf", 1.25, 0.80, 1.40),
                           ("Gfav", 1.00, 0.00, 1.40)]:
  ```
  Isso elimina o risco de subdimensionamento das ancoragens e fundações devido ao auxílio fictício de sobrecargas de cobertura durante o vento extremo.

---

### Bug 8.3: Esforço de Tração Axial Reduzindo a Utilização na Flexo-Tração
* **Arquivo:** [check_nbr8800.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/check_nbr8800.py#L182-L185)
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  A extração de frações de utilização de esforços axiais e momentos fletores na interação de perfis de aço foi alterada para utilizar o valor absoluto, impedindo que trações negativas decresçam o fator total sob flexão combinada:
  ```python
  # NBR 8800 5.5.1.2 aplica-se a forca axial de tracao OU compressao: a interacao
  # SOMA os modulos das utilizacoes. Usar abs() impede que a tracao (Nsd<0) subtraia
  n, m = abs(Nsd) / Nc_Rd, abs(Msd) / Mrd
  ```

---

### Bug 8.4: Ausência de Travamento Transversal Obrigatório para Fundações Estabilizadas por 1 ou 2 Estacas
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L525-L553)
* **Status:** **✅ RESOLVIDO E VERIFICADO.**
  O script principal foi modificado para identificar blocos com $n_{estacas} \le 2$ e dimensionar automaticamente uma viga/cinta de travamento transversal ortogonal ao galpão. Essa cinta é projetada para resistir à excentricidade executiva acidental regulamentar, calculada como 10% da carga vertical do pilar ($N_{amarracao} = 0,10 \cdot N_{pilar}$), com os resultados reportados no memorial executivo `gate7-travamento-transversal.txt`.
  ```python
  n_est_blk = re_["grupo"]["n"]
  if n_est_blk <= 2:
      N_cinta = 0.10 * N_pilar
      # ... dimensiona e gera gate7-travamento-transversal.txt via vbal.verifica_baldrame
  ```

---

## 2. Novos Bugs Identificados (Fase 9 - Discovery)

> [!NOTE]
> **Status da Fase 9 (verificação NotebookLM + correção — 2026-07-15):** dos 9 novos
> bugs, **7 foram confirmados reais e corrigidos** (8.5, 8.6, 8.7, 8.8, 8.10, 8.12, 8.13)
> e **2 foram reclassificados como FALSO POSITIVO** (8.9 e 8.11) após verificação
> normativa no notebook *"Diretrizes Técnicas para Revisão de Projetos de Engenharia"*.
>
> | ID | Veredito | Verificação normativa (MCP) |
> | :-- | :-- | :-- |
> | 8.5 | ✅ Real → corrigido | Erro dimensional (kN/m × m); só carga permanente |
> | 8.6 | ✅ Real → corrigido | Código morto (`delta` com `1e-8` nunca usado); removido |
> | 8.7 | ✅ Real → corrigido | NBR 8800 L.1.2: "em nenhum caso f < 3 Hz" — sem isenção por vão |
> | 8.8 | ✅ Real → corrigido | NBR 10844: parede vertical contribui 50% (`h_elev/2`); feature não era ligada |
> | 8.9 | ⚪ **Falso positivo** | FCC Report 65 é **aditivo** ("soma algébrica dos fatores") — código correto |
> | 8.10 | ✅ Real → corrigido | Param órfão `b_col_paralela` agora define `b_viga` |
> | 8.11 | ⚪ **Falso positivo** | Thornton: `L_livre = Lc` como fallback é **conservador** e já documentado |
> | 8.12 | ✅ Real → corrigido | Tirante = componente tangencial acumulada; agora escala com inclinação/vão |
> | 8.13 | ✅ Real → corrigido | NBR 14323 Anexo B: temperatura depende de `tp`; fator fixo 0,35 é inaceitável |

### Bug 8.5: Dupla Multiplicação por Largura no Peso Próprio em `escada.py`
* **Arquivo:** [escada.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/escada.py#L46)
* **Status:** **✅ RESOLVIDO** — `w_perm = (PESO_DEGRAU * largura + 0.50) / 2.0` (removido o `* largura` redundante). Selftest OK.
* **Risco:** 🔴 Crítico
* **Descrição:** A fórmula de carga permanente linear por longarina multiplica o termo linear por `largura` duas vezes:
  ```python
  w_perm = (PESO_DEGRAU * largura + 0.50) * largura / 2.0
  ```
  `PESO_DEGRAU * largura` já é a carga linear dos degraus em kN/m. Somar `0.50` (peso da longarina e guarda-corpo em kN/m) e multiplicar o resultado por `largura / 2.0` gera uma inconsistência dimensional de unidades e altera os esforços reais das longarinas (subdimensionando para larguras menores que 2.0 m e superdimensionando para larguras maiores). O correto seria apenas `w_perm = (PESO_DEGRAU * largura + 0.50) / 2.0`.

---

### Bug 8.6: Variável de Flecha Morta com Inércia Fixa Fictícia em `escada.py`
* **Arquivo:** [escada.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/escada.py#L52)
* **Status:** **✅ RESOLVIDO** — linha `delta` (com `1e-8`) removida; mantido só o limite `lim_delta` (a flecha real usa o `Ix` do perfil no loop). Impacto funcional nulo (era código morto).
* **Risco:** 🟡 Médio
* **Descrição:** A variável global `delta` calcula uma flecha teórica antes da iteração dos perfis utilizando o momento de inércia fixado como `1e-8` m⁴ (fictício):
  ```python
  delta = 5.0 * (w_perm + 0.6 * w_acid) * L_long ** 4 / (384.0 * 200e6 * 1e-8)
  ```
  Essa variável nunca é utilizada (a verificação real ocorre dentro do loop usando o $I_x$ real do perfil em `delta_real`), tratando-se de código morto e conceitualmente incorreto.

---

### Bug 8.7: Bypass Rígido Não-Normativo na Vibração de Plataformas em `plataforma.py`
* **Arquivo:** [plataforma.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/plataforma.py#L57)
* **Status:** **✅ RESOLVIDO** — removida a condição `and L > 4.0`; agora `if freq < FREQ_MIN: continue` (sempre). **MCP:** NBR 8800 Anexo L.1.2 é taxativo — *"em nenhum caso a freqüência natural pode ser inferior a 3 Hz"*, sem isenção por vão.
* **Risco:** 🟡 Médio
* **Descrição:** A rotina de frequência natural possui um descarte rígido baseado no vão horizontal $L$:
  ```python
  if freq < FREQ_MIN and L > 4.0:
      continue
  ```
  Ao pular a verificação de frequência dinâmica para vigas de vão inferior ou igual a 4.0 m, o módulo assume de forma não-normativa e sem validação física que todos os vãos menores estão isentos de vibração incômoda.

---

### Bug 8.8: Omissão da Altura de Elevação na Chamada de Calhas em `rodar_galpao.py`
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L559)
* **Status:** **✅ RESOLVIDO** — a chamada agora passa `h_elevacao=params["calha"].get("h_elevacao", 0.0)`, ligando a contribuição de parede vertical (já existente em `calhas.dimensiona`). **MCP:** NBR 10844 — superfície vertical adjacente contribui com **50%** da área (`A = L·(L_água + h_elev/2)`). Default 0,0 (beiral sem platibanda) preserva o comportamento; projetos com platibanda/oitão informam a altura.
* **Risco:** 🟡 Médio
* **Descrição:** O script orquestrador chama o módulo hidráulico de calhas omitindo o parâmetro de elevação vertical do oitão/platibanda (`h_elevacao`), fazendo com que o cálculo de área tributária da calha ignore qualquer acúmulo de chuva impulsionada pelo vento contra faces verticais, em desacordo com os critérios de contribuição da NBR 10844.

---

### Bug 8.9: Acúmulo Aditivo de Fatores de Redução de Junta Térmica em `junta_dilatacao.py`
* **Arquivo:** [junta_dilatacao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/junta_dilatacao.py#L48-L60)
* **Status:** **⚪ FALSO POSITIVO** — nenhuma correção. **MCP:** o FCC Report 65 aplica os fatores por **soma algébrica (aditiva)**, textualmente: *"Quando mais do que uma dessas condições existirem, o fator de percentual será a soma algébrica dos vários fatores."* A fórmula `base·(1 + Σfatores)` do código está correta (ex.: −33% −15% −25% = −73% → 32,4 m). Multiplicar sucessivamente daria 51,2 m — **não-conservador e errado**. O `Lmax = 1e-9` é apenas uma guarda numérica defensiva.
* **Risco:** ~~🟡 Médio~~ (não procede)
* **Descrição:** Os fatores de ajuste para o comprimento máximo entre juntas do Federal Construction Council (FCC Report 65) são acumulados de forma puramente aditiva:
  ```python
  f = 0.0
  if not aquecido: f -= 0.33
  if base_fixa: f -= 0.15
  if rigidez_assimetrica: f -= 0.25
  return base * (1.0 + f), f
  ```
  Fatores de redução de naturezas físicas independentes devem ser aplicados multiplicativamente. O acúmulo aditivo faz com que a redução total chegue a 73% (e poderia se tornar zero ou negativa dependendo da combinação), necessitando de uma trava matemática artificial `Lmax = 1e-9` (linha 71) para evitar divisões por zero em vez de modelar a física de forma adequada.

---

### Bug 8.10: Parâmetro Órfão e Largura Hardcoded de Viga Alavanca em `sapata_divisa.py`
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L22,L92)
* **Status:** **✅ RESOLVIDO** — `b_viga = max(b_col_paralela or 0.0, 0.25)`: o parâmetro antes órfão agora define a largura da viga alavanca (≥ largura do pilar), com piso de 0,25 m. Selftest OK.
* **Risco:** 🟡 Baixo
* **Descrição:** A assinatura da função principal aceita o parâmetro `b_col_paralela` mas nunca o utiliza. Ao mesmo tempo, a largura da viga de equilíbrio da sapata de divisa está fixada em `0.25` m no corpo da função de forma rígida (hardcoded), independentemente das dimensões do pilar de divisa fornecido.

---

### Bug 8.11: Comprimento de Flambagem $L_{livre}$ de Thornton Incorreto em `gusset_ligacao.py`
* **Arquivo:** [gusset_ligacao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/gusset_ligacao.py#L115)
* **Status:** **⚪ FALSO POSITIVO** — nenhuma correção. **MCP:** no método de Thornton (AISC DG29), `L_livre ≠ Lc` de fato, **mas** adotar `L_livre = Lc` como *fallback* (quando o usuário omite a distância livre real) é **conservador e boa prática defensiva**: majora o comprimento de flambagem → maior λ₀ → menor χ → menor Nc,Rd. O código já **desacopla** as variáveis (o usuário informa `L_livre` real quando disponível) e **documenta** isso na docstring (L91-92). Registro do notebook confirma que essa foi uma correção aplicada em 2026-07-10 (parecer sênior #1).
* **Risco:** ~~🔴 Crítico~~ (não procede)
* **Descrição:** Quando o usuário omite o comprimento livre de flambagem `L_livre` para a compressão de Thornton na chapa gusset, o módulo assume como default o comprimento da ligação `Lc`:
  ```python
  L_livre = caso.get("L_livre", Lc)
  ```
  Por definição do método de Thornton (AISC DG29), $L_c$ é o comprimento de acoplamento da diagonal ao gusset (onde a força é transferida) e $L_{livre}$ é a distância livre sem travamento entre o fim da ligação e o pilar/viga de apoio. Confundir essas duas extensões físicas gera avaliações de flambagem incorretas e potencialmente inseguras quando o comprimento de ligação é menor que o vão livre real da chapa.

---

### Bug 8.12: Esforço de Tração do Tirante Hardcoded em `rodar_galpao.py`
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1192)
* **Status:** **✅ RESOLVIDO** — a tração do tirante de cobertura passou a ser **calculada da geometria**: `N_tir_d = (1,25·G + 1,5·Q)·(ridge − eave)·trib_tir`, onde `trib_tir = bay/(n_tirantes+1)`. **MCP:** confirmado que a tração é a componente tangencial (`× senθ`) acumulada nas terças de uma água, e `w_água·senθ = (ridge − eave)`. O valor 8,0 kN da config vira apenas **piso prático** (pré-tensão): telhado raso → 8,0 kN governa (sem regressão); telhado íngreme/longo → a geometria governa (ex.: rise 3 m, bay 8, 1 tirante → 8,55 kN). Exposto em `res["Nsd_tirante_kN"]`.
* **Risco:** 🔴 Crítico
* **Descrição:** A força solicitante de tração nos tirantes de terça (sag rods), `cb["Nsd_tirante"]`, é extraída de um dicionário padrão onde está gravada fixamente como `8.0` kN de forma hardcoded:
  ```python
  "Nsd_tirante": 8.0
  ```
  A tração nos tirantes deveria ser calculada analiticamente em função do peso próprio de telhas/terças, carga acidental e inclinação do telhado acumulada, para obter a carga real sobre os tirantes de cumeeira. Usar um valor arbitrário fixo de 8.0 kN expõe o dimensionamento a falhas para galpões longos ou com inclinação severa.

---

### Bug 8.13: Espessura de Tinta Intumescente Ignorada no Incêndio em `fogo_nbr14323.py`
* **Arquivo:** [fogo_nbr14323.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/fogo_nbr14323.py#L131-L134)
* **Status:** **✅ RESOLVIDO** — `_temp_com_protecao` reescrita com o **método incremental da NBR 14323 Anexo B** (Fluxograma 2): a espessura `tp` entra na condutância `λp/tp` e no fator de inércia térmica `ξ = (cp·ρp)/(ca·ρa)·tp·(u/A)`. **MCP:** o fator fixo 0,35 é *"totalmente inaceitável, fisicamente incorreto"* — o fenômeno é transiente e depende de `tp`, `u/A` e da curva ISO 834. `λp` calibrado contra as cartas de cobertura (tinta 1,27 mm protege u/A≈240 a ~545 °C/60 min ✓ alvo 550 °C); monotônico na espessura (0,49 mm→827 °C … 3,96 mm→246 °C). Selftest OK.
* **Risco:** 🟡 Médio
* **Descrição:** O cálculo da temperatura do aço com proteção incremental sob pintura intumescente desconsidera a espessura da camada de tinta informada (`espessura_mm`):
  ```python
  if tipo == "intumescente":
      theta_s_prot = temp_aco_nao_protegido(t_min, u_A) * 0.35
      return round(theta_s_prot, 1)
  ```
  O fator redutor fixo de `0.35` é aplicado diretamente sobre a temperatura sem proteção. Como a variável `espessura_mm` é ignorada, alterar a especificação de espessura da película seca (DFT) no arquivo de entrada não gera nenhuma alteração física na temperatura calculada, mascarando o comportamento real do perfil sob fogo.

---

### Bug 8.14: Omissão de $B_2$ no Cortante Lateral em `estabilidade_b1b2.py`
* **Arquivo:** [estabilidade_b1b2.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estabilidade_b1b2.py#L120)
* **Status:** **⚪ FALSO POSITIVO** — nenhuma correção. **MCP:** a NBR 8800 **Item D.2.4** é literal: *"A força cortante solicitante de cálculo pode ser tomada igual à da análise elástica de primeira ordem [...] ou igual a: $V_{Sd} = V_{nt} + V_{lt}$"* — **sem** amplificação por $B_2$ (só $M$ e $N$ são amplificados, D.2.1/D.2.2). O código `v = mf_nt + mf_lt` está **correto**; aplicar $B_2·V_{lt}$ seria uma formulação inexistente na norma. (Ponto já confrontado e rejeitado em parecer sênior 2026-07-06.)
* **Risco:** ~~🔴 Crítico~~ (não procede)
* **Descrição:** A rotina `_combina_grupo` calcula o cortante final $V_{sd}$ simplesmente somando de forma linear os componentes `mf_nt` e `mf_lt`:
  ```python
  v = mf_nt[e][iV] + mf_lt[e][iV]
  ```
  De acordo com as regras de segunda ordem (NBR 8800 Anexo D.1.1), os esforços provenientes da translação lateral (estrutura `lt`) devem ser multiplicados pelo fator de amplificação global $B_2$, resultando em:
  $$V_{sd} = V_{nt} + B_2 \cdot V_{lt}$$
  Ao ignorar a amplificação no cortante lateral, o framework subdimensiona o esforço solicitante de cisalhamento em pilares e ligações de pórticos deslocáveis sujeitos ao vento.

---

### Bug 8.15: Erro de "Fencepost" no Comprimento de Flambagem $Lb_{terca}$ em `rodar_galpao.py`
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L663)
* **Status:** **✅ RESOLVIDO** — `Lb_terca = L_raft / n_terca` (era `/(n_terca+1)`). **MCP:** *fencepost* confirmado — `n_por_agua` é o **número de vãos** (com travamento no beiral e na cumeeira), logo o espaçamento é `L/n_terca`. O divisor errado encolhia o $L_b$ e **superestimava a resistência à FLT** (inseguro). Consistente agora com a L300 (vão da telha) e com o modelo em `build_galpao` — ambos já usam `/n_terca`.
* **Risco:** 🔴 Crítico
* **Descrição:** O vão de flexotração/flambagem lateral da mesa superior do rafter sob ações gravitacionais (`Lb_terca`) está definido como:
  ```python
  Lb_terca = L_raft / (n_terca + 1)
  ```
  Contudo, o parâmetro `n_terca` (retornado pela chave `n_por_agua` das terças) é usado no modelo físico (`build_galpao.py`) como o número de divisões (vãos) da telha, o que significa que o telhado já é dividido em `n_terca` espaços (gerando `n_terca - 1` terças intermediárias). Ao dividir `L_raft` por `n_terca + 1` no orquestrador, assume-se falsamente a existência de um travamento adicional, subestimando o comprimento livre de flambagem lateral com torção (FLT) real (por exemplo, em `n_por_agua = 3`, assume-se $L_b = L/4$ em vez de $L/3$, resultando em avaliações não-conservadoras de resistência da viga).

---

### Bug 8.16: Ausência de Salvaguardas para $B_2$ Negativo/Instabilidade em `estabilidade_b1b2.py`
* **Arquivo:** [estabilidade_b1b2.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estabilidade_b1b2.py#L161)
* **Status:** **✅ RESOLVIDO** — adicionadas salvaguardas: `denom ≤ 0 → B2 = inf` (instabilidade global P-Δ), `B2 = max(1/denom, 1.0)` (piso 1,0), flag `maes_valido` e alerta no relatório quando `B2max0 > 1,40` (rigidez original) ou `B2max_f > 1,55` (reduzida) ou infinito. **MCP:** B2 é sempre ≥ 1,0; denominador nulo/negativo = carga vertical ≥ carga crítica de flambagem lateral (colapso); limites de validade do MAES = **1,40 / 1,55** (NBR 8800 4.9.7 — acima → grande deslocabilidade, exige análise rigorosa).
* **Risco:** 🟡 Médio
* **Descrição:** A equação de amplificação global de segunda ordem (MAES) calcula $B_2$ como:
  ```python
  B2 = 1.0 / (1.0 - (1.0 / RS) * (dh * sumN) / (H_STORY * sumH))
  ```
  Se a rigidez lateral do pórtico for muito baixa em relação às cargas gravitacionais verticais, a expressão `(1.0 / RS) * (dh * sumN) / (H_STORY * sumH)` pode atingir ou ultrapassar `1.0`. Nesse caso, `B2` torna-se infinito ou negativo (ex.: $-10.0$), invertendo os momentos e gerando esforços absurdos que passam nas verificações locais sem disparar alertas. O código carece de um limitador inferior de $B_2 \ge 1.0$ e de uma trava de erro crítico caso $B_2$ supere o limite normativo da NBR 8800 de $1.40$ (original) ou $1.55$ (reduzida), que indica que o método aproximado é inválido.

---

### Bug 8.17: Omissão de Momento $M_z$ na Flexão da Chapa do Console em `console_ponte.py`
* **Arquivo:** [console_ponte.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/console_ponte.py#L107)
* **Status:** **✅ RESOLVIDO** — `u_flex = (|M| + |Mz|)/M_Rd` (era só `M/M_Rd`). **MCP:** $M = R_v·ecc$ e $M_z = H_t·(L/2+h_{trilho})$ fletem a chapa em torno do **mesmo eixo forte** (ambos no plano da chapa) → flexão reta, tensões normais **colineares que somam** (não é flexão oblíqua). Agora consistente com o grupo de solda, que já somava `f_bV+f_bH`. Selftest atualizado e OK.
* **Risco:** 🟡 Médio
* **Descrição:** Ao verificar as tensões na chapa do console em balanço, o código define a utilização por flexão pura no plano como:
  ```python
  u_flex = (M / M_Rd)
  ```
  onde `M = Rv * ecc`. No entanto, a força horizontal de surto transversal $H_t$ atua no topo do trilho com excentricidade vertical, gerando o momento fletor horizontal coplanar $M_z = H_t \cdot (L/2 + h_{trilho})$ na raiz da solda/chapa. Como $M_z$ também provoca tensões normais de flexão na mesma seção transversal da chapa do console, ignorá-lo no cálculo de $u_{flex}$ é inseguro, sendo necessário verificar a chapa sob a soma absoluta/envelope dos momentos $(|M| + |M_z|) / M_{Rd}$.
