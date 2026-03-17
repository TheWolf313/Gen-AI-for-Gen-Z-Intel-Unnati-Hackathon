from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_STORE = None

SAMPLE_DOCS = [
    # Photosynthesis (expanded with semantic variations + richer context)
    {
        "text": (
            "Photosynthesis is the process by which plants make food using sunlight, carbon dioxide, and water. "
            "Plants use carbon dioxide and water to produce glucose (food) and release oxygen."
        ),
        "chapter": "Plant Biology",
        "page": 12,
    },
    {
        "text": "Plants make their own food using sunlight in a process called photosynthesis.",
        "chapter": "Plant Biology",
        "page": 12,
    },
    {
        "text": "Photosynthesis allows plants to produce food from sunlight, water, and carbon dioxide.",
        "chapter": "Plant Biology",
        "page": 12,
    },
    {
        "text": "Food production in plants happens through photosynthesis.",
        "chapter": "Plant Biology",
        "page": 12,
    },
    {
        "text": (
            "In photosynthesis, green plants prepare their own food. "
            "Sunlight provides energy, and carbon dioxide plus water are used to form glucose; oxygen is produced."
        ),
        "chapter": "Plant Biology",
        "page": 13,
    },
    # Gravity (expanded with semantic variations + richer context)
    {
        "text": (
            "Gravity is the force that attracts objects toward the Earth. "
            "It makes objects fall downward and keeps planets in orbit around the Sun."
        ),
        "chapter": "Physics Basics",
        "page": 5,
    },
    {
        "text": "Gravity pulls objects toward the Earth, which is why things fall when dropped.",
        "chapter": "Physics Basics",
        "page": 5,
    },
    {
        "text": "The force of attraction between masses is called gravity.",
        "chapter": "Physics Basics",
        "page": 6,
    },
    {
        "text": "Gravity is the Earth’s pulling force that acts on all objects with mass.",
        "chapter": "Physics Basics",
        "page": 6,
    },
]


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

    def add_documents(self, docs: list[dict]) -> None:
        from app.llm.provider import get_embedding

        for d in docs:
            text = str(d.get("text", "")).strip()
            if not text:
                continue
            emb = get_embedding(text)
            md = {"chapter": d.get("chapter"), "page": d.get("page")}
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
                    "chapter": doc.metadata.get("chapter"),
                    "page": doc.metadata.get("page"),
                    "score": float(score),
                }
            )
        return results


def initialize_vector_store() -> VectorStore:
    """
    Create (or return) a global vector store instance and preload sample docs.
    """
    global _STORE
    if _STORE is None:
        _STORE = VectorStore()
        _STORE.add_documents(SAMPLE_DOCS)
    return _STORE