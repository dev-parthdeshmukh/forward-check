from datetime import date

from app import i18n
from app.pipeline import verdict as rules
from app.pipeline.risk import risk_flags
from app.schemas import Claim, Verdict

CLAIM = Claim(id="C1", text="Drinking hot water cures COVID-19.", original_span="hot water cures corona")
SCHEME = Claim(id="C1", text="The government gives free laptops.", original_span="free laptop", topic="government_scheme")
WHO = "https://www.who.int/emergencies/myth-busters"
PIB = "https://pib.gov.in/PressRelease?id=1"
BOOM = "https://www.boomlive.in/fact-check/laptop"
NDTV = "https://www.ndtv.com/india-news/story-1"
BLOG = "https://some-random-blog.example/post"
TODAY = date(2026, 10, 8)


def proposal(verdict, evidence, **extra):
    base = {
        "verdict": verdict, "confidence": "high", "evidence": evidence, "explanation": "model text",
        "what_is_wrong": "x", "correct_information": "y", "true_as_of": "", "changed_on": "",
    }
    return base | extra


def source(url, stance):
    return {"url": url, "source_name": "S", "published_date": "2024-01-01", "quote": "q", "stance": stance}


def test_supported_false_verdict_stands():
    result = rules.validate(CLAIM, proposal("FALSE", [source(WHO, "refutes")]), {WHO}, "en")
    assert result.verdict == Verdict.FALSE
    assert result.downgraded_from is None
    assert result.evidence[0].tier == "official"


def test_url_never_retrieved_is_dropped_and_verdict_withdrawn():
    result = rules.validate(CLAIM, proposal("FALSE", [source(WHO, "refutes")]), set(), "hi")
    assert result.verdict == Verdict.UNVERIFIABLE
    assert result.downgraded_from == Verdict.FALSE
    assert result.evidence == []
    assert result.explanation == i18n.abstain_text("hi")
    assert result.verdict_label == "पुष्टि नहीं हो सकी"
    assert result.what_is_wrong == ""


def test_untrusted_source_cannot_carry_a_verdict():
    result = rules.validate(CLAIM, proposal("VERIFIED", [source(BLOG, "supports")]), {BLOG}, "en")
    assert result.verdict == Verdict.UNVERIFIABLE
    assert len(result.evidence) == 1  # kept as context, shown to the reader


def test_false_needs_a_refuting_source():
    result = rules.validate(CLAIM, proposal("FALSE", [source(WHO, "context")]), {WHO}, "en")
    assert result.verdict == Verdict.UNVERIFIABLE


def test_outdated_needs_a_date():
    undated = rules.validate(CLAIM, proposal("OUTDATED", [source(WHO, "refutes")]), {WHO}, "en")
    dated = rules.validate(CLAIM, proposal("OUTDATED", [source(WHO, "refutes")], changed_on="2024-03"), {WHO}, "en")
    assert undated.verdict == Verdict.UNVERIFIABLE
    assert dated.verdict == Verdict.OUTDATED


def test_url_matching_ignores_www_trailing_slash_and_tracking():
    cited = "https://who.int/emergencies/myth-busters/?utm_source=wa"
    result = rules.validate(CLAIM, proposal("FALSE", [source(cited, "refutes")]), {WHO}, "en")
    assert result.verdict == Verdict.FALSE


def test_unverifiable_passes_without_evidence():
    result = rules.validate(CLAIM, proposal("UNVERIFIABLE", []), set(), "en")
    assert result.verdict == Verdict.UNVERIFIABLE
    assert result.downgraded_from is None
    assert result.explanation == "model text"


def dated(url, stance, published):
    return source(url, stance) | {"published_date": published}


def test_page_being_checked_cannot_be_its_own_proof():
    alone = rules.validate(CLAIM, proposal("VERIFIED", [source(NDTV, "supports")]), set(), "en", source_urls=[NDTV])
    assert alone.verdict == Verdict.UNVERIFIABLE
    assert alone.evidence[0].independent is False

    backed = rules.validate(
        CLAIM, proposal("VERIFIED", [source(NDTV, "supports"), source(WHO, "supports")]), {WHO}, "en",
        source_urls=[NDTV],
    )
    assert backed.verdict == Verdict.VERIFIED
    assert backed.confidence == "high"


def test_checked_page_from_a_fact_checker_counts_at_reduced_confidence():
    result = rules.validate(CLAIM, proposal("VERIFIED", [source(BOOM, "supports")]), set(), "en", source_urls=[BOOM])
    assert result.verdict == Verdict.VERIFIED
    assert result.confidence == "medium"


def test_outdated_with_a_future_change_date_is_withdrawn():
    result = rules.validate(
        CLAIM, proposal("OUTDATED", [source(WHO, "refutes")], changed_on="2027-01-01"), {WHO}, "en", today=TODAY,
    )
    assert result.verdict == Verdict.UNVERIFIABLE


def test_a_date_field_that_is_not_a_date_is_ignored():
    result = rules.validate(
        CLAIM, proposal("OUTDATED", [source(WHO, "refutes")], changed_on="sometime last year"), {WHO}, "en",
    )
    assert result.verdict == Verdict.UNVERIFIABLE  # the only date was unusable
    assert rules.parse_date("2023-10") == date(2023, 10, 1)
    assert rules.parse_date("2023-13-40") is None


def test_single_news_report_caps_confidence_at_medium():
    result = rules.validate(CLAIM, proposal("FALSE", [source(NDTV, "refutes")]), {NDTV}, "en", today=TODAY)
    assert result.verdict == Verdict.FALSE
    assert result.confidence == "medium"


def test_disagreeing_trusted_sources_cap_confidence_at_low():
    evidence = [source(WHO, "refutes"), source(NDTV, "supports")]
    result = rules.validate(CLAIM, proposal("FALSE", evidence), {WHO, NDTV}, "en", today=TODAY)
    assert result.verdict == Verdict.FALSE
    assert result.confidence == "low"


def test_old_confirmation_of_a_scheme_caps_confidence():
    old = rules.validate(SCHEME, proposal("VERIFIED", [dated(PIB, "supports", "2021-05-01")]), {PIB}, "en", today=TODAY)
    recent = rules.validate(SCHEME, proposal("VERIFIED", [dated(PIB, "supports", "2026-05-01")]), {PIB}, "en", today=TODAY)
    health = rules.validate(CLAIM, proposal("VERIFIED", [dated(WHO, "supports", "2021-05-01")]), {WHO}, "en", today=TODAY)
    assert old.confidence == "medium"
    assert recent.confidence == "high"
    assert health.confidence == "high"  # not a topic that expires


def codes(text, claims=(), language="en"):
    return [f.code for f in risk_flags(text, list(claims), language)]


def test_scheme_message_with_a_non_government_link_is_flagged():
    flags = risk_flags("Register now: http://pm-laptop-yojana.xyz last date tomorrow", [SCHEME], "hi")
    assert [f.code for f in flags] == ["unofficial_link", "pressure"]
    assert "pm-laptop-yojana.xyz" in flags[0].message
    assert ".gov.in" in flags[0].message


def test_official_and_ordinary_links_are_not_flagged():
    assert codes("Details at https://www.rbi.org.in/notice", [SCHEME]) == []
    assert codes("Nice recipe here https://www.example.com/dal", [CLAIM]) == []


def test_short_link_personal_info_and_hindi_pressure():
    assert codes("Claim prize https://bit.ly/abc and send your OTP") == ["short_link", "personal_info"]
    assert codes("यह संदेश सबको भेजिए, जल्दी करें") == ["pressure"]
    assert codes("Garlic is good for health.") == []


def test_overall_verdict():
    V = Verdict
    assert rules.overall([V.FALSE]) == V.FALSE
    assert rules.overall([V.VERIFIED, V.VERIFIED]) == V.VERIFIED
    assert rules.overall([V.VERIFIED, V.FALSE]) == V.PARTLY_SUPPORTED
    assert rules.overall([V.VERIFIED, V.UNVERIFIABLE]) == V.PARTLY_SUPPORTED
    assert rules.overall([V.FALSE, V.UNVERIFIABLE]) == V.FALSE
    assert rules.overall([V.OUTDATED, V.UNVERIFIABLE]) == V.OUTDATED
    assert rules.overall([]) == V.UNVERIFIABLE
