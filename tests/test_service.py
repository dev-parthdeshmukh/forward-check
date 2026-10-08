import pytest

from app import cache, i18n, service
from app.ingest import IngestError
from app.llm.claude_cli import _steps_in
from app.schemas import CheckResult, Verdict


def stored(summary="checked") -> CheckResult:
    return CheckResult(input_text="x", overall_verdict=Verdict.FALSE, summary=summary)


def test_cache_key_ignores_case_and_spacing_but_not_wording_or_language():
    base = cache.make_key("text", "Garlic cures  dengue", None)
    assert cache.make_key("text", "  garlic CURES dengue\n", "auto") == base
    assert cache.make_key("text", "Garlic cures malaria", None) != base
    assert cache.make_key("text", "Garlic cures dengue", "hi") != base
    assert cache.make_key("file", b"Garlic cures dengue", None) != base


def test_cached_result_comes_back_marked_and_counted():
    key = cache.make_key("text", "a message nobody has checked", None)
    assert cache.get(key) is None
    cache.put(key, stored("first answer"))
    first_repeat, second_repeat = cache.get(key), cache.get(key)
    assert first_repeat.cached and first_repeat.summary == "first answer"
    assert (first_repeat.times_checked, second_repeat.times_checked) == (2, 3)


def test_expired_entry_is_dropped(monkeypatch):
    key = cache.make_key("text", "an old message", None)
    cache.put(key, stored())
    # Negative, not zero: on Windows two clock readings a moment apart can be equal.
    monkeypatch.setattr(cache.config, "CACHE_TTL_DAYS", -1)
    assert cache.get(key) is None


def test_cached_message_is_answered_without_reading_or_checking(monkeypatch):
    text = "this forward was checked yesterday"
    cache.put(cache.make_key("text", text, None), stored("from cache"))
    monkeypatch.setattr(service.pipeline, "check", lambda *a, **k: pytest.fail("pipeline should not run"))
    events = []
    result = service.run_check(text=text.upper(), on_event=events.append)
    assert result.summary == "from cache"
    assert events == []


def test_an_answer_is_reused_for_the_same_reply_language_however_it_is_asked_for(monkeypatch):
    calls = []

    def fake_check(prepared, reply_language=None, on_event=None):
        calls.append(reply_language)
        reply = "en" if reply_language == "en" else "hi"
        return CheckResult(
            input_text=prepared.text, overall_verdict=Verdict.FALSE, language_code="hi",
            reply_language_code=reply, backend=service.config.LLM_BACKEND,
        )

    monkeypatch.setattr(service.pipeline, "check", fake_check)
    text = "एक हिंदी संदेश जिसे पहली बार जाँचा जा रहा है"
    service.run_check(text=text)                              # automatic: replies in Hindi
    assert service.run_check(text=text, reply_language="hi").cached
    assert service.run_check(text=text, reply_language="Hindi").cached
    assert not service.run_check(text=text, reply_language="en").cached   # a different answer
    assert calls == [None, "en"]

    english_first = "एक और हिंदी संदेश"
    service.run_check(text=english_first, reply_language="en")
    assert not service.run_check(text=english_first).cached   # automatic would reply in Hindi


def test_fallback_answers_are_not_kept(monkeypatch):
    monkeypatch.setattr(service.pipeline, "check", lambda prepared, reply_language=None, on_event=None: CheckResult(
        input_text=prepared.text, overall_verdict=Verdict.UNVERIFIABLE, backend="some-fallback"))
    text = "a message answered by the weaker backend"
    service.run_check(text=text)
    assert not service.run_check(text=text).cached


def test_empty_request_is_an_input_error():
    with pytest.raises(IngestError):
        service.run_check(text="   ")


def test_reply_language_resolution():
    assert i18n.resolve_reply(None, "hi", "Hindi") == ("hi", "Hindi")
    assert i18n.resolve_reply("auto", "mr", "Marathi") == ("mr", "Marathi")
    assert i18n.resolve_reply("mr", "en", "English") == ("mr", "Marathi")
    assert i18n.resolve_reply("hindi", "en", "English") == ("hi", "Hindi")
    assert i18n.resolve_reply("Tamil", "en", "English") == ("en", "Tamil")


def test_tool_calls_in_the_cli_stream_become_steps():
    event = {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "Let me look."},
        {"type": "tool_use", "name": "WebSearch", "input": {"query": "PIB free laptop scheme"}},
        {"type": "tool_use", "name": "WebFetch", "input": {"url": "https://pib.gov.in/x", "prompt": "quote it"}},
        {"type": "tool_use", "name": "StructuredOutput", "input": {"verdict": "FALSE"}},
    ]}}
    assert _steps_in(event) == [
        {"action": "search", "detail": "PIB free laptop scheme"},
        {"action": "fetch", "detail": "https://pib.gov.in/x"},
    ]
    assert _steps_in({"type": "user", "message": {"content": []}}) == []
