import csv
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .models import Citation, CommandResult, EvidenceBundle, SourceRecord


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

    @classmethod
    def load(cls, path):
        entries_by_title = {}
        with Path(path).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                title = row.get("nome_normalizado", "")
                if title:
                    entries_by_title[title.casefold()] = CatalogEntry(
                        title=title,
                        local_path=row.get("caminho_relativo", ""),
                        local_hash=row.get("hash_sha256") or None,
                    )
        return cls(entries_by_title)

    def find(self, title):
        return self.entries_by_title.get(title.casefold())


@dataclass(frozen=True)
class ManualSourceRequest:
    notebook_id: str
    title: str
    local_path: str | None
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
    ):
        self.notebook_map = notebook_map
        self.catalog = catalog
        self.runner = runner or self._run_subprocess
        self.artifact_dir = Path(artifact_dir)
        self.manual_request_path = Path(manual_request_path)
        self.last_artifact_path = None

    @staticmethod
    def _run_subprocess(argv):
        return subprocess.run(
            argv,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

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

    def _write_manual_request(self, source, notebook_id, *, absent_from_listing=False):
        reason = (
            "Fonte ausente da listagem remota; título e caminho local precisam ser fornecidos "
            f"para source_id {source.source_id!r}."
            if absent_from_listing
            else f"Fonte não pronta para consulta (status {source.status!r})."
        )
        ManualSourceRequest(
            notebook_id=notebook_id,
            title=source.title,
            local_path=source.local_path,
            reason=reason,
            suggested_command=f"nlm list sources {notebook_id} --full",
            source_id=source.source_id,
        ).write(self.manual_request_path)

    @staticmethod
    def _parse_citations(document, requested_source_ids):
        citations = document.get("citations", [])
        if not isinstance(citations, list):
            raise ValueError("nlm citations must be a list")
        parsed = []
        for citation in citations:
            if not isinstance(citation, dict):
                raise ValueError("nlm citation must be an object")
            source_id = citation.get("source_id", citation.get("sourceId"))
            if source_id not in requested_source_ids:
                raise ValueError("citation references an unrequested source")
            parsed.append(
                Citation(
                    number=str(citation.get("number", len(parsed) + 1)),
                    source_id=source_id,
                    cited_text=str(citation.get("cited_text", citation.get("text", ""))),
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

    def query(self, notebook_id, question, source_ids, source_metadata=None):
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
        stdout = self._run(
            (
                "nlm", "notebook", "query", notebook_id, question,
                "--source-ids", ",".join(selected_source_ids), "--timeout", "120", "--json",
            )
        )
        document = self._load_json(stdout)
        if not isinstance(document, dict):
            raise ValueError("nlm query JSON must be an object")
        document = self._without_credentials(document)
        self._write_response_artifact(document)
        return EvidenceBundle(
            notebook_id=notebook_id,
            source_ids=selected_source_ids,
            sources=selected_sources,
            question=question,
            answer=str(document.get("answer", "")),
            conversation_id=document.get("conversation_id", document.get("conversationId")),
            citations=self._parse_citations(document, selected_source_ids),
            retrieved_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            manual_request=str(self.manual_request_path) if missing_sources else None,
        )
