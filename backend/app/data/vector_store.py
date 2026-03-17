from __future__ import annotations


class VectorStore:
    """
    Minimal Vector Store interface placeholder.

    Later this will wrap FAISS or Chroma and support:
    - adding embeddings for textbook blocks
    - metadata filtering (grade/subject/chapter)
    - similarity search + re-ranking

    For now, it returns a few hard-coded "hits" so the app runs end-to-end.
    """

    def search(self, *, question: str, k: int = 3, grade: str | None = None, subject: str | None = None) -> list[dict]:
        # In a real implementation, this would do embedding search.
        base = [
            {
                "source": "demo-textbook",
                "chapter": "Chapter 1",
                "page": 1,
                "snippet": "Key idea: Start from basic definitions and build intuition step by step.",
            },
            {
                "source": "demo-textbook",
                "chapter": "Chapter 2",
                "page": 5,
                "snippet": "Example pattern: Identify given values → apply formula → simplify → final answer.",
            },
            {
                "source": "demo-textbook",
                "chapter": "Chapter 3",
                "page": 12,
                "snippet": "Exam tip: Write the definition first, then add one short example.",
            },
        ]

        # Very small "personalization" demo: tweak snippet labels if metadata exists.
        prefix = []
        if grade:
            prefix.append(f"Grade {grade}")
        if subject:
            prefix.append(subject)
        label = " / ".join(prefix)

        hits = base[: max(1, min(k, len(base)))]
        if label:
            for h in hits:
                h["snippet"] = f"[{label}] {h['snippet']}"
        return hits

