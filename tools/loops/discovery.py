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
_SOURCE_PENDING_NAMES = frozenset({"pendencias-atualizacao.md", "fontes-faltantes.md"})
_LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")
_CHECKBOX_RE = re.compile(r"^\s*\[(?P<mark>[ xX])\]\s*")
_PENDING_RE = re.compile(
    r"(?:\[\s*\]|\bainda\s+aberto\b|\baberto\b|\bpendente\b|"
    r"\bfaltam?\b(?!va)|\bnao\s+(?:feito|re-?verificado|verificado|implementado)\b|"
    r"\bnao\s+ha\s+fonte\b|\bfontes?\s+que\s+faltam?\b|"
    r"\bbloquead[oa]\b|\binconclusiv[oa]\b|\bfuzz\b|\ba\s+confirmar\b|"
    r"\b(?:obter|adquirir|procurar|incorporar|completar|confirmar|conferir|validar)\b|"
    r"\bainda\s+devem?\s+ser\b)",
    re.IGNORECASE,
)
_STRONG_PENDING_RE = re.compile(
    r"(?:\[\s*\]|\bnao\s+(?:feito|re-?verificado|verificado|implementado)\b|"
    r"\bbloquead[oa]\b|\binconclusiv[oa]\b)",
    re.IGNORECASE,
)
_RESOLVED_STATUS_RE = re.compile(
    r"(?:\bresolvid[oa]\b|\bmerged\b|\bfechad[oa]\b|\bhomologad[oa]\b|"
    r"\baprovad[oa]\b|\batende\b|\bcorrigid[oa]\b|\bacatad[oa]\b|"
    r"\bja\s+implementad[oa]\b)",
    re.IGNORECASE,
)
_COMPLETED_RE = re.compile(
    r"\b(?:feito|feita|concluido|concluida|executado|executada)\b",
    re.IGNORECASE,
)
_HISTORICAL_RE = re.compile(
    r"\b(?:historico|historica|historico|antigo|antiga|anterior|passado|passada|antes)\b",
    re.IGNORECASE,
)
_NON_ACTIONABLE_RE = re.compile(r"\bnao\s+se\s+aplica\b|\bnao\s+e\s+aplicavel\b", re.IGNORECASE)
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
        if path.name.casefold() == "revisao-indice.md":
            continue
        relative = path.relative_to(root)
        candidates.extend(_discover_markdown(root, relative, suggestions, include_all=False))
    return candidates


def _discover_source_pending_items(root: Path, suggestions: tuple[str, ...]) -> list[TaskCandidate]:
    source_root = root / _SOURCE_ROOT
    if not source_root.is_dir():
        return []
    candidates = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file() or path.name.casefold() not in _SOURCE_PENDING_NAMES:
            continue
        relative = path.relative_to(root)
        candidates.extend(
            _discover_markdown(root, relative, suggestions, include_all=False, list_only=True)
        )
    return candidates


def _discover_markdown(
    root: Path,
    relative_path: Path,
    suggestions: tuple[str, ...],
    *,
    include_all: bool,
    list_only: bool = False,
) -> list[TaskCandidate]:
    path = root / relative_path
    if not path.is_file():
        return []

    candidates = []
    heading = ""
    thread = ""
    thread_heading = ""
    item_lines: list[str] = []
    item_is_list = False

    def add_item() -> None:
        nonlocal item_is_list
        if not item_lines:
            return
        raw_title = " ".join(item_lines)
        title = _clean_title(raw_title)
        was_list = item_is_list
        item_lines.clear()
        item_is_list = False
        if not title or (list_only and not was_list):
            return
        context = thread_heading if include_all else heading
        if not _is_open_item(raw_title, context):
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
            if thread:
                thread_heading = heading
            elif not include_all:
                thread_heading = heading
            if not include_all:
                thread = heading or path.stem
            continue
        if not line.strip():
            add_item()
            continue
        if line.lstrip().startswith("|"):
            add_item()
            if not _is_table_separator(line):
                item_lines.append(line.strip())
                item_is_list = True
                add_item()
            continue
        if _LIST_RE.match(line):
            add_item()
            item_is_list = True
        elif list_only and not item_lines:
            continue
        item_lines.append(line.strip())
    add_item()
    return candidates


def _candidate(
    title: str,
    origin: str,
    evidence_path: str,
    suggestions: tuple[str, ...],
) -> TaskCandidate:
    discipline = _discipline_for(title, f"{origin} {evidence_path}")
    priority = _observed_priority(title, discipline)
    identifier = sha1(f"{origin}\n{title}".encode("utf-8")).hexdigest()[:12]
    return TaskCandidate(
        id=identifier,
        title=title,
        discipline=discipline,
        origin=origin,
        priority=priority,
        evidence_paths=(evidence_path,),
        suggested_tests=_tests_for_candidate(title, discipline, suggestions),
    )


def _is_open_item(title: str, context: str = "") -> bool:
    normalized = _normalized(title)
    if _checkbox_mark(title) == "x":
        return False
    if _is_status_label(normalized) or not _PENDING_RE.search(normalized):
        return False
    cleaned_normalized = _normalized(_clean_title(title))
    if _is_explicit_historical(cleaned_normalized) or _NON_ACTIONABLE_RE.search(normalized):
        return False
    if any(
        phrase in normalized
        for phrase in ("nao ha suspeita aberta", "nao tem pendencia", "zero pendente")
    ):
        return False

    strong_pending = bool(_STRONG_PENDING_RE.search(normalized))
    resolved = bool(_RESOLVED_STATUS_RE.search(normalized))
    if _COMPLETED_RE.search(normalized) and not re.search(
        r"\bnao\s+(?:feito|concluido|executado)\b", normalized
    ):
        resolved = True
    if resolved and not strong_pending:
        return False
    if _HISTORICAL_RE.search(normalized) and not strong_pending:
        return False

    normalized_context = _normalized(context)
    context_resolved = bool(_RESOLVED_STATUS_RE.search(normalized_context))
    if _COMPLETED_RE.search(normalized_context):
        context_resolved = True
    if context_resolved:
        return strong_pending and not _HISTORICAL_RE.search(normalized)
    return True


def _checkbox_mark(value: str) -> str | None:
    value = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", value)
    match = _CHECKBOX_RE.match(value)
    return match.group("mark").casefold() if match else None


def _is_explicit_historical(normalized: str) -> bool:
    return normalized.startswith("(hist.") or normalized.startswith("hist.") or normalized.startswith(
        ("historico", "historica")
    )


def _is_status_label(normalized: str) -> bool:
    value = normalized.strip(" :.-")
    return value in {
        "aberto",
        "ainda aberto",
        "pendente",
        "pendencias",
        "pendencias prioritarias",
        "fechado nesta sessao",
        "feito",
    }


def _is_table_separator(line: str) -> bool:
    cells = [cell.strip().replace(":", "") for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(cell and set(cell) <= {"-"} for cell in cells)


def _suggested_tests(root: Path) -> tuple[str, ...]:
    test_root = root / _TEST_ROOT
    if not test_root.is_dir():
        return ()
    return tuple(
        path.relative_to(root).as_posix()
        for path in sorted(test_root.glob("test_*.py"))
    )


def _tests_for_candidate(title: str, discipline: str, available: tuple[str, ...]) -> tuple[str, ...]:
    text = _normalized(title)
    if any(term in text for term in ("fundacao", "sapata", "estaca", "geotec", "tombamento", "deslizamento", "solo")):
        terms = ("fundacao", "geotec", "bloco", "galpao_concreto", "validacao")
    elif discipline == "eletrica":
        terms = ("eletric", "executivo_eletrico")
    elif discipline == "hidraulica":
        terms = ("hidraulic", "calha", "drenagem", "pluvial")
    elif discipline == "esgoto":
        terms = ("esgoto", "reuso")
    elif discipline == "seguranca":
        terms = ("incendio", "seguranca")
    elif discipline == "bim_ifc":
        terms = ("bim", "ifc", "federado", "clash")
    else:
        terms = ("robustez", "integracao", "validacao", "galpao_concreto")
    selected = tuple(
        path for path in available if any(term in _normalized(Path(path).stem) for term in terms)
    )
    if selected:
        return selected
    return tuple(
        path for path in available
        if any(term in _normalized(Path(path).stem) for term in ("robustez", "integracao"))
    )


def _discipline_for(title: str, context: str = "") -> str:
    text = _normalized(f"{title} {context}")
    if any(term in text for term in ("fundacao", "sapata", "estaca", "geotec", "tombamento", "deslizamento")):
        return "estrutura"
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
    value = re.sub(r"^\s*\[[ xX]\]\s*", "", value)
    value = _MARKDOWN_RE.sub("", value)
    return re.sub(r"\s+", " ", value).strip()


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).casefold()
