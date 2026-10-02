from pathlib import Path

from pypdf import PdfReader


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PDF_PATH = PROJECT_ROOT / "data" / "documents" / "NMAMIT_Complete_College_Information_Guide.pdf"


def extract_text_from_pdf(pdf_path):
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(
            f"PDF not found at '{path}'. Place the PDF in the project data/documents folder "
            "or pass the correct file path."
        )

    reader = PdfReader(str(path))
    all_text = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            all_text.append(text)
        print(f"Processed page {page_number}")

    return "\n".join(all_text)


if __name__ == "__main__":
    print("Looking for PDF at:")
    print(PDF_PATH)

    text = extract_text_from_pdf(PDF_PATH)

    print("\n" + "=" * 60)
    print("PDF TEXT EXTRACTION COMPLETED")
    print("=" * 60)
    print(f"\nTotal characters extracted: {len(text)}")
    print("\nFirst 2000 characters:")
    print(text[:2000])