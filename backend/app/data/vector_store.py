from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass
from typing import Any

_STORE = None

# Safe fallback dataset (used if JSON loading fails).
# This keeps the app runnable even if the external dataset is missing/malformed.
_FALLBACK_DOCS: list[dict] = [
    {
        "source": "demo-textbook",
        "grade": "9",
        "class_level": "9",
        "subject": "Science",
        "board": "State Board",
        "book_id": "science_foundation_book_1",
        "chapter": "Plant Biology",
        "topic": "Photosynthesis",
        "page": 12,
        "text": "Photosynthesis is the process by which plants make food using sunlight, carbon dioxide, and water.",
    },
    {
        "source": "demo-textbook",
        "grade": "9",
        "class_level": "9",
        "subject": "Science",
        "board": "State Board",
        "book_id": "science_foundation_book_1",
        "chapter": "Physics Basics",
        "topic": "Gravity",
        "page": 5,
        "text": "Gravity is the force that attracts objects toward the Earth.",
    },
]


def _load_demo_dataset_from_json() -> list[dict]:
    """
    Load a structured textbook dataset from disk (startup time).

    Expected format:
    - JSON list of objects with at least: text, chapter, page
    - Optional but recommended: topic, subject, grade, source

    Why load at startup:
    - Keeps request-time retrieval fast (docs already embedded and indexed).
    - Keeps the system beginner-friendly without adding a database yet.

    Why fallback exists:
    - The app must still start even if the JSON file is missing/malformed/empty.
    """
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "data" / "processed" / "demo_textbook.json"

    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
        if not isinstance(data, list):
            return []

        docs: list[dict] = []
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                print(f"[dataset] Skipping record #{idx}: not an object")
                continue
            text = str(item.get("text", "")).strip()
            chapter = str(item.get("chapter", "")).strip()
            page_raw = item.get("page", None)
            try:
                page = int(page_raw)
            except Exception:
                page = None

            # Minimal validation.
            if not text or not chapter or page is None:
                print(f"[dataset] Skipping record #{idx}: missing required fields (text/chapter/page)")
                continue

            # Fill defaults for optional fields so the rest of the system stays simple.
            source = item.get("source", "demo-textbook") or "demo-textbook"
            subject = item.get("subject", "Science") or "Science"
            grade = item.get("grade", "9") or "9"
            class_level = item.get("class_level", grade) or grade
            board = item.get("board", "State Board") or "State Board"
            book_id = item.get("book_id", "science_foundation_book_1") or "science_foundation_book_1"

            docs.append(
                {
                    "text": text,
                    "chapter": chapter,
                    "page": page,
                    "topic": item.get("topic"),
                    "subject": subject,
                    "grade": grade,
                    "class_level": class_level,
                    "board": board,
                    "book_id": book_id,
                    "source": source,
                }
            )
        return docs
    except Exception:
        return []


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """
    Cosine similarity using numpy (with a small pure-Python fallback).
    """
    if not a or not b:
        return 0.0

    try:
        from numpy import dot  # type: ignore
        from numpy.linalg import norm  # type: ignore

        return float(dot(a, b) / (norm(a) * norm(b)))
    except Exception:
        # Fallback if numpy isn't available yet.
        n = min(len(a), len(b))
        d = 0.0
        na = 0.0
        nb = 0.0
        for i in range(n):
            d += a[i] * b[i]
            na += a[i] * a[i]
            nb += b[i] * b[i]
        denom = (na**0.5) * (nb**0.5)
        return (d / denom) if denom else 0.0


@dataclass
class StoredDoc:
    text: str
    embedding: list[float]
    metadata: dict[str, Any]


class VectorStore:
    """
    In-memory vector store for the MVP.

    - Stores: embeddings + text + metadata
    - Supports: add_documents() and search()

    This keeps everything local and beginner-friendly.
    """

    def __init__(self) -> None:
        self._docs: list[StoredDoc] = []

    def clear(self) -> None:
        self._docs = []

    def add_documents(self, docs: list[dict]) -> None:
        from app.llm.provider import get_embedding

        for d in docs:
            text = str(d.get("text", "")).strip()
            if not text:
                continue
            emb = get_embedding(text)
            # Preserve structured metadata so we can provide citations and support filters.
            md = {
                "source": d.get("source", "demo-textbook"),
                "grade": d.get("grade"),
                "class_level": d.get("class_level"),
                "subject": d.get("subject"),
                "board": d.get("board"),
                "book_id": d.get("book_id"),
                "chapter": d.get("chapter"),
                "topic": d.get("topic"),
                "page": d.get("page"),
            }
            self._docs.append(StoredDoc(text=text, embedding=emb, metadata=md))

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        from app.llm.provider import get_embedding

        if not self._docs:
            return []

        q_emb = get_embedding(query)
        try:
            from numpy.linalg import norm  # type: ignore

            print("Query embedding norm:", float(norm(q_emb)))
        except Exception:
            # If numpy isn't installed, we skip norm debug.
            pass

        scored: list[tuple[float, StoredDoc]] = []
        for doc in self._docs:
            score = _cosine_similarity(q_emb, doc.embedding)
            scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)

        if scored:
            print("Top score:", float(scored[0][0]))

        results: list[dict] = []
        for score, doc in scored[: max(1, top_k)]:
            results.append(
                {
                    "text": doc.text,
                    "source": doc.metadata.get("source", "demo-textbook"),
                    "grade": doc.metadata.get("grade"),
                    "class_level": doc.metadata.get("class_level"),
                    "subject": doc.metadata.get("subject"),
                    "board": doc.metadata.get("board"),
                    "book_id": doc.metadata.get("book_id"),
                    "chapter": doc.metadata.get("chapter"),
                    "topic": doc.metadata.get("topic"),
                    "page": doc.metadata.get("page"),
                    "score": float(score),
                }
            )
        return results


def initialize_vector_store(docs: list[dict] | None = None) -> VectorStore:
    """
    Create (or return) a global vector store instance.

    If `docs` are provided, they are embedded and loaded into the store.
    This allows us to ingest textbook content from files at startup.
    """
    global _STORE
    if _STORE is None:
        _STORE = VectorStore()
    if docs is None:
        # Default startup path: load from disk with safe fallback.
        loaded = _load_demo_dataset_from_json()
        docs = loaded if loaded else _FALLBACK_DOCS

    _STORE.clear()
    _STORE.add_documents(docs)
    return _STORE