from openai import OpenAI
import numpy as np
from pypdf import PdfReader
import faiss
import pickle
import os

client = OpenAI()

INDEX_FILE = "faiss_index.bin"
CHUNKS_FILE = "chunks.pkl"

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
        model="text-embedding-3-small",
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
    faiss.write_index(index, INDEX_FILE)
    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump(chunks, f)


# -------------------------------
# Load data
# -------------------------------
def load_data():
    index = faiss.read_index(INDEX_FILE)
    with open(CHUNKS_FILE, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks


# -------------------------------
# Initialize system
# -------------------------------
def initialize():
    if os.path.exists(INDEX_FILE) and os.path.exists(CHUNKS_FILE):
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
        model="gpt-4.1-mini",
        input=prompt,
        max_output_tokens=200
    )

    return response.output_text