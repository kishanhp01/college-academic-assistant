from pathlib import Path

import pytest

from app.pdf_loader import extract_text_from_pdf


def test_missing_pdf_has_helpful_error(tmp_path: Path):
    missing_pdf = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError, match="data/documents|PDF not found"):
        extract_text_from_pdf(missing_pdf)