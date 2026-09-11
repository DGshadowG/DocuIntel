"""Text extraction for PDF, DOCX and TXT + upload validation helpers."""
import io
import re
from typing import List, Tuple

from docx import Document as DocxDocument
from pypdf import PdfReader

from app.core.errors import AppError

# Magic-number signatures for real content validation (extension alone is spoofable)
PDF_MAGIC = b"%PDF-"
ZIP_MAGIC = b"PK\x03\x04"  # docx is a zip container

MIME_BY_TYPE = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
}


class ExtractionError(Exception):
    pass


def sanitize_filename(name: str) -> str:
    """Keep only the base name and safe characters — neutralizes path traversal."""
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^\w.\- ()áéíóúÁÉÍÓÚñÑ]", "_", name).strip()
    return name[:200] or "documento"


def detect_file_type(filename: str, content: bytes) -> str:
    """Validate extension AND magic numbers; raise AppError(400) on mismatch."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "docx", "txt"):
        raise AppError(400, "invalid_format", f"Formato no permitido: .{ext or '?'} (solo PDF, DOCX, TXT)")
    if ext == "pdf" and not content.startswith(PDF_MAGIC):
        raise AppError(400, "invalid_content", "El archivo no es un PDF valido (firma incorrecta)")
    if ext == "docx" and not content.startswith(ZIP_MAGIC):
        raise AppError(400, "invalid_content", "El archivo no es un DOCX valido (firma incorrecta)")
    if ext == "txt":
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content.decode("latin-1")
            except UnicodeDecodeError:
                raise AppError(400, "invalid_content", "El archivo TXT no contiene texto legible")
    return ext


def extract_text(content: bytes, file_type: str) -> Tuple[str, int, List[Tuple[int, int]]]:
    """Return (full_text, page_count, page_offsets).

    page_offsets: list of (page_number, start_char_in_full_text) used later to
    map chunks back to their page for citations.
    """
    if file_type == "pdf":
        return _extract_pdf(content)
    if file_type == "docx":
        return _extract_docx(content)
    if file_type == "txt":
        return _extract_txt(content)
    raise ExtractionError(f"Tipo de archivo no soportado: {file_type}")


def _extract_pdf(content: bytes):
    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:
        raise ExtractionError(f"PDF ilegible o corrupto: {exc}")
    pages_text = []
    offsets = []
    cursor = 0
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        offsets.append((i, cursor))
        pages_text.append(text)
        cursor += len(text) + 1
    full = "\n".join(pages_text)
    if not full.strip():
        raise ExtractionError(
            "El PDF no contiene texto extraible (posiblemente escaneado). "
            "OCR no esta habilitado en este despliegue."
        )
    return _normalize_text(full), len(reader.pages), offsets


def _extract_docx(content: bytes):
    try:
        doc = DocxDocument(io.BytesIO(content))
    except Exception as exc:
        raise ExtractionError(f"DOCX ilegible o corrupto: {exc}")
    parts = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text for cell in row.cells))
    full = "\n".join(parts)
    if not full.strip():
        raise ExtractionError("El documento DOCX esta vacio")
    return _normalize_text(full), 1, [(1, 0)]


def _extract_txt(content: bytes):
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    if not text.strip():
        raise ExtractionError("El archivo TXT esta vacio")
    return _normalize_text(text), 1, [(1, 0)]


def _normalize_text(text: str) -> str:
    """Normalize whitespace while keeping line structure meaningful."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()
