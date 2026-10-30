from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from document_store import load_documents
from document_processing import DocumentProcessingError, process_upload
from rag_faiss import initialize, ask_rag
from hybrid_rag import hybrid_answer
from kg_layer import query_kg

import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="RAG API")

# Load the persisted index once for this API process.
logger.info("Initializing retrieval system")
index, chunks = initialize()
logger.info("Retrieval system ready with %d indexed chunks", len(chunks))


# Shared request body for the question endpoints.
class QueryRequest(BaseModel):
    question: str


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Report that the API process is responding.
@app.get("/")
def home():
    return {"message": "RAG API running 🚀"}


# Return saved uploads so the sidebar can restore its list after refresh.
@app.get("/documents")
def get_documents():
    return {"documents": load_documents()}


# Validate and index one uploaded PDF or TXT document.
@app.post("/upload")
def upload_document(file: UploadFile = File(...)):
    global index, chunks
    try:
        index, chunks, result = process_upload(
            file.file, file.filename, index, chunks
        )
    except DocumentProcessingError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return result


# Answer with semantic document retrieval.
@app.post("/ask")
def ask_question(request: QueryRequest):
    answer = ask_rag(request.question, index, chunks)

    return {
        "question": request.question,
        "answer": answer
    }

# Combine vector matches and graph facts for a single answer.
@app.post("/hybrid-ask")
def hybrid_query(request: QueryRequest):
    answer = hybrid_answer(request.question, index, chunks)

    return {
        "question": request.question,
        "answer": answer
    }

# Return graph facts ranked against the question.
@app.post("/kg-query")
def kg_query(request: QueryRequest):
    results = query_kg(request.question)

    return {
        "question": request.question,
        "kg_results": results
    }
