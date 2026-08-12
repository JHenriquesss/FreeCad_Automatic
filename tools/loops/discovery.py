"""Discover deterministic, evidence-backed follow-up tasks from local project files."""

from __future__ import annotations

from hashlib import sha1
from pathlib import Path
import re
import unicodedata

from tools.loops.models import TaskCandidate


_WIKI_PATH = Path("framework/galpao_fw/wiki/06-open-threads.md")
_FRAMEWORK_ROOT = Path("framework/galpao_fw")
_TEST_ROOT = _FRAMEWORK_ROOT / "tests"
_SOURCE_ROOT = Path("fontes")
_PENDING_RE = re.compile(
    r"\b(?:ainda\s+aberto|aberto|pendente|falta(?:m|va)?|não\s+(?:feito|re-?verificado)|"
    r"nao\s+(?:feito|re-?verificado)|não\s+verificado|nao\s+verificado|"
    r"não\s+há\s+fonte|nao\s+ha\s+fonte|fonte(?:s)?\s+que\s+falta(?:m)?|"
    r"bloquead[oa]|inconclusivo|fuzz)\b",
    re.IGNORECASE,
)
_HEADING_RE = re.compile(r"^#{1,6}\s+(?P<name>.+?)\s*$")
_THREAD_RE = re.compile(r"\b(T\d+[a-z]?)\b", re.IGNORECASE)
_MARKDOWN_RE = re.compile(r"[`*_~]")

_DISCIPLINE_ORDER = {
    "seguranca": 0,
    "eletrica": 1,
    "hidraulica": 2,
    "esgoto": 3,
    "estrutura": 4,
    "bim_ifc": 5,
    "2d": 6,
    "documentacao": 7,
    "geral": 8,
}


def discover_candidates(project_root) -> tuple[TaskCandidate, ...]:
    """Return local, observed task candidates in deterministic priority order.

    Only statements that explicitly describe an unresolved item become candidates.
    NotebookLM and every remote source are deliberately outside this discovery step.
    """
    root = Path(project_root)
    suggestions = _suggested_tests(root)
    candidates = []
    candidates.extend(_discover_markdown(root, _WIKI_PATH, suggestions, include_all=True))
    candidates.extend(_discover_revision_documents(root, suggestions))
    candidates.extend(_discover_source_pending_items(root, suggestions))
    return rank_candidates(_deduplicate(candidates))


def rank_candidates(candidates) -> tuple[TaskCandidate, ...]:
    """Sort candidates by observed urgency, discipline, origin, and stable ID."""
    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                -_priority_score(item),
                _DISCIPLINE_ORDER.get(item.discipline, _DISCIPLINE_ORDER["geral"]),
                item.origin,
                item.id,
            ),
        )
    )


def _discover_revision_documents(root: Path, suggestions: tuple[str, ...]) -> list[TaskCandidate]:
    framework = root / _FRAMEWORK_ROOT
    if not framework.is_dir():
        return []
    candidates = []
    for path in sorted(framework.glob("REVISAO-*.md")):
        relative = path.relative_to(root)
        candidates.extend(_discover_markdown(root, relative, suggestions, include_all=False))
    return candidates


def _discover_source_pending_items(root: Path, suggestions: tuple[str, ...]) -> list[TaskCandidate]:
    source_root = root / _SOURCE_ROOT
    if not source_root.is_dir():
        return []
    candidates = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt", ".csv"}:
            continue
        relative = path.relative_to(root)
        candidates.extend(_discover_markdown(root, relative, suggestions, include_all=False))
    return candidates


def _discover_markdown(
    root: Path,
    relative_path: Path,
    suggestions: tuple[str, ...],
    *,
    include_all: bool,
) -> list[TaskCandidate]:
    path = root / relative_path
    if not path.is_file():
        return []

    candidates = []
    heading = ""
    thread = ""
    item_lines: list[str] = []

    def add_item() -> None:
        if not item_lines:
            return
        title = _clean_title(" ".join(item_lines))
        item_lines.clear()
        if not title or not _is_open_item(title):
            return
        origin = relative_path.as_posix()
        if thread:
            origin = f"{origin}:{thread}"
        candidates.append(_candidate(title, origin, relative_path.as_posix(), suggestions))

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _HEADING_RE.match(line)
        if match:
            add_item()
            heading = _clean_title(match.group("name"))
            thread_match = _THREAD_RE.search(heading)
            thread = thread_match.group(1).upper() if thread_match else ""
            if not include_all:
                thread = heading or path.stem
            continue
        if not line.strip():
            add_item()
            continue
        if item_lines and re.match(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", line):
            add_item()
        item_lines.append(line.strip())
    add_item()
    return candidates


def _candidate(
    title: str,
    origin: str,
    evidence_path: str,
    suggestions: tuple[str, ...],
) -> TaskCandidate:
    discipline = _discipline_for(title)
    priority = _observed_priority(title, discipline)
    identifier = sha1(f"{origin}\n{title}".encode("utf-8")).hexdigest()[:12]
    return TaskCandidate(
        id=identifier,
        title=title,
        discipline=discipline,
        origin=origin,
        priority=priority,
        evidence_paths=(evidence_path,),
        suggested_tests=suggestions,
    )


def _is_open_item(title: str) -> bool:
    normalized = _normalized(title)
    if not _PENDING_RE.search(normalized):
        return False
    return not any(
        phrase in normalized
        for phrase in ("nao ha suspeita aberta", "nao tem pendencia", "zero pendente")
    )


def _suggested_tests(root: Path) -> tuple[str, ...]:
    test_root = root / _TEST_ROOT
    if not test_root.is_dir():
        return ()
    return tuple(
        path.relative_to(root).as_posix()
        for path in sorted(test_root.glob("test_*.py"))
        if any(term in _normalized(path.stem) for term in ("robustez", "integracao"))
    )


def _discipline_for(title: str) -> str:
    text = _normalized(title)
    if any(term in text for term in ("seguranca", "incendio", "contra-seguranca")):
        return "seguranca"
    if "eletric" in text:
        return "eletrica"
    if any(term in text for term in ("hidraulic", "pluvial")):
        return "hidraulica"
    if any(term in text for term in ("esgoto", "saneamento")):
        return "esgoto"
    if any(term in text for term in ("ifc", "bim")):
        return "bim_ifc"
    if any(term in text for term in ("2d", "techdraw", "prancha", "desenho")):
        return "2d"
    if any(term in text for term in ("documentacao", "wiki", "revisao", "fonte")):
        return "documentacao"
    return "estrutura"


def _observed_priority(title: str, discipline: str) -> int:
    text = _normalized(title)
    priority = 10
    if any(term in text for term in ("aberto", "pendente", "falta", "nao feito", "nao re-verificado", "fuzz")):
        priority += 20
    if any(term in text for term in ("seguranca", "valid", "regress", "fuzz", "bloquead")):
        priority += 30
    if discipline == "seguranca":
        priority += 20
    return priority


def _priority_score(candidate: TaskCandidate) -> int:
    return candidate.priority + _observed_priority(candidate.title, candidate.discipline)


def _deduplicate(candidates: list[TaskCandidate]) -> tuple[TaskCandidate, ...]:
    unique = {}
    for candidate in candidates:
        unique.setdefault(candidate.id, candidate)
    return tuple(unique.values())


def _clean_title(value: str) -> str:
    value = value.strip()
    value = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+|>\s*)", "", value)
    value = _MARKDOWN_RE.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()
