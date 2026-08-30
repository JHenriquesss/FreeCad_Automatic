# Loop de projeto Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um orquestrador de projeto que receba specs legados ou versionados, execute o vertical de galpão, registre entregáveis e conflitos com estados honestos e permita iterações explícitas.

**Architecture:** `framework/galpao_fw/project_loop.py` será uma camada de execução stateless sobre os orquestradores existentes. Um adaptador de galpão normaliza os formatos atuais, executa `galpao_turnkey`, emite IFC/coordenação e opcionalmente chama FreeCAD/TechDraw; um registro de adaptadores preserva a extensão futura para outros tipos de obra. Cada execução grava um manifesto JSON autocontido com hash da entrada, estados e artefatos.

**Tech Stack:** Python 3.11+, pytest, JSON, SHA-256, `galpao_turnkey`, `compatibilizacao`, `ifc_emit`, FreeCAD opcional.

## Estado verificado em 2026-08-14

- Contrato, execução, entregáveis, coordenação, iteração e jornada trunk: **15 testes aprovados**.
- Regressão afetada: **76 aprovados, 1 desmarcado**; `compileall` e `git diff --check` aprovados.
- Homologação sintética persistida: IFC, coordenação, hashes e vínculo pai/filho conferidos.
- Preflight do projeto real SJB/ENEL: **blocked**, pois ainda não existe spec real completo.
- A suíte ampla do framework já excedeu 300 s em fase legada; não é declarada verde até haver uma execução completa ou uma baseline formal.

### Verificação final após correção do layout IFC

- A causa do caminho `bim/bim/...` foi corrigida no wrapper do Loop: o emissor turnkey recebe a raiz da execução e cria uma única pasta `bim`.
- Execução persistida: `.loop-runtime/project-loop/post-auditoria-v2/`.
- Iterações 001 e 002: `needs_review`, coordenação `generated`, 15 artefatos por iteração, seis IFCs por iteração e `bim/turnkey_federado.ifc` presente.
- Conferência final: zero caminhos absolutos, zero `bim/bim/...`, 30/30 hashes de artefatos válidos e vínculo pai/filho confirmado.

## Global Constraints

- Preservar `Ask, Do Not Invent`: nenhum valor de engenharia novo será criado pelo loop.
- Não consultar web/NotebookLM dentro da execução; `source_refs` apenas serão validados e registrados.
- Não alterar os calculadores de disciplina para atender ao novo contrato.
- Caminhos persistidos no manifesto serão relativos à pasta da execução.
- Ausência de FreeCAD ou `ifcopenshell` será um estado explícito, não uma aprovação.
- Uma disciplina com erro não impedirá a execução das disciplinas independentes.
- O checkout contém alterações anteriores do usuário; não usar `git reset`, `git checkout` ou commits que misturem essas alterações.

---

### Task 1: Contrato normalizado e preflight

**Files:**
- Create: `framework/galpao_fw/project_loop.py`
- Create: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_contract.py`
- Create: `framework/galpao_fw/tests/branches/project_loop/conftest.py`

**Interfaces:**
- Produces `ProjectLoopOptions`, `normalize_spec(spec)`, `run_project(spec, out_dir, options=None)`.
- `normalize_spec` retorna um dicionário com `adapter`, `project_id`, `turnkey_spec`, `structure_spec`, `requested_disciplines`, `source_refs` e `derivations`.
- `run_project` sempre grava `input/spec.json`, `reports/preflight.json` e `project-run.json`, inclusive quando o preflight bloqueia.

- [ ] **Step 1: Write the failing tests**

```python
def test_structural_legacy_spec_is_registered_as_steel_and_blocks_missing_fields(tmp_path):
    result = run_project({"geometria": {"span": 20}}, tmp_path)
    assert result["status"] == "blocked"
    assert result["disciplines"]["aco"]["status"] == "blocked"
    assert (tmp_path / "project-run.json").exists()


def test_turnkey_spec_keeps_explicit_disciplines_and_derives_only_common_geometry(tmp_path):
    spec = {"slug": "g", "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
            "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350}}}
    result = run_project(spec, tmp_path, options={"generate_ifc": False})
    assert result["project_id"] == "g"
    assert result["disciplines"]["incendio"]["status"] in {"passed", "needs_review"}
    assert result["preflight"]["derivations"] == []


def test_versioned_envelope_preserves_sources_and_requires_them_when_requested(tmp_path):
    spec = {"schema": "freecad-automatic/project-spec", "schema_version": 1,
            "project": {"slug": "g"},
            "site": {"city": "São João da Barra", "state": "RJ", "utility": "ENEL"},
            "source_refs": {}, "turnkey": {
                "geometria": {"comprimento": 40, "vao": 20, "pe_direito": 6},
                "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350}}}}
    result = run_project(spec, tmp_path, options={"require_source_refs": True,
                                                   "generate_ifc": False})
    assert result["status"] == "blocked"
    assert result["disciplines"]["incendio"]["status"] == "blocked"
    assert result["sources"] == {}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_contract.py`

Expected: collection fails with `ModuleNotFoundError: No module named 'project_loop'`.

- [ ] **Step 3: Implement the minimal contract**

Implement in `project_loop.py`:

```python
@dataclass(frozen=True)
class ProjectLoopOptions:
    required_disciplines: tuple[str, ...] = ()
    require_source_refs: bool = False
    generate_ifc: bool = True
    generate_3d: bool = False
    generate_2d: bool = False
    generate_caderno: bool = False
    folga_mm: float = 1.0
    vol_min_mm3: float = 1000.0


def normalize_spec(spec):
    if not isinstance(spec, dict):
        raise TypeError("spec deve ser um dicionario")
    raw = copy.deepcopy(spec)
    if raw.get("schema") == "freecad-automatic/project-spec":
        turnkey = copy.deepcopy(raw.get("turnkey") or {})
        structure = copy.deepcopy(raw.get("structure"))
        project = copy.deepcopy(raw.get("project") or {})
    elif any(key in raw for key in ("terreno", "fundacao", "cargas", "vento")):
        turnkey = {"geometria": _geometry_from_structural(raw), "aco": copy.deepcopy(raw)}
        structure = raw
        project = {"slug": raw.get("slug", "projeto")}
    else:
        turnkey = raw
        structure = copy.deepcopy(raw.get("aco")) if isinstance(raw.get("aco"), dict) else None
        project = {"slug": raw.get("slug", "projeto")}
    return _normalized_result(project, turnkey, structure, raw)


def run_project(spec, out_dir, options=None, *, iteration=1,
                parent_run_id=None, changes=None, resolutions=None):
    opts = ProjectLoopOptions.from_value(options)
    normalized = normalize_spec(spec)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "input" / "spec.json", normalized["raw_spec"])
    preflight = _preflight(normalized, opts)
    _write_json(run_dir / "reports" / "preflight.json", preflight)
    if not preflight["ok"]:
        return _finish_blocked_manifest(run_dir, normalized, opts, preflight,
                                        iteration, parent_run_id, changes, resolutions)
    return _execute_and_persist(run_dir, normalized, opts, preflight,
                                iteration, parent_run_id, changes, resolutions)
```

The implementation must use `copy.deepcopy`, `projeto_spec.validar` for structural specs, and a positive common geometry check. It must distinguish a common-geometry error from a discipline-specific missing field.

The shared fixture in `conftest.py` must return this real turnkey input and accept the named overrides without mocks:

```python
@pytest.fixture
def turnkey_fixture():
    def make(**overrides):
        value = {
            "geometria": {"comprimento": 40.0, "vao": 20.0, "pe_direito": 6.0},
            "concreto": {"vao": 20.0, "n_porticos": 7, "v0": 40.0, "cat": "IV",
                         "classe": "B", "s1": 1.0, "s3": 1.0, "G_roof": 0.30,
                         "Q_roof": 0.25, "fck": 30e3, "fyk": 500e3,
                         "sigma_solo_adm": 250.0},
            "eletrico": {"tensao_V": 380.0,
                         "cargas": {"iluminacao_kW": 20.0, "ilum_fp": 0.92,
                                    "ocupacao": "industrial"},
                         "alimentador": {"L_km": 0.05, "metodo": "F", "isolacao": "EPR"}},
            "incendio": {"iluminacao_emergencia": {"fluxo_bloco_lm": 350.0},
                         "deteccao": {"viga_m": 0.0}},
        }
        for key, value_override in overrides.items():
            value[key] = value_override
        return value
    return make


@pytest.fixture
def turnkey_fixture_with_hvac_and_hydraulic(turnkey_fixture):
    return turnkey_fixture(climatizacao={"tipo": "galpao"}, hidraulica={})
```

- [ ] **Step 4: Run the focused tests**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_contract.py`

Expected: all three tests pass.

---

### Task 2: Discipline execution and honest state classification

**Files:**
- Modify: `framework/galpao_fw/project_loop.py`
- Create: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_execution.py`

**Interfaces:**
- `run_project` uses the `galpao` adapter to call `galpao_turnkey.rodar` with an isolated output directory.
- The return manifest has `disciplines[name]` with `status`, `native_atende`, `reprovados`, `gates`, `warnings`, `errors`, and `artifacts`.
- `classify_discipline(record)` returns one of `passed`, `needs_review`, `blocked`, `failed`, `not_requested`, `not_available`.

- [ ] **Step 1: Write the failing tests**

```python
def test_real_turnkey_execution_isolated_and_persists_native_gates(tmp_path, turnkey_fixture):
    result = run_project(turnkey_fixture(), tmp_path, options={"generate_ifc": False})
    assert set(result["disciplines"]) == {"concreto", "eletrico", "incendio"}
    assert result["disciplines"]["concreto"]["native_atende"] is True
    assert result["disciplines"]["eletrico"]["gates"]
    assert (tmp_path / "reports" / "disciplinas.json").exists()


def test_hydraulic_default_is_never_project_passed(tmp_path, turnkey_fixture):
    result = run_project(turnkey_fixture(hidraulica={}), tmp_path,
                         options={"generate_ifc": False})
    assert result["disciplines"]["hidraulica"]["status"] == "needs_review"
    assert result["status"] == "needs_review"
    assert result["atende"] is False


def test_invalid_discipline_does_not_hide_independent_discipline(tmp_path, turnkey_fixture):
    result = run_project(turnkey_fixture(eletrico="invalid", incendio={
        "iluminacao_emergencia": {"fluxo_bloco_lm": 350}}), tmp_path,
        options={"generate_ifc": False})
    assert result["disciplines"]["eletrico"]["status"] == "failed"
    assert result["disciplines"]["incendio"]["status"] != "failed"
    assert result["status"] == "failed"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_execution.py`

Expected: failures because the adapter execution and status ledger are not implemented.

- [ ] **Step 3: Implement the adapter and classifier**

Use the existing `galpao_turnkey.rodar(turnkey_spec, out_dir)` and preserve its raw result only in the report, not as the global verdict. Treat a false native `ATENDE`, an exception, and an isolated non-run differently. Recursively inspect `dimensionamento_completo=False`, `default=True`, `inconclusivo=True`, `A CONFIRMAR`, and structural `a_confirmar` to create review warnings.

- [ ] **Step 4: Run focused execution tests**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_contract.py framework/galpao_fw/tests/branches/project_loop/test_project_loop_execution.py`

Expected: all focused tests pass.

---

### Task 3: Deliverables, IFC and federated coordination

**Files:**
- Modify: `framework/galpao_fw/project_loop.py`
- Create: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_deliverables.py`

**Interfaces:**
- `register_artifact(run_dir, path, kind, status="generated")` returns a relative artifact record with SHA-256.
- `run_project` writes `reports/turnkey.txt`, `coordination/clash.json`, `coordination/pendencias.json`, `coordination/pendencias.bcf.json`, `coordination/matriz.svg`, and `coordination/relatorio.txt` when coordination is possible.
- IFC results are registered as `bim/<discipline>.ifc` and `bim/turnkey_federado.ifc`; missing `ifcopenshell` becomes `not_available`.

- [ ] **Step 1: Write the failing tests**

```python
def test_coordination_artifacts_are_real_and_manifest_paths_relative(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    result = run_project(turnkey_fixture_with_hvac_and_hydraulic, tmp_path,
                         options={"generate_ifc": False})
    assert (tmp_path / "coordination" / "clash.json").exists()
    assert (tmp_path / "coordination" / "pendencias.bcf.json").exists()
    assert result["coordination"]["n_revisar"] >= 1
    for artifact in result["artifacts"]:
        assert not os.path.isabs(artifact["path"])
        assert len(artifact["sha256"]) == 64


def test_ifc_dependency_is_explicit_instead_of_false_success(tmp_path, turnkey_fixture):
    result = run_project(turnkey_fixture(), tmp_path,
                         options={"generate_ifc": True})
    if ifc_emit.disponivel():
        assert result["deliverables"]["ifc"]["status"] == "generated"
        assert any(a["path"].endswith("turnkey_federado.ifc") for a in result["artifacts"])
    else:
        assert result["deliverables"]["ifc"]["status"] == "not_available"
        assert result["status"] == "needs_review"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_deliverables.py`

Expected: failures because the coordination files and artifact ledger do not exist.

- [ ] **Step 3: Implement deliverable registration**

Call `galpao_turnkey.emitir_bim`, `checa_interferencia_federada`, and `compatibilizacao.gerar_pendencias`. Emit the BCF-like JSON and SVG using existing pure functions. Add individual IFC emission for HVAC and hydraulic through their existing `emitir_bim` functions when the turnkey helper does not include them. Scan generated files only inside the run directory and exclude the manifest while it is being assembled.

- [ ] **Step 4: Run focused deliverable tests**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_deliverables.py`

Expected: all tests pass with either generated IFC or an explicit `not_available` state.

---

### Task 4: Explicit project iteration

**Files:**
- Modify: `framework/galpao_fw/project_loop.py`
- Create: `framework/galpao_fw/tests/branches/project_loop/test_project_loop_iteration.py`

**Interfaces:**
- `iterate_project(previous_run, spec=None, updates=None, resolutions=None, out_dir=None, options=None)` returns a new manifest.
- `updates` is a mapping from dotted path to value; it is applied only to a deep copy of the input spec.
- The new manifest has `iteration == parent.iteration + 1`, `parent_run_id`, `changes`, and `resolutions`.

- [ ] **Step 1: Write the failing tests**

```python
def test_iteration_preserves_parent_and_changes_only_explicit_path(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first_dir = tmp_path / "iteration-001"
    first = run_project(turnkey_fixture_with_hvac_and_hydraulic, first_dir,
                        options={"generate_ifc": False})
    second = iterate_project(first, updates={"geometria.pe_direito": 7.0},
                             options={"generate_ifc": False})
    assert second["iteration"] == 2
    assert second["parent_run_id"] == first["run_id"]
    assert second["changes"] == {"geometria.pe_direito": 7.0}
    assert first["input"]["geometria"]["pe_direito"] == 6.0
    assert second["input"]["geometria"]["pe_direito"] == 7.0


def test_iteration_does_not_close_conflict_by_text_only(
        tmp_path, turnkey_fixture_with_hvac_and_hydraulic):
    first = run_project(turnkey_fixture_with_hvac_and_hydraulic, tmp_path / "a",
                        options={"generate_ifc": False})
    second = iterate_project(first, resolutions=[{"issue_id": "CLH-001",
                                                  "status": "approved",
                                                  "note": "revisado pelo engenheiro"}],
                             options={"generate_ifc": False})
    assert second["resolutions"][0]["status"] == "approved"
    assert second["coordination"]["open"] >= 0
    assert second["coordination"]["resolution_requests"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_iteration.py`

Expected: import or attribute failures because iteration is not implemented.

- [ ] **Step 3: Implement safe update and parent loading**

Load a manifest from a dict or `project-run.json` path, recover the persisted input spec, apply dotted paths with a missing-parent error, derive the next output directory without deleting the parent, and pass resolution records through unchanged. The clash result from the new run remains authoritative.

- [ ] **Step 4: Run focused iteration tests**

Run: `python -m pytest -q framework/galpao_fw/tests/branches/project_loop/test_project_loop_iteration.py`

Expected: all iteration tests pass.

---

### Task 5: End-to-end trunk, documentation and regression verification

**Files:**
- Create: `framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`
- Modify: `framework/galpao_fw/COMO-RODAR.md`
- Modify: `docs/superpowers/plans/2026-08-14-loop1.5-homologacao.md`

**Interfaces:**
- The trunk exercises a real user journey: load a versioned São João da Barra/ENEL spec, execute the real galpão adapter, inspect the manifest and coordination report, then iterate.
- The guide documents `run_project` and `iterate_project`, including the distinction between calculation-ready and FreeCAD-dependent deliverables.

- [ ] **Step 1: Write the failing trunk test**

The test must use actual discipline modules and assert the final JSON/text artifacts, not mocks or private helper return values.

- [ ] **Step 2: Run the trunk to verify it fails**

Run: `python -m pytest -q framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`

Expected: failure until the public project-loop API and artifact contract are integrated.

- [ ] **Step 3: Add the documented command path**

Document:

```python
import project_loop
result = project_loop.run_project(spec, "projects/galpao-sjb/iterations/001")
next_result = project_loop.iterate_project(
    result, updates={"turnkey.hidraulica.aparelhos_esgoto": {"bacia": 2}},
)
```

Explain that `passed` requires all requested deliverables, while `needs_review` and `blocked` are valid audit outcomes that require engineering decisions.

- [ ] **Step 4: Run the focused trunk and the full framework suite**

Run: `python -m pytest -q framework/galpao_fw/tests/trunk/test_project_loop_golden_journey.py`

Expected: trunk passes.

Run: `python -m pytest -q framework/galpao_fw/tests`

Expected: no new failures relative to the measured pre-existing baseline; report any unrelated baseline failures separately.

- [ ] **Step 5: Verify syntax and repository hygiene**

Run: `python -m compileall -q framework/galpao_fw/project_loop.py` and `git diff --check`.

Expected: exit code 0 for both; no unrelated files staged or removed.

---

## Plan self-review

- The design requirements map to Tasks 1–4: input compatibility/preflight, discipline execution, deliverables/coordination, and iteration.
- Task 5 provides the real user journey and operational documentation.
- The plan contains no new engineering defaults and leaves FreeCAD optional but observable.
- The public names are consistent across tasks: `ProjectLoopOptions`, `normalize_spec`, `run_project`, `iterate_project`, `register_artifact`, and `classify_discipline`.
- Existing dirty files are not included in any task and must remain untouched.

### Incremento seguinte: entrada JSON/CLI

- `project_io.py` carrega JSON UTF-8, valida o envelope e delega ao mesmo `run_project`.
- `project_loop_cli.py` expõe `spec -> project-run.json` com códigos de saída do gate.
- `projects/galpao-sjb/project-spec.template.json` mantém SJB/RJ/ENEL e seis disciplinas explicitamente pendentes.
- A jornada trunk agora começa escrevendo o spec em JSON e termina com a iteração existente.
- Branch nova: 6 testes aprovados; trunk: 1 teste aprovado.

### Evidência executada da entrada JSON/CLI (2026-08-14)

- Branches do Loop + trunk: **21 testes aprovados**.
- Regressão afetada: **76 aprovados, 1 desmarcado**.
- CLI do template: retorno **2**, manifesto `blocked`, erros `invalid_common_geometry` e `pending_discipline_input` para as seis disciplinas.
- `compileall` e `git diff --check`: aprovados; a suíte ampla do framework continua não declarada verde por causa do timeout legado já registrado.
- Revisão independente: aprovada após cobertura adicional de UTF-8, versões, caminhos pendentes e código de falha CLI.

### Homologação real dos entregáveis opcionais (2026-08-14)

- Execução FreeCAD isolada: `.loop-runtime/project-loop/optional-audit-v2/`.
- IFC, modelo 3D e desenhos/caderno: **generated**.
- Artefatos: **83**, todos existentes e com SHA-256 válido.
- Metadados de `deliverables` e caminhos de artefatos: **0 caminhos absolutos**.
- Coordenação: 156 clashes detectados, 71 pendências abertas; veredito honesto `needs_review`.
- Defeito corrigido: o retorno bruto do caderno trazia caminhos absolutos; o Loop agora os normaliza para relativos antes de persistir.

### Auditoria operacional atual do Loop 2 (2026-08-14)

- Execução: `.loop-runtime/project-loop/loop2-current-audit/`.
- Iteração 001 e 002 executadas pelo API público `run_project`/`iterate_project`.
- IFC, modelo 3D e desenhos/caderno: `generated` nas duas iterações.
- Artefatos: 83 por iteração; 83/83 hashes válidos e todos os caminhos relativos.
- Coordenação: 156 clashes/71 abertos na primeira; 161 clashes/76 abertos na segunda.
- A segunda execução preservou `parent_run_id` e o novo modelo permaneceu a autoridade; o veredito foi `needs_review`, não aprovação silenciosa.
- Essa auditoria valida o framework com um spec completo de teste; o projeto real SJB/ENEL continua dependente do preenchimento do spec homologado.

### Interface CLI de iteração (2026-08-14)

- `project_loop_cli.py` aceita `--iterate-from` com pasta ou manifesto pai.
- `--update CAMINHO=JSON` aplica alterações pontuais; `--resolution JSON` registra decisões sem fechar conflitos por texto.
- JSON inválido, caminho ausente ou uso sem manifesto pai retorna código 4 e não cria `project-run.json` parcial.
- Auditoria direta: `.loop-runtime/project-loop/cli-iteration-audit/project-run.json`, iteração 2, coordenação generated, 161 clashes/76 abertos, 9 artefatos e status `needs_review`.
- A CLI também aceita `--iterate-from` com `--spec` substituto completo, preservando o `parent_run_id` e permitindo alterações maiores que um patch pontual.

### Proteção de histórico e retomada segura (2026-08-14)

- `run_project` e `preflight_project` agora exigem diretório novo ou vazio.
- Uma pasta com `project-run.json` ou restos de execução interrompida é recusada; nenhuma rodada anterior é sobrescrita ou misturada.
- Contrato verificado com 2 testes novos; suíte de branches/trunk do Loop: **49 aprovados**.

### Verificação pós-execução (2026-08-14)

- Nova API `verify_project_run` e comando `--verify-run` conferem presença, tamanho, caminhos e SHA-256 dos artefatos.
- Os dois manifestos da auditoria operacional foram verificados: **83/83 artefatos válidos em cada iteração**.
- A suíte de branches/trunk após a integração do verificador: **52 aprovados**.
- Código de saída: `0` íntegro, `3` artefato ausente/adulterado, `4` manifesto inválido.

### Verificação persistida no ciclo normal

- Toda nova execução grava `verification` no próprio `project-run.json`, sem caminho absoluto.
- Auditoria nova: `.loop-runtime/project-loop/verification-current-audit/`, status `passed`, 9/9 artefatos válidos.
- A suíte de branches/trunk após a persistência: **54 aprovados**.

### Auditoria completa após a verificação persistida

- Execução: `.loop-runtime/project-loop/loop2-verification-full-audit/`.
- IFC, modelo 3D e desenhos/caderno: `generated`.
- Coordenação: 156 clashes, 71 para revisão, 71 abertos; veredito honesto `needs_review`.
- Artefatos: 83; verificação persistida e pós-verificação: **83/83 válidos**, sem erros.
- Iteração 002: update hidráulico e resolução explícitos, 161 clashes/76 abertos, 9/9 artefatos válidos e `parent_run_id` preservado.

### Integridade obrigatória do pai antes da iteração (2026-08-14)

- `iterate_project` executa `verify_project_run` antes de ler/aplicar alterações.
- Pai com hash, tamanho, presença ou caminho inválido é recusado e não cria a próxima pasta.
- Jornada branches/trunk após a garantia: **53 aprovados**.

### Sequência declarativa de iterações (2026-08-15)

- `run_project_sequence` executa a rodada inicial e uma rodada por passo explícito.
- `project-sequence.json` registra status agregado, passos, caminhos relativos,
  `parent_run_id`, verificação persistida e erros.
- `--iteration-plan` expõe a mesma operação pela CLI; planos inválidos são
  rejeitados antes da criação da pasta de saída.
- Evidência: branches/trunk do Loop 2: **57 aprovados**; plano API e plano CLI
  cobertos, sem regressão observada.

### Gate ao vivo das fontes do projeto (2026-08-15)

- `project_source_gate.py` confere existência, status remoto `2`, stale e limite
  de 50 fontes para cada referência do spec.
- `--verify-source-refs` persiste `source-verification.json` antes do preflight;
  erros de consulta, IDs ausentes ou fontes não prontas resultam em `blocked`.
- Homologação real do template: 7 notebooks, 14 referências, 188 fontes
  consultadas, 0 erros; o template segue bloqueado apenas pelos dados pendentes.

### Preflight combinado com o gate de fontes (2026-08-15)

- `--verify-source-refs --preflight-only` executa os dois gates na mesma pasta.
- `reports/source-verification.json` e `project-readiness.json` preservam a
  decisão; uma fonte bloqueada força `can_start_project_loop=false`.
- O modo combinado tem cobertura de CLI e não cria `project-run.json`.

### Vínculo da execução ao readiness aprovado (2026-08-15)

- `--readiness` valida schema, status, input, `project_id` e, quando exigido,
  a verificação viva de fontes antes da execução inicial.
- Readiness `blocked`, divergente ou sem fonte viva aprovada retorna código `2`
  ou entrada inválida e não cria a pasta da rodada.
- `--iteration-plan` aplica a mesma validação antes de criar a raiz da sequência;
  readiness bloqueado não cria nenhuma rodada.
- Cobertura: execução inicial e sequência aprovadas, além de readiness bloqueado
  sem saída parcial.

### Fechamento seguro de falhas inesperadas (2026-08-15)

- Exceções do adaptador/entregável agora geram manifesto `failed` em vez de
  deixar somente uma pasta parcial sem veredito.
- `reports/execution-error.json` registra tipo e detalhe; arquivos produzidos
  antes da falha são registrados como `partial` e entram na verificação de hash.
- A falha foi coberta na jornada de execução e preserva a possibilidade de
  diagnóstico e nova iteração em pasta separada.

### Compatibilidade explícita do tipo de obra com o adaptador (2026-08-15)

- O preflight agora usa `project.type`, `project.project_type` ou `project.tipo`
  quando presente para comparar com `adapter_capabilities.project_types`.
- Tipo incompatível gera `unsupported_project_type` e bloqueia antes de chamar
  o runner; ausência do campo continua válida para specs legados.
- Cobertura: tipo residencial aceito e tipo industrial recusado por adaptador
  residencial; regressão completa pendente nesta rodada.

### Proveniência do readiness nos manifestos (2026-08-15)

- Execuções liberadas pela CLI persistem no manifesto o status do readiness,
  projeto, hash canônico do input, resumo da verificação de fontes e SHA-256 do
  arquivo de readiness.
- `project-sequence.json` e iterações filhas preservam a mesma proveniência.
- Evidência: branches/trunk do Loop 2: **70 aprovados**; `compileall` aprovado;
  `git diff --check` sem erros de conteúdo.

### Jornada completa das seis disciplinas (2026-08-14)

- A cobertura de execução agora usa um spec sintético coerente com estrutura,
  concreto, elétrica, incêndio, climatização e hidráulica na mesma rodada.
- A jornada verifica coordenação com clashes, hashes persistidos e uma segunda
  iteração com `parent_run_id`, sem usar os dados pendentes do SJB real.
- Evidência: branches/trunk do Loop 2: **71 aprovados**; status sintético
  `needs_review` por conflitos/revisões, sem disciplina `failed` ou `blocked`.
