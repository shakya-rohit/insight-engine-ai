from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from rag_faiss import initialize, ask_rag, add_pdf
from hybrid_rag import hybrid_answer
from kg_layer import update_kg, query_kg

import shutil
import os

app = FastAPI(title="RAG API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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
def upload_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    global index, chunks

    old_len = len(chunks)

    index, chunks = add_pdf(file_path, index, chunks)

    # 🔥 ONLY new chunks → KG
    new_chunks = chunks[old_len:]
    update_kg(new_chunks[:20])  # limit for cost

    return {
        "message": f"{file.filename} added",
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