import csv
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .models import Citation, CommandResult, EvidenceBundle, SourceRecord


class NlmCommandTimeout(RuntimeError):
    """NotebookLM CLI did not finish within the bounded research window."""


class NlmEvidenceRequired(ValueError):
    """NotebookLM answered, but its evidence needs manual correction first."""

    def __init__(self, message, manual_request_path):
        super().__init__(message)
        self.manual_request_path = str(manual_request_path)


@dataclass(frozen=True)
class NotebookMap:
    notebook_ids_by_folder: dict[str, str]

    @classmethod
    def load(cls, path):
        notebook_ids_by_folder = {}
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.startswith("|") or "---" in line:
                continue
            cells = [cell.strip().strip("`") for cell in line.strip("|").split("|")]
            if len(cells) >= 3 and cells[0] != "Pasta local":
                notebook_ids_by_folder[cells[0]] = cells[2]
        return cls(notebook_ids_by_folder)

    def notebook_id_for_path(self, local_path):
        local_parts = self._path_parts(local_path)
        matches = (
            (len(folder_parts), notebook_id)
            for folder, notebook_id in self.notebook_ids_by_folder.items()
            if (folder_parts := self._path_parts(folder))
            and local_parts[:len(folder_parts)] == folder_parts
        )
        return max(matches, default=(0, None))[1]

    @staticmethod
    def _path_parts(path):
        return tuple(
            part
            for part in PurePosixPath(str(path).replace("\\", "/")).parts
            if part not in {".", "/"}
        )


@dataclass(frozen=True)
class CatalogEntry:
    title: str
    local_path: str
    local_hash: str | None


@dataclass(frozen=True)
class CatalogIndex:
    entries_by_title: dict[str, CatalogEntry]
    entries_by_path: dict[str, CatalogEntry] | None = None

    @classmethod
    def load(cls, path):
        entries_by_title = {}
        entries_by_path = {}
        with Path(path).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                title = row.get("nome_normalizado", "")
                if title:
                    entry = CatalogEntry(
                        title=title,
                        local_path=row.get("caminho_relativo", ""),
                        local_hash=row.get("hash_sha256") or None,
                    )
                    entries_by_title[title.casefold()] = entry
                    if entry.local_path:
                        entries_by_path[_normalize_local_path(entry.local_path)] = entry
        return cls(entries_by_title, entries_by_path)

    def find(self, title):
        return self.entries_by_title.get(title.casefold())

    def find_path(self, local_path):
        entries = self.entries_by_path or {}
        return entries.get(_normalize_local_path(local_path))


def _normalize_local_path(value):
    parts = [part for part in str(value).replace("\\", "/").split("/") if part not in {"", "."}]
    if parts and parts[0].casefold() == "fontes":
        parts = parts[1:]
    return "/".join(parts).casefold()


def _stop_process_tree(process):
    """Stop an NLM CLI process and its descendants after a timeout."""
    if process is None:
        return
    if os.name == "nt":
        try:
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if result.returncode == 0:
                return
        except OSError:
            pass
    try:
        process.terminate()
    except (AttributeError, OSError):
        try:
            process.kill()
        except (AttributeError, OSError):
            pass
    try:
        process.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except (AttributeError, OSError):
            pass
        process.communicate()


@dataclass(frozen=True)
class ManualSourceRequest:
    notebook_id: str
    title: str
    local_path: str | None
    local_hash: str | None
    reason: str
    suggested_command: str
    source_id: str | None = None

    def write(self, path):
        request_path = Path(path)
        request_path.parent.mkdir(parents=True, exist_ok=True)
        with request_path.open("a", encoding="utf-8") as handle:
            handle.write(
                f"## {self.title}\n\n"
                f"- Notebook: `{self.notebook_id}`\n"
                f"- Source ID: `{self.source_id or 'desconhecido'}`\n"
                f"- Caminho local: `{self.local_path or 'desconhecido'}`\n"
                f"- Hash local: `{self.local_hash or 'desconhecido'}`\n"
                f"- Motivo: {self.reason}\n"
                f"- Comando manual sugerido: `{self.suggested_command}`\n\n"
            )


class NlmCliAdapter:
    def __init__(
        self,
        notebook_map,
        catalog,
        *,
        runner=None,
        artifact_dir=".loop-runtime/artifacts",
        manual_request_path=".loop-runtime/manual-source-requests.md",
        timeout_seconds=180,
    ):
        self.notebook_map = notebook_map
        self.catalog = catalog
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.timeout_seconds = timeout_seconds
        self.runner = runner or self._run_subprocess
        self.artifact_dir = Path(artifact_dir)
        self.manual_request_path = Path(manual_request_path)
        self.last_artifact_path = None

    def _run_subprocess(self, argv):
        process = None
        try:
            process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            stdout, stderr = process.communicate(timeout=self.timeout_seconds)
            return subprocess.CompletedProcess(
                argv,
                process.returncode,
                stdout or "",
                stderr or "",
            )
        except subprocess.TimeoutExpired as error:
            _stop_process_tree(process)
            command = " ".join(str(value) for value in argv)
            raise NlmCommandTimeout(
                f"nlm command timed out after {self.timeout_seconds:g}s: {command}"
            ) from error

    def _run(self, argv):
        result = self.runner(tuple(argv))
        if isinstance(result, (CommandResult, subprocess.CompletedProcess)):
            if result.returncode != 0:
                raise RuntimeError(
                    f"nlm command failed with return code {result.returncode}: {result.stderr}"
                )
            return result.stdout
        if not isinstance(result, str):
            raise TypeError("runner must return stdout text or a command result")
        return result

    @staticmethod
    def _load_json(stdout):
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as error:
            raise ValueError("nlm returned invalid JSON") from error

    def _catalog_entry(self, title, notebook_id):
        entry = self.catalog.find(title)
        if entry is None or self.notebook_map.notebook_id_for_path(entry.local_path) != notebook_id:
            return None
        return entry

    def _parse_sources(self, notebook_id):
        stdout = self._run(("nlm", "list", "sources", notebook_id, "--full", "--json"))
        document = self._load_json(stdout)
        items = document if isinstance(document, list) else document.get("sources") if isinstance(document, dict) else None
        if not isinstance(items, list):
            raise ValueError("nlm sources JSON must be a list or contain a sources list")
        records = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("nlm source must be an object")
            source_id = item.get("source_id", item.get("id"))
            title = item.get("title", item.get("name", ""))
            if not isinstance(source_id, str) or not isinstance(title, str):
                raise ValueError("nlm source must include string id and title")
            entry = self._catalog_entry(title, notebook_id)
            records.append(
                SourceRecord(
                    source_id=source_id,
                    title=title,
                    status=item.get("status"),
                    notebook_id=notebook_id,
                    local_path=entry.local_path if entry else None,
                    local_hash=entry.local_hash if entry else None,
                )
            )
        return tuple(records)

    @staticmethod
    def _is_ready(source):
        return type(source.status) is int and source.status == 2

    def list_ready_sources(self, notebook_id):
        return tuple(source for source in self._parse_sources(notebook_id) if self._is_ready(source))

    def list_ready_sources_for_paths(self, notebook_id, local_paths):
        """Return only ready sources whose catalogued local paths were declared.

        A scoped task must not silently broaden its evidence to the whole notebook.
        If any declared path is absent or not ready, write a manual request and stop.
        """
        requested_paths = tuple(dict.fromkeys(_normalize_local_path(path) for path in local_paths))
        if not requested_paths:
            raise ValueError("source scope must contain at least one local path")
        for local_path in requested_paths:
            mapped_notebook = self.notebook_map.notebook_id_for_path(local_path)
            if mapped_notebook and mapped_notebook != notebook_id:
                raise ValueError("source scope maps to multiple notebooks")

        all_sources = self._parse_sources(notebook_id)
        by_path = {}
        for source in all_sources:
            if source.local_path:
                by_path.setdefault(_normalize_local_path(source.local_path), []).append(source)

        selected = []
        missing = []
        for local_path in requested_paths:
            matches = tuple(sorted(by_path.get(local_path, ()), key=lambda item: item.source_id))
            ready = tuple(source for source in matches if self._is_ready(source))
            if ready:
                selected.append(ready[0])
                continue
            if matches:
                source = matches[0]
                absent_from_listing = False
            else:
                entry = self.catalog.find_path(local_path)
                source = SourceRecord(
                    source_id=f"local-path:{local_path}",
                    title=entry.title if entry else Path(local_path).name,
                    status=None,
                    notebook_id=notebook_id,
                    local_path=entry.local_path if entry else local_path,
                    local_hash=entry.local_hash if entry else None,
                )
                absent_from_listing = True
            self._write_manual_request(source, notebook_id, absent_from_listing=absent_from_listing)
            missing.append(local_path)

        if missing:
            raise NlmEvidenceRequired(
                "source scope is missing or not ready: " + ", ".join(missing),
                self.manual_request_path,
            )
        return tuple(selected)

    @staticmethod
    def _without_credentials(value):
        if isinstance(value, list):
            return [NlmCliAdapter._without_credentials(item) for item in value]
        if isinstance(value, dict):
            return {
                key: "[REDACTED]" if NlmCliAdapter._is_secret_key(key) else NlmCliAdapter._without_credentials(item)
                for key, item in value.items()
            }
        return value

    @staticmethod
    def _is_secret_key(key):
        normalized_key = "".join(character for character in str(key).casefold() if character.isalnum())
        return any(
            pattern in normalized_key
            for pattern in (
                "token",
                "secret",
                "password",
                "credential",
                "authorization",
                "cookie",
                "apikey",
                "csrf",
                "bearer",
            )
        )

    def _write_response_artifact(self, document):
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        artifact_path = self.artifact_dir / f"nlm-response-{timestamp}.json"
        artifact_path.write_text(
            json.dumps(self._without_credentials(document), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.last_artifact_path = str(artifact_path)

    def _write_manual_request(self, source, notebook_id, *, absent_from_listing=False, reason=None):
        reason = reason or (
            "Fonte ausente da listagem remota; título e caminho local precisam ser fornecidos "
            f"para source_id {source.source_id!r}."
            if absent_from_listing
            else f"Fonte não pronta para consulta (status {source.status!r})."
        )
        ManualSourceRequest(
            notebook_id=notebook_id,
            title=source.title,
            local_path=source.local_path,
            local_hash=source.local_hash,
            reason=reason,
            suggested_command=f"nlm list sources {notebook_id} --full",
            source_id=source.source_id,
        ).write(self.manual_request_path)

    @staticmethod
    def _parse_citations(document, requested_source_ids):
        citations = document.get("citations", [])
        if isinstance(citations, dict):
            if not citations:
                raise ValueError("no auditable citations")
            references = document.get("references", [])
            if not isinstance(references, list):
                raise ValueError("nlm references must be a list")
            references_by_number = {}
            for reference in references:
                if not isinstance(reference, dict):
                    raise ValueError("nlm reference must be an object")
                number = reference.get("citation_number", reference.get("number"))
                if number is not None:
                    references_by_number[str(number)] = reference
            parsed = []
            for number, source_id in citations.items():
                if not isinstance(source_id, str) or source_id not in requested_source_ids:
                    raise ValueError("citation references an unrequested source")
                reference = references_by_number.get(str(number), {})
                reference_source_id = reference.get("source_id", reference.get("sourceId"))
                if reference_source_id is not None and reference_source_id != source_id:
                    raise ValueError("reference source does not match citation")
                cited_text = str(reference.get("cited_text", reference.get("text", "")))
                if not cited_text.strip():
                    raise ValueError(f"empty citation text for source {source_id}")
                parsed.append(
                    Citation(
                        number=str(number),
                        source_id=source_id,
                        cited_text=cited_text,
                    )
                )
            return tuple(parsed)
        if not isinstance(citations, list):
            raise ValueError("nlm citations must be a list or map")
        if not citations:
            raise ValueError("no auditable citations")
        parsed = []
        for citation in citations:
            if not isinstance(citation, dict):
                raise ValueError("nlm citation must be an object")
            source_id = citation.get("source_id", citation.get("sourceId"))
            if source_id not in requested_source_ids:
                raise ValueError("citation references an unrequested source")
            cited_text = str(citation.get("cited_text", citation.get("text", "")))
            if not cited_text.strip():
                raise ValueError(f"empty citation text for source {source_id}")
            parsed.append(
                Citation(
                    number=str(citation.get("number", len(parsed) + 1)),
                    source_id=source_id,
                    cited_text=cited_text,
                )
            )
        return tuple(parsed)

    @staticmethod
    def _source_from_metadata(source_id, notebook_id, source_metadata):
        metadata = (source_metadata or {}).get(source_id, {})
        if isinstance(metadata, SourceRecord):
            return SourceRecord(
                source_id=source_id,
                title=metadata.title,
                status=metadata.status,
                notebook_id=notebook_id,
                local_path=metadata.local_path,
                local_hash=metadata.local_hash,
            )
        if not isinstance(metadata, dict):
            metadata = {}
        title = metadata.get("title")
        return SourceRecord(
            source_id=source_id,
            title=title if isinstance(title, str) and title else f"source_id {source_id} (título precisa ser informado)",
            status=metadata.get("status"),
            notebook_id=notebook_id,
            local_path=metadata.get("local_path"),
            local_hash=metadata.get("local_hash"),
        )

    def query(self, notebook_id, question, source_ids, source_metadata=None, retry_question=None):
        requested_source_ids = tuple(dict.fromkeys(source_ids))
        all_sources = self._parse_sources(notebook_id)
        sources_by_id = {source.source_id: source for source in all_sources}
        selected_sources = tuple(
            sources_by_id[source_id]
            for source_id in requested_source_ids
            if source_id in sources_by_id and self._is_ready(sources_by_id[source_id])
        )
        missing_sources = tuple(
            (
                sources_by_id[source_id]
                if source_id in sources_by_id
                else self._source_from_metadata(source_id, notebook_id, source_metadata),
                source_id not in sources_by_id,
            )
            for source_id in requested_source_ids
            if source_id not in sources_by_id or not self._is_ready(sources_by_id[source_id])
        )
        for source, absent_from_listing in missing_sources:
            self._write_manual_request(source, notebook_id, absent_from_listing=absent_from_listing)
        if not selected_sources:
            raise ValueError("no requested sources are ready")

        selected_source_ids = tuple(source.source_id for source in selected_sources)
        questions = tuple(dict.fromkeys(value for value in (question, retry_question) if value))
        last_error = None
        for current_question in questions:
            stdout = self._run(
                (
                    "nlm", "notebook", "query", notebook_id, current_question,
                    "--source-ids", ",".join(selected_source_ids), "--timeout", "120", "--json",
                )
            )
            document = self._load_json(stdout)
            if not isinstance(document, dict):
                raise ValueError("nlm query JSON must be an object")
            document = self._without_credentials(document)
            self._write_response_artifact(document)
            try:
                citations = self._parse_citations(document, selected_source_ids)
            except ValueError as error:
                last_error = error
                if str(error) == "no auditable citations" and current_question != questions[-1]:
                    continue
                detail = str(error)
                if detail == "no auditable citations" or "empty citation text for source " in detail:
                    self._record_evidence_error(selected_sources, notebook_id, error)
                    raise NlmEvidenceRequired(detail, self.manual_request_path) from error
                raise
            return EvidenceBundle(
                notebook_id=notebook_id,
                source_ids=selected_source_ids,
                sources=selected_sources,
                question=current_question,
                answer=str(document.get("answer", "")),
                conversation_id=document.get("conversation_id", document.get("conversationId")),
                citations=citations,
                retrieved_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                manual_request=str(self.manual_request_path) if missing_sources else None,
            )
        if last_error is not None:
            self._record_evidence_error(selected_sources, notebook_id, last_error)
            raise NlmEvidenceRequired(str(last_error), self.manual_request_path) from last_error
        raise ValueError("no query question provided")

    def _record_evidence_error(self, selected_sources, notebook_id, error):
        detail = str(error)
        marker = "empty citation text for source "
        if marker in detail:
            source_id = detail.split(marker, 1)[1].strip()
            source = next(
                (item for item in selected_sources if item.source_id == source_id),
                None,
            )
            if source is not None:
                self._write_manual_request(
                    source,
                    notebook_id,
                    reason=(
                        "Fonte retornou citacao sem trecho textual; recarregar ou corrigir "
                        "a fonte no NotebookLM antes de usar a evidencia."
                    ),
                )
        elif detail == "no auditable citations":
            for source in selected_sources:
                self._write_manual_request(
                    source,
                    notebook_id,
                    reason=(
                        "Fonte retornou resposta sem citacoes auditaveis; repetir a consulta "
                        "ou corrigir a indexacao no NotebookLM."
                    ),
                )
