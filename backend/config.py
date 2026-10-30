"""Environment-backed configuration for the InsightEngine backend."""

import os
from pathlib import Path

from dotenv import load_dotenv


# Load the backend's .env regardless of the directory used to start Uvicorn.
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

# Runtime files live outside the source modules and are excluded from Git.
DATA_DIR = BACKEND_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
INDEX_FILE = DATA_DIR / "faiss_index.bin"
CHUNKS_FILE = DATA_DIR / "chunks.pkl"
KG_FILE = DATA_DIR / "kg.pkl"
DOCUMENTS_FILE = DATA_DIR / "documents.json"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "200"))
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(20 * 1024 * 1024)))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "500"))

if MAX_UPLOAD_BYTES < 1 or MAX_PDF_PAGES < 1:
    raise ValueError("MAX_UPLOAD_BYTES and MAX_PDF_PAGES must be positive integers")
