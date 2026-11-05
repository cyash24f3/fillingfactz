import re
from decimal import Decimal
from difflib import SequenceMatcher

from filing_checker.documents import load_filings
from filing_checker.models import (
    VerdictCandidate,
    Evidence,
)
from filing_checker.retrieval import read_passage


MONEY_PATTERN = re.compile(
    r"(?:\bUSD\b|US\$|\$)\s*(\d[\d,]*(?:\.\d+)?)"
    r"(?:\s*(thousand|million|billion|bn|mn|[kmb])\b)?", re.IGNORECASE,
)
MONEY_SCALES = {None: Decimal(1), "thousand": Decimal(1000), "k": Decimal(1000),
                "million": Decimal(1000000), "mn": Decimal(1000000), "m": Decimal(1000000),
                "billion": Decimal(1000000000), "bn": Decimal(1000000000), "b": Decimal(1000000000)}


def simple_monetary_claim(statement: str) -> bool:
    return not re.search(
        r"\b(?:not|never|no)\b|n't|[<>]|\b(?:at\s+(?:least|most)|"
        r"(?:more|less|greater|lower|higher)\s+than|above|below|over|under|exceeds?)\b",
        statement, re.IGNORECASE,
    )


METRIC_PATTERNS = {
    "subscription revenue": (
        r"\bsubscription\s+revenues?\b",
        r"\bsubscription\b",
    ),
    "professional services": (
        r"\bprofessional\s+services(?:\s+revenues?)?\b",
        r"\bprofessional\s+services\b",
    ),
    "total revenue": (
        r"\btotal\s+revenues?\b",
        r"\btotal\s+revenues?\b",
    ),
    "cash and cash equivalents": (
        r"\bcash\s+(?:and|&)\s+cash\s+equivalents\b",
        r"\bcash\s+(?:and|&)\s+cash\s+equivalents\b",
    ),
    "accounts receivable": (
        r"\baccounts\s+receivable\b",
        r"\baccounts\s+receivable\b",
    ),
    "total current assets": (
        r"\btotal\s+current\s+assets\b",
        r"\btotal\s+current\s+assets\b",
    ),
    "total assets": (
        r"\btotal\s+assets\b",
        r"\btotal\s+assets\b",
    ),
    "total current liabilities": (
        r"\btotal\s+current\s+liabilities\b",
        r"\btotal\s+current\s+liabilities\b",
    ),
    "total liabilities": (
        r"\btotal\s+liabilities\b",
        r"\btotal\s+liabilities\b",
    ),
}


def check_verdict_consistency(candidate: VerdictCandidate) -> None:
    """Reject an explicit final classification that disagrees with the label.

    Only a final sentence naming an uppercase verdict is checked. This
    deliberately avoids interpreting general prose or mentions of earlier
    support as an instruction to change a verdict.
    """
    conclusion = re.search(
        r"(?i:\b(?:statement|claim|verdict)\s+(?:is|should\s+be|:)\s*)"
        r"\**(SUPPORTED|CONTRADICTED|OUTDATED|NOT_ENOUGH_INFO)\b"
        r"[^.!?]*[.!?]?\s*$",
        candidate.explanation,
    )
    if conclusion and conclusion.group(1) != candidate.verdict:
        raise ValueError(
            f"The verdict field says {candidate.verdict}, but the final "
            f"explanation concludes {conclusion.group(1)}. Reconcile the "
            "classification with the evidence and submit one consistent result."
        )


def check_supported_metrics(
    statement: str,
    candidate: VerdictCandidate,
    evidence: list[Evidence],
) -> None:
    """Reject support based only on a different named financial metric.

    This checks citation labels, not numerical or temporal entailment.
    Table rows may abbreviate a metric, such as 'Subscription' under
    a revenue heading, so source aliases are allowed.
    """
    if candidate.verdict != "SUPPORTED":
        return

    missing = [
        metric
        for metric, (claim_pattern, source_pattern) in METRIC_PATTERNS.items()
        if re.search(claim_pattern, statement, re.IGNORECASE)
        and not any(
            re.search(source_pattern, item.quote, re.IGNORECASE)
            for item in evidence
        )
    ]

    if missing:
        raise ValueError(
            "SUPPORTED citations do not identify the claimed metric(s): "
            + ", ".join(missing)
            + ". A matching amount in a different metric's row is insufficient. "
            "Check the requested row label, value, period and units; "
            "then choose the verdict warranted by that evidence."
        )


def check_financial_amount(
    statement: str,
    candidate: VerdictCandidate,
    evidence: list[Evidence],
    read_passage_ids: set[str] | None = None,
) -> None:
    """Check simple dollar claims against explicitly scaled numeric table rows.

    This is intentionally limited: one amount, one named metric, a numeric
    row, and an unambiguous page unit. Other claims remain model judgments.
    First-column comparisons are limited to the filing's reporting year.
    """
    if candidate.verdict not in {"SUPPORTED", "CONTRADICTED"} or not simple_monetary_claim(statement):
        return
    amounts = list(MONEY_PATTERN.finditer(statement))
    metrics = [source for claim, source in METRIC_PATTERNS.values()
               if re.search(claim, statement, re.IGNORECASE)]
    if len(amounts) != 1 or len(metrics) != 1:
        return

    scales = MONEY_SCALES
    number, suffix = amounts[0].groups()
    scale = scales[suffix.casefold() if suffix else None]
    claimed = Decimal(number.replace(",", "")) * scale
    # Rounded scale expressions (e.g. 3.06 billion) carry the precision of
    # their last digit; explicit exactness disables this allowance.
    precision = len(number.partition(".")[2])
    tolerance = (scale * Decimal(10) ** -precision / 2
                 if suffix and not re.search(r"\bexact(?:ly)?\b", statement, re.I)
                 else Decimal(0))
    years = {int(value) for value in re.findall(r"\b(?:19|20)\d{2}\b", statement)}
    current = bool(re.search(
        r"\b(?:latest|currently|current(?!\s+(?:assets|liabilities)\b)"
        r"|most\s+recent(?:ly)?(?:\s+reported)?)\b",
        statement, re.IGNORECASE,
    ))
    sources = [(read_passage(item.passage_id), item.quote) for item in evidence]
    if candidate.verdict == "CONTRADICTED" and current:
        cited_ids = {item.passage_id for item in evidence}
        for pid in sorted((read_passage_ids or set()) - cited_ids):
            passage = read_passage(pid)
            sources.append((passage, passage.text))
    observations = []
    for passage, text in sources:
        if years and passage.period_end.year not in years:
            continue
        unit_names = set(re.findall(
            r"\bin\s+(thousands|millions|billions)\b",
            passage.page_context, re.IGNORECASE,
        ))
        unit_names = {value.casefold() for value in unit_names}
        if len(unit_names) != 1:
            continue
        source_scale = scales[next(iter(unit_names)).removesuffix("s")]
        for row in text.splitlines():
            match = re.fullmatch(
                r"\s*" + metrics[0] + r"\s+\$?\s*"
                r"(\d[\d,]*(?:\.\d+)?)([\s\d,$.()%\-]*)",
                row, re.IGNORECASE,
            )
            if match and not match.group(2).lstrip().startswith("%"):
                value = Decimal(match.group(1).replace(",", "")) * source_scale
                observations.append((passage.filed_at, value))
    if not observations:
        return

    def matches(value):
        return abs(value - claimed) <= tolerance

    relevant = observations
    if current:
        latest = max(date for date, _ in observations)
        relevant = [(date, value) for date, value in observations if date == latest]
    if candidate.verdict == "SUPPORTED" and not any(matches(value) for _, value in relevant):
        raise ValueError(
            "The cited numeric row, after applying the page's table units, "
            "does not match the claimed dollar amount. Recheck the row, "
            "reporting period and scale before submitting a verdict."
        )
    if candidate.verdict == "CONTRADICTED" and all(matches(value) for _, value in relevant):
        raise ValueError(
            "The cited numeric rows match the claimed amount after units and "
            "rounding. These rows do not contradict the amount. Recheck the "
            "metric and reporting period, then submit the warranted verdict."
        )
    if candidate.verdict == "CONTRADICTED" and current and any(
        matches(older_value) and newer_date > older_date and not matches(newer_value)
        for older_date, older_value in observations
        for newer_date, newer_value in observations
    ):
        raise ValueError(
            "An earlier loaded row matches the claimed amount, and a later "
            "filing changes the same metric. For this current/latest claim, "
            "the verdict policy calls for OUTDATED rather than CONTRADICTED. "
            "Verify the periods, cite both filings, and submit a consistent classification."
        )


def check_rounding_contradiction(statement: str, candidate: VerdictCandidate,
                                 evidence: list[Evidence]) -> None:
    """A coarse rounded disclosure cannot disprove an overlapping finer amount."""
    if candidate.verdict != "CONTRADICTED" or not simple_monetary_claim(statement):
        return
    claimed_amounts = list(MONEY_PATTERN.finditer(statement))
    matching_metrics = [claim for claim, _ in METRIC_PATTERNS.values()
                        if re.search(claim, statement, re.I)]
    if len(claimed_amounts) != 1 or len(matching_metrics) != 1:
        return

    def interval(match, exact=False):
        number, suffix = match.groups()
        scale = MONEY_SCALES[suffix.casefold() if suffix else None]
        value = Decimal(number.replace(",", "")) * scale
        precision = len(number.partition(".")[2])
        tolerance = scale * Decimal(10) ** -precision / 2 if suffix and not exact else Decimal(0)
        return value - tolerance, value + tolerance

    lower, upper = interval(claimed_amounts[0], bool(re.search(r"\bexact(?:ly)?\b", statement, re.I)))
    claim_years = set(re.findall(r"\b(?:19|20)\d{2}\b", statement))
    for item in evidence:
        if not re.search(matching_metrics[0].replace(r"total\s+", ""), item.quote, re.I):
            continue
        source_amounts = list(MONEY_PATTERN.finditer(item.quote))
        quote_years = set(re.findall(r"\b(?:19|20)\d{2}\b", item.quote))
        for index, amount in enumerate(source_amounts):
            if not amount.group(2):
                continue
            end = source_amounts[index + 1].start() if index + 1 < len(source_amounts) else len(item.quote)
            following = item.quote[amount.end():end]
            explicit_year = re.match(r"\s+(?:in|for)\s+(?:the\s+)?(?:fiscal\s+)?(?:year\s+)?((?:19|20)\d{2})\b", following, re.I)
            source_years = ({explicit_year.group(1)} if explicit_year else
                            quote_years or {str(item.period_end.year)})
            if claim_years and (len(source_years) > 1 or not claim_years.intersection(source_years)):
                continue
            prefix = item.quote[max(0, amount.start() - 25):amount.start()]
            source_lower, source_upper = interval(amount, bool(re.search(r"\bexact(?:ly)?\b", prefix, re.I)))
            if max(lower, source_lower) <= min(upper, source_upper):
                raise ValueError(
                    "The rounded monetary disclosure overlaps the claimed amount's "
                    "precision range, so this quotation alone does not contradict it. "
                    f"Claim range: {lower} to {upper} dollars; source range: "
                    f"{source_lower} to {source_upper} dollars. Read the exact metric "
                    "in the financial statement table for the stated period before deciding."
                )


def check_employee_scope(statement: str, candidate: VerdictCandidate, evidence: list[Evidence]) -> None:
    """Do not infer a regional headcount from a company-wide employee total."""
    if candidate.verdict not in {"SUPPORTED", "CONTRADICTED"}:
        return
    claim = re.search(
        r"\b(\d[\d,]*)\s+([A-Za-z.]+)[ -]based\s+(?:full[ -]time\s+)?employees\b",
        statement, re.IGNORECASE,
    )
    if not claim:
        return
    count = int(claim.group(1).replace(",", ""))
    scope = claim.group(2).casefold().replace(".", "")
    if scope in {"global", "globally", "worldwide"}:
        return
    aliases = {"us": r"(?:US|U\.S\.|United States)",
               "uk": r"(?:UK|U\.K\.|United Kingdom)"}
    scope_pattern = r"(?<!\w)" + aliases.get(scope, re.escape(scope)) + r"(?!\w)"
    quotes = "\n".join(item.quote for item in evidence)
    # A location mention in another sentence (e.g. union representation)
    # does not scope the numeric headcount. Require a direct count relation.
    number = r"\b\d[\d,]*"
    full_time = r"(?:full[ -]time\s+)?"
    location = scope_pattern + r"(?:[ -]based)?"
    scoped_count = (
        number + r"\s+" + full_time + location + r"\s+" + full_time + r"employees\b"
        + "|" + number + r"\s+" + full_time
        + r"employees\s+(?:based\s+in|in)\s+(?:the\s+)?" + scope_pattern
        + "|" + location + r"\s+(?:employee\s+)?headcount\s*(?:of|was|is|:)\s*" + number
    )
    if re.search(scoped_count, quotes, re.IGNORECASE):
        return
    totals = [int(value.replace(",", "")) for value in re.findall(
        r"\b(\d[\d,]*)\s+(?:full[ -]time\s+)?employees\b", quotes, re.IGNORECASE,
    )]
    if not totals:
        return
    # A subset larger than every quoted total can be disproved by that
    # upper bound. A smaller subset can coexist with the larger total.
    if candidate.verdict == "CONTRADICTED" and count > max(totals):
        return
    raise ValueError(
        "The claim specifies a regional employee population, but these "
        "quotations report an unqualified/company-wide total. That total "
        "alone cannot establish the regional count or contradict a smaller "
        "regional subset. Look for region-specific evidence; if the filings "
        "do not disclose it, use NOT_ENOUGH_INFO rather than inferring a count."
    )


def normalise_with_positions(text):
    characters = []
    positions = []

    replacements = {
        "’": "'",
        "‘": "'",
        "“": '"',
        "”": '"',
    }

    for position, character in enumerate(text):
        character = replacements.get(
            character,
            character,
        )
        if character in {"'", '"'}:
            # Preserve internal apostrophes while matching external quote
            # styles consistently. Reports still recover original source text.
            internal_apostrophe = (
                character == "'" and position > 0 and position + 1 < len(text)
                and text[position - 1].isalnum() and text[position + 1].isalnum()
            )
            character = "'" if internal_apostrophe else '"'

        if character.isspace():
            if characters and characters[-1] != " ":
                characters.append(" ")
                positions.append(position)

        else:
            characters.append(character)
            positions.append(position)

    while characters and characters[-1] == " ":
        characters.pop()
        positions.pop()

    return "".join(characters), positions


def find_original_quote(source_text, requested_quote):
    normal_source, positions = normalise_with_positions(source_text)
    normal_quote, _ = normalise_with_positions(requested_quote)

    if not normal_quote:
        raise ValueError("The quotation is empty")

    location = normal_source.find(normal_quote)

    if location == -1:
        raise ValueError("The quotation does not occur in the passage")

    start = positions[location]
    end = positions[location + len(normal_quote) - 1] + 1

    return source_text[start:end]


def suggest_continuous_quote(source_text: str, requested_quote: str) -> str | None:
    """Return a substantial, literal shared span, never repair missing words."""
    source, _ = normalise_with_positions(source_text)
    requested, _ = normalise_with_positions(requested_quote)
    match = SequenceMatcher(None, requested, source, autojunk=False).find_longest_match()
    if match.size < 24:
        return None
    suggestion = source[match.b:match.b + match.size].strip()
    if re.search(r"\d", requested) and not re.search(r"\d", suggestion):
        return None
    # A shortened suggestion remains continuous and is rechecked against the
    # original source; no synthetic punctuation or omitted internal words.
    suggestion = suggestion[:400].rstrip()
    find_original_quote(source_text, suggestion)
    return suggestion


def validate_candidate(
    candidate: VerdictCandidate,
    searched_filings: set[str],
    read_passage_ids: set[str],
    statement: str = "",
) -> list[Evidence]:
    check_verdict_consistency(candidate)
    required_filings = {filing.filing_id for filing in load_filings()}

    if not required_filings.issubset(searched_filings):
        raise ValueError(
            "Search all supplied filings before submitting a final verdict."
        )

    if candidate.verdict != "NOT_ENOUGH_INFO" and not candidate.evidence:
        raise ValueError("This verdict requires supporting citations")

    evidence = []
    seen = set()

    for citation in candidate.evidence:
        if citation.passage_id not in read_passage_ids:
            raise ValueError(
                "Read the complete passage before citing it: " + citation.passage_id
            )

        passage = read_passage(citation.passage_id)

        try:
            original_quote = find_original_quote(
                passage.text,
                citation.quote,
            )

        except ValueError as error:
            suggestion = suggest_continuous_quote(passage.text, citation.quote)
            guidance = (
                " Continuous excerpt available in this same passage: "
                + repr(suggestion)
                + ". Use it only if it supports your reasoning."
                if suggestion else ""
            )
            raise ValueError(
                f"Invalid quotation in passage "
                f"{citation.passage_id}: {error}. "
                f"Rejected quotation: {citation.quote[:300]!r}. "
                "Use a short, continuous quotation from this passage. "
                "Do not combine separate sentences or omit words "
                "inside the quotation. Page units need not be joined to a row quote."
                + guidance
            ) from error

        key = (passage.passage_id, original_quote)

        if key in seen:
            continue

        seen.add(key)

        evidence.append(
            Evidence(
                passage_id=passage.passage_id,
                quote=original_quote,
                filing_id=passage.filing_id,
                form=passage.form,
                period_end=passage.period_end,
                filed_at=passage.filed_at,
                pdf_page=passage.pdf_page,
                source_url=passage.source_url,
                pdf_sha256=passage.pdf_sha256,
            )
        )

    check_financial_amount(statement, candidate, evidence, read_passage_ids)
    check_rounding_contradiction(statement, candidate, evidence)
    check_employee_scope(statement, candidate, evidence)

    if candidate.verdict == "OUTDATED":
        filing_ids = {item.filing_id for item in evidence}

        if len(filing_ids) < 2:
            raise ValueError(
                "OUTDATED requires evidence from at least two different filings."
            )

    return evidence
