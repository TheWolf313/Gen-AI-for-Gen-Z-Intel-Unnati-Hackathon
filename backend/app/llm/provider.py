from __future__ import annotations


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

