# Task 5 - Gates de execucao e testes

## Entrega

- Criado `tools/loops/commands.py` com execucao delimitada por timeout,
  captura de stdout/stderr e encerramento de processo timeoutado.
- Criado `tools/loops/tests_runner.py` com snapshots, parser de sumario pytest,
  delta de falhas preexistentes/novas e politica de promocao.
- Estendido `CommandResult` com `timed_out=False` para preservar a marcacao sem
  quebrar os consumidores existentes.
- Criado `tools/loops/tests/test_commands_and_tests.py` com fakes e subprocessos
  curtos; a saida completa fica no snapshot e tambem em artefatos UTF-8 do
  `.loop-runtime/test-results` por padrao (ou diretorio fornecido pelo chamador).

## Contratos verificados

- Targeted e regression rodam em `framework/galpao_fw`; build roda na raiz.
- Targeted usa pytest sem cache; regression usa `tools/run_tests.py`; build usa
  `tools/run_build_suite.ps1` com timeout separado.
- Timeout retorna `returncode=-1`, `timed_out=True`, duracao e saidas preservadas.
- O delta distingue falhas/erros preexistentes, novos e resolvidos por ID de
  teste; uma falha nova, erro novo, timeout ou alvo nao aprovado bloqueia promocao.
- Build so e exigido quando `build_required=True`; a execucao opcional nao cria
  um gate oculto.

## TDD e verificacao

- RED: a coleta inicial falhou por ausencia de `tools.loops.commands`.
- GREEN focado: `python -B -m pytest -p no:cacheprovider tools/loops/tests/test_commands_and_tests.py -q`
  -> 8 passed.
- GREEN completo: `python -B -m pytest -p no:cacheprovider tools/loops -q`
  -> 75 passed.
- Compilacao: `python -m py_compile tools/loops/commands.py tools/loops/tests_runner.py tools/loops/tests/test_commands_and_tests.py`.
- Nenhum comando externo pesado, rede ou build FreeCAD foi executado nesta tarefa.
