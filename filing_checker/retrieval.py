import re
import sqlite3
from contextlib import closing

from filing_checker.config import DATABASE_PATH
from filing_checker.documents import load_filings
from filing_checker.models import Passage


def require_database():
    if not DATABASE_PATH.is_file():
        raise RuntimeError("The corpus is not prepared. Run python prepare.py first.")


def search_filings(
    query: str,
    filing_id: str | None = None,
    per_filing: int = 2,
) -> dict:
    """Search filing passages and return source-labelled snippets."""
    require_database()

    if not 1 <= per_filing <= 3:
        raise ValueError("per_filing must be between 1 and 3")

    known_ids = [filing.filing_id for filing in load_filings()]

    if filing_id is not None:
        if filing_id not in known_ids:
            raise ValueError("Unknown filing ID: " + filing_id)

        selected_ids = [filing_id]

    else:
        selected_ids = known_ids

    terms = re.findall(r"[A-Za-z0-9]+", query)[:24]

    if not terms:
        raise ValueError("Search requires at least one word or number")

    expression = " OR ".join(f'"{term}"' for term in terms)

    matches = []

    with closing(sqlite3.connect(DATABASE_PATH)) as database:
        for current_id in selected_ids:
            rows = database.execute(
                """
                SELECT
                    payload,
                    snippet(
                        passages, 3, '', '', ' … ', 40
                    )
                FROM passages
                WHERE passages MATCH ?
                  AND filing_id = ?
                  AND CAST(is_toc AS INTEGER) = 0
                ORDER BY bm25(passages)
                LIMIT ?
                """,
                (
                    expression,
                    current_id,
                    per_filing,
                ),
            ).fetchall()

            for payload, snippet in rows:
                passage = Passage.model_validate_json(payload)

                matches.append(
                    {
                        "passage_id": passage.passage_id,
                        "filing_id": passage.filing_id,
                        "form": passage.form,
                        "period_end": passage.period_end.isoformat(),
                        "filed_at": passage.filed_at.isoformat(),
                        "pdf_page": passage.pdf_page,
                        "snippet": snippet,
                    }
                )

    return {
        "query": query,
        "searched_filings": selected_ids,
        "matches": matches,
    }


def read_passage(passage_id: str) -> Passage:
    """Read the complete indexed passage using its ID."""
    require_database()

    with closing(sqlite3.connect(DATABASE_PATH)) as database:
        row = database.execute(
            "SELECT payload FROM passages WHERE passage_id = ?",
            (passage_id,),
        ).fetchone()

    if row is None:
        raise ValueError("Unknown passage ID: " + passage_id)

    return Passage.model_validate_json(row[0])


def read_page_text(filing_id: str, pdf_page: int) -> str:
    """Reassemble one canonical page from its overlapping stored chunks."""
    require_database()
    with closing(sqlite3.connect(DATABASE_PATH)) as database:
        rows = database.execute(
            "SELECT payload FROM passages WHERE filing_id = ? "
            "AND CAST(json_extract(payload, '$.pdf_page') AS INTEGER) = ? "
            "ORDER BY CAST(json_extract(payload, '$.page_start') AS INTEGER)",
            (filing_id, pdf_page),
        ).fetchall()
    if not rows:
        raise ValueError("The requested page has no indexed text")
    text = ""
    for (payload,) in rows:
        passage = Passage.model_validate_json(payload)
        if passage.page_start > len(text):
            raise ValueError("The page index contains a text gap")
        text += passage.text[max(0, len(text) - passage.page_start):]
    return text


def read_page_context(filing_id: str, pdf_page: int) -> dict:
    """Read the first chunk of this page and its neighbours; list remaining IDs.

    At most three complete chunks enter model context. Additional row chunks
    can be requested explicitly using the returned navigation IDs.
    """
    require_database()
    if pdf_page < 1:
        raise ValueError("PDF page must be positive")
    known_ids = {filing.filing_id for filing in load_filings()}
    if filing_id not in known_ids:
        raise ValueError("Unknown filing ID: " + filing_id)
    with closing(sqlite3.connect(DATABASE_PATH)) as database:
        rows = database.execute(
            "SELECT payload FROM passages WHERE filing_id = ? "
            "AND CAST(json_extract(payload, '$.pdf_page') AS INTEGER) BETWEEN ? AND ? "
            "ORDER BY CAST(json_extract(payload, '$.pdf_page') AS INTEGER), "
            "CAST(json_extract(payload, '$.page_start') AS INTEGER)",
            (filing_id, max(1, pdf_page - 1), pdf_page + 1),
        ).fetchall()
    passages = [Passage.model_validate_json(row[0]) for row in rows]
    if not any(p.pdf_page == pdf_page for p in passages):
        raise ValueError("The requested PDF page does not exist")
    headers = {}
    for passage in passages:
        headers.setdefault(passage.pdf_page, passage)
    from filing_checker.context_views import compact_passage
    selected = list(headers.values())
    return {
        "filing_id": filing_id,
        "requested_page": pdf_page,
        "passages": [compact_passage(p) for p in selected],
        "read_passage_ids": [p.passage_id for p in selected],
        "navigation": [{"pdf_page": p.pdf_page, "passage_id": p.passage_id}
                       for p in passages],
        "instruction": "First chunks of adjacent pages expose table headings and units. "
                       "Navigation-only IDs must be read with read_passage before citing.",
    }
