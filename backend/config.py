"""Environment-backed configuration for the InsightEngine backend."""

import os
from pathlib import Path

from dotenv import load_dotenv


# Load the backend's .env regardless of the directory used to start Uvicorn.
load_dotenv(Path(__file__).with_name(".env"))

OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
)
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "200"))
