"""Warning signs read straight off the message text. Rules only, no model call."""
import re

from .. import i18n, sources
from ..schemas import Claim, RiskFlag

_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+|\bwww\.[^\s<>\"')\]]+", re.IGNORECASE)
_SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "goo.gl", "cutt.ly", "rb.gy", "is.gd", "shorturl.at", "tiny.cc", "ow.ly"}
# Words that make a non-government address look official.
_OFFICIAL_LOOKING = re.compile(r"gov|sarkar|yojana|pmkisan|\bpm[-.]|modi|aadhaar|aadhar|uidai|rbi|epfo|ration", re.IGNORECASE)
_SCHEME_TOPICS = {"government_scheme", "scam_offer"}

_PERSONAL_INFO = re.compile(
    r"\botp\b|\bcvv\b|password|\bpin\b|account number|bank details|ओटीपी|पासवर्ड|खाता नंबर|खाता संख्या|खाते क्रमांक",
    re.IGNORECASE,
)
_PRESSURE = re.compile(
    r"\bhurry\b|\burgent|last date|act now|register now|forward (this|to)|share (this|now|with|to)|send (this )?to (all|every)"
    r"|जल्दी|तुरंत|आखिरी तारीख|अंतिम तिथि|सभी को भेज|सबको भेज|शेयर कर|फॉरवर्ड"
    r"|त्वरित|लगेच|शेवटची तारीख|सर्वांना पाठव|सगळ्यांना पाठव",
    re.IGNORECASE,
)


def risk_flags(text: str, claims: list[Claim], language_code: str) -> list[RiskFlag]:
    flags: list[RiskFlag] = []
    scheme_message = any(c.topic in _SCHEME_TOPICS for c in claims)

    seen_domains: set[str] = set()
    for raw in _URL_RE.findall(text):
        url = raw if raw.lower().startswith("http") else "https://" + raw
        domain = sources.domain_of(url.rstrip(".,;:!?"))
        if not domain or domain in seen_domains:
            continue
        seen_domains.add(domain)
        if domain in _SHORTENERS:
            code = "short_link"
        elif sources.tier_of(url) != "official" and (scheme_message or _OFFICIAL_LOOKING.search(domain)):
            code = "unofficial_link"
        else:
            continue
        flags.append(RiskFlag(code=code, message=i18n.risk_text(code, language_code, domain=domain)))

    for code, pattern in (("personal_info", _PERSONAL_INFO), ("pressure", _PRESSURE)):
        if pattern.search(text):
            flags.append(RiskFlag(code=code, message=i18n.risk_text(code, language_code)))
    return flags
