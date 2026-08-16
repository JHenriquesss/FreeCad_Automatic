"""Gate de verificação ao vivo das fontes declaradas no spec do projeto.

O Loop de projeto não consulta o NotebookLM durante o cálculo. Esta camada é
executada antes dele e transforma o retrato remoto das fontes em evidência
persistida: cada ``source_id`` precisa existir no notebook declarado, estar em
status ``2`` e não estar marcado como stale.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from project_loop import normalize_spec


SOURCE_VERIFICATION_SCHEMA = "freecad-automatic/project-source-verification"
SOURCE_VERIFICATION_SCHEMA_VERSION = 1
MAX_NOTEBOOK_SOURCES = 50


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_document(source_refs):
    if source_refs is None:
        return {}
    if isinstance(source_refs, (dict, list)):
        return source_refs
    raise ValueError("source_refs deve ser um objeto ou lista JSON")


def _is_concrete_hashable_string(value):
    if type(value) is not str:
        return False
    try:
        hash(value)
    except TypeError:
        return False
    return True


def _declared_refs(source_refs):
    document = _source_document(source_refs)
    if isinstance(document, list):
        return [("all", item) for item in document]
    refs = []
    for discipline, values in document.items():
        if not isinstance(values, list):
            raise ValueError(
                "source_refs.%s deve ser uma lista JSON" % discipline)
        refs.extend((str(discipline), item) for item in values)
    return refs


def _run_nlm(argv, timeout_seconds):
    return subprocess.run(
        list(argv), capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=timeout_seconds, check=False,
    )


def _runner_output(result):
    if isinstance(result, str):
        return result
    if isinstance(result, (subprocess.CompletedProcess,)):
        if result.returncode != 0:
            raise RuntimeError(
                "nlm retornou código %s" % result.returncode)
        return result.stdout or ""
    if hasattr(result, "returncode") and hasattr(result, "stdout"):
        if result.returncode != 0:
            raise RuntimeError(
                "nlm retornou código %s" % result.returncode)
        return result.stdout or ""
    raise TypeError("runner deve retornar texto ou resultado de processo")


def _parse_remote_sources(stdout):
    try:
        document = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("nlm retornou JSON inválido") from exc
    if isinstance(document, list):
        items = document
    elif isinstance(document, dict) and isinstance(document.get("sources"), list):
        items = document["sources"]
    else:
        raise ValueError("nlm sources JSON deve ser uma lista ou conter sources")
    result = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("nlm source deve ser um objeto")
        source_id = item.get("source_id") or item.get("id")
        if not _is_concrete_hashable_string(source_id) or not source_id.strip():
            raise ValueError("nlm source requer id textual")
        result[source_id] = item
    return result


def _error(code, discipline, ref, detail, **extra):
    value = {"code": code, "discipline": discipline, "detail": detail}
    if isinstance(ref, dict):
        if ref.get("notebook_id") is not None:
            value["notebook_id"] = ref.get("notebook_id")
        if ref.get("source_id") is not None:
            value["source_id"] = ref.get("source_id")
    value.update(extra)
    return value


def verify_project_source_refs(spec, *, runner=None, timeout_seconds=120):
    """Confere ao vivo os ``source_refs`` do spec usando o CLI ``nlm``.

    ``runner`` é injetável para testes e deve aceitar a tupla de argumentos do
    comando ``nlm list sources``. A função não altera o spec nem executa
    disciplinas; problemas de fonte são retornados no relatório bloqueado.
    Erros de formato do próprio spec continuam sendo ``ValueError``.
    """
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds deve ser positivo")
    normalized = normalize_spec(spec)
    source_refs = _source_document(normalized["source_refs"])
    declared = _declared_refs(source_refs)
    errors = []
    references = []
    by_notebook = {}

    for discipline, ref in declared:
        if not isinstance(ref, dict):
            errors.append(_error(
                "invalid_source_ref", discipline, {},
                "referência de fonte deve ser um objeto JSON"))
            continue
        notebook_id = ref.get("notebook_id")
        source_id = ref.get("source_id") or ref.get("id")
        if (not _is_concrete_hashable_string(notebook_id)
                or not notebook_id.strip()):
            errors.append(_error(
                "invalid_source_ref", discipline, ref,
                "referência requer notebook_id"))
            continue
        if (not _is_concrete_hashable_string(source_id)
                or not source_id.strip()):
            errors.append(_error(
                "invalid_source_ref", discipline, ref,
                "referência requer source_id ou id"))
            continue
        entry = {
            "discipline": discipline,
            "notebook_id": notebook_id,
            "source_id": source_id,
            "declared_status": ref.get("status"),
        }
        references.append(entry)
        by_notebook.setdefault(notebook_id, []).append(entry)

    requested = list(normalized["requested_disciplines"])
    declared_disciplines = {item["discipline"] for item in references}
    if isinstance(source_refs, dict) and "all" not in source_refs:
        for discipline in requested:
            if discipline not in declared_disciplines:
                errors.append({
                    "code": "missing_source_refs",
                    "discipline": discipline,
                    "detail": "nenhuma fonte declarada para a disciplina",
                })

    call_runner = runner
    if call_runner is None:
        call_runner = lambda argv: _run_nlm(argv, timeout_seconds)

    notebook_reports = []
    for notebook_id, entries in by_notebook.items():
        argv = ("nlm", "list", "sources", notebook_id, "--full", "--json")
        try:
            remote = _parse_remote_sources(_runner_output(call_runner(argv)))
            query_error = None
        except Exception as exc:  # external CLI/auth/network boundary
            remote = {}
            query_error = str(exc)
        notebook_report = {
            "notebook_id": notebook_id,
            "requested_references": len(entries),
            "remote_source_count": len(remote),
            "source_limit": MAX_NOTEBOOK_SOURCES,
            "within_source_limit": len(remote) <= MAX_NOTEBOOK_SOURCES,
        }
        if query_error is not None:
            for entry in entries:
                errors.append(_error(
                    "notebook_query_failed", entry["discipline"], entry,
                    "não foi possível consultar o notebook: %s" % query_error))
                entry.update({"exists": False, "remote_status": None,
                              "remote_is_stale": None, "ready": False})
        else:
            if len(remote) > MAX_NOTEBOOK_SOURCES:
                errors.append({
                    "code": "notebook_source_limit",
                    "notebook_id": notebook_id,
                    "detail": "notebook excede o limite de 50 fontes",
                    "remote_source_count": len(remote),
                })
            for entry in entries:
                source = remote.get(entry["source_id"])
                if source is None:
                    errors.append(_error(
                        "source_not_found", entry["discipline"], entry,
                        "source_id não existe no notebook consultado"))
                    entry.update({"exists": False, "remote_status": None,
                                  "remote_is_stale": None, "ready": False})
                    continue
                status = source.get("status")
                stale = bool(source.get("is_stale", False))
                ready = status == 2 and not stale
                entry.update({"exists": True, "remote_status": status,
                              "remote_is_stale": stale, "ready": ready})
                if status != 2:
                    errors.append(_error(
                        "source_not_ready", entry["discipline"], entry,
                        "fonte não está pronta no NotebookLM",
                        remote_status=status))
                if stale:
                    errors.append(_error(
                        "source_stale", entry["discipline"], entry,
                        "fonte marcada como stale no NotebookLM"))
                declared_status = entry.get("declared_status")
                if (declared_status is not None and
                        str(declared_status) != str(status)):
                    errors.append(_error(
                        "source_snapshot_mismatch", entry["discipline"], entry,
                        "status declarado no spec difere do status remoto",
                        declared_status=declared_status,
                        remote_status=status))
        notebook_reports.append(notebook_report)

    status = "ready" if not errors else "blocked"
    return {
        "schema": SOURCE_VERIFICATION_SCHEMA,
        "schema_version": SOURCE_VERIFICATION_SCHEMA_VERSION,
        "verified_at": _utc_now(),
        "project_id": normalized["project_id"],
        "adapter": normalized["adapter"],
        "requested_disciplines": requested,
        "notebooks_checked": len(notebook_reports),
        "checked_references": len(references),
        "notebooks": notebook_reports,
        "references": references,
        "status": status,
        "ok": status == "ready",
        "errors": errors,
    }


def persist_source_verification(report, out_dir):
    """Persiste um relatório de fontes numa pasta nova ou vazia."""
    root = Path(out_dir).expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise ValueError("pasta do relatório de fontes não é um diretório")
    if root.exists() and any(root.iterdir()):
        raise ValueError("pasta do relatório de fontes deve ser nova ou vazia")
    root.mkdir(parents=True, exist_ok=True)
    path = root / "source-verification.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return path


__all__ = [
    "MAX_NOTEBOOK_SOURCES",
    "SOURCE_VERIFICATION_SCHEMA",
    "SOURCE_VERIFICATION_SCHEMA_VERSION",
    "persist_source_verification",
    "verify_project_source_refs",
]
