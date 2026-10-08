"""Gemini through the REST API. Free-tier fallback when the Claude backend is unavailable."""
import base64
import json
import time

import httpx

from .. import config
from .base import Attachment, LLMBackend, LLMError, OnStep, ResearchResult

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_NOTES_INSTRUCTION = (
    "\n\nFor this step, use Google Search and write plain-text research notes, not JSON. "
    "For each source you rely on, give its name, its publication date if shown, and a short quote, "
    "then say what the evidence shows about the claim."
)


_NO_SEARCH_INSTRUCTION = (
    "\n\nWeb search is not available in this run. Judge only from the seed fact-checks in the prompt, "
    "and cite only their URLs. If none of them covers this claim, the verdict is UNVERIFIABLE."
)


_TRANSCRIBE_PROMPT = (
    "Transcribe this voice note word for word, in the language it is spoken in and that language's "
    "own script (Devanagari for Hindi and Marathi). Give only the transcript, with no translation, "
    "summary or comment. If there is no speech, reply with an empty line."
)


class _QuotaError(LLMError):
    pass


class GeminiBackend(LLMBackend):
    name = "gemini"

    def __init__(self) -> None:
        if not config.GEMINI_API_KEY:
            raise LLMError("GEMINI_API_KEY is not set.")
        super().__init__()
        self.client = httpx.Client(timeout=180, headers={"x-goog-api-key": config.GEMINI_API_KEY})
        # Free-tier keys can have no Search grounding allowance; found out on the first attempt.
        self.search_available = True

    def _generate(self, body: dict) -> dict:
        url = f"{_BASE}/{config.GEMINI_MODEL}:generateContent"
        for attempt in range(3):
            try:
                resp = self.client.post(url, json=body)
            except httpx.HTTPError as exc:
                raise LLMError(f"Gemini request failed: {exc}") from exc
            if resp.status_code in (500, 503) and attempt < 2:
                time.sleep(4 * (attempt + 1))
                continue
            if resp.status_code == 429:
                raise _QuotaError(f"Gemini HTTP 429: {resp.text[:400]}")
            if resp.status_code != 200:
                raise LLMError(f"Gemini HTTP {resp.status_code}: {resp.text[:400]}")
            payload = resp.json()
            usage = payload.get("usageMetadata", {})
            self._count(
                usage.get("promptTokenCount", 0),
                usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0),
            )
            if not payload.get("candidates"):
                raise LLMError(f"Gemini returned no candidates: {json.dumps(payload)[:400]}")
            return payload["candidates"][0]
        raise LLMError("Gemini kept returning retryable errors.")

    @staticmethod
    def _text(candidate: dict) -> str:
        parts = candidate.get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts)

    @staticmethod
    def _file_parts(attachments: list[Attachment] | None) -> list[dict]:
        return [
            {"inline_data": {"mime_type": a.mime, "data": base64.b64encode(a.data).decode()}}
            for a in attachments or []
        ]

    def transcribe(self, audio: Attachment) -> str:
        """Verbatim transcript of a voice note, in the language and script it was spoken in."""
        candidate = self._generate({
            "contents": [{"role": "user", "parts": self._file_parts([audio]) + [{"text": _TRANSCRIBE_PROMPT}]}],
        })
        return self._text(candidate).strip()

    def structured(self, system: str, prompt: str, schema: dict, effort: str = "low",
                   attachments: list[Attachment] | None = None) -> dict:
        candidate = self._generate({
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": self._file_parts(attachments) + [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": schema},
        })
        try:
            return json.loads(self._text(candidate))
        except json.JSONDecodeError as exc:
            raise LLMError(f"Gemini returned invalid JSON: {self._text(candidate)[:300]}") from exc

    def research(self, system: str, prompt: str, schema: dict, effort: str = "medium",
                 on_step: OnStep | None = None) -> ResearchResult:
        # Search grounding and a response schema cannot be combined in one call, so research
        # runs first and a second call turns the notes into the structured verdict.
        candidate = None
        if self.search_available:
            try:
                candidate = self._generate({
                    "system_instruction": {"parts": [{"text": system + _NOTES_INSTRUCTION}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "tools": [{"google_search": {}}],
                })
            except _QuotaError:
                self.search_available = False
        if candidate is None:
            data = self.structured(system + _NO_SEARCH_INSTRUCTION, prompt, schema)
            return ResearchResult(data=data, notes=["Gemini web search unavailable; judged from published fact-checks only."])
        notes = self._text(candidate)
        chunks = candidate.get("groundingMetadata", {}).get("groundingChunks", [])
        sources = []
        for chunk in chunks:
            web = chunk.get("web", {})
            if web.get("uri"):
                sources.append((self._resolve(web["uri"]), web.get("title", "")))

        source_list = "\n".join(f"- {url} ({title})" for url, title in sources) or "(none)"
        data = self.structured(
            system,
            f"{prompt}\n\n<research_notes>\n{notes}\n</research_notes>\n\n"
            f"<retrieved_sources>\n{source_list}\n</retrieved_sources>\n\n"
            "Give the final structured answer. Cite only URLs listed in retrieved_sources or in the "
            "seed fact-checks above.",
            schema,
        )
        return ResearchResult(data=data, seen_urls={url for url, _ in sources})

    def _resolve(self, uri: str) -> str:
        """Grounding results come back as redirect links; follow one hop to the real page."""
        try:
            resp = self.client.get(uri, follow_redirects=False, timeout=15)
            return resp.headers.get("location", uri)
        except httpx.HTTPError:
            return uri
