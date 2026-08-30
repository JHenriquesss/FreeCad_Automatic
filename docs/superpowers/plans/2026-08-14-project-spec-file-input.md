# Project spec file input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que o Loop de projeto receba um spec JSON versionado ou legado diretamente de arquivo/CLI, preservando o preflight e os manifestos existentes.

**Architecture:** `project_io.py` fará apenas leitura/validação de JSON e delegará a `project_loop.run_project`. `project_loop_cli.py` será uma fina camada argparse. O preflight reconhecerá `__PENDENTE__` dentro de cada disciplina solicitada; nenhum calculador receberá valores inventados.

**Tech Stack:** Python 3.11+, JSON UTF-8, argparse, pytest, SHA-256 já existente no `project_loop`.

## Global Constraints

- Preservar `Ask, Do Not Invent`: o template terá somente São João da Barra/RJ/ENEL e marcadores `__PENDENTE__`.
- Não consultar web/NotebookLM durante leitura ou execução do spec.
- `run_project_file` deve delegar ao `run_project`; não haverá segundo orquestrador.
- Specs legados continuam permitidos por padrão; `allow_legacy=False` exige o envelope versionado.
- Erros de entrada não devem criar um manifesto parcial.
- Caminhos persistidos no manifesto continuam relativos à pasta de execução.
- Preservar alterações preexistentes do worktree e não usar reset/checkout/commit abrangente.

---

### Task 1: Leitura segura do spec JSON

**Files:**
- Create: `framework/galpao_fw/project_io.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py`

**Interfaces:**
- `ProjectSpecFileError(ValueError)` comunica arquivo, JSON ou envelope inválido.
- `load_project_spec(path, *, allow_legacy=True) -> dict` retorna uma cópia JSON desserializada.
- `run_project_file(spec_path, out_dir, options=None, *, iteration=1, parent_run_id=None, changes=None, resolutions=None) -> dict` chama `project_loop.run_project`.

- [ ] **Step 1: Escrever o teste RED de leitura e execução por arquivo**

```python
def test_json_file_entry_uses_the_project_loop_and_persists_input_hash(tmp_path,
                                                                         turnkey_fixture):
    spec = {
        "schema": "freecad-automatic/project-spec", "schema_version": 1,
        "project": {"slug": "arquivo"},
        "turnkey": {
            "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
            "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350}},
        },
    }
    source = tmp_path / "project-spec.json"
    source.write_text(json.dumps(spec), encoding="utf-8")
    result = run_project_file(source, tmp_path / "run",
                              options={"generate_ifc": False})
    assert result["project_id"] == "arquivo"
    assert result["status"] in {"passed", "needs_review"}
    persisted = json.loads((tmp_path / "run" / "project-run.json").read_text(
        encoding="utf-8"))
    assert persisted["input"] == spec
    assert len(persisted["input_sha256"]) == 64
```

- [ ] **Step 2: Executar o teste e confirmar RED**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py::test_json_file_entry_uses_the_project_loop_and_persists_input_hash`

Expected: `ImportError` ou `ModuleNotFoundError` porque `project_io.py` ainda não existe.

- [ ] **Step 3: Implementar o leitor e o delegado mínimo**

Implementar leitura UTF-8, rejeição de raiz não-dicionário, JSON inválido, schema diferente de `freecad-automatic/project-spec`, versão ausente/não inteira/não suportada e legado opcional. `run_project_file` deve chamar somente `project_loop.run_project` após `load_project_spec`.

- [ ] **Step 4: Executar o teste e confirmar GREEN**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py::test_json_file_entry_uses_the_project_loop_and_persists_input_hash`

Expected: `1 passed`.

### Task 2: Gate de marcadores pendentes e template SJB/ENEL

**Files:**
- Modify: `framework/galpao_fw/project_loop.py`
- Create: `projects/galpao-sjb/project-spec.template.json`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py`

**Interfaces:**
- O preflight produzirá `pending_discipline_input` com `discipline` e `paths` para cada disciplina que contenha `__PENDENTE__`.
- O template terá seis disciplinas turnkey, geometria pendente e nenhum ID de fonte fictício.

- [ ] **Step 1: Escrever teste RED do template bloqueado**

```python
def test_sjb_enel_template_is_blocked_without_inventing_engineering_data(tmp_path):
    template = Path("projects/galpao-sjb/project-spec.template.json")
    result = run_project_file(template, tmp_path / "run",
                              options={"generate_ifc": False})
    assert result["status"] == "blocked"
    assert any(item["code"] == "invalid_common_geometry"
               for item in result["preflight"]["errors"])
    assert any(item["code"] == "pending_discipline_input"
               for item in result["preflight"]["errors"])
    assert result["site"] == {
        "city": "São João da Barra", "state": "RJ", "utility": "ENEL"}
```

- [ ] **Step 2: Executar o teste e confirmar RED**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py::test_sjb_enel_template_is_blocked_without_inventing_engineering_data`

Expected: arquivo template ou código do gate ausente.

- [ ] **Step 3: Implementar o scanner recursivo mínimo e o template**

Percorrer somente o valor de cada disciplina solicitada, registrar caminhos pontilhados onde o valor seja exatamente `__PENDENTE__` e anexar um erro por disciplina. Não tratar strings parecidas como pendentes e não alterar os valores do spec.

- [ ] **Step 4: Executar o teste e confirmar GREEN**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py::test_sjb_enel_template_is_blocked_without_inventing_engineering_data`

Expected: `1 passed`.

### Task 3: API pública, CLI e erros de entrada

**Files:**
- Modify: `framework/galpao_fw/project_loop.py`
- Create: `framework/galpao_fw/project_loop_cli.py`
- Test: `framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py`

**Interfaces:**
- `project_loop.load_project_spec` e `project_loop.run_project_file` reexportam o carregador sem duplicar lógica.
- `project_loop_cli.main(argv=None) -> int` aceita `--spec`, `--out-dir`, `--no-ifc`, `--generate-3d`, `--generate-2d`, `--generate-caderno`, `--require-source-refs`, `--required-discipline` repetível e `--freecad-exe`.
- Códigos de saída: 0 para `passed`/`needs_review`, 2 para `blocked`, 3 para `failed`, 4 para entrada inválida.

- [ ] **Step 1: Escrever testes RED de erro e CLI**

Testar JSON malformado, schema desconhecido, `allow_legacy=False` sem envelope e `main([...])` com um spec válido; verificar que a CLI grava `project-run.json` e retorna 0. Testar também o template pela CLI e retorno 2.

- [ ] **Step 2: Executar os testes e confirmar RED**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py`

Expected: falhas por API/CLI ausentes.

- [ ] **Step 3: Implementar reexport e CLI mínima**

Construir `argparse` sem importar FreeCAD; montar apenas opções presentes e chamar `run_project_file`. Imprimir resumo JSON com `status`, `project_id` e caminho do manifesto; converter erro de entrada em código 4.

- [ ] **Step 4: Executar os testes e confirmar GREEN**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_spec_file_input.py`

Expected: todos os testes da nova branch passam.

### Task 4: Integrar a jornada trunk e documentar o uso

**Files:**
- Modify: `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`
- Modify: `framework/galpao_fw/COMO-RODAR.md`
- Modify: `docs/superpowers/specs/2026-08-14-project-loop-design.md`
- Modify: `docs/superpowers/plans/2026-08-14-project-loop.md`

**Interfaces:**
- A jornada trunk escreve o spec em JSON e chama `run_project_file` antes de inspecionar manifesto/coordenação/iteração.
- A documentação mostra `python framework/galpao_fw/project_loop_cli.py --spec ... --out-dir ...` e o código de saída do gate.

- [ ] **Step 1: Estender o trunk com entrada por arquivo**

Persistir o spec já usado pela jornada em `tmp_path`, chamar a API de arquivo e manter as asserções de manifesto, coordenação e iteração.

- [ ] **Step 2: Executar trunk RED/GREEN**

Run: `python -m pytest -q framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`

Expected: passa após o reexport e a integração; a jornada deve continuar gerando os mesmos artefatos.

- [ ] **Step 3: Atualizar guia e evidências**

Adicionar o comando CLI, o template e a distinção entre `blocked`, `needs_review` e `passed`; registrar que nenhum dado de engenharia é preenchido automaticamente.

- [ ] **Step 4: Verificar regressão e higiene**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`

Run: `python -m pytest -q framework/galpao_fw/tests/test_turnkey.py framework/galpao_fw/tests/test_turnkey_bim.py framework/galpao_fw/tests/test_turnkey_clash.py framework/galpao_fw/tests/test_caderno_turnkey.py framework/galpao_fw/tests/test_pipeline_bim.py framework/galpao_fw/tests/test_validacao.py framework/galpao_fw/tests/test_relatorio_x_calculo.py -m "not build"`

Run: `python -m compileall -q framework/galpao_fw/project_loop.py framework/galpao_fw/project_io.py framework/galpao_fw/project_loop_cli.py` and `git diff --check`.

Expected: nova branch/trunk e regressão afetada passam; suíte ampla continua sendo reportada separadamente se exceder o timeout legado.

## Review follow-up

- Cobertura adicional verifica UTF-8, `schema_version` ausente/não suportado,
  caminhos exatos de `pending_discipline_input` e código CLI `3`.
- O template pode conter descrições textuais de campos; somente os valores de
  engenharia são obrigados a permanecer `__PENDENTE__` até decisão.

## Plan self-review

- Toda regra do design tem uma tarefa: leitura/validação (1), pendências/template (2), API/CLI (3), jornada/documentação/regressão (4).
- Nenhum passo depende de fonte normativa nova ou de dados de engenharia não fornecidos.
- O scanner só bloqueia marcador exato e não muda o comportamento dos specs sem marcador.
- A iteração continua no `project_loop` existente; a nova camada não cria uma segunda trilha.
