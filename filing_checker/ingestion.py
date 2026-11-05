import hashlib
import json
import re
import sqlite3
from contextlib import closing

import pymupdf

from filing_checker.config import (
    RAW_DIR,
    RUNTIME_DIR,
    DATABASE_PATH,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    INDEX_VERSION,
)
from filing_checker.documents import load_filings
from filing_checker.models import Filing, Passage
from filing_checker.context_views import compact_text


def fingerprint(value: dict) -> str:
    text = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def page_context(text: str) -> str:
    """Retain page headings and unit disclosures for chunks below a table header."""
    lines = compact_text(text).splitlines()
    headings = lines[:5]
    units = [line for line in lines if re.search(
        r"\bin\s+(?:thousands|millions|billions)\b", line, re.IGNORECASE,
    )]
    return "\n".join(dict.fromkeys([*headings, *units]))[:1200]


def parse_pdf(filing: Filing, pdf_bytes: bytes, pdf_hash: str) -> list[Passage]:
    passages = []
    step = CHUNK_SIZE - CHUNK_OVERLAP

    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for page_index, page in enumerate(pdf):
            text = page.get_text("text", sort=True)
            context = page_context(text)

            item_headings = re.findall(r"(?im)^\s*Item\s+\d", text)

            is_toc = (
                page_index < 6
                and "table of contents" in text.casefold()
                and len(item_headings) >= 4
            )

            for chunk_index, start in enumerate(range(0, len(text), step)):
                end = min(start + CHUNK_SIZE, len(text))
                chunk = text[start:end]

                if chunk.strip():
                    passages.append(
                        Passage(
                            passage_id=(
                                f"{filing.filing_id}:p{page_index + 1}:c{chunk_index}"
                            ),
                            filing_id=filing.filing_id,
                            form=filing.form,
                            period_end=filing.period_end,
                            filed_at=filing.filed_at,
                            source_url=filing.source_url,
                            pdf_sha256=pdf_hash,
                            pdf_page=page_index + 1,
                            page_start=start,
                            page_end=end,
                            text=chunk,
                            is_toc=is_toc,
                            page_context=context,
                        )
                    )

                if end == len(text):
                    break

    if not passages:
        raise ValueError(
            f"No readable text found in {filing.filename}. "
            "Check whether the PDF requires OCR."
        )

    return passages


def prepare_corpus(force: bool = False) -> dict:
    filings = load_filings()

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    parsed_dir = RUNTIME_DIR / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)

    sources = []

    for filing in filings:
        path = RAW_DIR / filing.filename

        if not path.is_file():
            raise FileNotFoundError(f"Missing PDF: {path}")

        pdf_bytes = path.read_bytes()
        pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

        key = fingerprint(
            {
                "filing": filing.model_dump(mode="json"),
                "pdf_hash": pdf_hash,
                "parser_version": pymupdf.VersionBind,
                "index_version": INDEX_VERSION,
                "chunk_size": CHUNK_SIZE,
                "overlap": CHUNK_OVERLAP,
            }
        )

        sources.append((filing, pdf_bytes, pdf_hash, key))

    corpus_key = fingerprint({"sources": [source[3] for source in sources]})

    if DATABASE_PATH.exists() and not force:
        try:
            with closing(sqlite3.connect(DATABASE_PATH)) as database:
                row = database.execute(
                    "SELECT value FROM index_meta WHERE key = 'fingerprint'"
                ).fetchone()

                if row and row[0] == corpus_key:
                    count = database.execute(
                        "SELECT COUNT(*) FROM passages"
                    ).fetchone()[0]

                    return {
                        "index": "cache_hit",
                        "filings": len(filings),
                        "passages": count,
                    }

        except sqlite3.DatabaseError:
            # An absent or outdated schema needs rebuilding.
            pass

    all_passages = []
    parsed_pdfs = 0
    reused_pdfs = 0

    for filing, pdf_bytes, pdf_hash, key in sources:
        cache_path = parsed_dir / (filing.filing_id + ".json")

        passages = None

        if cache_path.exists() and not force:
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))

                if cached["fingerprint"] == key:
                    loaded = [
                        Passage.model_validate(item) for item in cached["passages"]
                    ]

                    if loaded:
                        passages = loaded

            except (
                ValueError,
                KeyError,
                TypeError,
            ):
                passages = None

        if passages is None:
            passages = parse_pdf(filing, pdf_bytes, pdf_hash)
            parsed_pdfs += 1

            cache_path.write_text(
                json.dumps(
                    {
                        "fingerprint": key,
                        "passages": [
                            passage.model_dump(mode="json") for passage in passages
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        else:
            reused_pdfs += 1

        all_passages.extend(passages)

    with closing(sqlite3.connect(DATABASE_PATH)) as database:
        with database:
            database.execute("BEGIN")

            database.execute("DROP TABLE IF EXISTS passages")
            database.execute("DROP TABLE IF EXISTS index_meta")

            database.execute("""
                CREATE VIRTUAL TABLE passages USING fts5(
                    passage_id UNINDEXED,
                    filing_id UNINDEXED,
                    is_toc UNINDEXED,
                    text,
                    payload UNINDEXED,
                    tokenize = 'porter unicode61'
                )
            """)

            database.execute("""
                CREATE TABLE index_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            database.executemany(
                "INSERT INTO passages "
                "(passage_id, filing_id, is_toc, text, payload) "
                "VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        passage.passage_id,
                        passage.filing_id,
                        int(passage.is_toc),
                        passage.text,
                        passage.model_dump_json(),
                    )
                    for passage in all_passages
                ],
            )

            database.execute(
                "INSERT INTO index_meta VALUES (?, ?)",
                ("fingerprint", corpus_key),
            )

    return {
        "index": "rebuilt",
        "filings": len(filings),
        "passages": len(all_passages),
        "parsed_pdfs": parsed_pdfs,
        "reused_pdfs": reused_pdfs,
    }
