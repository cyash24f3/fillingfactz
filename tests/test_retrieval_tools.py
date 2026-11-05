import unittest
from datetime import date
from unittest.mock import patch

from filing_checker.context_views import merge_passages
from filing_checker.ingestion import page_context
from filing_checker.models import Passage
from filing_checker.tools import search_and_read


def passage(pid):
    return Passage(passage_id=pid, filing_id="annual", form="10-K",
                   period_end=date(2024, 1, 31), filed_at=date(2024, 3, 7),
                   source_url="https://example.com/filing", pdf_sha256="hash",
                   pdf_page=1, page_start=0, page_end=40,
                   text="Subscription revenue accounted for 94%.",
                   page_context="Revenue (in thousands)")


def matches(*ids):
    return {"searched_filings": ["annual", "quarterly"],
            "matches": [{"passage_id": pid, "filing_id": "annual"} for pid in ids]}


class SearchFusionTests(unittest.TestCase):
    def test_agreement_between_original_and_plan_beats_unrelated_top_hit(self):
        with patch("filing_checker.tools.search_filings", side_effect=[
            matches("irrelevant", "revenue"), matches("revenue", "other"),
        ]) as search, patch("filing_checker.tools.read_passage", side_effect=passage) as read:
            result = search_and_read("revenue breakdown", additional_queries=["subscription revenue 94%"])
        self.assertEqual(result["read_passage_ids"], ["revenue"])
        self.assertEqual(result["searched_filings"], ["annual", "quarterly"])
        self.assertEqual(search.call_count, 2)
        read.assert_called_once_with("revenue")

    def test_single_query_keeps_requested_limit(self):
        with patch("filing_checker.tools.search_filings", return_value=matches("revenue")) as search, \
                patch("filing_checker.tools.read_passage", side_effect=passage):
            result = search_and_read("revenue", per_filing=1)
        search.assert_called_once_with(query="revenue", filing_id=None, per_filing=1)
        self.assertEqual(result["read_passage_ids"], ["revenue"])

    def test_duplicate_normalized_queries_are_searched_once(self):
        with patch("filing_checker.tools.search_filings", return_value=matches("revenue")) as search, \
                patch("filing_checker.tools.read_passage", side_effect=passage):
            search_and_read("CrowdStrike revenue", additional_queries=["revenue"])
        self.assertEqual(search.call_count, 1)

    def test_page_units_remain_available_after_passage_compaction(self):
        item = merge_passages([passage("revenue")])[0]
        self.assertEqual(item["page_context"], "Revenue (in thousands)")
        self.assertEqual(item["text"], "Subscription revenue accounted for 94%.")

    def test_units_after_long_intro_are_preserved_in_page_context(self):
        text = "Company\n" + "Introductory line\n" * 15 + "(in thousands, except per share data)\nCash 1000"
        self.assertIn("in thousands", page_context(text))


if __name__ == "__main__":
    unittest.main()
