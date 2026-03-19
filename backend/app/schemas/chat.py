from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    What the frontend sends to the backend.
    """

    question: str = Field(..., min_length=1, description="User's question")
    user_id: str | None = Field(default=None, description="Optional user identifier")
    grade: str | None = Field(default=None, description="Optional grade (e.g., '9')")
    subject: str | None = Field(default=None, description="Optional subject (e.g., 'Science')")
    language: str | None = Field(default=None, description="Optional language hint (e.g., 'hi' or 'en')")
    chapter: str | None = Field(default=None, description="Optional chapter filter (e.g., 'Plant Biology')")
    topic: str | None = Field(default=None, description="Optional topic filter (keyword/phrase)")
    # Optional multi-book filters (future-proofing; safe defaults if not provided).
    book_id: str | None = Field(default=None, description="Optional book identifier filter")
    board: str | None = Field(default=None, description="Optional board filter (e.g., 'State Board')")


class Citation(BaseModel):
    source: str
    chapter: str | None = None
    page: int | None = None


class ChatResponse(BaseModel):
    """
    What the backend returns.
    """

    answer: str
    citations: list[Citation] = []
    meta: dict[str, Any] = {}

