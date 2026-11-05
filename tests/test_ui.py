import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from streamlit.testing.v1 import AppTest

from filing_checker.models import VerificationResult


ROOT = Path(__file__).resolve().parents[1]


def mock_stream(api_base, payload):
    result = VerificationResult(
        statement=payload["statement"], verdict="NOT_ENOUGH_INFO",
        explanation="Mock interface evidence does not resolve this statement.",
        evidence=[], status="complete", stop_reason="validated_submission",
        model_calls=2, tool_calls=3, input_tokens=100, output_tokens=20,
        elapsed_seconds=0.1, searched_filings=["annual"], read_passage_ids=[], trace=[],
    ).model_dump(mode="json")
    for kind, data in [("started", {}), ("step", {"event": "model_call", "number": 1}),
                       ("result", result), ("done", {"outcome": "result"})]:
        yield {"type": kind, "run_id": "ui-test", "data": data}


class ReviewerUITests(unittest.TestCase):
    def setUp(self):
        self.stream = self.enterContext(patch("filing_checker.ui_client.stream_check", side_effect=mock_stream))

    def app(self):
        return AppTest.from_file(str(ROOT / "streamlit_app.py")).run(timeout=10)

    def test_single_review_renders_report_and_usage(self):
        app = self.app()
        next(b for b in app.button if b.label == "Check statement").click().run(timeout=10)
        self.assertEqual(len(app.exception), 0)
        record = app.session_state["single_run"]
        self.assertEqual(record["result"]["status"], "complete")
        self.assertEqual(len(record["events"]), 4)
        self.assertEqual(self.stream.call_count, 1)
        self.assertTrue(any(metric.label == "Model calls" and metric.value == "2" for metric in app.metric))

    def test_batch_review_processes_each_statement_and_retains_reports(self):
        app = self.app()
        next(b for b in app.button if b.label == "Check batch").click().run(timeout=10)
        self.assertEqual(len(app.exception), 0)
        records = app.session_state["batch_runs"]
        self.assertEqual(len(records), 2)
        self.assertTrue(all(r["result"]["status"] == "complete" for r in records))
        self.assertEqual(self.stream.call_count, 2)
        self.assertTrue(any(metric.label == "Statements processed" and metric.value == "2" for metric in app.metric))

    def test_invalid_budget_disables_verification(self):
        app = self.app()
        next(widget for widget in app.number_input if widget.label == "Maximum model calls").set_value(1).run()
        self.assertTrue(next(b for b in app.button if b.label == "Check statement").disabled)
        self.stream.assert_not_called()

    def test_api_failure_is_visible_and_does_not_crash_the_ui(self):
        self.stream.side_effect = httpx.ConnectError("API unavailable")
        app = self.app()
        next(b for b in app.button if b.label == "Check statement").click().run(timeout=10)
        self.assertEqual(len(app.exception), 0)
        self.assertIn("API unavailable", app.session_state["single_run"]["error"])
        self.assertGreater(len(app.error), 0)


if __name__ == "__main__":
    unittest.main()
