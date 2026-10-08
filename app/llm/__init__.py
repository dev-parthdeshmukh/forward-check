from functools import lru_cache

from .base import Attachment, LLMBackend, LLMError, OnStep, ResearchResult

__all__ = ["Attachment", "LLMBackend", "LLMError", "OnStep", "ResearchResult", "get_backend"]


@lru_cache(maxsize=None)
def get_backend(name: str) -> LLMBackend:
    if name == "claude_cli":
        from .claude_cli import ClaudeCLIBackend
        return ClaudeCLIBackend()
    if name == "gemini":
        from .gemini import GeminiBackend
        return GeminiBackend()
    raise LLMError(f"Unknown LLM backend: {name}")
