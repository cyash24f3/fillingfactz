import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from filing_checker.evidence import check_financial_amount, check_rounding_contradiction
from filing_checker.models import VerdictCandidate


class FinancialAmountTests(unittest.TestCase):
    def setUp(self):
        self.sources = {}
        self.enterContext(patch("filing_checker.evidence.read_passage",
                                side_effect=lambda pid: self.sources[pid]))

    def row(self, pid, text, period, context="Balance Sheets (in thousands)"):
        self.sources[pid] = SimpleNamespace(period_end=period, page_context=context,
                                            filed_at=period, text=text)
        return SimpleNamespace(passage_id=pid, quote=text, filed_at=period, period_end=period)

    def check(self, statement, evidence, verdict="SUPPORTED"):
        candidate = VerdictCandidate(verdict=verdict,
                                     explanation="A final explanation of the financial evidence.")
        check_financial_amount(statement, candidate, evidence)

    def test_thousands_cannot_be_reported_as_unscaled_dollars(self):
        row = self.row("new", "Cash and cash equivalents $ 8,123,456", date(2024, 10, 31))
        with self.assertRaisesRegex(ValueError, "table units"):
            self.check("Cash and cash equivalents were USD 8,123,456 on October 31, 2024.", [row])

    def test_scaled_dollar_amount_is_accepted(self):
        row = self.row("new", "Cash and cash equivalents $ 8,123,456", date(2024, 10, 31))
        self.check("Cash and cash equivalents were USD 8,123,456,000 on October 31, 2024.", [row])

    def test_rounded_billions_are_accepted(self):
        row = self.row("new", "Total revenue $ 3,055,555", date(2024, 1, 31))
        self.check("Total revenue in fiscal 2024 was approximately USD 3.06 billion.", [row])

    def test_exact_claim_does_not_get_rounding_allowance(self):
        row = self.row("new", "Total revenue $ 3,055,555", date(2024, 1, 31))
        with self.assertRaises(ValueError):
            self.check("Total revenue in fiscal 2024 was exactly USD 3.06 billion.", [row])

    def test_current_claim_matching_earlier_changed_balance_needs_temporal_verdict(self):
        rows = [self.row("old", "Total current liabilities 1,200,000", date(2024, 7, 31)),
                self.row("new", "Total current liabilities 1,500,000", date(2024, 10, 31))]
        with self.assertRaisesRegex(ValueError, "OUTDATED rather than CONTRADICTED"):
            self.check("Most recently reported total current liabilities are USD 1,200,000,000.",
                       rows, verdict="CONTRADICTED")

    def test_current_claim_cannot_use_only_an_older_matching_value(self):
        rows = [self.row("old", "Total current liabilities 1,200,000", date(2024, 7, 31)),
                self.row("new", "Total current liabilities 1,500,000", date(2024, 10, 31))]
        with self.assertRaises(ValueError):
            self.check("Latest total current liabilities are USD 1,200,000,000.", rows)

    def test_earlier_loaded_but_uncited_table_is_checked_for_temporal_change(self):
        self.row("old", "Total assets 1,200,000", date(2024, 1, 31))
        newer = self.row("new", "Total assets 1,500,000 1,200,000", date(2024, 10, 31))
        candidate = VerdictCandidate(verdict="CONTRADICTED",
                                     explanation="The latest filing reports a different balance.")
        with self.assertRaisesRegex(ValueError, "OUTDATED rather than CONTRADICTED"):
            check_financial_amount("Latest total assets are USD 1,200,000,000.",
                                   candidate, [newer], {"old", "new"})

    def test_historical_current_liabilities_is_not_a_latest_claim(self):
        rows = [self.row("old", "Total current liabilities 1,200,000", date(2024, 7, 31)),
                self.row("new", "Total current liabilities 1,500,000", date(2024, 10, 31))]
        self.check("Total current liabilities were USD 1,200,000,000 as of July 31, 2024.", rows)

    def test_unknown_units_do_not_trigger_an_assumed_scale(self):
        row = self.row("new", "Cash and cash equivalents $ 8,123,456", date(2024, 10, 31), "")
        self.check("Cash and cash equivalents were USD 8,123,456 on October 31, 2024.", [row])

    def test_percentage_row_is_not_a_monetary_amount(self):
        row = self.row("new", "Subscription 94 % 94 %", date(2024, 1, 31))
        self.check("Subscription revenue was USD 1 billion in fiscal 2024.", [row])

    def test_matching_rounded_table_value_does_not_support_contradiction(self):
        row = self.row("new", "Total revenue $ 3,055,555", date(2024, 1, 31))
        with self.assertRaisesRegex(ValueError, "do not contradict"):
            self.check("Total revenue was approximately USD 3.06 billion in fiscal 2024.",
                       [row], verdict="CONTRADICTED")

    def test_compact_scale_suffix_is_recognized(self):
        row = self.row("new", "Total revenue $ 3,055,555", date(2024, 1, 31))
        self.check("Total revenue was approximately USD 3.06bn in fiscal 2024.", [row])

    def test_range_and_negated_claims_are_left_to_semantic_judgment(self):
        row = self.row("new", "Total revenue $ 3,055,555", date(2024, 1, 31))
        self.check("Total revenue was more than USD 2 billion in fiscal 2024.", [row])
        self.check("Total revenue was not USD 3,055,555,000 in fiscal 2024.",
                   [row], verdict="CONTRADICTED")

    def test_coarser_narrative_rounding_cannot_refute_a_finer_approximation(self):
        row = self.row("new", "Revenue increased from $1.7 billion in fiscal 2023 "
                       "to $2.8 billion in fiscal 2024.", date(2024, 1, 31))
        candidate = VerdictCandidate(verdict="CONTRADICTED", explanation="The disclosed value is rounded.")
        with self.assertRaisesRegex(ValueError, "precision range"):
            check_rounding_contradiction("Total revenue was approximately USD 2.76 billion in fiscal 2024.",
                                         candidate, [row])

    def test_comparative_year_value_is_not_applied_to_the_claim_year(self):
        row = self.row("new", "Revenue increased from $1.7 billion in fiscal 2023 "
                       "to $2.8 billion in fiscal 2024.", date(2024, 1, 31))
        candidate = VerdictCandidate(verdict="CONTRADICTED", explanation="The earlier year has a different amount.")
        check_rounding_contradiction("Total revenue was approximately USD 1.7 billion in fiscal 2024.",
                                     candidate, [row])

    def test_an_explicitly_exact_source_does_not_get_coarse_rounding(self):
        row = self.row("new", "Revenue was exactly $2.8 billion in fiscal 2024.", date(2024, 1, 31))
        candidate = VerdictCandidate(verdict="CONTRADICTED", explanation="The source gives an exact figure.")
        check_rounding_contradiction("Total revenue was approximately USD 2.76 billion in fiscal 2024.",
                                     candidate, [row])

    def test_undated_rounded_quote_uses_its_filing_period(self):
        row = self.row("new", "Revenue was $2.8 billion.", date(2024, 1, 31))
        candidate = VerdictCandidate(verdict="CONTRADICTED", explanation="The source is rounded.")
        with self.assertRaisesRegex(ValueError, "precision range"):
            check_rounding_contradiction("Total revenue was approximately USD 2.76 billion in fiscal 2024.",
                                         candidate, [row])


if __name__ == "__main__":
    unittest.main()
