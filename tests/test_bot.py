from bot.telegram_bot import MESSAGE_LIMIT, extract_input, format_reply, spoken_text
from app.schemas import CheckResult, Claim, ClaimResult, Evidence, RiskFlag, Verdict
from eval.report import metrics


def evidence(url, tier="official", name="PIB"):
    return Evidence(id="E1", url=url, source_name=name, domain="pib.gov.in", tier=tier)


def claim_result(verdict=Verdict.FALSE, label="गलत", **extra):
    fields = {
        "claim": Claim(id="C1", text="Free laptops for all.", original_span="सबको मुफ्त <लैपटॉप>"),
        "verdict": verdict, "verdict_label": label, "explanation": "यह दावा गलत है & झूठा है।",
        "what_is_wrong": "ऐसी कोई योजना नहीं है।", "correct_information": "सही जानकारी myscheme.gov.in पर है।",
        "evidence": [evidence("https://pib.gov.in/a?x=1&y=2")],
    }
    return ClaimResult(**(fields | extra))


def result_with(*claims, **extra):
    fields = {
        "input_text": "x", "overall_verdict": Verdict.FALSE, "overall_label": "गलत",
        "reply_language_code": "hi", "claims": list(claims),
    }
    return CheckResult(**(fields | extra))


def test_what_a_telegram_message_asks_us_to_check():
    assert extract_input({"text": "  is this true?  "}) == {"text": "is this true?"}
    assert extract_input({"photo": [{"file_id": "small"}, {"file_id": "large"}]}) == {"file_id": "large", "filename": "photo.jpg"}
    assert extract_input({"voice": {"file_id": "v"}}) == {"file_id": "v", "filename": "voice.ogg"}
    assert extract_input({"document": {"file_id": "d", "file_name": "notice.pdf"}}) == {"file_id": "d", "filename": "notice.pdf"}
    assert extract_input({"sticker": {"file_id": "s"}}) is None


def test_reply_shows_verdict_reasons_warnings_and_sources_with_markup_escaped():
    flag = RiskFlag(code="pressure", message="जल्दी करने का दबाव।")
    reply = format_reply(result_with(claim_result(), risk_flags=[flag]))
    assert reply.startswith("❌ <b>गलत</b>")
    assert "गलत है &amp; झूठा है" in reply                      # text from the model is escaped
    assert "<b>क्या गलत है:</b> ऐसी कोई योजना नहीं है।" in reply
    assert "⚠️ <b>खतरे के संकेत</b>\n• जल्दी करने का दबाव।" in reply
    assert '<a href="https://pib.gov.in/a?x=1&amp;y=2">PIB</a>' in reply


def test_reply_for_several_claims_numbers_and_quotes_each():
    reply = format_reply(result_with(
        claim_result(), claim_result(Verdict.VERIFIED, "सही", what_is_wrong=""),
        overall_verdict=Verdict.PARTLY_SUPPORTED, overall_label="आंशिक रूप से सही",
    ))
    assert "🟡 <b>आंशिक रूप से सही</b>" in reply
    assert "<b>1. ❌ गलत</b>" in reply and "<b>2. ✅ सही</b>" in reply
    assert "<i>“सबको मुफ्त &lt;लैपटॉप&gt;”</i>" in reply


def test_reply_leaves_out_untrusted_and_non_web_links():
    reply = format_reply(result_with(claim_result(evidence=[
        evidence("https://blog.example/post", tier="other", name="Blog"),
        evidence("javascript:alert(1)", name="Bad"),
    ])))
    assert "Blog" not in reply and "javascript" not in reply and "स्रोत" not in reply


def test_long_reply_is_cut_to_fit_one_message_and_keeps_its_sources():
    reply = format_reply(result_with(claim_result(explanation="बहुत लंबा। " * 1200)))
    assert len(reply) <= MESSAGE_LIMIT
    assert reply.rstrip().endswith("</a>")


def test_message_with_no_claims_gets_the_plain_note():
    assert format_reply(result_with(summary="Only a greeting <3")) == "Only a greeting &lt;3"


def test_spoken_text_leads_with_the_verdict():
    assert spoken_text(result_with(claim_result())).startswith("गलत. यह दावा गलत है")


def row(gold, got, accept=(), **extra):
    base = {
        "id": f"{gold}-{got}", "gold": gold, "got": got, "accept": list(accept), "evidence": 2, "trusted_evidence": 2,
        "dropped_citations": 0, "withdrawn": 0, "seconds": 30, "input_tokens": 20000, "output_tokens": 1500,
    }
    return base | extra


def test_eval_metrics_separate_exact_lenient_and_the_two_kinds_of_error():
    m = metrics([
        row("FALSE", "FALSE"),
        row("OUTDATED", "FALSE", accept=["FALSE"]),
        row("VERIFIED", "UNVERIFIABLE", trusted_evidence=0),
        row("UNVERIFIABLE", "FALSE", trusted_evidence=0),
        row("UNVERIFIABLE", "UNVERIFIABLE", evidence=0, trusted_evidence=0, from_cache=True),
    ])
    assert (m["total"], m["exact"], m["lenient"]) == (5, 2, 3)
    assert (m["over_abstained"], m["checkable"]) == (1, 3)
    assert (m["over_confident"], m["uncheckable"]) == (1, 2)
    assert m["decisive_without_evidence"] == 1
    assert m["matrix"]["OUTDATED"]["FALSE"] == 1
    assert m["live"] == 4
    assert [r["id"] for r in m["misses"]] == ["VERIFIED-UNVERIFIABLE", "UNVERIFIABLE-FALSE"]
