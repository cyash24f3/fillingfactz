import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from filing_checker.memory import recall_evidence, remember_evidence, memory_terms
from filing_checker.models import Passage, Evidence


class EvidenceRecallTests(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(patch("filing_checker.memory.MEMORY_PATH", Path(folder) / "memory.sqlite"))
        self.passages = {}
        self.read = self.enterContext(patch("filing_checker.memory.read_passage",
                                            side_effect=lambda pid: self.passages[pid]))

    def store(self, pid, text, namespace="test"):
        passage = Passage(passage_id=pid, filing_id="annual", form="10-K",
                          period_end=date(2024, 1, 31), filed_at=date(2024, 3, 7),
                          source_url="https://example.com/filing", pdf_sha256="hash",
                          pdf_page=1, page_start=0, page_end=len(text), text=text)
        self.passages[pid] = passage
        fields = {name: getattr(passage, name) for name in Evidence.model_fields if name != "quote"}
        remember_evidence([Evidence(**fields, quote=text)], namespace)

    def test_dates_quantities_and_units_do_not_drive_recall(self):
        self.assertEqual(memory_terms("CrowdStrike as of January 31, 2024 USD 5,000"), [])

    def test_shared_dates_do_not_recall_unrelated_financial_passage(self):
        self.store("financial", "Fiscal 2024 liabilities were USD 5,000 and include employee benefits.")
        self.read.reset_mock()
        self.assertEqual(recall_evidence("Exactly 5,000 US-based full-time employees January 31, 2024", "test"), [])
        self.read.assert_not_called()

    def test_employee_evidence_is_recalled_for_related_population_query(self):
        self.store("employees", "We had 8,000 full-time employees globally.")
        results = recall_evidence("US-based full-time employees January 31, 2024", "test")
        self.assertEqual([item["passage_id"] for item in results], ["employees"])

    def test_historical_revenue_alone_does_not_match_forecast_query(self):
        self.store("revenue", "Revenue grew in fiscal 2024 and total revenue was USD 3 billion.")
        self.assertEqual(recall_evidence("Forecasts total revenue of USD 20 billion for fiscal 2030", "test"), [])

    def test_term_agreement_uses_fts_stemming(self):
        self.store("employees", "The headcount includes employees worldwide.")
        results = recall_evidence("Employee headcount", "test")
        self.assertEqual([item["passage_id"] for item in results], ["employees"])

    def test_namespaces_remain_isolated(self):
        self.store("cash", "Cash and cash equivalents were 1,000.", "first")
        self.assertEqual(recall_evidence("Cash equivalents", "second"), [])
        self.assertEqual(len(recall_evidence("Cash equivalents", "first")), 1)

    def test_changed_source_is_still_rejected(self):
        self.store("cash", "Cash and cash equivalents were 1,000.")
        self.passages["cash"] = self.passages["cash"].model_copy(update={"pdf_sha256": "changed"})
        self.assertEqual(recall_evidence("Cash equivalents", "test"), [])


if __name__ == "__main__":
    unittest.main()
