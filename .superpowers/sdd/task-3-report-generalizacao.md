# Relatório — Task 3: adaptador residencial sintético

## Arquivos alterados

- `framework/galpao_fw/casa_residencial_sintetica.py`
- `framework/galpao_fw/builtin_adapters.py`
- `.superpowers/sdd/task-3-report-generalizacao.md`

## Comportamento implementado

- Criado o adaptador `casa-residencial-sintetica`, sem importar módulos do
  galpão.
- Declaradas as disciplinas `arquitetura`, `eletrico` e `hidraulica`.
- Entradas sintéticas presentes produzem `needs_review`, com o gate
  `synthetic_fixture`, warning explícito e nenhum artefato técnico.
- Entradas sintéticas ausentes produzem `blocked`, com o erro
  `missing_synthetic_input`.
- O resultado do adaptador é serializável e identifica a fixture como
  sintética; não há cálculo técnico nem geração de IFC, modelo, desenho ou
  caderno.
- O carregador nativo registra o adaptador residencial após o galpão e
  preserva o guard de importação circular/directa do adaptador do galpão.

## RED

Comando:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py -k "residential_adapter_is_registered_with_declared_capabilities"
```

Resultado antes da implementação:

```text
1 failed, 9 deselected
AssertionError: adaptador casa-residencial-sintetica nao registrado;
adaptadores registrados: ['galpao']
```

## GREEN

Comando 1:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_generalization.py -k "residential_adapter_is_registered_with_declared_capabilities or galpao_adapter_is_directly_importable_in_a_fresh_process"
```

Resultado:

```text
2 passed, 8 deselected in 0.20s
```

Comando 2:

```powershell
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_adapter_contract.py framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py
```

Resultado:

```text
7 passed in 4.11s
```

## Commit

Commit da implementação da Task 3: `b6c35b816e1a67f97e0d47f2ef4625693ddbf9d2`.

O commit separado de documentação deste relatório é registrado no histórico
como o commit imediatamente seguinte.
