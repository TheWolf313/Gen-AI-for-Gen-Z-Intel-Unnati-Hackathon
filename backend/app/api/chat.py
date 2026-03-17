from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.query_pipeline import normalize_query, retrieve_answer, run_query_pipeline

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    Minimal chat endpoint.

    Current behavior (MVP):
    - Accept a user question
    - Run a dummy pipeline (no real LLM yet)
    - Return a simulated answer + basic "citations"
    """
    normalized = normalize_query(req.question)
    _retrieved = retrieve_answer(normalized)

    # The pipeline constructs the final structured response format.
    result = run_query_pipeline(
        question=normalized,
        user_id=req.user_id,
        grade=req.grade,
        subject=req.subject,
        language=req.language,
    )
    return ChatResponse(**result)

