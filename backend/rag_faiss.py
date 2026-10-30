from openai import OpenAI
from config import (
    CHUNKS_FILE,
    INDEX_FILE,
    OPENAI_CHAT_MODEL,
    OPENAI_EMBEDDING_MODEL,
    OPENAI_MAX_OUTPUT_TOKENS,
)
import numpy as np
from pypdf import PdfReader
import faiss
import pickle
import os

client = OpenAI()

# -------------------------------
# Load PDF
# -------------------------------
def load_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text


# -------------------------------
# Clean text
# -------------------------------
def clean_text(text):
    return " ".join(text.split())


# -------------------------------
# Chunk text (with metadata)
# -------------------------------
def chunk_text(text, source, chunk_size=500, overlap=100):
    chunks = []
    start = 0

    while start < len(text):
        chunk = text[start:start + chunk_size]
        chunks.append({
            "text": chunk,
            "source": source
        })
        start += chunk_size - overlap

    return chunks


# -------------------------------
# Get embedding
# -------------------------------
def get_embedding(text):
    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=text
    )
    return np.array(response.data[0].embedding, dtype="float32")


# -------------------------------
# Build FAISS index
# -------------------------------
def build_faiss_index(embeddings):
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings))
    return index


# -------------------------------
# Save data
# -------------------------------
def save_data(index, chunks):
    faiss.write_index(index, str(INDEX_FILE))
    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump(chunks, f)


# -------------------------------
# Load data
# -------------------------------
def load_data():
    index = faiss.read_index(str(INDEX_FILE))
    with open(CHUNKS_FILE, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks


# -------------------------------
# Initialize system
# -------------------------------
def initialize():
    if INDEX_FILE.exists() and CHUNKS_FILE.exists():
        print("⚡ Loading existing index...")
        return load_data()

    print("🆕 Creating new empty index...")
    dim = 1536  # embedding size for text-embedding-3-small
    index = faiss.IndexFlatL2(dim)
    chunks = []

    return index, chunks


# -------------------------------
# Add PDF to system (NEW)
# -------------------------------
def add_pdf(file_path, index, chunks):
    print(f"📄 Processing {file_path}...")

    text = load_pdf(file_path)
    text = clean_text(text)

    if not text:
        raise ValueError(
            "This PDF has no extractable text. It may be scanned or image-based; "
            "OCR is needed before it can be indexed."
        )

    new_chunks = chunk_text(text, os.path.basename(file_path))
    print(f"➕ New chunks: {len(new_chunks)}")

    new_embeddings = [get_embedding(c["text"]) for c in new_chunks]

    index.add(np.array(new_embeddings))
    chunks.extend(new_chunks)

    save_data(index, chunks)

    return index, chunks


# -------------------------------
# Retrieve
# -------------------------------
def retrieve(query, index, chunks, k=3):
    query_embedding = get_embedding(query).reshape(1, -1)
    distances, indices = index.search(query_embedding, k)

    return [chunks[i] for i in indices[0]]


# -------------------------------
# RAG pipeline
# -------------------------------
def ask_rag(query, index, chunks):
    retrieved = retrieve(query, index, chunks)

    context = "\n\n".join(
        [f"[{c['source']}]: {c['text']}" for c in retrieved]
    )

    prompt = f"""
Answer using the context below.

If the answer is not present, say "I don't know".

Context:
{context}

Question:
{query}
"""

    response = client.responses.create(
        model=OPENAI_CHAT_MODEL,
        input=prompt,
        max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS
    )

    return response.output_text
