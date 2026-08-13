# Fase 24: guarda de escopo da pesquisa NotebookLM — desenho

## Contexto

O dry-run `loop-20260813T214243716844Z` escolheu a candidata ampla
`05f6b69aedb5`, cuja `source_paths` estava vazia. O adaptador de pesquisa tratou
essa ausência como autorização para listar todas as fontes prontas do notebook
de incêndio; a consulta atingiu o timeout e não produziu evidência. Isso
contradiz o contrato documentado de que cada candidata deve declarar o escopo
normativo exato.

## Decisão

O loop adotará uma guarda estrita antes da consulta:

- `tools/loops/__main__.py::_research_candidate()` exigirá pelo menos um caminho
  em `candidate.source_paths`;
- quando a lista estiver vazia, levantará `ValueError` com a ação de decompor a
  pendência e declarar os caminhos locais;
- `tools/loops/supervisor.py` reconhecerá `source scope` como lacuna de fonte e
  estacionará a tarefa como `manual_source_required` antes de qualquer chamada ao
  NotebookLM;
- fontes prontas do notebook inteiro continuarão disponíveis apenas para uso
  explícito de API interna, nunca como fallback de uma candidata sem escopo;
- a descoberta continuará expondo itens amplos para que permaneçam auditáveis,
  mas o scheduler os bloqueará até que uma unidade atômica declare suas fontes.

## Alternativas rejeitadas

- Consultar o notebook inteiro com limite de tempo: evita o timeout infinito, mas
  não garante que as citações sustentem a norma da tarefa.
- Inferir automaticamente os PDFs pelo título: pode escolher edição, suplemento
  ou disciplina errada e viola `Ask, Do Not Invent`.
- Remover candidatos sem escopo da descoberta: esconderia lacunas e impediria o
  ledger de registrar a ação manual necessária.

## Critérios de aceite

- candidata sem `source_paths` falha antes de `list_ready_sources()` e de qualquer
  comando `nlm notebook query`;
- o supervisor estaciona essa candidata como `manual_source_required`, grava a
  assinatura e não cria worktree nem executa testes de implementação;
- candidata com `source_paths` continua usando somente
  `list_ready_sources_for_paths()`;
- testes atuais do loop permanecem verdes;
- o README explica que itens amplos devem ser decompostos antes da pesquisa;
- o dry-run de diagnóstico não volta a terminar por timeout causado por escopo
  vazio.

## Fora de escopo

Esta fase não decompõe as pendências NBR 12693/NBR 13434, não baixa fontes, não
altera a descoberta de disciplinas e não muda o contrato de evidência citada.
