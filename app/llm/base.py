import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field

OnStep = Callable[[dict], None]


class LLMError(RuntimeError):
    pass


@dataclass
class Attachment:
    """An image or PDF handed to the model alongside the prompt."""
    mime: str
    data: bytes


@dataclass
class ResearchResult:
    data: dict
    # Every URL the model actually retrieved (search hits and fetched pages).
    seen_urls: set[str] = field(default_factory=set)
    notes: list[str] = field(default_factory=list)


class LLMBackend(ABC):
    name: str

    def __init__(self) -> None:
        self._usage_lock = threading.Lock()
        self.input_tokens = 0
        self.output_tokens = 0

    def _count(self, input_tokens: int, output_tokens: int) -> None:
        with self._usage_lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens

    @abstractmethod
    def structured(
        self, system: str, prompt: str, schema: dict, effort: str = "low",
        attachments: list[Attachment] | None = None,
    ) -> dict:
        """One call, no tools, output matching the JSON schema."""

    @abstractmethod
    def research(self, system: str, prompt: str, schema: dict, effort: str = "medium",
                 on_step: OnStep | None = None) -> ResearchResult:
        """Web research followed by output matching the JSON schema.

        on_step is called with {"action": "search" | "fetch", "detail": ...} as each lookup starts,
        on backends that can report it.
        """
