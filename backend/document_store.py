"""Persistence helpers for the uploaded-document list."""

from datetime import datetime, timezone
import json
import uuid

from config import DOCUMENTS_FILE, UPLOAD_DIR


def load_documents():
    """Load saved metadata and include uploads created before metadata tracking."""
    try:
        payload = json.loads(DOCUMENTS_FILE.read_text(encoding="utf-8"))
        documents = payload.get("documents", []) if isinstance(payload, dict) else []
        if not isinstance(documents, list):
            documents = []
        documents = [
            document
            for document in documents
            if isinstance(document, dict)
            and isinstance(document.get("id"), str)
            and isinstance(document.get("name"), str)
        ]
    except (OSError, json.JSONDecodeError):
        documents = []

    known_ids = {document["id"] for document in documents}
    for path in UPLOAD_DIR.iterdir():
        if path.is_file() and path.name not in known_ids:
            documents.append({
                "id": path.name,
                "name": path.name,
                "uploaded_at": datetime.fromtimestamp(
                    path.stat().st_mtime, tz=timezone.utc
                ).isoformat(),
            })

    return sorted(
        documents,
        key=lambda document: str(document.get("uploaded_at", "")),
        reverse=True,
    )


def save_document(document):
    """Persist one document record, replacing an existing record with its ID."""
    documents = [item for item in load_documents() if item.get("id") != document["id"]]
    documents.append(document)

    temporary_file = DOCUMENTS_FILE.with_name(f".{uuid.uuid4().hex}.tmp")
    temporary_file.write_text(
        json.dumps({"documents": documents}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_file.replace(DOCUMENTS_FILE)
