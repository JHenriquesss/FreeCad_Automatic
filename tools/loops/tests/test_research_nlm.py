import csv
import json
import subprocess
import sys
from pathlib import Path

import fitz
import pytest

from tools.loops.models import CommandResult
from tools.loops.research_nlm import (
    CatalogIndex,
    NlmCliAdapter,
    NlmCommandTimeout,
    NlmEvidenceRequired,
    NotebookMap,
)


def write_local_sources(tmp_path):
    map_path = tmp_path / "notebooklm-mapa.md"
    map_path.write_text(
        "| Pasta local | Notebook | Notebook ID |\n"
        "| --- | --- | --- |\n"
        "| `01_TESTE` | Teste | `nb-1` |\n",
        encoding="utf-8",
    )
    catalog_path = tmp_path / "catalogo.csv"
    with catalog_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("caminho_relativo", "nome_normalizado", "hash_sha256"),
        )
        writer.writeheader()
        writer.writerow(
            {
                "caminho_relativo": "01_TESTE/norma-teste.pdf",
                "nome_normalizado": "Norma teste",
                "hash_sha256": "sha256:ok",
            }
        )
        writer.writerow(
            {
                "caminho_relativo": "01_TESTE/norma-pendente.pdf",
                "nome_normalizado": "Norma pendente",
                "hash_sha256": "sha256:pending",
            }
        )
    source_path = tmp_path / "01_TESTE" / "norma-teste.pdf"
    source_path.parent.mkdir(exist_ok=True)
    document = fitz.open()
    document.new_page().insert_text((72, 72), "Norma teste com texto extraivel")
    document.save(source_path)
    document.close()
    return NotebookMap.load(map_path), CatalogIndex.load(catalog_path)


class FakeRunner:
    def __init__(self, sources, response=None):
        self.sources = sources
        default_response = {
            "answer": "A resposta de teste exige verificacao.",
            "conversation_id": "conv-1",
            "citations": [
                {"number": "1", "source_id": "src-ok", "cited_text": "trecho curto"}
            ],
            "token": "credential-that-must-not-be-written",
        }
        self.responses = list(response) if isinstance(response, (list, tuple)) else [response or default_response]
        self.calls = []

    def __call__(self, argv):
        self.calls.append(tuple(argv))
        if tuple(argv[:3]) == ("nlm", "list", "sources"):
            return json.dumps(self.sources)
        if tuple(argv[:3]) == ("nlm", "notebook", "query"):
            return json.dumps(self.responses.pop(0))
        raise AssertionError(f"unexpected command: {argv}")


def make_adapter(tmp_path, sources, response=None):
    notebook_map, catalog = write_local_sources(tmp_path)
    runner = FakeRunner(sources, response)
    adapter = NlmCliAdapter(
        notebook_map,
        catalog,
        runner=runner,
        artifact_dir=tmp_path / "artifacts",
        manual_request_path=tmp_path / "manual-source-requests.md",
        source_root=tmp_path,
    )
    return adapter, runner


def test_list_ready_sources_filters_status_two(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [
            {"id": "src-ok", "title": "Norma teste", "status": 2},
            {"id": "src-string", "title": "Nao pronta", "status": "2"},
            {"id": "src-wait", "title": "Pendente", "status": 1},
        ],
    )

    sources = adapter.list_ready_sources("nb-1")

    assert tuple(source.source_id for source in sources) == ("src-ok",)
    assert sources[0].local_path == "01_TESTE/norma-teste.pdf"


def test_list_ready_sources_for_paths_selects_only_declared_local_scope(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [
            {"id": "src-ok", "title": "Norma teste", "status": 2},
            {"id": "src-other", "title": "Outra norma", "status": 2},
        ],
    )

    sources = adapter.list_ready_sources_for_paths("nb-1", ("01_TESTE/norma-teste.pdf",))

    assert tuple(source.source_id for source in sources) == ("src-ok",)


def test_list_ready_sources_for_paths_parks_when_declared_source_is_missing(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
    )

    with pytest.raises(NlmEvidenceRequired, match="source scope") as error:
        adapter.list_ready_sources_for_paths("nb-1", ("01_TESTE/norma-pendente.pdf",))

    assert error.value.manual_request_path == str(tmp_path / "manual-source-requests.md")
    assert "Norma pendente" in (tmp_path / "manual-source-requests.md").read_text(encoding="utf-8")


def test_scoped_image_only_pdf_parks_before_notebook_query(tmp_path):
    adapter, runner = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
    )
    image_path = tmp_path / "01_TESTE" / "norma-teste.pdf"
    image_path.parent.mkdir(exist_ok=True)
    document = fitz.open()
    document.new_page()
    document.save(image_path)
    document.close()
    adapter.source_root = tmp_path

    with pytest.raises(NlmEvidenceRequired, match="texto extraível") as error:
        adapter.list_ready_sources_for_paths("nb-1", ("01_TESTE/norma-teste.pdf",))

    request = tmp_path / "manual-source-requests.md"
    assert error.value.manual_request_path == str(request)
    content = request.read_text(encoding="utf-8")
    assert "páginas=1" in content
    assert "caracteres=0" in content
    assert not any(call[:3] == ("nlm", "notebook", "query") for call in runner.calls)


def test_query_passes_only_requested_source_ids(tmp_path):
    adapter, runner = make_adapter(
        tmp_path,
        [
            {"id": "src-ok", "title": "Norma teste", "status": 2},
            {"id": "src-other", "title": "Outra norma", "status": 2},
        ],
    )

    evidence = adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))

    assert evidence.source_ids == ("src-ok",)
    assert runner.calls[-1] == (
        "nlm", "notebook", "query", "nb-1", "Qual requisito deve ser verificado?",
        "--source-ids", "src-ok", "--timeout", "120", "--json",
    )
    artifact = next((tmp_path / "artifacts").glob("*.json"))
    stored_response = json.loads(artifact.read_text(encoding="utf-8"))
    assert stored_response["answer"] == "A resposta de teste exige verificacao."
    assert stored_response["token"] == "[REDACTED]"


def test_query_redacts_nested_secret_key_patterns_from_artifact_and_evidence(tmp_path):
    secret_values = {
        "token": "token-secret",
        "secret": "secret-secret",
        "password": "password-secret",
        "credential": "credential-secret",
        "authorization": "authorization-secret",
        "cookie": "cookie-secret",
        "api-key": "api-key-secret",
        "csrf": "csrf-secret",
        "bearer": "bearer-secret",
        "client-secret": "client-secret-secret",
        "id-token": "id-token-secret",
        "refresh-token": "refresh-token-secret",
    }
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response={
            "answer": "Resposta segura.",
            "conversation_id": "conv-1",
            "citations": [{"source_id": "src-ok", "cited_text": "trecho seguro"}],
            "metadata": {"nested_values": [secret_values]},
        },
    )

    evidence = adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))

    artifact = next((tmp_path / "artifacts").glob("*.json"))
    stored_response = json.loads(artifact.read_text(encoding="utf-8"))
    redacted = stored_response["metadata"]["nested_values"][0]
    assert set(redacted) == set(secret_values)
    assert set(redacted.values()) == {"[REDACTED]"}
    assert all(value not in json.dumps(stored_response) for value in secret_values.values())
    assert all(value not in json.dumps(evidence.to_dict()) for value in secret_values.values())


def test_query_parses_notebooklm_citation_map_with_references(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response={
            "answer": "Resposta real.",
            "citations": {"1": "src-ok"},
            "references": [
                {
                    "source_id": "src-ok",
                    "citation_number": 1,
                    "cited_text": "trecho normativo",
                }
            ],
        },
    )

    evidence = adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))

    assert evidence.citations[0].number == "1"
    assert evidence.citations[0].source_id == "src-ok"
    assert evidence.citations[0].cited_text == "trecho normativo"


def test_query_parses_auditable_json_nested_in_answer(tmp_path):
    nested = {
        "sources_used": ["src-ok"],
        "citations": [
            {"number": 1, "source_id": "src-ok", "cited_text": "trecho da resposta"}
        ],
        "references": [
            {
                "source_id": "src-ok",
                "citation_number": 1,
                "secao": "Subcláusula 5.2.2.4",
                "cited_text": "trecho normativo auditável",
            }
        ],
    }
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response={
            "answer": json.dumps(nested, ensure_ascii=False),
            "citations": {},
            "references": [],
        },
    )

    evidence = adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))

    assert evidence.source_ids == ("src-ok",)
    assert evidence.citations[0].source_id == "src-ok"
    assert evidence.citations[0].number == "1"
    assert evidence.citations[0].cited_text == (
        "Subcláusula 5.2.2.4: trecho normativo auditável"
    )


def test_query_rejects_nested_answer_with_unrequested_source(tmp_path):
    nested = {
        "sources_used": ["src-other"],
        "citations": [
            {"number": 1, "source_id": "src-other", "cited_text": "fora do escopo"}
        ],
        "references": [
            {"source_id": "src-other", "citation_number": 1, "secao": "4.1", "cited_text": "fora"}
        ],
    }
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response={
            "answer": json.dumps(nested),
            "citations": {},
            "references": [],
        },
    )

    with pytest.raises(ValueError, match="unrequested source"):
        adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))


def test_query_rejects_nested_answer_without_section_or_text(tmp_path):
    nested = {
        "sources_used": ["src-ok"],
        "citations": [{"number": 1, "source_id": "src-ok", "cited_text": "resumo"}],
        "references": [{"source_id": "src-ok", "citation_number": 1}],
    }
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response={
            "answer": json.dumps(nested),
            "citations": {},
            "references": [],
        },
    )

    with pytest.raises(NlmEvidenceRequired, match="nested citation"):
        adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))


def test_query_rejects_empty_reference_text_for_notebooklm_citation_map(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response={
            "answer": "Resposta sem trecho.",
            "citations": {"1": "src-ok"},
            "references": [{"source_id": "src-ok", "citation_number": 1}],
        },
    )

    with pytest.raises(NlmEvidenceRequired, match="empty citation text") as error:
        adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))

    request = tmp_path / "manual-source-requests.md"
    assert error.value.manual_request_path == str(request)
    assert "src-ok" in request.read_text(encoding="utf-8")
    assert "Fonte retornou citacao sem trecho textual" in request.read_text(encoding="utf-8")


def test_query_rejects_response_without_auditable_citations(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response={
            "answer": "Resposta sem citacoes.",
            "citations": {},
            "references": [],
        },
    )

    with pytest.raises(NlmEvidenceRequired, match="no auditable citations") as error:
        adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))

    request = tmp_path / "manual-source-requests.md"
    assert error.value.manual_request_path == str(request)
    content = request.read_text(encoding="utf-8")
    assert "src-ok" in content
    assert "Fonte retornou resposta sem citacoes auditaveis" in content


def test_query_retries_once_with_compact_question_after_empty_citations(tmp_path):
    adapter, runner = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response=[
            {
                "answer": "Resposta sem citacoes.",
                "citations": {},
                "references": [],
            },
            {
                "answer": "Resposta auditavel.",
                "conversation_id": "conv-2",
                "citations": {"1": "src-ok"},
                "references": [
                    {
                        "source_id": "src-ok",
                        "citation_number": 1,
                        "cited_text": "trecho normativo",
                    }
                ],
            },
        ],
    )

    evidence = adapter.query(
        "nb-1",
        "Pergunta detalhada com contexto amplo.",
        ("src-ok",),
        retry_question="Pergunta compacta: cite o requisito.",
    )

    query_calls = [call for call in runner.calls if call[:3] == ("nlm", "notebook", "query")]
    assert len(query_calls) == 2
    assert query_calls[0][4] == "Pergunta detalhada com contexto amplo."
    assert query_calls[1][4] == "Pergunta compacta: cite o requisito."
    assert evidence.question == "Pergunta compacta: cite o requisito."
    assert evidence.citations[0].cited_text == "trecho normativo"


@pytest.mark.parametrize(
    "sources",
    [
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        {"sources": [{"id": "src-ok", "title": "Norma teste", "status": 2}]},
    ],
)
def test_query_parses_list_and_object_json_shapes(tmp_path, sources):
    adapter, _ = make_adapter(tmp_path, sources)

    evidence = adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))

    assert evidence.sources[0].source_id == "src-ok"


def test_query_rejects_citation_from_unrequested_source(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
        response={
            "answer": "Resposta inválida.",
            "citations": [
                {"number": "1", "source_id": "src-other", "cited_text": "fora do escopo"}
            ],
        },
    )

    with pytest.raises(ValueError, match="unrequested source"):
        adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok",))


def test_missing_source_writes_manual_request(tmp_path):
    adapter, runner = make_adapter(
        tmp_path,
        [
            {"id": "src-ok", "title": "Norma teste", "status": 2},
            {"id": "src-pending", "title": "Norma pendente", "status": 1},
        ],
    )

    evidence = adapter.query(
        "nb-1",
        "Qual requisito deve ser verificado?",
        ("src-ok", "src-pending"),
    )

    request = tmp_path / "manual-source-requests.md"
    assert evidence.source_ids == ("src-ok",)
    assert evidence.manual_request == str(request)
    assert "src-ok,src-pending" not in runner.calls[-1]
    assert "src-ok" in runner.calls[-1]
    content = request.read_text(encoding="utf-8")
    assert "nb-1" in content
    assert "Norma pendente" in content
    assert "01_TESTE/norma-pendente.pdf" in content
    assert "nlm list sources nb-1 --full" in content


def test_missing_source_writes_complete_manual_request_from_local_metadata(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
    )

    adapter.query(
        "nb-1",
        "Qual requisito deve ser verificado?",
        ("src-ok", "src-missing"),
        source_metadata={
            "src-missing": {
                "title": "Norma local ainda ausente",
                "local_path": "01_TESTE/norma-a-inserir.pdf",
                "local_hash": "sha256:metadata",
            }
        },
    )

    content = (tmp_path / "manual-source-requests.md").read_text(encoding="utf-8")
    assert "src-missing" in content
    assert "nb-1" in content
    assert "Norma local ainda ausente" in content
    assert "01_TESTE/norma-a-inserir.pdf" in content
    assert "sha256:metadata" in content
    assert "Fonte ausente da listagem remota" in content
    assert "nlm list sources nb-1 --full" in content


def test_missing_source_without_metadata_requests_title_and_path(tmp_path):
    adapter, _ = make_adapter(
        tmp_path,
        [{"id": "src-ok", "title": "Norma teste", "status": 2}],
    )

    adapter.query("nb-1", "Qual requisito deve ser verificado?", ("src-ok", "src-missing"))

    content = (tmp_path / "manual-source-requests.md").read_text(encoding="utf-8")
    assert "src-missing" in content
    assert "título e caminho local precisam ser fornecidos" in content


def test_manual_request_default_is_inside_loop_runtime(tmp_path):
    notebook_map, catalog = write_local_sources(tmp_path)

    adapter = NlmCliAdapter(notebook_map, catalog, runner=FakeRunner([]))

    assert adapter.manual_request_path == Path(".loop-runtime/manual-source-requests.md")


def test_notebook_map_prefers_the_most_specific_real_path_prefix():
    project_root = Path(__file__).resolve().parents[3]
    notebook_map = NotebookMap.load(project_root / "fontes" / "notebooklm-mapa.md")

    notebook_id = notebook_map.notebook_id_for_path(
        "fontes/_NOTEBOOKLM_COMPLEMENTAR/01_CONCRETO_DIGITALIZADO/parte-01.pdf"
    )

    assert notebook_id == "76235e0c-94f6-44c1-9977-200fe02f2198"


@pytest.mark.parametrize(
    "result",
    [
        CommandResult(
            argv=("nlm", "list"),
            cwd=".",
            returncode=7,
            duration_seconds=0.1,
            stdout='{"sources": []}',
            stderr="command-result failure",
        ),
        subprocess.CompletedProcess(
            ("nlm", "list"),
            9,
            stdout='{"sources": []}',
            stderr="completed-process failure",
        ),
    ],
)
def test_run_rejects_nonzero_command_results_and_preserves_stderr(tmp_path, result):
    notebook_map, catalog = write_local_sources(tmp_path)
    adapter = NlmCliAdapter(notebook_map, catalog, runner=lambda argv: result)

    with pytest.raises(RuntimeError, match="failure") as error:
        adapter._run(("nlm", "list"))

    assert "return code" in str(error.value)


def test_default_runner_surfaces_stderr_for_nonzero_process(tmp_path):
    notebook_map, catalog = write_local_sources(tmp_path)
    adapter = NlmCliAdapter(notebook_map, catalog)

    with pytest.raises(RuntimeError, match="default runner failure") as error:
        adapter._run(
            (
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('default runner failure'); sys.exit(3)",
            )
        )

    assert "return code 3" in str(error.value)


def test_default_runner_decodes_nlm_utf8_output_on_windows(tmp_path):
    notebook_map, catalog = write_local_sources(tmp_path)
    adapter = NlmCliAdapter(notebook_map, catalog)

    result = adapter.runner(
        (
            sys.executable,
            "-c",
            "import sys; sys.stdout.buffer.write('Fonte: aço — válido'.encode('utf-8'))",
        )
    )

    assert result.stdout == "Fonte: aço — válido"


def test_default_runner_marks_nlm_timeout(tmp_path):
    notebook_map, catalog = write_local_sources(tmp_path)
    adapter = NlmCliAdapter(notebook_map, catalog, timeout_seconds=0.1)

    with pytest.raises(NlmCommandTimeout, match="timed out"):
        adapter.runner(
            (
                sys.executable,
                "-c",
                "import time; time.sleep(2)",
            )
        )


def test_default_runner_timeout_kills_process_tree(monkeypatch, tmp_path):
    class HangingProcess:
        pid = 4242

        def communicate(self, input=None, timeout=None):
            if timeout == 0.1:
                raise subprocess.TimeoutExpired(["nlm"], timeout, output="partial")
            return "", ""

        def terminate(self):
            raise AssertionError("Windows path must kill the complete tree")

        def kill(self):
            raise AssertionError("Windows path must kill the complete tree")

    taskkill_calls = []

    def fake_popen(argv, **kwargs):
        return HangingProcess()

    def fake_run(argv, **kwargs):
        taskkill_calls.append((tuple(argv), kwargs))
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr("tools.loops.research_nlm.os.name", "nt")
    monkeypatch.setattr("tools.loops.research_nlm.subprocess.Popen", fake_popen)
    monkeypatch.setattr("tools.loops.research_nlm.subprocess.run", fake_run)
    notebook_map, catalog = write_local_sources(tmp_path)
    adapter = NlmCliAdapter(notebook_map, catalog, timeout_seconds=0.1)

    with pytest.raises(NlmCommandTimeout):
        adapter.runner((sys.executable, "-c", "pass"))

    assert taskkill_calls[0][0] == ("taskkill", "/PID", "4242", "/T", "/F")
