import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from .. import config, i18n
from ..ingest import Prepared
from ..llm import LLMBackend, LLMError, get_backend
from ..schemas import CheckResult, Claim, ClaimResult, Step, Verdict
from . import verdict as rules
from .extract import extract_claims
from .research import research_claim
from .risk import risk_flags

# Progress events, for a caller that wants to show the check as it happens:
#   {"type": "claims", "claims": [...], "input_text": ..., "language_code": ..., "reply_language_code": ...}
#   {"type": "step", "claim_id": ..., "action": "search" | "fetch", "detail": ...}
#   {"type": "claim_done", "claim": {...}}
#   {"type": "status", "stage": "retrying"}   the first backend failed and the fallback is starting over
Emit = Callable[[dict], None]

# How much of the message the progress event carries; the full text is in the final result.
_PREVIEW_CHARS = 4000


def _backends() -> list[str]:
    names = [config.LLM_BACKEND]
    if config.LLM_FALLBACK and config.LLM_FALLBACK != config.LLM_BACKEND:
        names.append(config.LLM_FALLBACK)
    return names


def _check_claim(
    llm: LLMBackend, claim: Claim, message_code: str, reply_code: str, reply_name: str,
    source_urls: list[str], emit: Emit,
) -> ClaimResult:
    steps: list[Step] = []

    def on_step(step: dict) -> None:
        steps.append(Step(**step))
        emit({"type": "step", "claim_id": claim.id, **step})

    found = research_claim(llm, claim, message_code, reply_name, on_step=on_step)
    result = rules.validate(claim, found.data, found.seen_urls, reply_code, source_urls=source_urls)
    result.validation_notes = found.notes + result.validation_notes
    result.steps = steps
    emit({"type": "claim_done", "claim": result.model_dump(mode="json")})
    return result


def _run(llm: LLMBackend, prepared: Prepared, reply_language: str | None, emit: Emit) -> CheckResult:
    found = extract_claims(llm, prepared)
    reply_code, reply_name = i18n.resolve_reply(reply_language, found.language_code, found.language_name)
    result = CheckResult(
        source_kind=prepared.kind,
        input_text=prepared.text or found.transcript,
        language_code=found.language_code,
        language_name=found.language_name,
        reply_language=reply_name,
        reply_language_code=reply_code,
        overall_verdict=Verdict.UNVERIFIABLE,
        overall_label=i18n.verdict_label(Verdict.UNVERIFIABLE, reply_code),
        backend=llm.name,
        notes=list(prepared.notes),
    )
    # A fetched web page is an article, not a forward, so forwarding-pressure signs do not apply to it.
    if prepared.kind != "url":
        result.risk_flags = risk_flags(result.input_text, found.claims, reply_code)
    emit({
        "type": "claims",
        "claims": [c.model_dump() for c in found.claims],
        "input_text": result.input_text[:_PREVIEW_CHARS],
        "source_kind": prepared.kind,
        "language_code": found.language_code,
        "reply_language_code": reply_code,
    })
    if not found.claims:
        result.summary = found.note or "This message does not make a factual claim that can be checked."
        result.notes.append("No checkable claims found.")
        return result

    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_CLAIMS) as pool:
        result.claims = list(pool.map(
            lambda c: _check_claim(
                llm, c, found.language_code, reply_code, reply_name, prepared.source_urls, emit,
            ),
            found.claims,
        ))

    result.overall_verdict = rules.overall([c.verdict for c in result.claims])
    result.overall_label = i18n.verdict_label(result.overall_verdict, reply_code)
    if len(result.claims) == 1:
        result.summary = result.claims[0].explanation
    else:
        result.summary = "\n".join(f"{c.verdict_label}: {c.what_is_wrong or c.explanation}" for c in result.claims)
    return result


def check(prepared: Prepared, reply_language: str | None = None, on_event: Emit | None = None) -> CheckResult:
    """Fact-check prepared input. Tries the configured backend, then the fallback."""
    emit = on_event or (lambda event: None)
    started = time.time()
    failures: list[str] = []
    for name in _backends():
        try:
            llm = get_backend(name)
            # Counters are per backend, so totals are only exact for one check at a time.
            used_in, used_out = llm.input_tokens, llm.output_tokens
            if failures:
                emit({"type": "status", "stage": "retrying"})
            result = _run(llm, prepared, reply_language, emit)
        except LLMError as exc:
            failures.append(f"{name} failed: {exc}")
            continue
        result.input_tokens = llm.input_tokens - used_in
        result.output_tokens = llm.output_tokens - used_out
        result.notes = failures + result.notes
        result.seconds = round(time.time() - started, 1)
        return result
    raise LLMError("; ".join(failures))
