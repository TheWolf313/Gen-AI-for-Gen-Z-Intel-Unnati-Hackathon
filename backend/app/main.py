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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    app.include_router(chat_router, tags=["chat"])

    @app.on_event("startup")
    def _startup() -> None:
        """
        Startup indexing:
        - Load a structured dataset from disk and build the in-memory index.
        - If disk loading fails, a safe fallback dataset is used so the app still starts.

        Why load at startup:
        - Keeps request-time retrieval fast (embeddings already computed in-memory).
        - Avoids adding a database for the MVP.
        """
        initialize_vector_store()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()

