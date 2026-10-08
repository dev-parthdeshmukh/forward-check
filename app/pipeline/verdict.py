"""Code-side checks on the model's verdict. The model proposes; these rules decide what stands."""
import re
from datetime import date

from .. import i18n, sources
from ..schemas import Claim, ClaimResult, Evidence, Verdict

# The stance a verdict needs at least one trusted source to take; None means any stance will do.
_REQUIRED_STANCE = {
    Verdict.VERIFIED: "supports",
    Verdict.FALSE: "refutes",
    Verdict.OUTDATED: None,
    Verdict.PARTLY_SUPPORTED: None,
}

_CONFIDENCE = ["low", "medium", "high"]
_DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$")
# Topics where a rule or offer can quietly change, so an old confirmation is weaker.
_TIME_SENSITIVE = {"government_scheme", "finance", "safety_alert", "scam_offer"}
_STALE_AFTER_DAYS = 2 * 365
_SELF_VOUCHING_TIERS = {"official", "fact_checker"}


def parse_date(text: str) -> date | None:
    """Earliest day a YYYY, YYYY-MM or YYYY-MM-DD string can mean, or None if it is not a date."""
    match = _DATE_RE.match(text.strip())
    if not match:
        return None
    year, month, day = (int(part) if part else 1 for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def validate(
    claim: Claim, data: dict, seen_urls: set[str], language_code: str,
    source_urls: list[str] | None = None, today: date | None = None,
) -> ClaimResult:
    today = today or date.today()
    notes: list[str] = []
    seen = {sources.normalize_url(u) for u in seen_urls}
    checked_page = {sources.normalize_url(u) for u in source_urls or []}

    evidence: list[Evidence] = []
    for item in data.get("evidence", []):
        url = item.get("url", "").strip()
        normalized = sources.normalize_url(url) if url else ""
        # The page under check counts as retrieved (we fetched it), but never as independent support.
        if not url or (normalized not in seen and normalized not in checked_page):
            notes.append(f"Dropped a cited source that was never retrieved: {url or '(blank)'}")
            continue
        evidence.append(Evidence(
            id=f"E{len(evidence) + 1}",
            url=url,
            source_name=item.get("source_name", ""),
            domain=sources.domain_of(url),
            tier=sources.tier_of(url),
            published_date=item.get("published_date", ""),
            quote=item.get("quote", ""),
            stance=item.get("stance", "context"),
            independent=normalized not in checked_page,
        ))
    if any(not e.independent and e.tier not in _SELF_VOUCHING_TIERS for e in evidence):
        notes.append("The page being checked was cited as evidence; it does not count toward the verdict.")

    proposed = Verdict(data["verdict"])
    result = ClaimResult(
        claim=claim,
        verdict=proposed,
        confidence=data.get("confidence") if data.get("confidence") in _CONFIDENCE else "low",
        explanation=data.get("explanation", ""),
        what_is_wrong=data.get("what_is_wrong", ""),
        correct_information=data.get("correct_information", ""),
        true_as_of=_clean_date(data.get("true_as_of", ""), "true_as_of", notes),
        changed_on=_clean_date(data.get("changed_on", ""), "changed_on", notes),
        evidence=evidence,
        validation_notes=notes,
    )

    problem = _unsupported_reason(result, today)
    if problem:
        notes.append(f"{proposed.value} withdrawn: {problem}")
        result.downgraded_from = proposed
        result.verdict = Verdict.UNVERIFIABLE
        result.confidence = "low"
        result.explanation = i18n.abstain_text(language_code)
        result.what_is_wrong = ""
        result.correct_information = ""
        result.true_as_of = ""
        result.changed_on = ""
    else:
        _cap_confidence(result, today)
    result.verdict_label = i18n.verdict_label(result.verdict, language_code)
    return result


def _clean_date(value: str, field: str, notes: list[str]) -> str:
    value = value.strip()
    if value and parse_date(value) is None:
        notes.append(f"Ignored {field} because it is not a date: {value}")
        return ""
    return value


def _decisive(result: ClaimResult) -> list[Evidence]:
    """Evidence allowed to carry a verdict: from a trusted source, and not a page vouching for itself.

    The exception is a checked page that is itself an official body or a fact-checker: telling the
    reader "this comes from PIB" is the right answer, so it counts, at reduced confidence.
    """
    return [
        e for e in result.evidence
        if e.tier != "other" and (e.independent or e.tier in _SELF_VOUCHING_TIERS)
    ]


def _unsupported_reason(result: ClaimResult, today: date) -> str:
    if result.verdict not in _REQUIRED_STANCE:
        return ""
    trusted = _decisive(result)
    if not trusted:
        return "no independent evidence from a trusted source"
    stance = _REQUIRED_STANCE[result.verdict]
    if stance and not any(e.stance == stance for e in trusted):
        return f"no trusted source that {stance} the claim"
    if result.verdict == Verdict.OUTDATED:
        if not (result.true_as_of or result.changed_on):
            return "no date for when the claim stopped being true"
        changed = parse_date(result.changed_on) if result.changed_on else None
        if changed and changed > today:
            return f"the change is dated in the future ({result.changed_on}), so the claim is not outdated yet"
    return ""


def _cap_confidence(result: ClaimResult, today: date) -> None:
    """Lower the model's confidence when the evidence behind a standing verdict is thin, split or old."""
    if result.verdict not in _REQUIRED_STANCE:
        return
    trusted = _decisive(result)
    cap, reasons = "high", []

    if len(trusted) == 1 and trusted[0].tier == "news":
        cap, reasons = "medium", ["it rests on a single news report"]
    if not any(e.independent for e in trusted):
        cap, reasons = "medium", ["it rests only on the page being checked, which is a trusted source"]

    if result.verdict == Verdict.VERIFIED and result.claim.topic in _TIME_SENSITIVE:
        dates = [parse_date(e.published_date) for e in trusted if e.stance == "supports"]
        dated = [d for d in dates if d]
        if dated and (today - max(dated)).days > _STALE_AFTER_DAYS:
            cap = "medium"
            reasons.append(f"the newest supporting source is from {max(dated).year}, and this may have changed since")

    stances = {e.stance for e in trusted}
    if result.verdict in (Verdict.VERIFIED, Verdict.FALSE) and {"supports", "refutes"} <= stances:
        cap = "low"
        reasons.append("trusted sources disagree")

    if _CONFIDENCE.index(result.confidence) > _CONFIDENCE.index(cap):
        result.confidence = cap
        result.validation_notes.append("Confidence lowered: " + "; ".join(reasons) + ".")


def overall(verdicts: list[Verdict]) -> Verdict:
    """One verdict for the whole message from its per-claim verdicts."""
    kinds = set(verdicts)
    if not kinds:
        return Verdict.UNVERIFIABLE
    if len(kinds) == 1:
        return verdicts[0]
    # Some support alongside anything else means the message as a whole is only partly right.
    if kinds & {Verdict.VERIFIED, Verdict.PARTLY_SUPPORTED}:
        return Verdict.PARTLY_SUPPORTED
    if Verdict.FALSE in kinds:
        return Verdict.FALSE
    return Verdict.OUTDATED
