# 08 — New Discovered Bugs (Auditoria com Base em Diretrizes Técnicas)

Este documento registra as novas inconformidades, inconsistências e riscos estruturais identificados no framework **FreeCAD Automatic (Steel Warehouse Design Framework)** durante a auditoria baseada no caderno de *"Diretrizes Técnicas para Revisão de Projetos de Engenharia"*.

> [!NOTE]
> **Status: ✅ TODOS VERIFICADOS E RESOLVIDOS (2026-07-15)**
> Os 4 itens foram revisados um a um contra o notebook *"Diretrizes Técnicas para
> Revisão de Projetos de Engenharia"* (NBR 6118 17.4, NBR 8681/8800 combinações e
> 5.5.1.2, NBR 6122 8.5.6). **Veredito: todos procedem** e foram corrigidos; os
> selftests dos módulos passam sem regressão.

| ID | Arquivo | Correção aplicada |
|----|---------|-------------------|
| 8.1 | `sapata_divisa.py` | verificação de cortante da viga alavanca (biela VRd2 + estribo mín, `Vd=1,4·ΔP`), iterando `h` até passar flexão E biela |
| 8.2 | `galpao_portico.py` | combinação `Gfav` de uplift agora `1,0·G + 1,4·W` (removido `0,80·Q`; ação variável favorável → γq=0) |
| 8.3 | `check_nbr8800.py` | interação 5.5.1.2 usa `abs(Nsd)`/`abs(Msd)` — flexo-tração soma módulos (tração não subtrai) |
| 8.4 | `rodar_galpao.py` | dimensiona cinta de travamento **transversal** para blocos de 1–2 estacas (amarração acidental `0,10·N_pilar`, NBR 6122) |

---

## Índice das Inconformidades

| ID | Nível de Risco | Módulo Afetado | Descrição do Problema | Referência Normativa |
| :--- | :--- | :--- | :--- | :--- |
| **Bug 8.1** | 🔴 Crítico | [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py) | Omissão total da verificação de esforço cortante na viga alavanca superficial. | NBR 6118 (Item 17.4) |
| **Bug 8.2** | 🔴 Crítico | [galpao_portico.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/galpao_portico.py) | Inclusão de sobrecarga variável ($Q$) atuando como estabilizadora em combinações de arrancamento por vento (uplift). | NBR 8681 e NBR 8800 |
| **Bug 8.3** | 🟡 Alto | [check_nbr8800.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/check_nbr8800.py) | Esforço axial de tração atuando de forma a reduzir/subtrair a utilização na interação de flexo-tração. | NBR 8800 (Item 5.5.1) |
| **Bug 8.4** | 🟡 Médio | [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) | Ausência de travamento transversal (baldrame ortogonal) para blocos apoiados sobre 1 ou 2 estacas. | NBR 6122 (Item 8.4.1) |

---

## 1. Detalhamento Técnico dos Bugs

### Bug 8.1: Omissão de Cisalhamento na Viga Alavanca da Sapata de Divisa
* **Arquivo:** [sapata_divisa.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py#L86-L100)
* **Descrição detalhada:** 
  Diferentemente do bloco de divisa sobre estacas ([viga_equilibrio.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/viga_equilibrio.py#L84)), que realiza a verificação de cisalhamento da viga de equilíbrio comparando a demanda $V_d = 1,4 \cdot \Delta P$ com o esmagamento de biela ($V_{Rd2}$) e estribos mínimos ($V_{Rd3}$) por meio da função `vb._verifica_cortante`, o módulo de sapatas superficiais excêntricas ([sapata_divisa.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/sapata_divisa.py)) **ignora por tempo indeterminado a verificação de esforço cortante** na viga alavanca. 
  O script dimensiona a seção e a armadura longitudinal superior para o momento $M_d = 1,4 \cdot P_{divisa} \cdot e$, inclusive aumentando a altura $h_{viga}$ se a flexão falhar, mas o cisalhamento constante $\Delta P = R_{divisa} - P_{divisa}$ nunca é checado.
* **Impacto:** Alto risco de ruína frágil por tração diagonal do concreto (sem aviso preliminar) na viga alavanca para sapatas de divisa sob cargas elevadas.
* **Status:** **✅ RESOLVIDO E VERIFICADO.** Adicionada `vb._verifica_cortante` com `Vd = 1,4·ΔP`; a iteração de altura agora cresce `h` até passar flexão **E** biela (VRd2). Novas saídas: `Vd_kN`, `VRd2_kN`, `u_biela`, `s_estribo_max_m`, `ok_cortante`.

---

### Bug 8.2: Sobrecarga Variável Estabilizando Combinações de Uplift (Vento)
* **Arquivo:** [galpao_portico.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/galpao_portico.py#L360-L362)
* **Descrição detalhada:** 
  A rotina de geração de combinações ELU no pórtico define a combinação com carga permanente favorável (`"Gfav"`) da seguinte forma:
  ```python
  ("Gfav", 1.00, 0.80, 1.40)  # Significa: 1.00*G + 0.80*Q + 1.40*W
  ```
  O vento $W$ causa levantamento (uplift/sucção) na cobertura do galpão, gerando esforços de tração nos pilares e fundações. A sobrecarga de uso/manutenção da cobertura ($Q$) atua de forma gravitacional (para baixo). Ao somar $0,80 \cdot Q$ nesta combinação, o framework utiliza uma ação variável de forma **favorável** (auxiliando a estabilização/ancoragem da base). 
  As normas **NBR 8681** e **NBR 8800** vetam terminantemente o uso de ações variáveis secundárias atuando de forma favorável ($\gamma_q = 0$), visto que não há garantia física da presença da sobrecarga durante o evento extremo de vento. A combinação correta deve ser $1,00 G + 1,40 W$.
* **Impacto:** Subdimensionamento não-conservativo de chumbadores de base, blocos de coroamento e estacas sob forças de tração/arrancamento.
* **Inconsistência Interna:** O script principal [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L60) zera corretamente a sobrecarga na combinação homônima: `"C3_Gfav": {"G": 1.00, "W2": 1.40}`.
* **Status:** **✅ RESOLVIDO E VERIFICADO.** A tupla passou a `("Gfav", 1.00, 0.00, 1.40)` — combinação `1,0·G + 1,4·W`, alinhada à intenção documentada (`REVISAO-PORTICO.md`) e ao `C3_Gfav` do orquestrador.

---

### Bug 8.3: Esforço de Tração Axial Reduzindo a Utilização na Flexo-Tração
* **Arquivo:** [check_nbr8800.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/check_nbr8800.py#L183-L186)
* **Descrição detalhada:** 
  Na verificação de peças sob flexo-compressão/flexo-tração baseada no item 5.5.1 da NBR 8800:2008, o código calcula:
  ```python
  n = Nsd / Nc_Rd
  if n >= 0.2:
      inter, eq = n + (8.0 / 9.0) * m, "N/Nrd + 8/9*(M/Mrd)"
  else:
      inter, eq = n / 2.0 + m, "N/(2Nrd) + M/Mrd"
  ```
  Se a peça estiver sob esforço de tração ($N_{Sd} < 0$), o valor de $n$ é negativo. Visto que $n < 0.2$, o bloco `else` é executado, resultando em:
  $$\text{utilização} = \frac{-|N_{Sd}|}{2 \cdot N_{c,Rd}} + \frac{M_{Sd}}{M_{Rd}}$$
  Fisicamente, a tração axial e a flexão se acumulam na mesa tracionada. Matematicamente, a fórmula acima **subtrai** a tração da flexão, informando uma utilização artificialmente menor (mais favorável) do que se houvesse apenas flexão pura.
  De acordo com a NBR 8800:2008 Item 5.5.1.2, a flexo-tração exige a verificação com termos positivos somados:
  $$\frac{N_{t,Sd}}{N_{t,Rd}} + \frac{M_{x,Sd}}{M_{x,Rd}} + \frac{M_{y,Sd}}{M_{y,Rd}} \le 1,0$$
* **Impacto:** Se este módulo helper for utilizado em ligações ou vigas que possuem esforços de tração e flexão concomitantes sem o pré-tratamento de módulos absolutos, as peças serão avaliadas de forma perigosamente insegura.
* **Nota de Atenuação:** No fluxo atual de [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py#L264), as axiais concomitantes das combinações são passadas com seus valores absolutos, porém, a premissa e a estática do módulo de verificação `check_nbr8800.py` estão incorretas e vulneráveis a chamadas diretas com convenção de sinal de tração.
* **Status:** **✅ RESOLVIDO E VERIFICADO.** A interação passou a usar `abs(Nsd)/Nc_Rd + abs(Msd)/Mrd`, garantindo a soma dos módulos (5.5.1.2). Teste direto: para o mesmo `|N|` e `M`, a flexo-tração dá interação `0,521` — igual à flexo-compressão e maior que a flexão pura (`0,422`), nunca a subtraindo.

---

### Bug 8.4: Ausência de Travamento Transversal Obrigatório para Fundações Estabilizadas por 1 ou 2 Estacas
* **Arquivo:** [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/rodar_galpao.py) e [viga_baldrame.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/viga_baldrame.py)
* **Descrição detalhada:** 
  A NBR 6122 prescreve que blocos de coroamento de fundações suportados por apenas uma estaca ($n_{est} = 1$) ou por uma única linha de duas estacas ($n_{est} = 2$) carecem de rigidez rotacional intrínseca na direção perpendicular à linha/centro da estaca. Para garantir a estabilidade contra excentricidades executivas inevitáveis, a norma exige que esses blocos sejam amarrados por vigas de fundação (baldrames) em **duas direções ortogonais**.
  O framework atual projeta e detalha as vigas baldrame exclusivamente na direção longitudinal do galpão (entre pórticos, ao longo do comprimento do prédio). Os blocos de 1 ou 2 estacas ficam totalmente livres de travamento transversal na direção transversal (paralela ao vão do pórtico).
* **Impacto:** Risco de rotação descontrolada do bloco de fundação, flambagem lateral da cabeça das estacas e fissuração severa de recalques por excentricidades geométricas de execução.
* **Status:** **✅ RESOLVIDO E VERIFICADO.** Para blocos com `n_estacas <= 2`, o orquestrador dimensiona automaticamente a **cinta de travamento transversal** (via `verifica_baldrame`, vão = `g["span"]`), com amarração acidental `N = 0,10·N_pilar` (NBR 6122 8.5.6). Gera o relatório `gate7-travamento-transversal.txt` e a chave `res["travamento_transversal"]`.
