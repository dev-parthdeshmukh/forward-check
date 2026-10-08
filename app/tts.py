"""Spoken replies through Microsoft Edge's online voices (free, needs internet)."""
import asyncio
import hashlib

import aiohttp
import edge_tts
from edge_tts.exceptions import EdgeTTSException

from . import config

VOICES = {
    "en": "en-IN-NeerjaNeural", "hi": "hi-IN-SwaraNeural", "mr": "mr-IN-AarohiNeural",
    "bn": "bn-IN-TanishaaNeural", "gu": "gu-IN-DhwaniNeural", "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural", "kn": "kn-IN-SapnaNeural", "ml": "ml-IN-SobhanaNeural",
    "ur": "ur-IN-GulNeural",
}
MAX_CHARS = 1500


class TTSError(RuntimeError):
    """The voice service failed."""


class TTSInputError(TTSError):
    """The request itself cannot be spoken."""


def synthesize(text: str, language_code: str) -> bytes:
    """MP3 audio of the text. Repeats are served from disk."""
    text = " ".join(text.split())
    if not text:
        raise TTSInputError("There is nothing to read out.")
    if len(text) > MAX_CHARS:
        raise TTSInputError(f"The text is longer than {MAX_CHARS} characters.")
    voice = VOICES.get(language_code)
    if not voice:
        raise TTSInputError(f"No voice is available for language '{language_code}'.")

    folder = config.CACHE_DIR / "tts"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (hashlib.sha256(f"{voice}|{text}".encode()).hexdigest() + ".mp3")
    if path.exists():
        return path.read_bytes()
    partial = path.with_suffix(".part")
    try:
        asyncio.run(edge_tts.Communicate(text, voice).save(str(partial)))
    except (EdgeTTSException, aiohttp.ClientError, asyncio.TimeoutError, OSError) as exc:
        partial.unlink(missing_ok=True)
        raise TTSError(f"The voice service could not be reached: {exc}") from exc
    partial.replace(path)
    return path.read_bytes()
