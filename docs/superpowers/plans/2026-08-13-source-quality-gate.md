# Source Quality Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect local PDF sources without extractable text before NotebookLM queries and park them with an auditable manual request.

**Architecture:** Add a pure PyMuPDF inspector in `tools/loops/source_quality.py`. Inject the project `fontes/` root into `NlmCliAdapter`, inspect each selected PDF after remote status/path matching, and raise the existing `NlmEvidenceRequired` with a metric-rich manual request before any query subprocess is started.

**Tech Stack:** Python 3.12 standard library, PyMuPDF (`fitz`), pytest, existing `NlmCliAdapter` and `ManualSourceRequest`.

## Global Constraints

- Only declared `source_paths` may be inspected or queried.
- PDF inspection is read-only and never runs OCR.
- Non-PDF sources are unchanged in this phase.
- A source without `cited_text` remains invalid evidence.
- No new runtime dependency is added; PyMuPDF is already declared by the project.
- The repository root and unrelated dirty files must not be changed.

---

### Task 1: Add the PDF text inspection contract

**Files:**
- Create: `tools/loops/source_quality.py`
- Test: `tools/loops/tests/test_source_quality.py`

**Interfaces:**
- Produces `PdfTextReport` and `inspect_pdf_text(path: Path) -> PdfTextReport` for Task 2.

- [x] **Step 1: Write the failing tests**

```python
from pathlib import Path

import fitz
import pytest

from tools.loops.source_quality import inspect_pdf_text


def _pdf(path: Path, *, text: str | None):
    document = fitz.open()
    page = document.new_page()
    if text is not None:
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()


def test_inspect_pdf_text_reports_extractable_text(tmp_path):
    path = tmp_path / "textual.pdf"
    _pdf(path, text="NBR requisito verificavel")

    report = inspect_pdf_text(path)

    assert report.pages == 1
    assert report.pages_with_text == 1
    assert report.total_chars >= len("NBR requisito verificavel")
    assert report.max_page_chars == report.total_chars
    assert report.usable is True


def test_inspect_pdf_text_rejects_image_only_pdf(tmp_path):
    path = tmp_path / "scan.pdf"
    _pdf(path, text=None)

    report = inspect_pdf_text(path)

    assert report.pages == 1
    assert report.pages_with_text == 0
    assert report.total_chars == 0
    assert report.usable is False
    assert "sem texto" in report.summary().casefold()


def test_inspect_pdf_text_reports_missing_file(tmp_path):
    with pytest.raises(ValueError, match="source PDF"):
        inspect_pdf_text(tmp_path / "missing.pdf")
```

- [x] **Step 2: Run tests to verify they fail**

Run: `python -m pytest -q tools/loops/tests/test_source_quality.py`

Expected: FAIL during import because `tools.loops.source_quality` does not exist.

- [x] **Step 3: Implement the minimal inspector**

```python
from dataclasses import dataclass
from pathlib import Path

import fitz


@dataclass(frozen=True)
class PdfTextReport:
    path: str
    pages: int
    pages_with_text: int
    total_chars: int
    max_page_chars: int

    @property
    def usable(self):
        return self.total_chars > 0 and self.pages_with_text > 0

    def summary(self):
        status = "texto extraível" if self.usable else "PDF sem texto extraível"
        return (
            f"{status}; páginas={self.pages}; páginas_com_texto={self.pages_with_text}; "
            f"caracteres={self.total_chars}; máximo_por_página={self.max_page_chars}"
        )


def inspect_pdf_text(path: Path):
    path = Path(path)
    if not path.is_file() or path.suffix.casefold() != ".pdf":
        raise ValueError(f"source PDF is missing or invalid: {path}")
    try:
        with fitz.open(path) as document:
            lengths = [len(page.get_text("text").strip()) for page in document]
    except Exception as error:
        raise ValueError(f"source PDF cannot be inspected: {path}") from error
    return PdfTextReport(
        path=str(path),
        pages=len(lengths),
        pages_with_text=sum(length > 0 for length in lengths),
        total_chars=sum(lengths),
        max_page_chars=max(lengths, default=0),
    )
```

- [x] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -q tools/loops/tests/test_source_quality.py`

Expected: 3 passed.

- [x] **Step 5: Commit**

```powershell
git add tools/loops/source_quality.py tools/loops/tests/test_source_quality.py
git commit -m "feat: inspect local pdf text quality"
```

### Task 2: Gate selected sources before NotebookLM query

**Files:**
- Modify: `tools/loops/research_nlm.py:1-330`
- Modify: `tools/loops/__main__.py:214-225`
- Modify: `tools/loops/tests/test_research_nlm.py:19-130`

**Interfaces:**
- `NlmCliAdapter(..., source_root=Path(...))` uses `source_root` to resolve catalog paths.
- `NlmCliAdapter.list_ready_sources_for_paths()` raises `NlmEvidenceRequired` for a non-usable PDF before `query()` is called.

- [x] **Step 1: Write the failing integration tests**

Add a catalog PDF path and create a one-page image-only PDF in the test fixture. Add:

```python
def test_scoped_image_only_pdf_parks_before_notebook_query(tmp_path):
    adapter, runner = make_adapter(tmp_path, [{"id": "src-ok", "title": "Norma teste", "status": 2}])
    image_path = tmp_path / "01_TESTE" / "norma-teste.pdf"
    image_path.parent.mkdir()
    document = fitz.open()
    document.new_page()
    document.save(image_path)
    document.close()
    adapter.source_root = tmp_path

    with pytest.raises(NlmEvidenceRequired, match="texto extraível") as error:
        adapter.list_ready_sources_for_paths("nb-1", ("01_TESTE/norma-teste.pdf",))

    assert error.value.manual_request_path == str(tmp_path / "manual-source-requests.md")
    assert "páginas=1" in (tmp_path / "manual-source-requests.md").read_text(encoding="utf-8")
    assert not any(call[:3] == ("nlm", "notebook", "query") for call in runner.calls)
```

The test adapter uses the temporary directory as `source_root`; production catalog data remains unchanged.

- [x] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest -q tools/loops/tests/test_research_nlm.py -k image_only`

Expected: FAIL because `NlmCliAdapter` does not inspect the selected PDF or expose `source_root`.

- [x] **Step 3: Implement the source-root resolution and gate**

Add `source_root=Path("fontes")` to the adapter constructor. Resolve only normalized catalog paths below that root. After matching a ready source, for each PDF call `inspect_pdf_text`; if unusable, write a manual request whose reason includes the report summary and raise `NlmEvidenceRequired`. If inspection raises, write the same request with the error and raise. Keep non-PDF selection unchanged.

Update `_build_deps()` to pass `source_root=root / "fontes"`.

- [x] **Step 4: Run the focused integration tests**

Run: `python -m pytest -q tools/loops/tests/test_research_nlm.py -k "image_only or list_ready_sources_for_paths or query_passes_only"`

Expected: all selected tests pass and no query call is recorded for the image-only PDF.

- [x] **Step 5: Run the complete loop suite**

Run: `python -m pytest -q tools/loops/tests`

Expected: all tests pass with no new warnings.

- [x] **Step 6: Commit**

```powershell
git add tools/loops/research_nlm.py tools/loops/__main__.py tools/loops/tests/test_research_nlm.py
git commit -m "feat: park pdf sources without extractable text"
```

### Task 3: Document and verify the real NBR 6122 behavior

**Files:**
- Modify: `tools/README.md`
- Modify: `fontes/pendencias-atualizacao.md` (local ignored operational record)
- Modify: `sessions/2026-08-13.md` (ignored session record)

**Interfaces:**
- Documentation states that PDF quality is checked before NotebookLM query.

- [x] **Step 1: Add the README contract**

Document that status `2` is not sufficient: PDF sources must also contain extractable text locally, and the loop parks the candidate with page/character metrics otherwise.

- [x] **Step 2: Run the real diagnostic**

Run:

```powershell
python -c "from pathlib import Path; from tools.loops.source_quality import inspect_pdf_text; print(inspect_pdf_text(Path('fontes/03_FUNDACOES_GEOTECNIA/FUNDACOES__NBR__NBR-6122-2022__projeto-fundacoes.pdf')).summary())"
```

Expected: 120 pages, 0 pages with text, 0 characters, and a non-usable diagnosis.

- [x] **Step 3: Re-run the real dry-run with valid login**

Run `nlm login --check`, then the same scoped dry-run for task `4389afbe93fb` with `--retry-blocked` and broad candidates excluded.

Expected: `manual_source_required` without a new NotebookLM query artifact for the NBR 6122 source.

- [x] **Step 4: Run final verification**

Run `python -m pytest -q tools/loops/tests`, `python -m py_compile tools/loops/source_quality.py tools/loops/research_nlm.py tools/loops/__main__.py`, and `git diff --check`.

- [x] **Step 5: Commit documentation and record the phase**

```powershell
git add tools/README.md
git commit -m "docs: document local source quality gate"
```

Keep ignored operational records updated without staging them.
