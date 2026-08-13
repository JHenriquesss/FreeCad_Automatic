"""Local, read-only quality checks for NotebookLM source files."""

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


def inspect_pdf_text(path: Path) -> PdfTextReport:
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
