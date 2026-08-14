# Segurança de armazenamento por chuveiros — NBR 16981:2021

**Status:** aprovado operacionalmente pela continuidade do loop; implementação ainda não iniciada.

## Objetivo

Adicionar ao vertical de segurança contra incêndio um gate explícito para áreas de armazenamento, sem substituir o dimensionamento existente de sprinklers da NBR 10897 e sem usar outra norma como fonte. O gate deve distinguir dados ausentes, que tornam o resultado inconclusivo, de condições conhecidamente incompatíveis, que reprovam o projeto.

## Fonte autorizada

- Notebook: `a7e4b5d9-4e07-401b-970e-e973bae3aada`.
- Source ID: `ce183de0-750c-4330-bf4d-a5a67a15f012`.
- Arquivo local: `09_INCENDIO/INCENDIO__NBR__NBR-16981-2021__sprinklers-areas-armazenamento.pdf`.
- Consulta real: conversation ID `dde31ba7-c6a6-4494-9031-d7b94a146d7a`; o adaptador normalizou 10 referências com seção e `cited_text`.
- É proibido completar valores com NBR 10897, NBR 13792, instrução técnica estadual, fabricante ou memória de projeto não citada nesta fase.

## Contrato executável

Criar `verifica_armazenamento_nbr16981(caso)` em módulo próprio. O argumento é um dicionário de projeto; não há defaults normativos. O retorno contém:

```python
{
    "OK": bool,
    "inconclusivo": bool,
    "faltantes": list[str],
    "violacoes": list[str],
    "requisitos_aplicados": list[str],
}
```

Campos gerais obrigatórios:

- `mercadoria_risco_mais_grave_declarada: bool` — Anexo B, B.2.2.1;
- `altura_armazenamento_m: number` e `altura_teto_m: number`;
- `interpolacao_densidade_area: bool` — a condição `True` reprova, pois a norma não permite interpolação para alturas intermediárias.

Quando `altura_armazenamento_m > 3.7`, exigir e verificar `densidade_projeto_Lmin_m2 >= 6.1` e `area_operacao_m2 >= 186`, conforme 5.2.2.4. Ausência é inconclusiva.

Quando `armazenamento_encapsulado` for `True`, exigir `densidade_base_Lmin_m2` e verificar que a densidade de projeto foi aumentada em pelo menos 25%, conforme 6.3.1.2.1.

Quando `sistema_esfr` for `True`, exigir `sem_extracao_ou_barreira_fumaca == True`, `n_chuveiros_operacao == 12` e `n_ramais_operacao == 3`, conforme 4.1.1 e 8.3.3.3. A ausência de qualquer campo é inconclusiva; valor incompatível reprova.

Quando `chuveiros_intraprateleiras` for `True`, exigir `area_porta_paletes_m2 <= 3700`, conforme 4.6.1. A consulta específica não determinou um limite de 115 L/min para altura superior a 7,6 m; esse critério permanece lacuna e não será implementado nesta fase.

Quando `bobinas_papel` for `True` e a altura de armazenamento for pelo menos 4,6 m, exigir `chuveiro_temperatura_alta == True`, conforme 9.1.4.1.4. Se `metodo_area_densidade` for `True`, verificar `6.5 <= area_por_chuveiro_m2 <= 9.3`, conforme 9.1.4.1.5.

Quando `papel_tissue` for `True` e a altura superar 6,1 m, o resultado deve ser inconclusivo e declarar a lacuna da Nota 2 de 9.1; não reprovar por um limite inventado.

## Integração

`galpao_seguranca_incendio.rodar(spec)` só cria `gates["armazenamento_nbr16981"]` quando `spec["armazenamento_nbr16981"]` existir. O gate será incluído em `reprovados`, `ATENDE` e no resultado serializável. A ausência do bloco preserva o contrato histórico do vertical. O módulo `proteccao_sprinklers_nbr10897.py` não será alterado nesta fase.

## Descoberta e pesquisa

Adicionar uma candidata atômica `fogo_armazenamento` em `tools/loops/discovery.py`, com o caminho de fonte acima, testes sugeridos do novo módulo e do vertical, e prompts que exigem somente o source ID autorizado. O prompt deve declarar que tabelas ou critérios não citados retornam como lacuna, nunca como default.

## Critérios de aceitação

- Todo requisito implementado possui referência de seção e teste positivo/negativo.
- Dados ausentes produzem `OK=False` e `inconclusivo=True`.
- Violação conhecida produz `OK=False` e `inconclusivo=False`.
- Configuração completa e coerente produz `OK=True`.
- A pesquisa real gera `EvidenceBundle` com source ID exato, seção e texto citado.
- Targeted, regressão, revisão local e `py_compile` são executados pelo loop.

## Fora de escopo

Não dimensionar automaticamente tabela completa de ESFR, bombas, RTI, hidrantes, curvas hidráulicas, classificação detalhada de todas as mercadorias, critérios de fabricante ou aprovação do Corpo de Bombeiros. Esses itens serão candidatos posteriores quando houver fontes e dados de projeto suficientes.
