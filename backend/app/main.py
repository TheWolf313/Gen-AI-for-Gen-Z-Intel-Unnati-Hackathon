from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.core.config import get_settings
from app.data.vector_store import initialize_vector_store


def create_app() -> FastAPI:
    """
    FastAPI application factory.

    Why this exists:
    - Keeps app creation clean and testable
    - Central place to wire routers, middleware, and configuration
    """
    settings = get_settings()

    app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)

    # For the hackathon MVP we enable CORS so a simple frontend can call the API.
    # In production, restrict origins to your real domains.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(chat_router, tags=["chat"])

    @app.on_event("startup")
    def _startup() -> None:
        # Ensure the in-memory vector store is ready for queries.
        initialize_vector_store()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()

