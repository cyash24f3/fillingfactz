import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from filing_checker.models import Passage
from filing_checker.retrieval import read_page_context, read_passage, read_page_text


class PageBoundaryTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        database = Path(folder) / "corpus.sqlite"
        self.database_path = database
        self.enterContext(patch("filing_checker.retrieval.DATABASE_PATH", database))
        self.enterContext(patch("filing_checker.retrieval.load_filings",
                                return_value=[SimpleNamespace(filing_id="annual")]))
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE passages (passage_id TEXT, filing_id TEXT, payload TEXT)")
            for page in range(1, 4):
                for chunk in range(2):
                    text = ("Balance sheet (in thousands)" if page == 1 and chunk == 0
                            else "Continued table row 1,500")
                    passage = Passage(passage_id=f"annual:p{page}:c{chunk}",
                                      filing_id="annual", form="10-K", period_end=date(2024, 1, 31),
                                      filed_at=date(2024, 3, 7), source_url="https://example.com/filing",
                                      pdf_sha256="hash", pdf_page=page,
                                      page_start=chunk * 100, page_end=chunk * 100 + len(text), text=text)
                    connection.execute("INSERT INTO passages VALUES (?, ?, ?)",
                                       (passage.passage_id, passage.filing_id, passage.model_dump_json()))

    def test_continued_table_exposes_previous_header_and_bounded_navigation(self):
        result = read_page_context("annual", 2)
        self.assertEqual(len(result["passages"]), 3)
        self.assertIn("in thousands", result["passages"][0]["text"])
        self.assertEqual(len(result["navigation"]), 6)
        self.assertNotIn("annual:p2:c1", result["read_passage_ids"])
        self.assertEqual(read_passage("annual:p2:c1").text, "Continued table row 1,500")

    def test_first_page_does_not_attempt_page_zero(self):
        result = read_page_context("annual", 1)
        self.assertEqual([p["pdf_page"] for p in result["passages"]], [1, 2])

    def test_unknown_page_and_filing_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            read_page_context("annual", 9)
        with self.assertRaisesRegex(ValueError, "Unknown filing"):
            read_page_context("missing", 1)

    def test_full_page_reconstruction_removes_overlap_without_changing_source(self):
        original = "Column heading\nCash and cash equivalents 1,500 1,200\n"
        first = read_passage("annual:p1:c0").model_copy(update={
            "text": original[:35], "page_start": 0, "page_end": 35})
        second = read_passage("annual:p1:c1").model_copy(update={
            "text": original[25:], "page_start": 25, "page_end": len(original)})
        with sqlite3.connect(self.database_path) as database:
            for passage in (first, second):
                database.execute("UPDATE passages SET payload = ? WHERE passage_id = ?",
                                 (passage.model_dump_json(), passage.passage_id))
        self.assertEqual(read_page_text("annual", 1), original)

    def test_full_page_reconstruction_rejects_missing_text(self):
        with self.assertRaisesRegex(ValueError, "text gap"):
            read_page_text("annual", 1)


if __name__ == "__main__":
    unittest.main()
