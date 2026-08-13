# Task 9 - primeira execucao real supervisionada

## Resultado atual

- `nlm login --check` valido; perfil `default`, conta `henriquessilvat@gmail.com`,
  64 notebooks.
- Suíte do loop: 118 testes passando.
- Baseline do framework: 1.413 testes coletados; `framework/galpao_fw/tools/run_tests.py`
  excedeu 604 s no ambiente local. Nenhum processo FreeCAD permaneceu ativo.
- Dry-run real final: `loop-20260813T013026156810Z`, `outcome=dry_run`,
  `phase=park`, notebook `abc2617c-7a60-4c9f-a12a-1078a520fc9c`, 9 fontes prontas,
  41 citações com trechos textuais.
- Consulta isolada da NBR 6122:2022 usando somente o source ID
  `fbbdff0f-de66-4c13-a414-284aaf8b8fb9` retornou `sources_used: []`,
  `citations: {}` e `references: []`.
- Diagnóstico do PDF local: 120 páginas, 120 imagens e 0 caracteres extraídos em
  todas as páginas; a fonte precisa ser substituída por OCR/textual ou reprocessada.

## Candidata e decisão

- Candidata: fator de segurança 1,5 para tombamento/deslizamento.
- A resposta consultou livros de fundações, mas não produziu citações da fonte
  `fbbdff0f-de66-4c13-a414-284aaf8b8fb9` (NBR 6122:2022), embora a mencionasse.
- Nenhuma implementação ou execução de agente foi autorizada; a evidência não
  sustenta confirmar o parâmetro normativo.
- O loop não deve tratar a resposta textual sem `sources_used`/citações como
  confirmação normativa; a fila manual foi registrada em `fontes/pendencias-atualizacao.md`.

## Hardening aplicado

- Descoberta usa origem/caminho da evidência para classificar fundações antes de
  “fator de segurança” e filtrar testes por disciplina; commits `e9ef6db` e
  `e1f8f86`.
- Saída do `nlm` lida explicitamente como UTF-8 no Windows.
- Formato real `citations` como mapa + `references` aceito.
- Citação sem trecho ou resposta sem citações gera fila manual e estaciona.
- Timeout externo de pesquisa limitado a 180 s e classificado como `command_timeout`.

## Próximo passo

Corrigir/reindexar a NBR 6122:2022 no NotebookLM, confirmar citações textuais
para tombamento/deslizamento e repetir o dry-run. A autenticação foi verificada
novamente em 2026-08-13 (`nlm login --check`: 64 notebooks). Só depois selecionar
uma tarefa de módulo único, executar RED e iniciar a primeira rodada `supervised`.
