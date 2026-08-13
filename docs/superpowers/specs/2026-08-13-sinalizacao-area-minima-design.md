# Fase 22: validação da área mínima de placas — NBR 16820

## Objetivo

Tornar rastreável no módulo de sinalização de emergência a verificação da área
real da placa contra a relação normativa da ABNT NBR 16820:2020. A validação
deve ser opcional para preservar as chamadas antigas que ainda não informam a
área fabricada, mas, quando a área for fornecida, não pode deixar uma placa
subdimensionada passar pelo gate `OK`.

## Evidência normativa

Fonte única declarada para esta unidade:

- NotebookLM `09_INCENDIO`: `a7e4b5d9-4e07-401b-970e-e973bae3aada`.
- ABNT NBR 16820:2020: source ID `3510e0c9-f90d-41b5-87ca-42446212c710`.
- Consulta auditável: seção 5.1.1 exige `A > L²/2000`; 5.1.1.1 limita a
  relação a `L < 50 m`; 5.1.1.2 determina que a medida mínima considerada seja
  `L = 4 m`.

Não usar resposta do NotebookLM sem `sources_used`, `citations` e `references`
do source acima. A ausência de NBR 15200 não bloqueia esta unidade porque a
regra é exclusiva da sinalização de emergência e está no PDF local da NBR
16820.

## Contrato público

As APIs existentes continuam válidas:

```python
area_minima_placa(L: float) -> float
dimensiona_sinalizacao(caso: dict) -> dict
```

`dimensiona_sinalizacao` aceita opcionalmente `area_placa_m2`. A presença da
chave exige um número real finito e não negativo. O retorno acrescenta:

- `distancia_calculo_m`: `max(dist_visualizacao_m, 4.0)`;
- `area_minima_m2`: valor usado na comparação;
- `area_placa_m2`: área informada, ou `None` quando ausente;
- `area_atende`: `True`/`False` quando a área foi informada, ou `None` no modo
  legado;
- `limite_normativo_excedido`: indica que a distância derivada da geometria
  atingiu `50 m` ou mais.

O campo legado `placa_area_min_m2` permanece no retorno, agora refletindo a
distância de cálculo e arredondado como antes. A comparação é estrita:
`area_placa_m2 > area_minima_m2`.

## Regras de entrada e compatibilidade

- `C`, `L` e uma `dist_visualizacao_m` informada explicitamente devem ser
  positivos e finitos.
- Uma `dist_visualizacao_m` explícita com `L >= 50 m` é entrada inválida e
  levanta `ValueError`, porque a relação citada não é válida nesse domínio.
- Quando `L >= 50 m` resulta apenas da geometria padrão, a função não quebra o
  pipeline existente: retorna `OK=False`, `placa_satura=True`,
  `limite_normativo_excedido=True` e não apresenta área como cálculo normativo.
- Sem `area_placa_m2`, `area_atende` é `None` e a área não derruba o resultado
  legado. Saturação da maior placa continua reprovando `OK`.
- Área zero passa pela validação de tipo, mas reprova pela desigualdade estrita.
  Valores negativos, `NaN`, infinitos, booleanos e tipos não numéricos levantam
  `ValueError`.
- O orquestrador já repassa o dicionário `sinalizacao`; não haverá duplicação de
  regra no orquestrador, no SVG ou no emissor BIM.

## Fora do escopo

- escolher automaticamente uma área comercial a partir do lado da placa;
- alterar a tabela de lados padronizados ou os espaçamentos da NBR 16820;
- validar projeto arquitetônico, rotas de fuga da NBR 9077 ou estruturas em
  situação de incêndio;
- substituir análise e assinatura do responsável técnico.

## Integração no loop

O descobridor terá uma unidade atômica `sinalizacao-area-minima`, disciplina
`seguranca`, tópico `sinalizacao`, prioridade 75 e exatamente a fonte local da
NBR 16820. A unidade será criada a partir da thread T42 e apontará para o teste
focal; ao fechar a fase, a thread será marcada como resolvida para não ser
redescoberta.

## Critérios de aceitação

- `L=10 m` exige área estritamente maior que `0,05 m²`;
- `L<4 m` calcula a área com `L=4 m`;
- ausência de área preserva o comportamento legado;
- área inválida e distância explícita fora do domínio falham com `ValueError`;
- galpão cuja distância derivada satura continua reprovado sem extrapolação
  normativa silenciosa;
- orquestrador, desenho e BIM permanecem compatíveis;
- descoberta retorna uma única fonte pronta e o teste focal;
- testes focais, regressões de incêndio, testes do loop, compilação e `git diff
  --check` passam.
