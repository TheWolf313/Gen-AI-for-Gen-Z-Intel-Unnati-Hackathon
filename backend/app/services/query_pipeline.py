from __future__ import annotations

from app.data.vector_store import VectorStore


def normalize_query(question: str) -> str:
    """
    Normalize user input for consistent matching.

    Rules:
    - lowercase
    - strip leading/trailing whitespace
    - collapse extra internal spaces
    """
    q = (question or "").lower().strip()
    q = " ".join(q.split())
    return q


knowledge_base: dict[str, dict] = {
    "photosynthesis": {
        "answer": "Photosynthesis is the process by which plants make food using sunlight, carbon dioxide, and water.",
        "chapter": "Plant Biology",
        "page": 12,
    },
    "gravity": {
        "answer": "Gravity is the force that attracts objects toward the Earth.",
        "chapter": "Physics Basics",
        "page": 5,
    },
}


def retrieve_answer(query: str) -> dict:
    """
    Simulated retrieval.

    Logic:
    - If a knowledge_base keyword exists in the query, return that entry.
    - Otherwise return a fallback response.
    """
    for keyword, data in knowledge_base.items():
        if keyword in query:
            return {"found": True, "keyword": keyword, **data}

    return {
        "found": False,
        "keyword": None,
        "answer": "I could not find relevant information in the textbook.",
        "chapter": "N/A",
        "page": 0,
    }


def run_query_pipeline(
    *,
    question: str,
    user_id: str | None = None,
    grade: str | None = None,
    subject: str | None = None,
    language: str | None = None,
) -> dict:
    """
    Query pipeline placeholder.

    This is where the real system will eventually do:
    - query normalization (Hindi/English)
    - retrieval from vector DB
    - context pruning
    - LLM generation

    For now it is intentionally simple and runnable:
    User Query -> Dummy Retrieval -> Dummy Response
    """
    normalized = normalize_query(question)
    retrieved = retrieve_answer(normalized)

    # Keep VectorStore import + object available for the next step of the project.
    # (Not used for keyword retrieval yet.)
    _ = VectorStore  # noqa: F841

    confidence = "high" if retrieved["found"] else "low"

    return {
        "answer": retrieved["answer"],
        "citations": [
            {
                "source": "demo-textbook",
                "chapter": retrieved["chapter"],
                "page": retrieved["page"],
            }
        ],
        "meta": {
            "grade": grade,
            "subject": subject,
            "confidence": confidence,
        },
    }

