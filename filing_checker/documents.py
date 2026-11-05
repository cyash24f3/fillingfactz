import json

from filing_checker.config import MANIFEST_PATH
from filing_checker.models import Filing


def load_filings() -> list[Filing]:
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    records = json.loads(text)

    filings = [Filing.model_validate(record) for record in records]

    identifiers = [filing.filing_id for filing in filings]

    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Filing IDs must be unique")

    return filings


def list_filings() -> list[dict]:
    """List the available filings and their reporting dates."""
    return [
        filing.model_dump(mode="json", exclude={"filename"})
        for filing in load_filings()
    ]
