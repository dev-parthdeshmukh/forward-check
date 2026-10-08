import json

from fastapi.testclient import TestClient

from app import cache
from app.main import app
from app.schemas import CheckResult, Verdict

client = TestClient(app)


def stream_events(**form):
    response = client.post("/check/stream", **form)
    assert response.status_code == 200
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_web_page_and_meta_are_served():
    assert "Forward Check" in client.get("/").text
    meta = client.get("/meta").json()
    assert set(meta["sources"]) == {"official", "fact_checker", "news"}
    assert "hi" in meta["voices"]


def test_stream_answers_a_cached_message_with_a_single_result_event():
    text = "a forward the stream test has seen before"
    cache.put(cache.make_key("text", text, None), CheckResult(input_text=text, overall_verdict=Verdict.FALSE))
    events = stream_events(data={"text": text})
    assert [e["type"] for e in events] == ["result"]
    assert events[0]["result"]["cached"] is True
    assert events[0]["result"]["overall_verdict"] == "FALSE"


def test_stream_reports_an_unreadable_file_as_an_input_error():
    events = stream_events(files={"file": ("setup.exe", b"MZ", "application/octet-stream")})
    assert events[0] == {"type": "status", "stage": "text"}
    assert events[-1]["type"] == "error" and events[-1]["code"] == "input"
    assert "Unsupported file type" in events[-1]["message"]


def test_stream_with_nothing_to_check_is_an_input_error():
    events = stream_events(data={"reply_language": "hi"})
    assert events[-1]["type"] == "error" and events[-1]["code"] == "input"


def test_speech_rejects_empty_text_and_unknown_languages():
    assert client.post("/tts", json={"text": "   ", "language_code": "hi"}).status_code == 400
    assert client.post("/tts", json={"text": "hello", "language_code": "xx"}).status_code == 400


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_empty_request_is_rejected():
    assert client.post("/check", json={}).status_code == 400


def test_unsupported_upload_is_rejected_with_a_readable_message():
    response = client.post("/check/file", files={"file": ("setup.exe", b"MZ", "application/octet-stream")})
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_private_link_is_rejected():
    response = client.post("/check", json={"url": "http://127.0.0.1:9/secret"})
    assert response.status_code == 400
