"""Turn whatever the user forwarded (text, screenshot, PDF, voice note, link) into text or
model attachments that the claim extractor can read."""
import io
import ipaddress
import re
import socket
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx
from pypdf import PdfReader
from pypdf.errors import PyPdfError

from .llm import Attachment, get_backend

MAX_TEXT_CHARS = 40_000
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PDF_BYTES = 20 * 1024 * 1024
MAX_AUDIO_BYTES = 15 * 1024 * 1024
MAX_SCANNED_PDF_PAGES = 20
# Below this much extractable text, a PDF is treated as scanned and read as images.
_MIN_PDF_TEXT_CHARS = 200

IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
AUDIO_TYPES = {
    ".ogg": "audio/ogg", ".opus": "audio/ogg", ".mp3": "audio/mp3", ".wav": "audio/wav",
    ".m4a": "audio/aac", ".aac": "audio/aac", ".flac": "audio/flac", ".webm": "audio/webm",
}
_URL_ONLY = re.compile(r"^\s*(https?://\S+)\s*$")
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ForwardCheck/0.1"


class IngestError(ValueError):
    """The input could not be read; the message is safe to show to the user."""


@dataclass
class Prepared:
    kind: str  # text | image | pdf | audio | url
    text: str = ""
    attachments: list[Attachment] = field(default_factory=list)
    source: str = ""  # one line telling the extractor where the content came from
    source_urls: list[str] = field(default_factory=list)  # the link being checked, before and after redirects
    notes: list[str] = field(default_factory=list)


def is_link_only(text: str) -> bool:
    return bool(_URL_ONLY.match(text))


def from_text(text: str) -> Prepared:
    link = _URL_ONLY.match(text)
    if link:
        return from_url(link.group(1))
    return Prepared(kind="text", text=text)


def from_file(data: bytes, filename: str) -> Prepared:
    ext = Path(filename).suffix.lower()
    if ext in IMAGE_TYPES:
        return _image(data, IMAGE_TYPES[ext])
    if ext == ".pdf":
        return _pdf(data, source=f"a PDF document named {filename}")
    if ext in AUDIO_TYPES:
        return _audio(data, AUDIO_TYPES[ext])
    if ext in (".txt", ""):
        return from_text(data.decode("utf-8", errors="replace"))
    raise IngestError(f"Unsupported file type: {ext}. Send text, an image, a PDF or a voice note.")


def _image(data: bytes, mime: str) -> Prepared:
    if len(data) > MAX_IMAGE_BYTES:
        raise IngestError("The image is larger than 5 MB. Send a smaller screenshot.")
    return Prepared(kind="image", attachments=[Attachment(mime, data)], source="a screenshot or image")


def _clip(text: str, notes: list[str]) -> str:
    if len(text) > MAX_TEXT_CHARS:
        notes.append(f"The content is long; only the first {MAX_TEXT_CHARS:,} of {len(text):,} characters were checked.")
        return text[:MAX_TEXT_CHARS]
    return text


def _pdf(data: bytes, source: str) -> Prepared:
    if len(data) > MAX_PDF_BYTES:
        raise IngestError("The PDF is larger than 20 MB.")
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = len(reader.pages)
        text = "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
    except (PyPdfError, ValueError, KeyError) as exc:
        raise IngestError(f"Could not read the PDF: {exc}") from exc

    notes: list[str] = []
    if len(text) >= _MIN_PDF_TEXT_CHARS:
        return Prepared(kind="pdf", text=_clip(text, notes), source=f"{source} ({pages} pages)", notes=notes)
    if pages > MAX_SCANNED_PDF_PAGES:
        raise IngestError(f"This PDF is a {pages}-page scan with no readable text. Send the pages that matter as images.")
    return Prepared(kind="pdf", attachments=[Attachment("application/pdf", data)], source=f"{source} (scanned, {pages} pages)")


def _audio(data: bytes, mime: str) -> Prepared:
    if len(data) > MAX_AUDIO_BYTES:
        raise IngestError("The voice note is larger than 15 MB.")
    transcript = get_backend("gemini").transcribe(Attachment(mime, data))
    if not transcript:
        raise IngestError("No speech could be heard in the voice note.")
    return Prepared(
        kind="audio", text=transcript, source="a voice note, transcribed automatically (expect small transcription errors)",
    )


class _PageText(HTMLParser):
    _SKIP = {"script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg", "button"}
    _BREAK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "article", "section"}

    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self._BREAK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        joined = "".join(self.parts)
        lines = (re.sub(r"[ \t\xa0]+", " ", line).strip() for line in joined.splitlines())
        return "\n".join(line for line in lines if line)


def _assert_public(url: str) -> None:
    """Refuse links that point inside the machine or local network."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise IngestError("Only http and https links can be checked.")
    try:
        infos = socket.getaddrinfo(parts.hostname, None)
    except socket.gaierror as exc:
        raise IngestError(f"Could not find the site {parts.hostname}.") from exc
    for info in infos:
        if not ipaddress.ip_address(info[4][0]).is_global:
            raise IngestError("That link points to a private address and cannot be checked.")


def _fetch(url: str) -> httpx.Response:
    with httpx.Client(timeout=20, headers={"User-Agent": _USER_AGENT}) as client:
        for _ in range(5):
            _assert_public(url)
            try:
                resp = client.get(url, follow_redirects=False)
            except httpx.HTTPError as exc:
                raise IngestError(f"Could not open the link: {exc}") from exc
            if resp.is_redirect and resp.headers.get("location"):
                url = urljoin(url, resp.headers["location"])
                continue
            if resp.status_code != 200:
                raise IngestError(f"The link returned an error (HTTP {resp.status_code}).")
            return resp
    raise IngestError("The link redirects too many times.")


def from_url(url: str) -> Prepared:
    resp = _fetch(url)
    final_url = str(resp.url)
    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if content_type == "application/pdf":
        prepared = _pdf(resp.content, source=f"a PDF at {final_url}")
    elif content_type in IMAGE_TYPES.values():
        prepared = _image(resp.content, content_type)
        prepared.source = f"an image at {final_url}"
    else:
        page = _PageText()
        page.feed(resp.text)
        body = page.text()
        if len(body) < 100:
            raise IngestError("The page has no readable text (it may need JavaScript or a login).")
        notes: list[str] = []
        prepared = Prepared(
            kind="url", text=_clip(body, notes), notes=notes,
            source=f'a web page at {final_url} titled "{page.title.strip()}"',
        )
    prepared.kind = "url"
    prepared.source_urls = [url, final_url]
    return prepared
