"""Run with: uvicorn app.main:app --reload     then open http://127.0.0.1:8000"""
import json
import logging
import queue
import threading

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, service, sources, tts
from .ingest import IngestError
from .llm import LLMError
from .schemas import CheckResult

log = logging.getLogger("forward_check")
app = FastAPI(title="Forward Check")

# Sent while a check is quiet, so proxies and browsers keep the connection open.
_PING_SECONDS = 15


class CheckRequest(BaseModel):
    text: str | None = None
    url: str | None = None
    reply_language: str | None = None


class SpeakRequest(BaseModel):
    text: str
    language_code: str = "en"


def _guarded(run) -> CheckResult:
    try:
        return run()
    except IngestError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/meta")
def meta() -> dict:
    """What the web page needs to describe the service."""
    return {
        "model": config.CLAUDE_MODEL if config.LLM_BACKEND == "claude_cli" else config.GEMINI_MODEL,
        "sources": {name: len(domains) for name, domains in sources.TIERS},
        "voices": sorted(tts.VOICES),
    }


@app.post("/check", response_model=CheckResult)
def check(request: CheckRequest) -> CheckResult:
    """Check a text message or a link."""
    return _guarded(lambda: service.run_check(
        text=request.text, url=request.url, reply_language=request.reply_language,
    ))


@app.post("/check/file", response_model=CheckResult)
def check_file(file: UploadFile = File(...), reply_language: str | None = Form(None)) -> CheckResult:
    """Check a screenshot, PDF or voice note."""
    upload = (file.filename or "", file.file.read())
    return _guarded(lambda: service.run_check(file=upload, reply_language=reply_language))


@app.post("/check/stream")
def check_stream(
    text: str | None = Form(None), url: str | None = Form(None),
    reply_language: str | None = Form(None), file: UploadFile | None = File(None),
) -> StreamingResponse:
    """Check any input and stream progress as newline-delimited JSON.

    Lines are the pipeline's progress events, then one {"type": "result", "result": {...}} or
    {"type": "error", "code": "input" | "model" | "internal", "message": ...}.
    """
    upload = (file.filename or "", file.file.read()) if file else None
    events: queue.Queue = queue.Queue()

    def work() -> None:
        try:
            result = service.run_check(
                text=text, url=url, file=upload, reply_language=reply_language, on_event=events.put,
            )
            events.put({"type": "result", "result": result.model_dump(mode="json")})
        except IngestError as exc:
            events.put({"type": "error", "code": "input", "message": str(exc)})
        except LLMError as exc:
            events.put({"type": "error", "code": "model", "message": str(exc)})
        except Exception:  # last line of defence for the worker thread; the client must hear back
            log.exception("check failed")
            events.put({"type": "error", "code": "internal", "message": "Unexpected error while checking."})
        finally:
            events.put(None)

    threading.Thread(target=work, daemon=True).start()

    def lines():
        while True:
            try:
                event = events.get(timeout=_PING_SECONDS)
            except queue.Empty:
                yield '{"type": "ping"}\n'
                continue
            if event is None:
                return
            yield json.dumps(event, ensure_ascii=False) + "\n"

    return StreamingResponse(
        lines(), media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@app.post("/tts")
def speak(request: SpeakRequest) -> Response:
    """MP3 of a reply read aloud."""
    try:
        audio = tts.synthesize(request.text, request.language_code)
    except tts.TTSInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except tts.TTSError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return Response(audio, media_type="audio/mpeg", headers={"Cache-Control": "private, max-age=86400"})


# Mounted last so the API routes above win.
app.mount("/", StaticFiles(directory=config.ROOT / "web", html=True), name="web")
