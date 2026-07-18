# 07 — Relatório de Revisão Técnica (T15)

Este documento apresenta a revisão das novas implementações realizadas na árvore de trabalho (branch `revisao/homologacao-12-modulos`), confrontando as decisões tomadas e as alterações de código com as diretrizes normativas brasileiras e a base de conhecimento técnica.

---

## 1. Correção do Bug de Sinal do Frame2D (UDL)
*   **Arquivo modificado:** [frame2d.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/frame2d.py)
*   **Problema anterior:** Na montagem do vetor de forças global $F$, a carga nodal equivalente da UDL era subtraída (`F -= F_eq`). Além disso, no cálculo do esforço das barras, a carga de engastamento perfeito era somada (`f = k_loc @ d_e + fef`). Esses dois erros se cancelavam em magnitude nos selftests baseados em valores absolutos, mas invertiam a deformada e o sentido das reações, fazendo com que cargas gravitacionais atuassem de baixo para cima (como *uplift*) e superdimensionando as sapatas.
*   **Correção efetuada:**
    *   Montagem do vetor global alterada para `F += F_eq_global`.
    *   Cálculo do esforço das barras alterado para `f_loc = k_loc @ (T @ d_e) - fef`.
*   **Confronto com a base técnica (NotebookLM):**
    *   A função `_fef_local` calcula as forças equivalentes no nó (a ação direta que a carga distribuída impõe aos nós de extremidade). Portanto, sua contribuição no sistema global deve ser somada ao vetor de forças ($F + F_{eq}$).
    *   O vetor de forças de extremidade do membro (local) é dado por $f_{local} = k_{local} \cdot d_{local} + f_{fef,membro}$. Como $f_{fef,membro} = -F_{eq} = -fef$, a formulação correta é $f_{local} = k_{local} \cdot d_{local} - fef$.
*   **Correção de Vazamento de Estado (State Leak):**
    *   Identificamos que a suíte de testes apresentava uma falha em [test_validacao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/tests/test_validacao.py) (`test_validacao_sistema_cbca`) devido à contaminação de estado global de execuções anteriores.
    *   Modificamos a função `reset()` de [galpao_portico.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/galpao_portico.py) para limpar as variáveis globais `W_WALL_COL`, `ABERTURA_DOMINANTE`, `AGUAS` e `TAPERED` entre execuções de testes.
    *   Após a limpeza, todos os **304 testes passaram com 100% de sucesso**, validando o modelo CBCA:
        *   **Reação Vertical (V):** 42.94 kN medido vs. 42.77 kN teórico (Diferença de **0,4%**).
        *   **Reação Horizontal (H):** 13.66 kN medido vs. 13.67 kN teórico (Diferença de **0,1%**).
        *   **Momento na Coluna (Mcol):** 81.93 kNm medido vs. 82.56 kNm teórico (Diferença de **0,8%**).

---

## 2. Ação do Vento e Pressão Interna (NBR 6123)
*   **Arquivos modificados:** [vento_nbr6123.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/vento_nbr6123.py) e [galpao_portico.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/galpao_portico.py)
*   **Implementações realizadas:**
    1.  **Mapeamento de Abertura Dominante:** Adicionada a função `cpi_por_abertura(abertura_dominante)`. Se o usuário define o galpão como `vedada` (sem aberturas dominantes), o coeficiente de pressão interna passa a ser $C_{pi} = +0,20 / -0,30$ (conforme item 6.2.5 da NBR 6123), em vez do antigo padrão fixo de portão aberto de $+0,80 / -0,60$.
    2.  **Telhado de 1 Água (Shed):** Adicionada a função `cpe_telhado_1agua(theta)` que interpola os coeficientes de forma externos ($C_e$) da **Tabela 6 da NBR 6123** para metade baixa ($H$) e metade alta ($L$) do telhado nas duas direções do vento perpendicular.
    3.  **Vento no Pórtico de 1 Vão:** A função `_wind_unico` foi corrigida. Antes ela aplicava uma UDL de vento para baixo de magnitude $q$ sem considerar os coeficientes externos e internos, o que anulava o arrancamento. Agora ela calcula a pressão líquida real $(C_{pe} - C_{pi}) \cdot q$, aplicando a sucção correta (resultante vertical de *uplift*).
*   **Confronto com a base técnica (NotebookLM):**
    *   A Tabela 6 da NBR 6123 dita coeficientes inteiramente de sucção para inclinações baixas (barlavento sempre $\le -0,9$ e sotavento $\approx -0,5$), gerando forças de arrancamento dominantes. O script reflete exatamente os coeficientes de Tabela 6 para $5^\circ$, $10^\circ$ e $15^\circ$ ($H90$, $L90$, $Hm90$, $Lm90$).

---

## 3. Blocos de Fundação de Concreto Simples (NBR 6122)
*   **Arquivos modificados:** [fundacao_sapata.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/fundacao_sapata.py) e [rodar_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/rodar_galpao.py)
*   **Implementações realizadas:**
    *   Introduzido o novo tipo de fundação rasa `fund_tipo='bloco'` através da função `dimensiona_bloco_env`.
    *   Diferente da sapata armada, o bloco de concreto simples não possui armadura de flexão. O mecanismo de transferência de cargas baseia-se unicamente em bielas de compressão.
    *   Para garantir o comportamento de bloco simples sem fissuração por tração, a geometria do bloco adota a regra de rigidez geométrica da **NBR 6122:2022 item 7.8.2**, que impõe o ângulo $\beta \ge 60^\circ$ da face inclinada com a horizontal:
        $$h \ge \tan(60^\circ) \cdot \frac{dim\_bloco - dim\_pilar}{2}$$
    *   Limitação da tensão de tração média no solo: $\sigma_{t,adm} = \min(f_{ck}/25, 800\text{ kPa})$, correspondente a $0,8\text{ MPa}$ conforme literatura consagrada (Urbano Alonso).
*   **Confronto com a base técnica (NotebookLM) & Validação:**
    *   O ângulo $\beta \ge 60^\circ$ elimina a necessidade de armar o bloco. O teste `test_alonso_bloco_altura_beta_60` no arquivo [test_validacao_alonso.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/tests/test_validacao_alonso.py) comprova a equivalência com os exercícios resolvidos de Urbano Alonso, obtendo o ângulo exato de $60^\circ$ e a altura útil necessária sem ferragem.

---

## 4. Geometria 3D e Cumeeiras (TechDraw / FreeCAD)
*   **Arquivos modificados:** [build_galpao.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/build_galpao.py)
*   **Implementações realizadas:**
    *   A função `cumeeira_conn` foi estendida para aceitar parâmetros locais `ry` e `rh` por vão. Anteriormente, ela dependia de constantes globais estáticas (`RIDGE_Y` e `RIDGE_H`), o que causava a modelagem das chapas e parafusos de cumeeira fora da posição correta em pórticos de múltiplos vãos com vãos heterogêneos.
    *   A função `build` e `rafter_z` foram estendidas para suportar a montagem e renderização 3D de coberturas de 1 água (shed) com colunas de alturas diferentes e inclinação contínua sem cumeeira intermediária.

---

## 5. Viabilidade do Terreno (Mapeamento "Area-Only")
*   **Arquivos modificados:** [terreno.py](file:///C:/Users/joseh/OneDrive/Área%20de%20Trabalho/dev/FreeCad_Automatic/framework/galpao_fw/terreno.py)
*   **Implementações realizadas:**
    *   Permite a análise de viabilidade urbanística (Taxa de Ocupação, Coeficiente de Aproveitamento e Taxa de Permeabilidade) usando apenas a área informada pelo wizard (`area_lote_m2`), sem exigir o contorno do lote em KML ou lista de coordenadas.
    *   Nesse modo simplificado ("area-only"), a checagem de recuos de contorno é marcada como `PENDENTE`, não gerando falhas de execução no pipeline orquestrador.

---

# Pareceres Técnicos para Decisão (Engenheiro Responsável)

Solicitamos a manifestação do Engenheiro Sênior sobre os seguintes critérios adotados:

### 1. Critério de Altura de Sapata: Rigidez (NBR 6118) vs. Cisalhamento (Alonso/ACI)
*   **Situação:** Para uma sapata isolada submetida a $1700\text{ kN}$, o framework adotou a altura total $h = 0,70\text{ m}$ baseando-se rigorosamente no critério de sapata rígida da **NBR 6118 item 22.6.1** ($h \ge (L - a_p)/3$). O livro de Urbano Alonso, aplicando o critério do ACI 318 de cisalhamento unidirecional ($d$) e bidirecional ($d/2$ - puncionamento), adota uma altura menor ($h = 0,60\text{ m}$).
*   **Nossa Recomendação:** Manter o critério de **Sapata Rígida**. Além de estar a favor da segurança, a NBR 6118 dispensa a verificação de punção para geometrias rígidas, tornando o cálculo numérico automatizado muito mais confiável e padronizado nas prefeituras nacionais.

### 2. Espaçamento de Terças na Cobertura Shed
*   **Situação:** O telhado de 1 água (shed) segue o caimento geométrico e o vento correto. Contudo, o cálculo e espaçamento das terças no visual 3D ainda utiliza o espaçamento projetado originalmente para o telhado de 2 águas (com a mesma distância). A modelagem estrutural foi validada e está segura.
*   **Nossa Recomendação:** Aceitar a premissa de que a distribuição espacial das terças é cosmética na representação visual 3D e não compromete a rigidez ou a verificação de capacidade (NBR 8800). O multi-vão shed (dente-de-serra) segue bloqueado no validador por segurança.
