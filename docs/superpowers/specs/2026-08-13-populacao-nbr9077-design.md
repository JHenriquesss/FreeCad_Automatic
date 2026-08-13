# Fase 23: população de depósitos pela NBR 9077:2025 — desenho

## Contexto

O vertical de segurança contra incêndio já calcula iluminação de emergência,
sinalização, detecção, sprinklers e hidrantes, mas ainda não possui uma unidade
explícita para a população de projeto das rotas de saída. A consulta normativa foi
feita no NotebookLM `09_INCENDIO`, usando somente o source ID
`878dc921-2664-43ec-b2c8-14641b3c7641`, correspondente ao arquivo local
`09_INCENDIO/INCENDIO__NBR__NBR-9077-2025__saidas-emergencia.pdf`.

## Evidência normativa

- A seção 5.1 determina que a área computável exclua circulação vertical protegida,
  caixas de elevadores, shafts, vazios, áreas técnicas sem ocupação humana contínua
  e sanitários; a seção 5.1.2 determina a inclusão de áreas descobertas com presença
  humana prevista.
- A seção 5.2 e a Tabela 4 estabelecem, para “Depósitos em geral”, uma pessoa por
  30 m² de área computável.
- A seção 5.3 trata assentos fixos e não faz parte desta fase.
- A consulta isolada não encontrou, na NBR 9077:2025, regra para arredondar a divisão
  de área por densidade. O sistema não pode escolher `ceil`, `floor` ou `round` como
  se fossem exigência normativa.

## Escopo

Será criado o módulo puro `framework/galpao_fw/populacao_nbr9077.py` com uma função
para depósitos. O chamador fornecerá a área bruta do pavimento e listas explícitas de
áreas a excluir ou incluir; o módulo calculará a área computável e a população exata.
O vertical `galpao_seguranca_incendio.rodar()` aceitará opcionalmente o bloco
`spec["populacao"]`, mas não inventará esse bloco nem deduzirá a área computável de
`geometria`.

## Contrato

```python
dimensiona_populacao_deposito(
    area_pavimento_m2,
    *,
    areas_excluidas_m2=(),
    areas_incluidas_m2=(),
) -> dict
```

O retorno conterá:

- `area_pavimento_m2`, `areas_excluidas_m2`, `areas_incluidas_m2`;
- `area_computavel_m2 = area_pavimento_m2 - sum(excluídas) + sum(incluídas)`;
- `densidade_m2_por_pessoa = 30.0` e `populacao_exata`;
- `populacao_inteira = None`, `politica_arredondamento = None` e
  `arredondamento_normativo = "nao declarado pela NBR 9077:2025"`;
- `requer_decisao_arredondamento = True`, `pronto_para_rotas = False` e `OK = True`
  somente para indicar que o cálculo da área e da população exata é válido.

O gate opcional do vertical usará `OK = pronto_para_rotas`, mantendo separado o
resultado aritmético da autorização para dimensionar rotas com população inteira.
Assim, uma entrada explícita sem política de arredondamento reprova o gate de rotas
sem apagar a evidência do cálculo.

## Validações e anti-invenção

- Todas as áreas devem ser reais, finitas e não negativas; a área do pavimento deve
  ser positiva e a área computável resultante deve permanecer positiva.
- `bool`, texto, `NaN`, infinito e coleções inválidas levantam `ValueError` limpo.
- O módulo não classifica automaticamente áreas como técnicas, protegidas ou de uso
  humano; essa classificação vem nas listas explícitas do chamador.
- O módulo não transforma população exata em população inteira.
- Não serão alterados nesta fase os limites de caminhamento, largura das rotas,
  quantidade de saídas, BIM ou pranchas.

## Integração

Quando `spec["populacao"]` existir, o vertical repassará seus campos ao módulo e
retornará `res["populacao"]` e `gates["populacao"]`. O relatório textual exibirá a
população exata e o bloqueio de decisão. Sem esse bloco, as chamadas antigas
permanecerão compatíveis e sem um gate oculto.

## Testes e critérios de aceite

- unidade de depósito: 600 m² → 20 pessoas exatas;
- exclusões e inclusões explícitas alteram a área computável pela fórmula declarada;
- área computável fracionária retorna população fracionária e não arredonda;
- entradas inválidas levantam `ValueError`;
- integração opcional produz gate reprovado para rotas enquanto a política faltar;
- chamadas antigas do vertical permanecem verdes;
- descoberta do loop usa a fonte NBR 9077:2025 por caminho exato;
- consulta/dry-run registra NotebookLM, source ID e citações antes do fechamento.
