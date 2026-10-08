from enum import Enum

from pydantic import BaseModel, Field


class Verdict(str, Enum):
    VERIFIED = "VERIFIED"
    FALSE = "FALSE"
    OUTDATED = "OUTDATED"
    PARTLY_SUPPORTED = "PARTLY_SUPPORTED"
    UNVERIFIABLE = "UNVERIFIABLE"


class Claim(BaseModel):
    id: str
    text: str  # standalone English restatement, used for searching
    original_span: str  # verbatim piece of the message, used for highlighting
    topic: str = "other"
    time_reference: str = ""


class Evidence(BaseModel):
    id: str
    url: str
    source_name: str
    domain: str
    tier: str  # official | fact_checker | news | other
    published_date: str = ""
    quote: str = ""
    stance: str = "context"  # supports | refutes | context
    independent: bool = True  # False when this is the very page the user asked us to check


class RiskFlag(BaseModel):
    code: str  # unofficial_link | short_link | personal_info | pressure
    message: str  # in the reply language


class Step(BaseModel):
    """One lookup made while researching a claim."""
    action: str  # search | fetch
    detail: str  # the search query, or the URL read


class ClaimResult(BaseModel):
    claim: Claim
    verdict: Verdict
    verdict_label: str = ""  # the verdict in the reply language
    confidence: str = "low"
    explanation: str = ""
    what_is_wrong: str = ""
    correct_information: str = ""
    true_as_of: str = ""
    changed_on: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    downgraded_from: Verdict | None = None
    validation_notes: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)


class CheckResult(BaseModel):
    source_kind: str = "text"  # text | image | pdf | audio | url
    input_text: str  # the message as text: typed, transcribed from audio, or read off the image
    language_code: str = "en"
    language_name: str = "English"
    reply_language: str = "English"
    reply_language_code: str = "en"
    overall_verdict: Verdict
    overall_label: str = ""  # the overall verdict in the reply language
    summary: str = ""
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    claims: list[ClaimResult] = Field(default_factory=list)
    backend: str = ""
    seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    checked_at: str = ""  # ISO time of the original check
    cached: bool = False  # answered from an earlier check of the same message
    times_checked: int = 1
    notes: list[str] = Field(default_factory=list)
