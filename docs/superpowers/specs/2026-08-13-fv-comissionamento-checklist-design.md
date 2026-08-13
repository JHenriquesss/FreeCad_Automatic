# Fase 20: checklist de comissionamento fotovoltaico

## Objetivo

Criar uma unidade pura do framework que transforme os requisitos verificáveis da
ABNT NBR 16274:2014 em um checklist rastreável de comissionamento de sistemas
fotovoltaicos. A unidade deve separar documentação, inspeção, ensaio e relatório,
sem escolher dados de catálogo, executar medições ou inventar critérios normativos.

## Evidência normativa

Fonte única declarada para esta unidade:

- NotebookLM `05_ELETRICA`: `78cd2efd-0652-484e-b312-c5c5a7648962`.
- ABNT NBR 16274:2014: source ID
  `4e6d55ec-65cf-4fc0-bf03-0d2648a6f731`, status remoto `2`.
- Hash e caminho local devem continuar sendo obtidos pelo catálogo antes de uma
  execução real do loop.

As consultas auditáveis confirmaram as seções 4.2.1, 4.3.1--4.3.5, todas as
alíneas 5.2.2(a-m), 5.2.5(a-g), 5.2.6(a-d), 6.1, 6.2, 6.4.2, 6.5, 6.6,
6.7.3/Tabela 1 e 9.1(a-f). O módulo
registrará a seção e o source ID em cada item e não usará a resposta combinada
sem citações como evidência.

## Contrato público

Criar `framework/galpao_fw/comissionamento_fv.py` com duas funções puras:

```python
montar_checklist_comissionamento_fv() -> list[dict]
validar_comissionamento_fv(caso: dict) -> dict
```

`montar_checklist_comissionamento_fv` retorna uma nova lista, em ordem estável,
com itens contendo `id`, `grupo`, `tipo`, `secao`, `criterio` e `referencia`.
Os grupos são `documentacao`, `inspecao`, `ensaio` e `relatorio`.

O caso de entrada possui uma chave `verificacoes`, indexada pelos IDs do
checklist. Para verificações qualitativas, `True` significa aprovado, `False`
significa reprovado e um dicionário pode fornecer `status` e `observacao`. O
validador rejeita chaves desconhecidas e campos extras em qualquer registro;
eles produzem `NAO_AVALIADO` e nunca podem resultar em aprovação.

Os ensaios quantitativos usam estes registros. A tensão para selecionar a faixa
da Tabela 1 não é aceita como valor nominal arbitrário: o validador calcula
`tensao_sistema_v = voc_stc_v * 1,25`.

```python
{
    "verificacoes": {
        "tensao_voc": {"medido_v": 1000.0, "referencia_v": 1000.0, "confirmado": True},
        "corrente_isc": {"medido_a": 10.0, "referencia_a": 10.0, "confirmado": True},
        "isolamento_cc": {
            "metodo": "metodo_1",
            "voc_stc_v": 240.0,
            "tensao_ensaio_v": 500.0,
            "resistencia_mohm": 1.0,
        },
    },
}
```

## Estados e regras

Cada item e o resultado geral usam somente `APROVADO`, `REPROVADO`,
`REVISAO_MANUAL` ou `NAO_AVALIADO`.

- `APROVADO`: requisito confirmado, ou ensaio com critério automático satisfeito.
- `REPROVADO`: requisito qualitativo explicitamente falso, ou resistência de
  isolamento abaixo da Tabela 1, ou tensão de ensaio diferente da prescrita.
- `REVISAO_MANUAL`: medição de Voc/Isc sem confirmação responsável, ou desvio
  que precisa de avaliação. O valor típico de 5% será somente alerta; nunca
  causará `REPROVADO` automaticamente.
- `NAO_AVALIADO`: item ausente, entrada inválida ou caso sem verificações.

Chaves desconhecidas em `verificacoes`, campos extras em registros qualitativos
ou quantitativos e tipos de chave que não possam ser ordenados são entradas
inválidas. O resultado deve permanecer não aprovado, sem exceção não tratada.

O resultado geral terá `ok`, `status`, `itens`, `falhas`, `avisos` e
`referencias`. `ok` só será verdadeiro quando o status geral for `APROVADO`.
A precedência geral é `REPROVADO`, `REVISAO_MANUAL`, `NAO_AVALIADO`,
`APROVADO`.

### Critérios automáticos

Para isolamento, calcular a faixa a partir de `voc_stc_v * 1,25` e exigir
simultaneamente a tensão de ensaio e a resistência mínima da Tabela 1:

| Tensão do sistema | Tensão de ensaio | Resistência mínima |
| --- | ---: | ---: |
| `< 120 V` | `250 Vcc` | `0,5 MOhm` |
| `120--500 V` | `500 Vcc` | `1,0 MOhm` |
| `> 500 V` | `1 000 Vcc` | `1,0 MOhm` |

Os limites de 120 V e 500 V são inclusivos na faixa intermediária. Valores
ausentes, não positivos, não finitos ou de tipo inválido não serão calculados;
um cálculo derivado não finito também nunca poderá aprovar o ensaio.

Para Voc e Isc, o módulo calcula o desvio percentual quando houver medição e
referência positivas. O valor típico de 5% aparece em `avisos` e não é tratado
como limite de aprovação; a confirmação de um responsável pode encerrar o item
como `APROVADO`.

## Fora do escopo

- dimensionamento de strings, proteção, conectores ou interface com a rede;
- interpretação de outras normas ou da vigência regulatória da ANEEL;
- execução de ensaios, captura de fotos ou geração de PDF;
- aceitação automática de texto livre como evidência;
- substituição da inspeção e assinatura do responsável técnico.

## Integração no loop

O descobridor deve criar um candidato atômico `fv-commissioning-checklist` a
partir da pendência de vigência das normas fotovoltaicas, com disciplina
`eletrica`, tópico `fotovoltaico`, prioridade abaixo do validador de strings e
exatamente a fonte local da NBR 16274. O candidato deve apontar para o novo
teste, sem ampliar a consulta para o notebook inteiro.

## Critérios de aceitação

- o checklist tem referências completas e ordem determinística;
- todos os estados, entradas inválidas, chaves desconhecidas e campos extras são cobertos por testes;
- as três faixas de isolamento e suas fronteiras são testadas;
- Voc/Isc nunca reprovam somente pelo valor típico de 5%;
- a descoberta retorna o candidato com uma única fonte declarada;
- a suíte focal, a suíte do loop e a compilação passam;
- revisão do diff não deixa regra sem referência, branch sem teste ou marcador
  de trabalho incompleto.
