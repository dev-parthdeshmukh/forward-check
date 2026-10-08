"""Google Fact Check Tools API: published fact-checks that may already cover a claim."""
from dataclasses import dataclass

import httpx

from . import config

_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


@dataclass
class SeedFactCheck:
    url: str
    publisher: str
    review_date: str
    reviewed_claim: str
    rating: str
    title: str


def search(query: str, language_code: str = "", limit: int = 5) -> list[SeedFactCheck]:
    """Keyword search, so results can be off-topic; the judge decides what is relevant."""
    if not config.FACTCHECK_API_KEY or not query.strip():
        return []
    params = {"query": query[:300], "pageSize": limit}
    if language_code:
        params["languageCode"] = language_code
    try:
        resp = httpx.get(_URL, params=params, headers={"x-goog-api-key": config.FACTCHECK_API_KEY}, timeout=20)
        resp.raise_for_status()
    except httpx.HTTPError:
        return []
    hits = []
    for claim in resp.json().get("claims", []):
        for review in claim.get("claimReview", []):
            if not review.get("url"):
                continue
            hits.append(SeedFactCheck(
                url=review["url"],
                publisher=review.get("publisher", {}).get("name", ""),
                review_date=(review.get("reviewDate") or claim.get("claimDate") or "")[:10],
                reviewed_claim=claim.get("text", ""),
                rating=review.get("textualRating", ""),
                title=review.get("title", ""),
            ))
    return hits
