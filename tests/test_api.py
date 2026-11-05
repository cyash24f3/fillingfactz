import json
import unittest
from unittest.mock import patch, AsyncMock

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
    def test_swagger_and_openapi_expose_verification_post_operations(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/docs").status_code, 200)
            schema = client.get("/openapi.json").json()
            self.assertIn("post", schema["paths"]["/verify"])
            self.assertIn("post", schema["paths"]["/verify/stream"])
            self.assertEqual(client.get("/verify").status_code, 405)
            self.assertEqual(client.get("/health").status_code, 200)

    def test_json_endpoint_returns_a_valid_report_and_forwards_settings(self):
        with patch("filing_checker.api.verify_once", new_callable=AsyncMock,
                   return_value=VerificationResult.model_validate(fake_result())) as verifier:
            with TestClient(app) as client:
                response = client.post("/verify", json={"statement": "  A test statement.  ",
                    "use_memory": False, "use_decomposer": False, "memory_namespace": "api-test",
                    "max_model_calls": 3, "max_tool_calls": 5})
        self.assertEqual(response.status_code, 200)
        VerificationResult.model_validate(response.json())
        payload = verifier.await_args.args[0]
        self.assertEqual(payload.statement, "A test statement.")
        self.assertFalse(payload.use_memory)
        self.assertFalse(payload.use_decomposer)
        self.assertEqual(payload.max_model_calls, 3)

    def test_invalid_budget_fails_validation_before_workflow_execution(self):
        with patch("filing_checker.api.verify_once", new_callable=AsyncMock) as verifier:
            with TestClient(app) as client:
                response = client.post("/verify", json={"statement": "A claim.", "max_model_calls": 1})
        self.assertEqual(response.status_code, 422)
        verifier.assert_not_awaited()

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
