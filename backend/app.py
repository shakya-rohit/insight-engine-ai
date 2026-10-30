from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from config import MAX_PDF_PAGES, MAX_UPLOAD_BYTES, UPLOAD_DIR
from rag_faiss import initialize, ask_rag, add_document
from hybrid_rag import hybrid_answer
from kg_layer import update_kg, query_kg

from pathlib import Path
import uuid

app = FastAPI(title="RAG API")

# -------------------------------
# Load system ONCE
# -------------------------------
print("🚀 Initializing RAG system...")
index, chunks = initialize()
print("✅ RAG ready!\n")


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
    else:
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

    global index, chunks

    old_len = len(chunks)

    try:
        index, chunks = add_document(
            file_path, index, chunks, source_name=original_filename
        )
    except ValueError as exc:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 🔥 ONLY new chunks → KG
    new_chunks = chunks[old_len:]
    update_kg(new_chunks[:20])  # limit for cost

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
