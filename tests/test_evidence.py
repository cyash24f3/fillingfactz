import unittest
from types import SimpleNamespace

from filing_checker.evidence import (
    check_supported_metrics,
    check_verdict_consistency,
    find_original_quote,
    suggest_continuous_quote,
)
from filing_checker.models import VerdictCandidate


class MetricGroundingTests(unittest.TestCase):
    def setUp(self):
        self.supported = VerdictCandidate(
            verdict="SUPPORTED",
            explanation="The selected source supports the statement.",
        )

    def test_total_revenue_cannot_support_subscription_revenue(self):
        with self.assertRaisesRegex(ValueError, "subscription revenue"):
            check_supported_metrics(
                "Subscription revenue was USD 100 million.",
                self.supported,
                [SimpleNamespace(quote="Total revenue $ 100,000")],
            )

    def test_subscription_cannot_support_total_revenue(self):
        with self.assertRaisesRegex(ValueError, "total revenue"):
            check_supported_metrics(
                "Total revenue was USD 80 million.",
                self.supported,
                [SimpleNamespace(quote="Subscription $ 80,000")],
            )

    def test_matching_table_row_alias_is_accepted(self):
        check_supported_metrics(
            "Subscription revenue was USD 80 million.",
            self.supported,
            [SimpleNamespace(quote="Subscription\n$ 80,000")],
        )

    def test_different_balance_sheet_metrics_are_not_interchangeable(self):
        with self.assertRaisesRegex(ValueError, "total current liabilities"):
            check_supported_metrics(
                "Total current liabilities were USD 50 million.",
                self.supported,
                [SimpleNamespace(quote="Total liabilities 50,000")],
            )

    def test_missing_information_does_not_require_a_positive_metric_quote(self):
        check_supported_metrics(
            "Total revenue will be USD 100 million next year.",
            VerdictCandidate(
                verdict="NOT_ENOUGH_INFO",
                explanation="The supplied sources do not resolve this forecast.",
            ),
            [],
        )


class QuoteRecoveryTests(unittest.TestCase):
    def test_external_quote_style_recovers_original_source_punctuation(self):
        source = 'The update caused crashes (the “Sensor Incident”).'
        self.assertEqual(find_original_quote(source,
            "The update caused crashes (the 'Sensor Incident')."), source)

    def test_internal_apostrophes_are_preserved(self):
        source = "Acme’s headquarters is in Pune."
        self.assertEqual(find_original_quote(source, "Acme's headquarters is in Pune."), source)
        with self.assertRaises(ValueError):
            find_original_quote(source, 'Acme"s headquarters is in Pune.')

    def test_punctuation_normalization_does_not_allow_changed_words(self):
        with self.assertRaises(ValueError):
            find_original_quote('The update caused crashes (the “Sensor Incident”).',
                                "The update prevented crashes (the 'Sensor Incident').")

    def test_nonadjacent_header_and_row_get_a_literal_continuous_alternative(self):
        source = "(in thousands)\nOther table headers\nCash and cash equivalents $ 8,123,456 $ 7,000,000"
        requested = "(in thousands)\nCash and cash equivalents $ 8,123,456"
        with self.assertRaises(ValueError):
            find_original_quote(source, requested)
        suggestion = suggest_continuous_quote(source, requested)
        self.assertIn("8,123,456", suggestion)
        self.assertEqual(find_original_quote(source, suggestion), suggestion)

    def test_a_shared_metric_name_without_the_requested_number_is_not_suggested(self):
        self.assertIsNone(suggest_continuous_quote(
            "Professional services revenue accounted for 6%.",
            "Professional services 94%",
        ))


class VerdictConsistencyTests(unittest.TestCase):
    def test_conflicting_final_classification_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "final explanation concludes CONTRADICTED"):
            check_verdict_consistency(VerdictCandidate(
                verdict="SUPPORTED",
                explanation="The amounts refer to different metrics. Therefore, the statement is CONTRADICTED by the evidence.",
            ))

    def test_reverse_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "final explanation concludes SUPPORTED"):
            check_verdict_consistency(VerdictCandidate(
                verdict="CONTRADICTED",
                explanation="The claim should be **SUPPORTED** by this source.",
            ))

    def test_consistent_conclusion_is_accepted(self):
        check_verdict_consistency(VerdictCandidate(
            verdict="CONTRADICTED",
            explanation="The statement is CONTRADICTED by the cited evidence.",
        ))

    def test_earlier_support_does_not_override_temporal_judgment(self):
        check_verdict_consistency(VerdictCandidate(
            verdict="OUTDATED",
            explanation="The claim is SUPPORTED by the earlier filing. A later filing reports a different value.",
        ))


if __name__ == "__main__":
    unittest.main()
