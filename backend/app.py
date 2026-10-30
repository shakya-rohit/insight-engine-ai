from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from config import DOCUMENTS_FILE, MAX_PDF_PAGES, MAX_UPLOAD_BYTES, UPLOAD_DIR
from rag_faiss import initialize, ask_rag, add_document
from hybrid_rag import hybrid_answer
from kg_layer import update_kg, query_kg

from pathlib import Path
from datetime import datetime, timezone
import json
import logging
import uuid

logger = logging.getLogger(__name__)

app = FastAPI(title="RAG API")

# -------------------------------
# Load system ONCE
# -------------------------------
logger.info("Initializing retrieval system")
index, chunks = initialize()
logger.info("Retrieval system ready with %d indexed chunks", len(chunks))


# -------------------------------
# Request schema
# -------------------------------
class QueryRequest(BaseModel):
    question: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------
# Health
# -------------------------------
@app.get("/")
def home():
    return {"message": "RAG API running 🚀"}


def read_documents():
    """Load persisted document metadata and include files from older uploads."""
    try:
        payload = json.loads(DOCUMENTS_FILE.read_text(encoding="utf-8"))
        documents = payload.get("documents", []) if isinstance(payload, dict) else []
        documents = [
            doc for doc in documents
            if isinstance(doc, dict)
            and isinstance(doc.get("id"), str)
            and isinstance(doc.get("name"), str)
        ] if isinstance(documents, list) else []
    except (OSError, json.JSONDecodeError):
        documents = []

    known_ids = {doc.get("id") for doc in documents if isinstance(doc, dict)}
    for path in UPLOAD_DIR.iterdir():
        if path.is_file() and path.name not in known_ids:
            uploaded_at = datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).isoformat()
            documents.append({
                "id": path.name,
                "name": path.name,
                "uploaded_at": uploaded_at,
            })

    return sorted(
        documents,
        key=lambda doc: str(doc.get("uploaded_at", "")),
        reverse=True,
    )


def save_document_metadata(document):
    documents = read_documents()
    documents = [doc for doc in documents if doc.get("id") != document["id"]]
    documents.append(document)

    temporary_file = DOCUMENTS_FILE.with_name(f".{uuid.uuid4().hex}.tmp")
    temporary_file.write_text(
        json.dumps({"documents": documents}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_file.replace(DOCUMENTS_FILE)


@app.get("/documents")
def get_documents():
    return {"documents": read_documents()}


# -------------------------------
# Upload (APPEND, NOT RESET)
# -------------------------------
@app.post("/upload")
def upload_document(file: UploadFile = File(...)):
    original_filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    extension = Path(original_filename).suffix.lower()
    if extension not in {".pdf", ".txt"}:
        raise HTTPException(status_code=415, detail="Only PDF and TXT files are accepted")
    if len(original_filename) > 255:
        raise HTTPException(status_code=400, detail="Filename is too long")

    # Use a server-generated name so client filenames cannot overwrite uploads.
    file_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    try:
        with file.file as source, open(file_path, "xb") as destination:
            prefix = source.read(1024 if extension == ".pdf" else 0)
            if extension == ".pdf" and b"%PDF-" not in prefix:
                raise HTTPException(status_code=415, detail="File is not a valid PDF")
            if len(prefix) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="File exceeds the upload size limit")

            destination.write(prefix)
            total_bytes = len(prefix)
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                if total_bytes + len(chunk) > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File exceeds the upload size limit")
                destination.write(chunk)
                total_bytes += len(chunk)
    except HTTPException:
        file_path.unlink(missing_ok=True)
        raise
    except OSError:
        file_path.unlink(missing_ok=True)
        raise

    logger.info(
        "Validated document upload id=%s type=%s size_bytes=%d",
        file_path.stem,
        extension,
        total_bytes,
    )

    if extension == ".pdf":
        try:
            reader = PdfReader(file_path)
            if reader.is_encrypted:
                raise HTTPException(status_code=415, detail="Encrypted PDFs are not supported")
            page_count = len(reader.pages)
            if page_count == 0:
                raise HTTPException(status_code=422, detail="PDF contains no pages")
            if page_count > MAX_PDF_PAGES:
                raise HTTPException(
                    status_code=413,
                    detail=f"PDF exceeds the {MAX_PDF_PAGES}-page limit",
                )
        except HTTPException:
            file_path.unlink(missing_ok=True)
            raise
        except Exception as exc:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=415, detail="PDF is invalid or unreadable") from exc
    elif extension == ".txt":
        try:
            text = file_path.read_text(encoding="utf-8-sig")
            if "\x00" in text:
                raise HTTPException(status_code=415, detail="TXT files must contain UTF-8 text")
        except UnicodeDecodeError as exc:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=415, detail="TXT files must use UTF-8 encoding") from exc
        except HTTPException:
            file_path.unlink(missing_ok=True)
            raise
    else:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=415, detail="Only PDF and TXT files are accepted")

    global index, chunks

    old_len = len(chunks)

    try:
        index, chunks = add_document(
            file_path, index, chunks, source_name=original_filename
        )
    except ValueError as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    save_document_metadata({
        "id": file_path.name,
        "name": original_filename,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    logger.info(
        "Indexed document id=%s type=%s chunks_added=%d",
        file_path.stem,
        extension,
        len(chunks) - old_len,
    )

    # 🔥 ONLY new chunks → KG
    new_chunks = chunks[old_len:]
    update_kg(new_chunks[:20])  # limit for cost
    logger.info(
        "Knowledge graph update completed document_id=%s chunks_processed=%d",
        file_path.stem,
        min(len(new_chunks), 20),
    )

    return {
        "message": f"{original_filename} added",
        "total_chunks": len(chunks)
    }


# -------------------------------
# Query
# -------------------------------
@app.post("/ask")
def ask_question(request: QueryRequest):
    answer = ask_rag(request.question, index, chunks)

    return {
        "question": request.question,
        "answer": answer
    }

@app.post("/hybrid-ask")
def hybrid_query(request: QueryRequest):
    answer = hybrid_answer(request.question, index, chunks)

    return {
        "question": request.question,
        "answer": answer
    }

@app.post("/kg-query")
def kg_query(request: QueryRequest):
    results = query_kg(request.question)

    return {
        "question": request.question,
        "kg_results": results
    }
