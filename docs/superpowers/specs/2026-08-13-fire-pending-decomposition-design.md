# Decomposição da pendência de proteção contra incêndio — Especificação de Design

**Data:** 2026-08-13
**Status:** aprovado para implementação nesta sessão
**Escopo:** Fase 27 do loop de desenvolvimento

## Objetivo

Transformar a pendência ampla que menciona NBR 12693 e NBR 13434 em duas tarefas
de pesquisa independentes, com escopo de fonte local explícito, para que cada uma
possa ser consultada, bloqueada ou concluída sem arrastar a outra.

## Contexto observado

`fontes/fontes-faltantes.md:P1` registra que a NBR 16981:2021 já cobre áreas de
armazenamento e que ainda faltam NBR 12693 e NBR 13434. Os dois PDFs ainda não
estão em `fontes/09_INCENDIO`, nem há entradas correspondentes no catálogo local.

Há também uma linha agregada em `fontes/pendencias-atualizacao.md`; ela não será
tratada como uma nova origem nesta fase para evitar duplicação.

## Decisão de decomposição

Serão criadas duas candidatas atômicas, além da candidata ampla original:

1. **NBR 12693 — proteção por extintores.**
2. **NBR 13434 — sinalização de segurança contra incêndio.**

Cada candidata atômica terá:

- disciplina `seguranca`;
- prioridade própria e menor que a tarefa já concluída de população/saídas;
- `topic` próprio para selecionar prompt e testes adequados;
- um único caminho declarado sob `09_INCENDIO`;
- título indicando que a edição da fonte ainda precisa ser confirmada;
- origem estável derivada da P1, garantindo IDs determinísticos.

## Caminhos canônicos pendentes

Enquanto a edição não for confirmada, os arquivos deverão ser organizados com os
seguintes nomes neutros:

```text
09_INCENDIO/INCENDIO__NBR__NBR-12693__sistemas-extintores.pdf
09_INCENDIO/INCENDIO__NBR__NBR-13434__sinalizacao-seguranca.pdf
```

O loop não deve consultar outro PDF de incêndio como substituto. Se o caminho
declarado estiver ausente, a solicitação manual deve registrar exatamente o
caminho faltante; se o arquivo existir mas não tiver texto extraível, o gate
local da Fase 26 deve estacionar a tarefa antes de qualquer consulta remota.

## Prompts

O tópico `extintores` deve pedir somente requisitos verificáveis de seleção,
distribuição, capacidade/quantidade, posicionamento e limitações expressamente
presentes na NBR 12693 fornecida, sempre com seção/tabela e source ID.

O tópico `sinalizacao_incendio` deve pedir somente requisitos verificáveis de
tipos, finalidade, características, localização e aplicação da sinalização
conforme a NBR 13434 fornecida, sempre com seção/tabela e source ID.

Os prompts não devem afirmar edição, valor ou regra que não esteja no PDF
declarado. A resposta de retry deve ser compacta e exigir citações textuais.

## Fora do escopo

- baixar ou procurar as normas na internet;
- alterar `framework/galpao_fw` ou implementar regras de engenharia;
- criar notebooks ou alterar o mapa remoto;
- remover a candidata ampla original;
- considerar a linha duplicada de `pendencias-atualizacao.md` uma nova tarefa.

## Critério de aceitação

Os testes devem provar a decomposição, a estabilidade das origens/IDs, os
caminhos de fonte e os prompts. Um dry-run real deve selecionar uma candidata
atômica e, com os PDFs ausentes, gerar pedido manual antes de `nlm notebook query`.
