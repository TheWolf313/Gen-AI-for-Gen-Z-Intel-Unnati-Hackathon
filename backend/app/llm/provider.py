from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from typing import List

_LOCAL_MODEL = None


class LLMProvider:
    """
    Placeholder for a future LLM integration.

    In the real system this will:
    - call an external model API (or a local model)
    - handle retries/timeouts
    - support model routing (cheap vs better)

    For MVP scaffolding we keep it simple and unused.
    """

    def generate(self, prompt: str) -> str:
        # Not implemented in this scaffold.
        return "LLM generation is not enabled yet."


def get_embedding(text: str) -> list[float]:
    """
    Return an embedding vector for the given text.

    Behavior:
    - If `OPENAI_API_KEY` is set, use OpenAI embeddings over HTTPS.
    - Else fallback to a local embedding model (sentence-transformers).

    Notes:
    - This is intentionally minimal for the MVP.
    - If sentence-transformers isn't installed, we fall back to a small deterministic
      embedding so the API keeps working (semantic quality will be lower).
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return [0.0] * 32

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        payload = {"model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), "input": cleaned}
        req = urllib.request.Request(
            url="https://api.openai.com/v1/embeddings",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return list(map(float, data["data"][0]["embedding"]))

    # Local fallback: sentence-transformers (recommended for offline/cost control)
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        model_name = os.getenv("LOCAL_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        global _LOCAL_MODEL
        if _LOCAL_MODEL is None:
            print("USING LOCAL EMBEDDING MODEL")
            _LOCAL_MODEL = SentenceTransformer(model_name)
        embedding = _LOCAL_MODEL.encode(cleaned, normalize_embeddings=True)
        vec: List[float] = embedding.tolist()
        return vec
    except Exception as e:
        print("Embedding fallback triggered:", e)
        # Deterministic tiny fallback: stable pseudo-embedding from SHA256.
        # Keeps the system runnable even if local model isn't installed yet.
        h = hashlib.sha256(cleaned.encode("utf-8")).digest()
        return [((b / 255.0) * 2.0 - 1.0) for b in h]  # 32-dim in [-1, 1]

