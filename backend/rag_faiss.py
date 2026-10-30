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
from pathlib import Path
import logging
from textwrap import dedent

logger = logging.getLogger(__name__)
client = OpenAI()

# Extract selectable text from each page of a PDF.
def load_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"

    return text


# Normalize whitespace before splitting text into chunks.
def clean_text(text):
    return " ".join(text.split())


# Keep adjacent chunks slightly overlapping to preserve boundary context.
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


# Create a vector embedding with the configured OpenAI model.
def get_embedding(text):
    response = client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=text
    )
    return np.array(response.data[0].embedding, dtype="float32")


# Persist the FAISS index and its matching chunk metadata.
def save_data(index, chunks):
    faiss.write_index(index, str(INDEX_FILE))
    with open(CHUNKS_FILE, "wb") as f:
        pickle.dump(chunks, f)


# Load the persisted FAISS index and chunk metadata.
def load_data():
    index = faiss.read_index(str(INDEX_FILE))
    with open(CHUNKS_FILE, "rb") as f:
        chunks = pickle.load(f)
    return index, chunks


# Restore retrieval state or create an empty index on first run.
def initialize():
    if INDEX_FILE.exists() and CHUNKS_FILE.exists():
        index, chunks = load_data()
        logger.info("Loaded persisted vector index with %d chunks", len(chunks))
        return index, chunks

    logger.info("No persisted vector index found; creating an empty index")
    dim = 1536  # embedding size for text-embedding-3-small
    index = faiss.IndexFlatL2(dim)
    chunks = []

    return index, chunks


# Extract, embed, and persist all chunks from one uploaded document.
def add_document(file_path, index, chunks, source_name=None):
    extension = Path(file_path).suffix.lower()
    logger.info("Processing uploaded document type=%s", extension)

    if extension == ".pdf":
        text = load_pdf(file_path)
    elif extension == ".txt":
        try:
            text = Path(file_path).read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("TXT files must use UTF-8 encoding") from exc
    else:
        raise ValueError("Only PDF and TXT files can be indexed")

    text = clean_text(text)

    if not text:
        raise ValueError(
            "This document contains no extractable text and cannot be indexed."
        )

    new_chunks = chunk_text(text, source_name or os.path.basename(file_path))
    logger.info("Created %d text chunks from uploaded document", len(new_chunks))

    new_embeddings = [get_embedding(c["text"]) for c in new_chunks]

    index.add(np.array(new_embeddings))
    chunks.extend(new_chunks)

    save_data(index, chunks)

    return index, chunks


# Return the nearest valid chunks for a question.
def retrieve(query, index, chunks, k=3):
    available_chunks = min(index.ntotal, len(chunks))
    if available_chunks == 0 or k <= 0:
        return []

    query_embedding = get_embedding(query).reshape(1, -1)
    _, indices = index.search(query_embedding, min(k, available_chunks))

    return [chunks[i] for i in indices[0] if 0 <= i < len(chunks)]


# Generate an answer grounded in the retrieved document context.
def ask_rag(query, index, chunks):
    retrieved = retrieve(query, index, chunks)
    if not retrieved:
        return "I don't know."

    context = "\n\n".join(
        [f"[{c['source']}]: {c['text']}" for c in retrieved]
    )

    prompt = dedent("""\
        Answer using the context below.

        If the answer is not present, say "I don't know".

        Context:
        {context}

        Question:
        {query}
        """).format(context=context, query=query)

    response = client.responses.create(
        model=OPENAI_CHAT_MODEL,
        input=prompt,
        max_output_tokens=OPENAI_MAX_OUTPUT_TOKENS
    )

    return response.output_text
