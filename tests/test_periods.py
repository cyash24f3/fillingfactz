import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from filing_checker.ingestion import page_context
from filing_checker.periods import future_annual_period, table_column
from filing_checker.evidence import check_financial_amount
from filing_checker.models import VerdictCandidate


class ReportingPeriodTests(unittest.TestCase):
    def setUp(self):
        self.filings = [
            SimpleNamespace(form="10-K", period_end=date(2024, 1, 31), filed_at=date(2024, 3, 7)),
            SimpleNamespace(form="10-Q", period_end=date(2024, 10, 31), filed_at=date(2024, 11, 27)),
        ]

    def test_future_annual_actual_is_outside_supplied_filing_coverage(self):
        self.assertEqual(future_annual_period(
            "Full-year revenue for the fiscal year ended January 31, 2025 was USD 5 billion.",
            self.filings), (date(2025, 1, 31), date(2024, 11, 27)))
        self.assertIsNotNone(future_annual_period("Revenue in FY2025 was USD 5 billion.", self.filings))

    def test_forecast_and_interim_claims_need_their_own_disclosure_search(self):
        for statement in ("Revenue guidance for fiscal 2025 is USD 5 billion.",
                          "Revenue for the third quarter of fiscal 2025 was USD 1 billion.",
                          "Revenue in fiscal 2024 was USD 3 billion."):
            self.assertIsNone(future_annual_period(statement, self.filings))

    def test_fiscal_columns_bind_to_the_requested_year(self):
        heading = "Year Ended January 31,\n2024 2023 2022\n(in thousands)\n"
        self.assertEqual(table_column("Total revenue in fiscal 2023 was USD 2 billion.",
                                      heading, date(2024, 1, 31), "10-K"), 1)
        self.assertEqual(table_column("Total revenue in fiscal 2024 was USD 3 billion.",
                                      heading, date(2024, 1, 31), "10-K"), 0)

    def test_balance_date_selects_comparative_column(self):
        heading = "October 31, January 31,\n2024 2024\n(in thousands)\n"
        self.assertEqual(table_column("Cash on January 31, 2024 was USD 2 billion.",
                                      heading, date(2024, 10, 31), "10-Q"), 1)
        self.assertIsNone(table_column("Cash on July 31, 2024 was USD 2 billion.",
                                       heading, date(2024, 10, 31), "10-Q"))

    def test_quarterly_flow_table_cannot_establish_full_annual_revenue(self):
        self.assertIsNone(table_column("Total revenue in fiscal 2024 was USD 3 billion.",
                                       "2024 2023\n", date(2024, 10, 31), "10-Q"))

    def test_wrapped_units_are_retained_below_the_heading(self):
        context = page_context("Company\n" + "Intro\n" * 15 + "(in\nthousands, except percentages)\n")
        self.assertIn("(in thousands, except percentages)", context)

    def test_validator_recovers_full_row_and_years_when_quote_starts_mid_page(self):
        page = "Year Ended January 31,\n2024 2023 2022\n(in\nthousands)\nTotal revenue $ 3,055,555 2,241,236 1,451,599\n"
        offset = page.index("Total revenue")
        passage = SimpleNamespace(filing_id="annual", pdf_page=70, page_start=offset,
                                  text=page[offset:], page_context="(in thousands)", form="10-K",
                                  period_end=date(2024, 1, 31), filed_at=date(2024, 3, 7))
        evidence = [SimpleNamespace(passage_id="row", quote="Total revenue $ 3,055,555 2,241,236")]
        candidate = VerdictCandidate(verdict="SUPPORTED", explanation="The statement matches this row.")
        with patch("filing_checker.evidence.read_passage", return_value=passage), \
                patch("filing_checker.evidence.read_page_text", return_value=page):
            with self.assertRaisesRegex(ValueError, "table units"):
                check_financial_amount("Total revenue in fiscal 2024 was USD 2,241,236,000.", candidate, evidence)
            check_financial_amount("Total revenue in fiscal 2023 was USD 2,241,236,000.", candidate, evidence)


if __name__ == "__main__":
    unittest.main()
