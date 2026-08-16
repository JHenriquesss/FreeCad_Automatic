# Relatório — Task 3: padrão de entrada Enel BT

## RED

Comando:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py
```

Resultado: coleta interrompida com `ModuleNotFoundError: No module named 'entrada_enel_bt'`, conforme esperado para o módulo ausente.

## GREEN

Comando focal:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py
```

Resultado: `8 passed in 0.14s`.

Verificação detalhada:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py -vv
```

Resultado: os 8 testes passaram, incluindo seleção por tipo de fornecimento, distinção dos Anexos A/C e bloqueios de tensão/carga sem linha.

Verificações adicionais:

```text
python -m py_compile framework/galpao_fw/entrada_enel_bt.py
git diff --check -- framework/galpao_fw/entrada_enel_bt.py
```

Resultado: ambas passaram sem saída de erro.

## Implementação

- Tabelas imutáveis para Anexo A (127/220, página 72) e Anexo C (120/240, página 77).
- Tipo de fornecimento obrigatório e validado; nenhuma seleção cruza tipos.
- Limite inferior exclusivo e limite superior inclusivo.
- Retorno com `document`, `edition`, `annex` e `page`.
- Campos não transcritos permanecem `None` e geram warning `not_transcribed`.
- Sem imports de galpão, FreeCAD, `project_loop` ou NotebookLM.

## Correção TDD — ponto de conexão do C3

O teste `test_annex_a_selects_c3_without_silently_changing_type` foi corrigido
para esperar `point_of_connection == "medidor"`, conforme o PDF Enel
R02/2025, página 72, e o brief: C1, C2 e C3 usam medidor; C4 a C9 usam poste.

RED após corrigir o teste:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py
```

Resultado: `1 failed, 7 passed`; a falha era exclusivamente o C3 retornado
como `poste` pelo módulo.

GREEN após corrigir `entrada_enel_bt.py`:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py
```

Resultado: `8 passed`.

Verificações adicionais após a correção:

```text
python -m py_compile framework/galpao_fw/entrada_enel_bt.py
git diff --check -- framework/galpao_fw/entrada_enel_bt.py framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py
```

Resultado: ambas passaram sem saída de erro.

## Preocupações

- Nenhuma preocupação funcional nesta correção; C3 agora está alinhado à fonte e C4-C9 permanecem como `poste`.
- As faixas e campos continuam limitados à transcrição do brief; não foram adicionadas linhas ou valores não transcritos.

## Correção TDD — limites normativos e medição

Foram adicionados testes parametrizados sem alterar os testes anteriores para
as fronteiras publicadas na página 72 (Anexo A) e página 77 (Anexo C), além de
um teste de rastreabilidade e medição de C4.

RED antes da implementação:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py
```

Resultado: `10 failed, 27 passed`. As falhas demonstraram que as lacunas entre
as faixas eram aceitas e que C4 retornava `medidor` em vez de exigir consulta
prévia.

GREEN após a implementação:

```text
python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py
```

Resultado: `37 passed in 0.14s`.

Limites corrigidos conforme impressos na fonte:

- Anexo A: B2 `11.1`, C2 `15.1`, C3 `19.1`, C4 `24.1`, C5 `30.1`, C6 `38.1`,
  C7 `48.1`, C8 `57.2`, C9 `67.1`; C1 permanece `10.0`.
- Anexo C: A2 `5.1` e B1 `6.1`.
- Inferior estritamente maior e superior inclusivo; lacunas retornam
  `no_entry_table_row`.

Medição passou a ser dado da linha: linhas diretas/Tabela 7 usam
`direct_table_7`; C4-C9 usam `direct_consultation_required`. Os campos não
transcritos continuam `None` e geram warnings `not_transcribed`. A referência
mantém documento `CNC-NDBR-DBR-24-1569-EDBR`, edição `R02/2025`, anexos A/C e
páginas 72/77.

Verificações adicionais:

```text
python -m py_compile framework/galpao_fw/entrada_enel_bt.py
git diff --check -- framework/galpao_fw/entrada_enel_bt.py framework/galpao_fw/tests/branches/project_loop/test_residential_electrical_entry.py
```

Resultado: ambas passaram sem saída de erro.
