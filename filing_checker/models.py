from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Filing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filing_id: str
    form: Literal["10-K", "10-Q"]
    period_end: date
    filed_at: date
    filename: str
    source_url: str


class Passage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage_id: str
    filing_id: str
    form: Literal["10-K", "10-Q"]
    period_end: date
    filed_at: date
    source_url: str
    pdf_sha256: str

    pdf_page: int = Field(ge=1)
    page_start: int = Field(ge=0)
    page_end: int = Field(ge=1)

    text: str
    is_toc: bool = False
    page_context: str = ""


Verdict = Literal[
    "SUPPORTED",
    "CONTRADICTED",
    "OUTDATED",
    "NOT_ENOUGH_INFO",
]


class CitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passage_id: str = Field(min_length=1)
    quote: str = Field(min_length=1, max_length=4000)


class VerdictCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence: list[CitationRequest] = Field(
        default_factory=list,
        max_length=8,
    )
    explanation: str = Field(
        min_length=10,
        max_length=3000,
        description="Brief final explanation comparing the claim with the cited evidence.",
    )
    verdict: Verdict = Field(
        description="Final classification consistent with the evidence and explanation.",
    )


class Evidence(CitationRequest):
    filing_id: str
    form: str
    period_end: date
    filed_at: date
    pdf_page: int
    source_url: str
    pdf_sha256: str


class ClaimPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=1)
    relation: str = Field(min_length=1)
    object: str = Field(min_length=1)

    attribution: str | None
    time_reference: str | None

    topics: list[str] = Field(min_length=1, max_length=6)
    search_queries: list[str] = Field(min_length=1, max_length=4)

    @field_validator(
        "attribution",
        "time_reference",
        mode="before",
    )
    @classmethod
    def normalize_missing_text(cls, value):
        if isinstance(value, str):
            return value.strip() or None

        return value


class MemoryStats(BaseModel):
    enabled: bool = False
    namespace: str | None = None

    recalled_passage_ids: list[str] = Field(default_factory=list)
    saved_passages: int = 0

    recall_calls: int = 0
    write_calls: int = 0


class VerificationResult(BaseModel):
    statement: str
    verdict: Verdict
    explanation: str
    evidence: list[Evidence]

    status: Literal["complete", "incomplete"]
    stop_reason: str
    memory: MemoryStats = Field(default_factory=MemoryStats)
    model_calls: int
    tool_calls: int
    input_tokens: int | None
    output_tokens: int | None
    elapsed_seconds: float

    searched_filings: list[str]
    read_passage_ids: list[str]
    trace: list[dict]
    research_plan: ClaimPlan | None = None

    decomposer_status: Literal[
        "disabled",
        "validated",
        "fallback",
    ] = "disabled"
