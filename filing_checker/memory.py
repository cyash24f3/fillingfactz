import hashlib
import json
import re
import sqlite3
from contextlib import closing, contextmanager

from filing_checker.config import MEMORY_PATH
from filing_checker.evidence import find_original_quote
from filing_checker.models import Evidence, Passage
from filing_checker.retrieval import read_passage


STOP_WORDS = set(
    """
    a an the and or of to in on at by for from with
    is are was were be been being has have had
    it its this that these those as than
    do does did not no
    crowdstrike holdings inc company corporation
    """.split()
)


@contextmanager
def memory_database():
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(MEMORY_PATH, timeout=10.0)) as database:
        with database:
            database.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS
                evidence_memory USING fts5(
                    namespace UNINDEXED,
                    passage_id UNINDEXED,
                    filing_id UNINDEXED,
                    source_key UNINDEXED,
                    quote UNINDEXED,
                    text,
                    tokenize = 'porter unicode61'
                )
                """
            )

            yield database


def source_key(passage: Passage) -> str:
    text = json.dumps(
        passage.model_dump(mode="json"),
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def search_expression(statement: str) -> str:
    words = re.findall(
        r"[A-Za-z0-9]+",
        statement.casefold(),
    )

    # Preserve order while removing duplicates and common words.
    terms = list(dict.fromkeys(word for word in words if word not in STOP_WORDS))[:24]

    return " OR ".join(f'"{term}"' for term in terms)


def recall_evidence(
    statement: str,
    namespace: str,
    limit: int = 3,
) -> list[dict]:
    if not 1 <= limit <= 3:
        raise ValueError("Memory recall limit must be between 1 and 3.")

    expression = search_expression(statement)

    if not expression:
        return []

    with memory_database() as database:
        rows = database.execute(
            """
            SELECT passage_id, source_key, quote
            FROM evidence_memory
            WHERE evidence_memory MATCH ?
              AND namespace = ?
            ORDER BY bm25(evidence_memory)
            LIMIT ?
            """,
            (
                expression,
                namespace,
                limit * 8,
            ),
        ).fetchall()

    recalled = []
    seen = set()

    for passage_id, saved_key, saved_quote in rows:
        if passage_id in seen:
            continue

        try:
            passage = read_passage(passage_id)

            # Reject entries whose source text or metadata changed.
            if source_key(passage) != saved_key:
                continue

            if passage.is_toc:
                continue

            # Recheck the stored supporting quotation.
            find_original_quote(
                passage.text,
                saved_quote,
            )

        except (ValueError, KeyError, TypeError):
            # Removed passages or invalid old entries are cache misses.
            continue

        seen.add(passage_id)

        recalled.append(passage.model_dump(mode="json"))

        if len(recalled) >= limit:
            break

    return recalled


def remember_evidence(
    evidence: list[Evidence],
    namespace: str,
) -> int:
    rows = []
    seen = set()

    for item in evidence:
        if item.passage_id in seen:
            continue

        passage = read_passage(item.passage_id)

        if passage.pdf_sha256 != item.pdf_sha256:
            raise ValueError("The source changed before memory could be saved.")

        quote = find_original_quote(
            passage.text,
            item.quote,
        )

        seen.add(passage.passage_id)

        rows.append(
            (
                namespace,
                passage.passage_id,
                passage.filing_id,
                source_key(passage),
                quote,
                passage.text,
            )
        )

    if not rows:
        return 0

    with memory_database() as database:
        for row in rows:
            # Keep one entry per passage within each namespace.
            database.execute(
                """
                DELETE FROM evidence_memory
                WHERE namespace = ?
                  AND passage_id = ?
                """,
                (namespace, row[1]),
            )

            database.execute(
                """
                INSERT INTO evidence_memory (
                    namespace,
                    passage_id,
                    filing_id,
                    source_key,
                    quote,
                    text
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                row,
            )

    return len(rows)
