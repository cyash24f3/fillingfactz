import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from filing_checker.api import app
from filing_checker.models import VerificationResult


def fake_result():
    return VerificationResult(
        statement="A test statement.",
        verdict="NOT_ENOUGH_INFO",
        explanation="Mock evidence is insufficient to resolve this claim.",
        evidence=[],
        status="complete",
        stop_reason="validated_submission",
        model_calls=1,
        tool_calls=1,
        input_tokens=10,
        output_tokens=10,
        elapsed_seconds=0.01,
        searched_filings=[],
        read_passage_ids=[],
        trace=[],
    ).model_dump(mode="json")


class FakeGraph:
    def __init__(self, fail=False):
        self.fail = fail

    async def astream(self, *args, **kwargs):
        if self.fail:
            raise RuntimeError("Simulated workflow failure")

        yield {
            "type": "custom",
            "data": {
                "event": "model_call",
                "number": 1,
            },
        }

        yield {
            "type": "updates",
            "data": {
                "remember": {
                    "result": fake_result(),
                }
            },
        }


def parse_events(text):
    return [
        json.loads(line.removeprefix("data: "))
        for line in text.splitlines()
        if line.startswith("data: ")
    ]


class APITests(unittest.TestCase):
    def test_blank_statement_is_rejected(self):
        with TestClient(app) as client:
            response = client.post(
                "/verify/stream",
                json={"statement": "   "},
            )

        self.assertEqual(response.status_code, 422)

    def test_stream_contains_steps_and_final_result(self):
        with patch(
            "filing_checker.service.build_graph",
            return_value=FakeGraph(),
        ) as builder:
            with TestClient(app) as client:
                response = client.post(
                    "/verify/stream",
                    json={
                        "statement": "A test statement.",
                        "use_memory": False,
                        "use_decomposer": False,
                    },
                )

        self.assertEqual(response.status_code, 200)

        events = parse_events(response.text)
        types = [event["type"] for event in events]

        self.assertIn("step", types)
        self.assertIn("result", types)
        self.assertEqual(types[-1], "done")

        result = next(event["data"] for event in events if event["type"] == "result")

        self.assertEqual(
            result["verdict"],
            "NOT_ENOUGH_INFO",
        )

        self.assertFalse(builder.call_args.kwargs["use_memory"])

        self.assertFalse(builder.call_args.kwargs["use_decomposer"])

    def test_workflow_failure_becomes_error_event(self):
        with patch(
            "filing_checker.service.build_graph",
            return_value=FakeGraph(fail=True),
        ):
            with patch("filing_checker.service.logger.exception"):
                with TestClient(app) as client:
                    response = client.post(
                        "/verify/stream",
                        json={"statement": "A test statement."},
                    )

        events = parse_events(response.text)
        types = [event["type"] for event in events]

        self.assertIn("error", types)
        self.assertNotIn("result", types)
        self.assertEqual(types[-1], "done")


if __name__ == "__main__":
    unittest.main()
