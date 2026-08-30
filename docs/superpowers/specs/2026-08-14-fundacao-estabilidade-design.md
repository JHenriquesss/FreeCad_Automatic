# Verificação de estabilidade de fundações rasas — desenho

**Status:** aprovado em conversa; aguardando revisão da especificação escrita antes da implementação

**Escopo:** `framework/galpao_fw/fundacao_sapata.py` e os adaptadores de configuração que alimentam esse módulo.

## Objetivo

Separar, no cálculo de sapatas e blocos, dois métodos que hoje estão misturados:

1. `nbr6122_valores_calculo`: ações e resistências verificadas por coeficientes parciais, com rastreabilidade dos fatores aplicados.
2. `fs_global_legacy`: ações características verificadas por fatores globais de segurança informados pelo responsável, sem criar automaticamente um FS universal de 1,5.

O resultado deve deixar claro se a entrada já é característica ou de cálculo, impedir dupla majoração e registrar quando um caminho antigo de compatibilidade foi usado.

## Base normativa consultada

A fonte local OCR da ABNT NBR 6122:2022 foi carregada no NotebookLM de fundações e revalidada. Os pontos relevantes para esta fase são:

- **6.2.1.1.2:** para tração, deslizamento e tombamento, a fonte indica minoração de 1,2 para a parcela favorável do peso, minoração de 1,4 para a resistência do solo e majoração de 1,4 para o esforço atuante quando só houver valor característico.
- **6.2.1.1.3:** o FS global mínimo de 1,1 é específico para flutuação; não será reutilizado para deslizamento ou tombamento.
- **7.6.2:** a área comprimida mínima é 2/3 da base para solicitações características e 50% para solicitações de cálculo.
- **7.6.3:** a resistência passiva só pode ser considerada quando o solo não será removido durante a vida útil; a pressão passiva calculada deve ser reduzida por coeficiente mínimo 2,0 para limitar deformações.

A norma consultada não confirma um FS global universal de 1,5 para deslizamento/tombamento. Portanto, esse valor não será tratado como requisito normativo.

## Contrato de configuração

O contrato canônico no `spec` será aninhado em `fundacao.verificacao_estabilidade`:

```python
{
    "metodo": "nbr6122_valores_calculo",
    "tipo_acoes": "caracteristicas",  # ou "calculo"
    "gamma_f": 1.4,
    "gamma_peso_favoravel": 1.2,
    "gamma_resistencia_solo": 1.4,
    "peso_favoravel_superestrutura_kN": 0.0,
    "N_acao_desfavoravel_kN": None,
    "fs_tombamento": None,
    "fs_deslizamento": None,
    "empuxo_passivo_kN": 0.0,
    "solo_nao_removivel": False,
}
```

O caso achatado usado por `fundacao_sapata` aceitará a mesma configuração em `caso["verificacao_estabilidade"]`. Durante a transição, o normalizador também reconhecerá os campos legados `fs_tomb_min` e `fs_desl_min`, sem alterar silenciosamente seus significados.

Valores permitidos:

- `metodo`: exatamente `nbr6122_valores_calculo` ou `fs_global_legacy`.
- `tipo_acoes`: exatamente `caracteristicas` ou `calculo`; `fs_global_legacy` aceita somente `caracteristicas`.
- Todos os coeficientes devem ser numéricos e positivos.
- No modo legado, `fs_tombamento` e `fs_deslizamento` devem ser fornecidos explicitamente para um caso novo.
- No modo NBR, FS globais não serão combinados com os coeficientes parciais; se forem fornecidos, a validação do caso será bloqueada com erro de configuração conflitante.
- Em `tipo_acoes == "caracteristicas"`, `N_acao_desfavoravel_kN` e `peso_favoravel_superestrutura_kN` devem ser declarados separadamente quando a reação vertical `N` vier agregada. A soma dessas parcelas deve reproduzir a reação vertical externa fornecida. Sem essa decomposição o caso será `inconclusivo`, pois o motor não poderá decidir se uma parcela vertical é ação ou peso favorável.

## Regras de cálculo

### Modo `nbr6122_valores_calculo`

- Se `tipo_acoes == "caracteristicas"`, majorar `V`, `M` e `N_acao_desfavoravel_kN` pelo `gamma_f` declarado. A parcela vertical externa será composta explicitamente por `N_acao_desfavoravel_kN` e `peso_favoravel_superestrutura_kN`; o peso favorável será minorado, e uma parcela vertical desfavorável não será convertida em peso.
- Reduzir a parcela favorável de peso, formada pelo peso próprio local e por `peso_favoravel_superestrutura_kN`, pelo `gamma_peso_favoravel`.
- Em `tipo_acoes == "calculo"`, usar as parcelas de `N`, `V` e `M` já fatoradas sem nova majoração; somente a parcela explicitamente informada como peso favorável será minorada para a verificação de estabilidade.
- Reduzir a resistência do solo, incluindo atrito e coesão efetivamente mobilizados, pelo `gamma_resistencia_solo`.
- Exigir área comprimida mínima de 50% da base.
- Exigir que o resultado identifique os valores de entrada, os valores usados e cada fator aplicado.
- Não introduzir fórmulas de empuxo passivo genéricas nesta fase. Quando `empuxo_passivo_kN` for positivo, ele só poderá entrar se `solo_nao_removivel` for verdadeiro e será reduzido por fator mínimo 2,0.

### Modo `fs_global_legacy`

- Interpretar o caso novo como baseado em ações características.
- Usar `fs_tombamento` e `fs_deslizamento` fornecidos pelo caso.
- Não aplicar automaticamente `gamma_f`, `gamma_peso_favoravel` ou `gamma_resistencia_solo`.
- Exigir área comprimida mínima de 2/3 da base para o caminho característico.
- Não usar os atuais `FS_TOMB_MIN = 1.5` e `FS_DESL_MIN = 1.5` como requisitos normativos. Eles ficarão apenas como fallback transitório de chamadas sem configuração, com aviso explícito de legado.

### Chamadas sem configuração

Chamadas diretas antigas que não possuem `verificacao_estabilidade` continuarão funcionando temporariamente para preservar regressões existentes. Elas deverão retornar:

- `metodo_verificacao == "compatibilidade_legacy"`;
- aviso de que os critérios antigos, inclusive o terço médio e os FS legados, não são uma escolha normativa válida para um novo projeto;
- nenhum novo adaptador ou template deverá gerar essa configuração implícita.

O template de projeto novo deverá declarar explicitamente o modo NBR. O adaptador do fluxo `rodar_galpao` deverá marcar corretamente como `calculo` as combinações que já chegam fatoradas, evitando dupla majoração.

## Saída auditável

`verifica_sapata_A` manterá as chaves existentes e acrescentará, no mínimo:

```python
{
    "metodo_verificacao": "nbr6122_valores_calculo",
    "tipo_acoes": "caracteristicas",
    "fatores_verificacao": {
        "gamma_f": 1.4,
        "gamma_peso_favoravel": 1.2,
        "gamma_resistencia_solo": 1.4,
        "fator_empuxo_passivo": 2.0,
    },
    "area_comprimida_ratio": 0.50,
    "limite_area_comprimida": 0.50,
    "avisos_verificacao": [],
}
```

Os nomes acima representam contrato de resultado, não arredondamento de relatório. O valor de `area_comprimida_ratio` será calculado com `x_contato / L`, limitado ao intervalo físico `[0, 1]` quando a geometria for válida.

## Limites desta fase

Incluído:

- normalização e validação dos dois métodos;
- aplicação isolada dos fatores em estabilidade de sapata;
- critério de área comprimida da NBR 6122;
- rastreabilidade no resultado e no relatório textual;
- propagação explícita pelo template de projeto e pelo caminho do galpão;
- regressões unitárias e de integração do dimensionador de sapata.

Não incluído:

- cálculo automático de parâmetros geotécnicos, atrito ou coesão;
- cálculo de empuxo passivo a partir de geometria do terreno;
- revisão das combinações globais NBR 8681 fora da entrada da fundação;
- alteração de fundações profundas;
- decisão de projeto sobre quais parcelas de uma reação externa são favoráveis. Quando a decomposição não puder ser determinada pelo adaptador, o caso deve carregar a classificação explicitamente ou ser sinalizado como inconclusivo.

## Estratégia de testes

Os testes serão escritos antes do código de produção e executados em ciclos RED/GREEN:

1. modo NBR aceita contato de 50% e rejeita contato abaixo desse limite;
2. modo legado exige FS explícito e não injeta FS 1,5 em caso novo;
3. modo legado usa contato de 2/3 para ações características;
4. modo NBR aplica fatores uma única vez e não reaplica `gamma_f` a ações já de cálculo;
5. peso favorável e resistência do solo aparecem com os fatores corretos no resultado;
6. empuxo passivo é ignorado sem `solo_nao_removivel` e reduzido por pelo menos 2 quando habilitado;
7. chamadas antigas continuam funcionando apenas pelo caminho de compatibilidade e produzem aviso;
8. `dimensiona_sapata`, `dimensiona_sapata_env` e o fluxo do galpão propagam a configuração sem mutá-la entre combinações;
9. a suíte existente de fundações permanece verde, descontadas falhas preexistentes já registradas pelo supervisor.

## Riscos e decisões de segurança

- Não será permitido inferir que uma reação vertical inteira é peso favorável sem declaração do adaptador; essa inferência pode superestimar a estabilidade.
- Não será permitido tratar o FS de flutuação 1,1 como FS de deslizamento/tombamento.
- Uma ação já fatorada não poderá receber `gamma_f` novamente.
- Resultado `compatibilidade_legacy` não será apresentado como validação NBR 6122.
