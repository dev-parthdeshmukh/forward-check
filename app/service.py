"""One entry point for every way in (CLI, API, bot): cache lookup, reading the input, the check itself."""
from datetime import datetime, timezone
from pathlib import Path

from . import cache, config, i18n, ingest, pipeline
from .schemas import CheckResult


def _stage_for_file(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in ingest.IMAGE_TYPES:
        return "image"
    if ext in ingest.AUDIO_TYPES:
        return "audio"
    return "pdf" if ext == ".pdf" else "text"


def run_check(
    *, text: str | None = None, url: str | None = None, file: tuple[str, bytes] | None = None,
    reply_language: str | None = None, on_event: pipeline.Emit | None = None, use_cache: bool = True,
) -> CheckResult:
    """Check exactly one of text, url or file (filename, bytes).

    on_event receives {"type": "status", "stage": text | link | image | pdf | audio} before the
    input is read, then the pipeline's own progress events. A cached answer sends no events.
    """
    emit = on_event or (lambda event: None)
    if file:
        filename, data = file
        kind, content, stage = "file", data, _stage_for_file(filename)
    elif url and url.strip():
        url = url.strip()
        kind, content, stage = "url", url, "link"
    elif text and text.strip():
        kind, content, stage = "text", text, "link" if ingest.is_link_only(text) else "text"
    else:
        raise ingest.IngestError("Send a message, a link or a file to check.")

    def key_for(reply: str | None) -> str:
        return cache.make_key(kind, content, reply)

    asked = i18n.reply_key(reply_language)
    if use_cache:
        hit = cache.get(key_for(asked))
        if hit:
            return hit

    emit({"type": "status", "stage": stage})
    if file:
        prepared = ingest.from_file(data, filename)
    elif url:
        prepared = ingest.from_url(url)
    else:
        prepared = ingest.from_text(text)

    result = pipeline.check(prepared, reply_language, on_event=emit)
    result.checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    # An answer from the fallback backend is weaker, so it is not kept for the next person.
    if use_cache and result.backend == config.LLM_BACKEND:
        # The same answer serves whoever asks for this reply language by name, and whoever leaves
        # it on automatic when the message is already in that language.
        replies = {asked, result.reply_language_code}
        if result.reply_language_code == result.language_code:
            replies.add("auto")
        for reply in replies:
            cache.put(key_for(reply), result)
    return result
