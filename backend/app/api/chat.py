from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.query_pipeline import normalize_query, run_query_pipeline

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """
    Minimal chat endpoint.

    Current behavior (MVP):
    - Accept a user question
    - Run embedding-based retrieval pipeline
    - Return structured response
    """
    normalized = normalize_query(req.question)

    result = run_query_pipeline(
        question=normalized,
        user_id=req.user_id,
        grade=req.grade,
        subject=req.subject,
        language=req.language,
    )

    return ChatResponse(**result)