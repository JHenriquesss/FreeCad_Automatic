# Relatório — correção Task 4: metadado explícito do fixture do galpão

## Escopo

Foi alterado somente o teste autorizado:

- `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`

O relatório foi criado no arquivo autorizado:

- `.superpowers/sdd/task-4-fix-report-generalizacao.md`

Núcleo, adaptadores, fixture residencial e `tests/conftest.py` permaneceram
inalterados.

## RED antes da correção

Com `run_project(turnkey_fixture(), ...)`, o teste universal do manifesto
falhava porque o formato legado não declarava `project.type`:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py
........F.                                                               [100%]
1 failed, 9 passed
```

A falha era `isinstance(manifest["project_type"], str)`, pois o valor era
`None`.

## Correção

O teste agora envolve o mesmo `turnkey_fixture()` em um envelope explícito de
`project-spec`, declarando `slug` e `type: "galpao"`. As asserções universais
foram preservadas.

## GREEN

Branch de generalização:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py
..........                                                               [100%]
10 passed in 1.70s
```

Branch completa e trunk:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py
........................................                                 [100%]
114 passed in 66.45s (0:01:06)
```

As duas execuções terminaram com código de saída zero.
