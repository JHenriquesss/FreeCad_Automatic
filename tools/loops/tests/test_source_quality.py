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
