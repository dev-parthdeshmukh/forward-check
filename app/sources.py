"""Trusted-source allowlist. A domain matches if the host equals it or ends with '.<domain>'."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

OFFICIAL = {
    "gov.in", "nic.in", "gov", "gov.uk", "europa.eu", "who.int", "un.org", "unicef.org",
    "rbi.org.in", "npci.org.in", "sebi.gov.in", "worldbank.org", "imf.org", "nhs.uk",
    "icmr.org.in", "isro.gov.in",
}

FACT_CHECKER = {
    "altnews.in", "boomlive.in", "factly.in", "vishvasnews.com", "newschecker.in",
    "factcrescendo.com", "newsmeter.in", "thip.media", "logicallyfacts.com", "dfrac.org",
    "snopes.com", "politifact.com", "factcheck.org", "fullfact.org", "africacheck.org",
    "leadstories.com", "factcheck.afp.com", "thequint.com",
}

NEWS = {
    "reuters.com", "apnews.com", "afp.com", "bbc.com", "bbc.co.uk", "ptinews.com",
    "thehindu.com", "indianexpress.com", "hindustantimes.com", "indiatimes.com", "ndtv.com",
    "livemint.com", "business-standard.com", "indiatoday.in", "scroll.in", "theprint.in",
    "deccanherald.com", "theguardian.com", "nytimes.com", "aljazeera.com", "dw.com",
    "nature.com", "thelancet.com", "nejm.org", "bmj.com", "mayoclinic.org",
}

TIERS = (("official", OFFICIAL), ("fact_checker", FACT_CHECKER), ("news", NEWS))

_TRACKING_PARAMS = ("utm_", "fbclid", "gclid", "ref", "igshid")


def domain_of(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def tier_of(url: str) -> str:
    host = domain_of(url)
    for name, domains in TIERS:
        if any(host == d or host.endswith("." + d) for d in domains):
            return name
    return "other"


def is_trusted(url: str) -> bool:
    return tier_of(url) != "other"


def normalize_url(url: str) -> str:
    """Canonical form for comparing a cited URL against the URLs actually retrieved."""
    parts = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith(_TRACKING_PARAMS)]
    return urlunsplit(("https", domain_of(url), parts.path.rstrip("/"), urlencode(query), ""))


def describe_tiers() -> str:
    lines = []
    for name, domains in TIERS:
        lines.append(f"- {name}: " + ", ".join(sorted(domains)))
    return "\n".join(lines)
