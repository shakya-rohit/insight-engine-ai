"""Upload validation and document indexing workflow."""

from datetime import datetime, timezone
import logging
from pathlib import Path
import uuid

from pypdf import PdfReader

from config import MAX_PDF_PAGES, MAX_UPLOAD_BYTES, UPLOAD_DIR
from document_store import save_document
from kg_layer import update_kg
from rag_faiss import add_document

logger = logging.getLogger(__name__)


class DocumentProcessingError(Exception):
    """Expected upload failure with an HTTP status for the API layer."""

    def __init__(self, detail: str, status_code: int):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def process_upload(source, filename, index, chunks):
    """Validate, persist, index, and add an uploaded PDF or TXT to the graph."""
    original_filename = (filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    extension = Path(original_filename).suffix.lower()
    if extension not in {".pdf", ".txt"}:
        raise DocumentProcessingError("Only PDF and TXT files are accepted", 415)
    if len(original_filename) > 255:
        raise DocumentProcessingError("Filename is too long", 400)

    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    try:
        with source, open(file_path, "xb") as destination:
            prefix = source.read(1024 if extension == ".pdf" else 0)
            if extension == ".pdf" and b"%PDF-" not in prefix:
                raise DocumentProcessingError("File is not a valid PDF", 415)
            if len(prefix) > MAX_UPLOAD_BYTES:
                raise DocumentProcessingError("File exceeds the upload size limit", 413)

            destination.write(prefix)
            total_bytes = len(prefix)
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                if total_bytes + len(chunk) > MAX_UPLOAD_BYTES:
                    raise DocumentProcessingError(
                        "File exceeds the upload size limit", 413
                    )
                destination.write(chunk)
                total_bytes += len(chunk)
    except Exception:
        file_path.unlink(missing_ok=True)
        raise

    try:
        if extension == ".pdf":
            _validate_pdf(file_path)
        else:
            _validate_txt(file_path)

        old_chunk_count = len(chunks)
        index, chunks = add_document(
            file_path, index, chunks, source_name=original_filename
        )
    except DocumentProcessingError:
        file_path.unlink(missing_ok=True)
        raise
    except ValueError as exc:
        file_path.unlink(missing_ok=True)
        raise DocumentProcessingError(str(exc), 422) from exc
    except Exception:
        logger.exception("Document processing failed id=%s", file_path.stem)
        raise

    new_chunks = chunks[old_chunk_count:]
    save_document({
        "id": file_path.name,
        "name": original_filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(
        "Indexed document id=%s type=%s size_bytes=%d chunks_added=%d",
        file_path.stem,
        extension,
        total_bytes,
        len(new_chunks),
    )

    update_kg(new_chunks[:20])
    logger.info(
        "Knowledge graph update completed document_id=%s chunks_processed=%d",
        file_path.stem,
        min(len(new_chunks), 20),
    )

    return index, chunks, {
        "message": f"{original_filename} added",
        "total_chunks": len(chunks),
    }


def _validate_pdf(file_path: Path) -> None:
    try:
        reader = PdfReader(file_path)
        if reader.is_encrypted:
            raise DocumentProcessingError("Encrypted PDFs are not supported", 415)
        page_count = len(reader.pages)
    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError("PDF is invalid or unreadable", 415) from exc

    if page_count == 0:
        raise DocumentProcessingError("PDF contains no pages", 422)
    if page_count > MAX_PDF_PAGES:
        raise DocumentProcessingError(
            f"PDF exceeds the {MAX_PDF_PAGES}-page limit", 413
        )


def _validate_txt(file_path: Path) -> None:
    try:
        text = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentProcessingError("TXT files must use UTF-8 encoding", 415) from exc
    if "\x00" in text:
        raise DocumentProcessingError("TXT files must contain UTF-8 text", 415)
