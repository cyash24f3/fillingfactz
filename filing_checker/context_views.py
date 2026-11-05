import json
import re

from filing_checker.models import Passage


def compact_text(text):
    lines = []

    for line in text.splitlines():
        line = line.strip()

        if (
            not line
            or line.casefold() == "table of contents"
            or line.startswith("https://www.sec.gov/Archives/edgar/")
            or re.match(
                r"^\d{2}/\d{2}/\d{4},\s*\d{2}:\d{2}"
                r"\s+crwd-\d{8}$",
                line,
            )
        ):
            continue

        lines.append(re.sub(r"[ \t]+", " ", line))

    return "\n".join(lines)


def compact_passage(passage):
    item = passage.model_dump(mode="json") if isinstance(passage, Passage) else passage

    return {
        "passage_id": item["passage_id"],
        "filing_id": item["filing_id"],
        "pdf_page": item["pdf_page"],
        "period_end": item["period_end"],
        "filed_at": item["filed_at"],
        "page_context": compact_text(item.get("page_context", "")),
        "text": compact_text(item["text"]),
    }


def merge_passages(*groups):
    merged = {}

    for group in groups:
        for passage in group:
            item = compact_passage(passage)
            merged[item["passage_id"]] = item

    return list(merged.values())


def packed_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    )
