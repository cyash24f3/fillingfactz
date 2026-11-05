import unittest
from types import SimpleNamespace

from filing_checker.evidence import check_employee_scope
from filing_checker.models import VerdictCandidate


class EmployeeScopeTests(unittest.TestCase):
    def check(self, statement, quote, verdict="CONTRADICTED"):
        candidate = VerdictCandidate(verdict=verdict,
                                     explanation="The cited passage describes employee headcount.")
        check_employee_scope(statement, candidate, [SimpleNamespace(quote=quote)])

    def test_larger_company_total_does_not_disprove_smaller_regional_subset(self):
        with self.assertRaisesRegex(ValueError, "regional subset"):
            self.check("There were 4,000 US-based full-time employees.",
                       "We had 8,000 full-time employees globally.")

    def test_unqualified_headcount_growth_does_not_supply_a_regional_breakdown(self):
        with self.assertRaises(ValueError):
            self.check("There were 4,000 India-based employees.",
                       "Our headcount grew from 3,200 employees to 6,800 employees.")

    def test_company_total_cannot_prove_regional_headcount(self):
        with self.assertRaises(ValueError):
            self.check("There were 4,000 US-based employees.",
                       "We had 4,000 employees globally.", verdict="SUPPORTED")

    def test_region_specific_evidence_can_contradict_the_claim(self):
        self.check("There were 4,000 US-based employees.",
                   "We had 2,000 employees in the United States.")

    def test_subset_above_company_total_is_not_blocked(self):
        self.check("There were 9,000 US-based employees.",
                   "We had 8,000 employees globally.")

    def test_company_wide_claim_is_not_mistaken_for_regional_claim(self):
        self.check("There were 4,000 employees globally.",
                   "We had 8,000 employees globally.")

    def test_unionization_location_does_not_scope_the_headcount(self):
        with self.assertRaises(ValueError):
            self.check("There were 4,000 US-based full-time employees.",
                       "We had 8,000 full-time employees. None of our employees "
                       "in the United States are represented by a labor union.")

    def test_same_sentence_location_mention_is_not_a_regional_count(self):
        with self.assertRaises(ValueError):
            self.check("There were 4,000 US-based employees.",
                       "We had 8,000 employees, and our United States "
                       "employees are not represented by a labor union.")

    def test_direct_regional_count_before_employee_label_is_accepted(self):
        self.check("There were 4,000 US-based employees.",
                   "We had 2,000 US-based full-time employees.")

    def test_direct_regional_headcount_relation_is_accepted(self):
        self.check("There were 4,000 UK-based employees.",
                   "Our United Kingdom employee headcount was 2,000.")


if __name__ == "__main__":
    unittest.main()
