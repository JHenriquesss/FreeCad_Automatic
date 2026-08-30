# Task 1 — RED: testes de generalização do `project_loop`

## Escopo executado

- Criado somente o teste `framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py`.
- Não foram criados arquivos de produção.
- Não foi criado o spec persistido `projects/casa-residencial-sintetica/project-spec.json`.
- Alterações preexistentes do checkout foram preservadas.

## Comando RED

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py
```

## Resultado RED

O comando terminou com código de saída `1`:

```text
FFFFFFFF                                                                 [100%]
8 failed in 0.87s
```

As falhas são as esperadas para esta etapa:

1. `test_residential_adapter_is_registered_with_declared_capabilities` falhou com `StopIteration`, pois `casa-residencial-sintetica` ainda não está registrada.
2. Os testes de execução e verificação falharam ao carregar o fixture ausente com `project_io.ProjectSpecFileError: arquivo de spec nao encontrado: ...\projects\casa-residencial-sintetica\project-spec.json`.
3. `test_residential_execution_does_not_import_galpao_turnkey` falhou no subprocesso pelo mesmo fixture ausente, com retorno `1`.

Não houve erro de coleta, erro de sintaxe, erro de importação do módulo de teste ou falha causada por caminho incorreto do teste. O teste do galpão não foi alterado nem executado nesta Task 1.

## Cobertura definida

O teste RED define o contrato para:

- registro do adaptador residencial e suas capacidades;
- execução pelo caminho real `run_project_file`;
- estados honestos de hooks opcionais;
- isolamento de importação de `galpao_turnkey`;
- bloqueios de tipo e geometria;
- chaves universais do manifesto entre casa e galpão;
- detecção de adulteração por hash.

## Verificação de escopo

O único arquivo destinado ao commit desta Task 1 é:

```text
framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py
```

O relatório foi atualizado no caminho solicitado, mas não será incluído no commit da Task 1.
