# 08 — New Discovered Bugs (Auditoria com Base em Diretrizes Técnicas)

Este documento registra as novas inconformidades, inconsistências e riscos estruturais identificados no framework **FreeCAD Automatic (Steel Warehouse Design Framework)** durante a auditoria baseada no caderno de *"Diretrizes Técnicas para Revisão de Projetos de Engenharia"*, bem como a verificação de suas resoluções.

> [!NOTE]
> **Status Geral (2026-07-15):**
> - **Fase 1 (bugs 8.1–8.4):** ✅ 4/4 verificados e corrigidos — commit `dad7b87`.
> - **Fase 9 (bugs 8.5–8.13):** ✅ 7 reais corrigidos (8.5, 8.6, 8.7, 8.8, 8.10, 8.12, 8.13) + ⚪ 2 falsos positivos (8.9, 8.11) — commit `06130c0`.
> - **Fase 10 (bugs 8.14–8.17):** ✅ 3 reais corrigidos (8.15, 8.16, 8.17) + ⚪ 1 falso positivo (8.14) — commit `ac529a2`.
> - **Fase 11 (bugs 8.18–8.20):** ✅ 3 reais corrigidos (8.18, 8.19, 8.20) — commit `a6e3808`.
> - **Fase 12 (bugs 8.21–8.36):** ✅ 16/16 reais corrigidos. Detalhe por bug:
>
> | Bug | Correção |
> | :-- | :-- |
> | 8.21 | `sincronizar` deixava de sobrescrever seções por-coluna: flag `SEC_COLS_EXTERNO` (setada por `redimensionamento`) preserva o `I` de cada coluna → B1 por-coluna correto. *(O frame do `galpao_portico` ainda modela colunas uniformes — B2/esforços; o B1 local agora honra o perfil real de cada coluna.)* |
> | 8.22 | Trava de B1: `denom≤0 → B1=inf` (flambagem local elástica), igual ao B2 (8.16); fim do `max(negativo,1)=1` silencioso. |
> | 8.23 | **Tesoura (treliça)** no quadro (`res["tesoura"]["u_max"]/["OK"]`). |
> | 8.24 | Viga de rolamento: `res["ponte_viga_ok"]` (fadiga Anexo K + flecha) força NAO ATENDE mesmo com `inter<1`. |
> | 8.25 | **Console da ponte** no quadro (`console_u_max/console_ok`). |
> | 8.26 | **Contraventos/tirantes/mão-francesa** no quadro (`barras_u_max/barras_ok`). |
> | 8.27 | **Gusset** no quadro (`gusset_u_max/gusset_ok`). |
> | 8.28 | Base: usa `base_ok` (interação tração+corte, ACI, grout) → falha surface mesmo com `base_util<1`. |
> | 8.29 | Sapata: `sapata_ok` agora inclui `rB["OK_B"]` (flexão B/L, compressão diagonal, punção), não só solo. |
> | 8.30 | **Telha** no quadro (`telha_util/telha_ok`). |
> | 8.31 | **Baldrame longitudinal** no quadro (`res["baldrame"]["ok"]`). |
> | 8.32 | `terreno.py` deixou de ser órfão: importado + gate `params["terreno"]` (TO/CA/TP/recuos) + linha no quadro, defensivo (try/except). |
> | 8.33 | `rodar_projeto` exporta ao TechDraw todos os novos subsistemas (`resultados` + `estados`). |
> | 8.34 | Fogo: temperatura (°C) não é mais tratada como util. `fogo_util=θ/θ_cr`, `fogo_ok=θ≤θ_cr` (θ_cr=550 °C, NBR 14323, A CONFIRMAR). |
> | 8.35 | **Junta de dilatação** no quadro (`precisa → NAO ATENDE`). |
> | 8.36 | **Zona de painel do joelho** no quadro (`res["zona_painel"]["u_max"]`). |
>
> Validado por simulação: itens com `util<1` porém `ok=False` (base/interação, sapata/punção, viga-rolamento/fadiga) agora surfaçam como NAO ATENDE.






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
| **Bug 8.18** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da verificação de fundação profunda no QUADRO DE VERIFICAÇÕES global. | NBR 6122 / NBR 6118 | **✅ Resolvido** |
| **Bug 8.19** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da verificação do drift/estabilidade de 2ª ordem do sismo no QUADRO DE VERIFICAÇÕES global. | NBR 15421 (§9.6) | **✅ Resolvido** |
| **Bug 8.20** | 🟡 Médio | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da verificação de calhas e de fundação de divisa no QUADRO DE VERIFICAÇÕES global. | NBR 10844 / NBR 6118 | **✅ Resolvido** |
| **Bug 8.21** | 🔴 Crítico | [estabilidade_b1b2.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estabilidade_b1b2.py) | Sobrescrita de perfis de coluna em pórticos multi-vão no sincronizar. | NBR 8800 Anexo D | **✅ Resolvido** |
| **Bug 8.22** | 🔴 Crítico | [estabilidade_b1b2.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estabilidade_b1b2.py) | Ausência de salvaguardas para $B_1$ negativo ou esmagamento elástico (instabilidade local). | NBR 8800 Anexo D.1.2 | **✅ Resolvido** |
| **Bug 8.23** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da verificação de tesoura (treliça) no QUADRO DE VERIFICAÇÕES global. | NBR 8800 | **✅ Resolvido** |
| **Bug 8.24** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão de falhas de fadiga e deformação na viga de rolamento no QUADRO DE VERIFICAÇÕES global. | NBR 8800 (§6.3) | **✅ Resolvido** |
| **Bug 8.25** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão do console de apoio da viga de rolamento no QUADRO DE VERIFICAÇÕES global. | NBR 8800 (§5.4) | **✅ Resolvido** |
| **Bug 8.26** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão das barras tracionadas (contraventos e tirantes) no QUADRO DE VERIFICAÇÕES global. | NBR 8800 (§5.2) | **✅ Resolvido** |
| **Bug 8.27** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão dos gussets de ligação de contraventamento no QUADRO DE VERIFICAÇÕES global. | NBR 8800 (§6.5) | **✅ Resolvido** |
| **Bug 8.28** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão de falhas de interação/concreto/grout da placa de base no QUADRO DE VERIFICAÇÕES global. | NBR 8800 / ACI 318 | **✅ Resolvido** |
| **Bug 8.29** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão das verificações estruturais de flexão, cisalhamento e punção de sapata no QUADRO DE VERIFICAÇÕES global. | NBR 6118 / NBR 6122 | **✅ Resolvido** |
| **Bug 8.30** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da verificação de telha no QUADRO DE VERIFICAÇÕES global. | NBR 14762 | **✅ Resolvido** |
| **Bug 8.31** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da verificação da viga de baldrame longitudinal no QUADRO DE VERIFICAÇÕES global. | NBR 6118 | **✅ Resolvido** |
| **Bug 8.32** | 🔴 Crítico | [terreno.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/terreno.py) | Módulo terreno.py completamente órfão/desconectado da cadeia de cálculo e validação. | Lei de Uso do Solo | **✅ Resolvido** |
| **Bug 8.33** | 🔴 Crítico | [rodar_projeto.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_projeto.py) | Omissão de todos os novos sub-sistemas no dicionário de resultados exportado para o TechDraw. | TechDraw 2D | **✅ Resolvido** |
| **Bug 8.34** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Temperatura do fogo em Celsius é tratada erroneamente como taxa de utilização no quadro consolidado. | NBR 14323 | **✅ Resolvido** |
| **Bug 8.35** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da verificação de necessidade de junta de dilatação no QUADRO DE VERIFICAÇÕES global. | FCC Report 65 / Bellei | **✅ Resolvido** |
| **Bug 8.36** | 🔴 Crítico | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Omissão da verificação de Zona de Painel do joelho no QUADRO DE VERIFICAÇÕES global. | NBR 8800 | **✅ Resolvido** |







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

---

### Bug 8.18: Omissão da Verificação de Fundação Profunda no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1150-L1159)
* **Status:** **✅ RESOLVIDO** — `res["estaca"]` passou a expor `ok` (consolidando grupo + tração + bloco) e `util`, e foram adicionadas ao quadro as linhas **"Estaca (fund. profunda)"** e **"Travamento transversal"**. A estaca entra pela util real do grupo, forçada a >1,0 se qualquer estado (grupo/tração/bloco) reprovar mesmo com util ≤ 1. Verificado por simulação: estaca com `util=0,80` porém `ok=False` (bloco reprova) agora aparece como **NAO ATENDE**.
* **Risco:** 🔴 Crítico
* **Descrição:** Quando o usuário seleciona fundação profunda (`params.get("estaca")`), o framework calcula a capacidade das estacas, dimensiona o bloco de coroamento, o travamento transversal e a viga de equilíbrio de divisa. No entanto, os resultados e taxas de utilização dessas peças estruturais (como `re_["grupo"]["util"]`, `re_["bloco"]["OK"]`, `rct["OK"]`, `rve["viga"]["ok"]`) são completamente omitidos da lista `checks` e do controle de `falhas` de `rodar_galpao.py`. Se qualquer um desses elementos de fundação profunda falhar, a consolidação no topo do memorial exibirá silenciosamente que todos os elementos estão "OK", mascarando falhas graves de fundação sob compressão, tração ou flexo-compressão.

---

### Bug 8.19: Omissão da Verificação do Drift/Estabilidade Sísmica no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1150-L1159)
* **Status:** **✅ RESOLVIDO** — adicionada a linha **"Sismo (theta 2ª ordem)"** ao quadro, lendo `res["sismo_theta"]["ok"]` (já calculado como `θ ≤ θ_max`, NBR 15421 §9.6). Falha de estabilidade sísmica agora surface como NAO ATENDE.
* **Risco:** 🔴 Crítico
* **Descrição:** Se a ação sísmica for ativada e o coeficiente de estabilidade global de segunda ordem exceder o limite normativo da NBR 15421 (§9.6, $\theta > \theta_{max}$), indicando instabilidade física da estrutura sob terremoto, a util correspondente ou o estado de aprovação (`res["sismo_theta"]["ok"]`) não é incluído na lista `checks` de verificação consolidada. O programa indica que a estrutura atende integralmente ao projeto mesmo em estado crítico de colapso sísmico.

---

### Bug 8.20: Omissão da Verificação de Calhas e Sapata de Divisa no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1150-L1159)
* **Status:** **✅ RESOLVIDO** — adicionadas as linhas **"Calha (hidráulica)"** (`res["calha"]["ok"]`) e **"Fundação de divisa"** ao quadro. `res["divisa"]` passou a expor `ok` nas duas variantes (viga de equilíbrio sobre estacas `rve["viga"]["ok"]` e sapata + viga alavanca `rdv["viga"]["ok"]`). **Bônus:** corrigido o padrão `0 if ok else None` de Escada/Plataforma, que enviava a **falha** para `None` (pulada no quadro) — agora falha → 1,99 (NAO ATENDE) e "não rodou" → pulado, distinguidos por presença da chave.
* **Risco:** 🟡 Médio
* **Descrição:** Semelhante às fundações profundas e ao sismo, o dimensionamento hidráulico de calhas (`res["calha"]["ok"]`) e a fundação superficial de divisa (`res["divisa"]["ok"]`) não são inseridos no `checks` do relatório consolidado de `rodar_galpao.py`. Caso a calha transborde (altura d'água requerida acima do limite ou desconformidade com a regra prática de 1 cm²/m² de Bellei), ou a viga alavanca da sapata de divisa falhe à flexão/cisalhamento, o erro passará desapercebido na tabela sumária de utilizações.

---

### Bug 8.21: Sobrescrita de Perfis de Coluna em Pórticos Multi-vão no `sincronizar` de `estabilidade_b1b2.py`
* **Arquivo:** [estabilidade_b1b2.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estabilidade_b1b2.py#L33-L41) e [redimensionamento.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/redimensionamento.py#L62-L65)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** A rotina `avalia` de `redimensionamento.py` define seções de colunas individuais no vetor `est.SEC_COLS` para pórticos multi-vão assimétricos. No entanto, logo em seguida ela chama `est.analyse()`, a qual executa `sincronizar()` como primeiro passo. A função `sincronizar()` lê o valor global `gp.A_COL` (que contém as propriedades de uma única seção, correspondente a `cols_perfil[0]`) e sobrescreve todas as colunas do vetor com essa única seção:
  ```python
  for i in range(nv + 1):
      SEC_COLS[i].update(A=gp.A_COL, I=gp.I_COL, L=gp.EAVE)
  ```
  Isso apaga os perfis de coluna individuais (por exemplo, `cols_perfil[1]`, `cols_perfil[2]`) e força toda a análise de estabilidade e amplificação de segunda ordem ($B_1/B_2$) a ocorrer como se todas as colunas tivessem a seção da coluna 0, mascarando subdimensionamentos severos e distorcendo a física de pórticos com rigidezes laterais distintas.

---

### Bug 8.22: Ausência de Salvaguardas para $B_1$ em `estabilidade_b1b2.py`
* **Arquivo:** [estabilidade_b1b2.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/estabilidade_b1b2.py#L114)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** O cálculo do fator de amplificação local de segunda ordem ($B_1$) é feito por:
  ```python
  B1 = max(Cm / (1.0 - abs(Nsd1) / Ne), 1.0) if Nsd1 < 0 else 1.0
  ```
  Se o esforço axial de compressão de projeto $N_{sd1}$ na peça exceder a carga crítica de Euler $N_e$, o termo `1.0 - abs(Nsd1) / Ne` torna-se negativo (ex.: $-0,2$), resultando em um $B_1$ negativo (ex.: $-5,0$). Pelo uso direto de `max(..., 1.0)`, o programa adota silenciosamente $B_1 = 1.0$, o que é extremamente perigoso e fisicamente incorreto, pois ignora o colapso por flambagem local elástica e não amplifica os momentos fletores. É necessário implementar a trava `denom <= 0.0 -> B1 = inf`, idêntica à que foi corrigida no fator $B_2$.

---

### Bug 8.23: Omissão da Verificação de Tesoura (Treliça) no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1150-L1159)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** Se o tipo de pórtico selecionado for `"tesoura"` (`params.get("tipo_portico") == "tesoura"`), o programa dimensiona a treliça de cobertura através de `tesoura.py`. Entretanto, a utilização máxima obtida (`res["tesoura"]["u_max"]`) e a flag de aprovação (`res["tesoura"]["OK"]`) são totalmente omitidas da lista `checks` consolidada. Se a tesoura falhar (por exemplo, por flambagem catastrófica dos banzos sob gravidade ou diagonais sob sucção), o quadro continuará mostrando `"Viga: (falta)"` (já que a viga de alma cheia não foi dimensionada) e não reportará a falha da treliça que de fato sustenta a cobertura.

---

### Bug 8.24: Omissão de Falhas de Fadiga e Deformação da Viga de Rolamento no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L172) e [rodar_galpao.py#L1185](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1185)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** A taxa de utilização da viga de rolamento gravada em `res["ponte_viga_inter"]` recebe estritamente a interação plástica de flexão biaxial (`round(viga["inter"], 2)`). Caso a viga de rolamento sofra falha de fadiga (vida útil excedida pelo Anexo K da NBR 8800) ou falha por deformação excessiva (flecha maior que L/600 ou L/800), a flag `viga["OK"]` é setada para `False`, mas a utilização em `checks` permanece inferior a `1.0`, impedindo que o sumário alerte o engenheiro sobre o colapso por fadiga ou travamento da ponte.

---

### Bug 8.25: Omissão do Console de Apoio da Viga de Rolamento no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1150-L1159)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** Se houver ponte rolante, o console metálico excentricamente soldado que serve de apoio para a viga de rolamento é verificado (`console_ponte.py`). O status de aprovação (`res["console_ok"]`) e a utilização (`res["console_u_max"]`) não constam na lista `checks` de unificação do relatório. Se a solda da raiz ou a chapa do console falharem estruturalmente, o erro passará silenciosamente na consolidação.

---

### Bug 8.26: Omissão de Contraventamentos, Tirantes e Mão-Francesa no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1150-L1159)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** A verificação de todas as barras puramente tracionadas (contraventamento de parede/cobertura, tirantes de terça e barra de mão-francesa) é consolidada na variável `res["barras_ok"]` e `res["barras_u_max"]`. Contudo, esses itens não são inseridos no checklist `checks` de `rodar_galpao.py`. Se qualquer diagonal sob vento longitudinal romper, ou o tirante de terça falhar na rosca, o quadro sumário não apontará nenhuma desconformidade.

---

### Bug 8.27: Omissão dos Gussets de Contraventamento no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1150-L1159)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** A chapa de nó (gusset) que conecta as diagonais de contraventamento aos pilares e rafters é verificada em `gusset_ligacao.py`, gerando `res["gusset_ok"]` e `res["gusset_u_max"]`. O resultado do cálculo da solda e ruptura da chapa não é incorporado ao checklist global, ocultando falhas mecânicas na ligação dos contraventamentos.

---

### Bug 8.28: Omissão de Falhas de Interação/Concreto/Grout da Placa de Base no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L425)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** A utilização do chumbador gravada em `res["base_util"]` é definida por:
  ```python
  res["base_util"] = round(max(rb["u_tracao"], rb["u_corte"], rb["u_concreto"]), 2)
  ```
  Isso omite por completo a taxa de utilização da interação de tração e cisalhamento nos chumbadores (`rb["interacao"]`), a verificação de interação no concreto pela ACI 318 (`rb["interacao_conc"]`), as falhas por geometria insuficiente da placa (`Y > L_placa`) e a falha de esmagamento do grout (`grout_ok == False`). Se os parafusos falharem em cortante-tração combinados (por exemplo, `u_tracao = 0,8` e `u_corte = 0,8` -> `interacao = 1,28 > 1,0`), `rb["OK"]` é setado para `False`, mas `base_util` reportará falsamente `0,80` (OK).

---

### Bug 8.29: Omissão das Verificações Estruturais de Concreto da Sapata no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1054)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** A taxa de utilização da sapata de fundação superficial é definida em `res["sapata_util"]` levando em conta apenas critérios geotécnicos (pressão no solo, tombamento e deslizamento). No entanto, o dimensionamento estrutural do concreto armado (flexão na direção B e L, compressão diagonal na face do pedestal e punção para sapatas flexíveis) é totalmente ignorado para fins de aprovação no quadro. Caso ocorra ruptura por punção ou flexão na armadura da sapata, `rB["OK_B"]` será `False`, mas o relatório final indicará que a sapata atende perfeitamente ao projeto baseado apenas nas pressões de solo.

---

### Bug 8.30: Omissão da Verificação de Telha no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L307)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** A chapa de cobertura (telha) é verificada contra flexão e deformação limite através de `telha_cobertura.py`, gerando as variáveis `res["telha_util"]` e `res["telha_ok"]`. Contudo, nenhuma destas variáveis é incluída no quadro de verificações sumário. Se a cobertura do galpão falhar sob ação de sucção de vento local (borda e canto), a estrutura será erroneamente aprovada no relatório consolidado.

---

### Bug 8.31: Omissão da Verificação da Viga de Baldrame Longitudinal no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L509)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** Quando a fundação profunda é utilizada, a viga de baldrame longitudinal (viga de amarração) que resiste ao peso da alvenaria e ao empuxo de terra/tração é calculada, gerando `res["baldrame"]["ok"]`. No entanto, a aprovação dessa viga é completamente omitida do quadro de verificações global de `rodar_galpao.py` (o qual inclui apenas a viga de travamento transversal da fundação), deixando as vigas longitudinais sem validação final no resumo.

---

### Bug 8.32: Módulo `terreno.py` Completamente Órfão e sem Integração
* **Arquivo:** [terreno.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/terreno.py)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** O módulo `terreno.py` implementa toda a lógica geométrica e urbanística para leitura de KML de lotes e validação contra restrições de Taxa de Ocupação (TO), Coeficiente de Aproveitamento (CA), Taxa de Permeabilidade (TP) e recuos limites (utilizando Oriented Bounding Box - OBB). No entanto, este arquivo nunca é importado ou acoplado na rotina principal `rodar_galpao.py` ou no runner `rodar_projeto.py`, fazendo com que os parâmetros de terreno fornecidos fiquem inoperantes e sem validação alguma no projeto estrutural do galpão. O módulo também carece de arquivos de testes unitários em `tests/`.

---

### Bug 8.33: Inconsistência na Exportação de Resultados para Desenhos TechDraw em `rodar_projeto.py`
* **Arquivo:** [rodar_projeto.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_projeto.py#L71-L79)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** O dicionário `spec["estrutura"]["resultados"]` montado ao final de `calcular()` é a fonte de dados que `techdraw_exec.py` utiliza para desenhar a tabela sumária de resultados de utilização diretamente nas folhas 2D do projeto executivo. Esse dicionário contém apenas um subconjunto estático de elementos antigos. Ele omite por completo todos os novos sub-sistemas adicionados (como Tesoura, Calhas, Sismo, Estacas, Baldrame longitudinal/transversal, Divisas, Escadas, Plataformas, Contraventamento e Gussets). Com isso, as pranchas técnicas desenhadas contêm um quadro de verificações desatualizado e incompleto em relação ao escopo real de elementos do galpão.

---

### Bug 8.34: Temperatura de Incêndio em Celsius Tratada como Taxa de Utilização no Quadro Consolidado
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1186)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** O cálculo ao fogo pelo módulo `fogo_nbr14323.py` exporta a temperatura física final do aço em Celsius (`res["fogo_theta"] = rf["theta_aco_C"]`), que normalmente varia entre 400°C e 950°C. No entanto, no checklist consolidado, este valor é inserido diretamente como `("Fogo theta C", res.get("fogo_theta"))` na lista `checks` de taxas de utilização. Na consolidação, qualquer valor maior que 1,001 (ou seja, qualquer temperatura acima de 1°C) é tratado como uma falha grave, forçando a impressão de `"Fogo theta C     550.00   *** NAO ATENDE ***"` no sumário de erros do memorial, mesmo se o elemento passar na resistência sob combinação excepcional.

---

### Bug 8.35: Omissão da Verificação de Necessidade de Junta de Dilatação no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L1007)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** O módulo `junta_dilatacao.py` determina o limite de comprimento de edificação retangular sem juntas e calcula o deslocamento térmico (`rj = jd.verifica_junta(...)`), definindo se a edificação precisa ou não de junta de dilatação. No entanto, a flag de aprovação (`rj["OK"]` ou `not precisa_junta`) é completamente omitida da lista `checks` em `rodar_galpao.py`. Se um galpão exceder o comprimento térmico máximo (gerando esforços excessivos de coação nos pilares de extremidade), o quadro de verificações unificado continuará aprovando a estrutura de forma silenciosa.

---

### Bug 8.36: Omissão da Verificação da Zona de Painel do Joelho no QUADRO DE VERIFICAÇÕES Global
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L454)
* **Status:** **✅ RESOLVIDO** (Fase 12 — ver tabela de correções no topo do documento)
* **Risco:** 🔴 Crítico
* **Descrição:** A verificação de cisalhamento do painel da alma do pilar no nó rígido do pórtico (zona de painel) é calculada através de `zona_painel.py`, definindo as taxas de utilização e se necessita de chapa de reforço (`t_doubler_mm`). Apesar da importância para a estabilidade da ligação viga-coluna, o resultado de sua validação (`rzp["u_max"]` ou `rzp["OK"]`) não consta na lista global `checks` do orquestrador principal, permitindo que falhas de cisalhamento no nó passem sem report no resumo.




