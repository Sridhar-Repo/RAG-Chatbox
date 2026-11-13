import io
import re

from pypdf import PdfReader

from .config import settings


def extract_pages(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    """Return [(page_number_or_None, text)]. PDFs keep page numbers so we can cite them."""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    return [(None, data.decode("utf-8", errors="ignore"))]


def chunk_text(text: str, size: int | None = None, overlap: int | None = None) -> list[str]:
    size = size or settings.chunk_size
    overlap = settings.chunk_overlap if overlap is None else overlap
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        while len(para) > size:  # one huge paragraph: hard split
            if current:
                chunks.append(current)
                current = ""
            chunks.append(para[:size])
            para = para[size - overlap:]
        if len(current) + len(para) + 2 <= size:
            current = f"{current}\n\n{para}".strip()
        else:
            tail = current[-overlap:] if current else ""
            if current:
                chunks.append(current)
            current = f"{tail} {para}".strip()
    if current:
        chunks.append(current)
    return chunks


def build_chunks(filename: str, data: bytes) -> list[dict]:
    out = []
    for page, text in extract_pages(filename, data):
        for piece in chunk_text(text):
            out.append({"text": piece, "source": filename, "page": page or 0})
    return out
