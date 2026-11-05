import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ollama import ChatResponse

from filing_checker.agent import run_verifier


def response(name=None, arguments=None):
    message = {"role": "assistant", "content": "Unstructured model response."}
    if name:
        message["content"] = ""
        message["tool_calls"] = [
            {"function": {"name": name, "arguments": arguments or {}}}
        ]
    return ChatResponse(
        message=message,
        prompt_eval_count=20,
        eval_count=10,
    )


def insufficient_evidence():
    return response("submit_verdict", {
        "verdict": "NOT_ENOUGH_INFO",
        "explanation": "The available filings do not resolve this statement.",
        "evidence": [],
    })


class ExecutorFailureTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("filing_checker.agent.prepare_corpus"))
        self.enterContext(patch("filing_checker.agent.list_filings", return_value=[{
            "filing_id": "annual",
            "form": "10-K",
            "period_end": "2024-01-31",
            "filed_at": "2024-03-07",
        }]))
        self.enterContext(patch("filing_checker.evidence.load_filings", return_value=[
            SimpleNamespace(filing_id="annual"),
        ]))
        self.bootstrap = {
            "searched_filings": ["annual"],
            "read_passage_ids": [],
            "passages": [],
        }
        self.tools = self.enterContext(patch(
            "filing_checker.agent.execute_tool", return_value=self.bootstrap,
        ))
        self.model = self.enterContext(patch("filing_checker.agent.ask_model"))

    def run_claim(self, **kwargs):
        return run_verifier("An unresolved test claim.", **kwargs)

    def test_repeated_unstructured_output_stops_incomplete(self):
        self.model.side_effect = [response(), response()]
        result = self.run_claim(max_model_calls=4)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.stop_reason, "invalid_output")
        self.assertEqual(result.model_calls, 2)
        self.assertEqual(result.tool_calls, 1)

    def test_malformed_submission_gets_feedback_and_can_recover(self):
        self.model.side_effect = [
            response("submit_verdict", {"explanation": "The verdict is missing."}),
            insufficient_evidence(),
        ]
        result = self.run_claim(max_model_calls=3)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.stop_reason, "validated_submission")
        self.assertEqual(result.model_calls, 2)
        self.assertTrue(any(event["event"] == "tool_error" for event in result.trace))
        feedback = self.model.call_args_list[1].args[0]
        self.assertTrue(any(
            item["role"] == "tool" and "verdict" in json.loads(item["content"])["error"]
            for item in feedback if item["role"] == "tool"
        ))

    def test_tool_error_is_returned_to_the_model_without_crashing(self):
        self.tools.side_effect = [self.bootstrap, ValueError("Unknown passage ID")]
        self.model.side_effect = [
            response("read_passage", {"passage_id": "missing"}),
            insufficient_evidence(),
        ]
        result = self.run_claim(max_model_calls=3)
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.tool_calls, 3)
        feedback = self.model.call_args_list[1].args[0]
        self.assertTrue(any(
            item["role"] == "tool" and "Unknown passage ID" in item["content"]
            for item in feedback
        ))

    def test_model_failure_is_incomplete_with_unknown_token_usage(self):
        self.model.side_effect = OSError("Ollama is unavailable")
        result = self.run_claim()
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.stop_reason, "model_error")
        self.assertEqual(result.model_calls, 1)
        self.assertIsNone(result.input_tokens)
        self.assertIsNone(result.output_tokens)

    def test_finalization_prevents_more_retrieval_and_obeys_model_limit(self):
        self.model.return_value = response("read_passage", {"passage_id": "missing"})
        result = self.run_claim(max_model_calls=1)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.stop_reason, "model_call_limit")
        self.assertEqual(result.model_calls, 1)
        self.assertEqual(result.tool_calls, 2)
        self.tools.assert_called_once()
        offered = self.model.call_args.args[1]
        self.assertEqual([tool["function"]["name"] for tool in offered], ["submit_verdict"])

    def test_exhausted_tool_budget_stops_before_another_model_call(self):
        result = self.run_claim(max_tool_calls=1)
        self.assertEqual(result.status, "incomplete")
        self.assertEqual(result.stop_reason, "tool_call_limit")
        self.assertEqual(result.tool_calls, 1)
        self.assertEqual(result.model_calls, 0)
        self.model.assert_not_called()

    def test_inconsistent_verdict_is_rejected_then_retried(self):
        self.model.side_effect = [
            response("submit_verdict", {
                "verdict": "SUPPORTED",
                "explanation": "Therefore, the statement is CONTRADICTED by the evidence.",
                "evidence": [],
            }),
            insufficient_evidence(),
        ]
        result = self.run_claim(max_model_calls=3)
        self.assertEqual(result.verdict, "NOT_ENOUGH_INFO")
        self.assertEqual(result.status, "complete")
        self.assertEqual(result.model_calls, 2)
        errors = [event for event in result.trace if event["event"] == "tool_error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("final explanation concludes CONTRADICTED", errors[0]["error"])

    def test_repeated_search_results_reference_existing_text_without_duplicating_it(self):
        passage = {"passage_id": "annual:p1:c0", "filing_id": "annual", "pdf_page": 1,
                   "period_end": "2024-01-31", "filed_at": "2024-03-07",
                   "text": "A reusable source paragraph.", "page_context": ""}
        found = {**self.bootstrap, "read_passage_ids": [passage["passage_id"]],
                 "passages": [passage]}
        self.tools.return_value = found
        self.model.side_effect = [response("search_and_read", {"query": "more detail"}),
                                  insufficient_evidence()]
        result = self.run_claim(max_model_calls=3)
        history = self.model.call_args_list[1].args[0]
        observation = json.loads(next(item["content"] for item in history
                                      if item["role"] == "tool"))
        self.assertEqual(observation["passages"], [])
        self.assertEqual(observation["already_loaded_passage_ids"], ["annual:p1:c0"])
        initial = [item for item in history if item["role"] == "user"
                   and "initial_evidence" in item["content"]]
        self.assertIn("A reusable source paragraph.", initial[0]["content"])
        self.assertEqual(result.read_passage_ids, ["annual:p1:c0"])
        self.assertEqual(result.tool_calls, 3)
        self.assertEqual(result.status, "complete")


if __name__ == "__main__":
    unittest.main()
