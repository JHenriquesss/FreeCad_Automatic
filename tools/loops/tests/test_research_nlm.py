import csv
import json

import pytest

from tools.loops.research_nlm import CatalogIndex, NlmCliAdapter, NotebookMap


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
    return NotebookMap.load(map_path), CatalogIndex.load(catalog_path)


class FakeRunner:
    def __init__(self, sources, response=None):
        self.sources = sources
        self.response = response or {
            "answer": "A resposta de teste exige verificacao.",
            "conversation_id": "conv-1",
            "citations": [
                {"number": "1", "source_id": "src-ok", "cited_text": "trecho curto"}
            ],
            "token": "credential-that-must-not-be-written",
        }
        self.calls = []

    def __call__(self, argv):
        self.calls.append(tuple(argv))
        if tuple(argv[:3]) == ("nlm", "list", "sources"):
            return json.dumps(self.sources)
        if tuple(argv[:3]) == ("nlm", "notebook", "query"):
            return json.dumps(self.response)
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
    assert "token" not in stored_response


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
