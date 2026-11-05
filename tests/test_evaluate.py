import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from filing_checker import evaluate
from filing_checker.models import MemoryStats, VerificationResult


class EvaluationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.dataset = (
            evaluate.PROJECT_ROOT / "data" / "test_statements.json"
        ).read_text(encoding="utf-8")
        self.benchmark = evaluate.Benchmark.model_validate_json(self.dataset)
        self.references = {
            key: reference.model_dump(mode="json")
            for key, reference in self.benchmark.references.items()
        }

    async def test_requested_subset_is_used_for_calls_and_saved_results(self):
        requested = ["T18", "T03", "T15"]
        expected_cases = [
            case for case in self.benchmark.statements if case.id in requested
        ]
        expected_ids = [case.id for case in expected_cases]

        async def fake_verify(payload):
            return VerificationResult(
                statement=payload.statement,
                verdict="NOT_ENOUGH_INFO",
                explanation="Mocked result for testing evaluation orchestration.",
                evidence=[],
                status="complete",
                stop_reason="validated_submission",
                model_calls=1,
                tool_calls=1,
                input_tokens=10,
                output_tokens=5,
                elapsed_seconds=0.25,
                searched_filings=[],
                read_passage_ids=[],
                trace=[],
                memory=MemoryStats(
                    enabled=payload.use_memory,
                    namespace=payload.memory_namespace,
                    recall_calls=1,
                ),
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset = root / "test_statements.json"
            dataset.write_text(self.dataset, encoding="utf-8")
            args = SimpleNamespace(
                ids=requested,
                limit=None,
                mode="full",
                dataset=dataset,
                max_model_calls=8,
                max_tool_calls=16,
            )

            with (
                patch.object(evaluate, "PROJECT_ROOT", root),
                patch.object(
                    evaluate, "corpus_fingerprint", return_value="fixed-corpus"
                ),
                patch.object(
                    evaluate,
                    "verify_once",
                    new_callable=AsyncMock,
                    side_effect=fake_verify,
                ) as verifier,
                redirect_stdout(io.StringIO()),
            ):
                await evaluate.run_evaluation(
                    args, self.benchmark, self.references
                )

            self.assertEqual(
                [call.args[0].statement for call in verifier.await_args_list],
                [case.statement for case in expected_cases],
            )

            run_directories = list((root / "results").iterdir())
            self.assertEqual(len(run_directories), 1)
            run = run_directories[0]
            metadata = json.loads((run / "run.json").read_text())
            predictions = json.loads(
                (run / "full" / "predictions.json").read_text()
            )
            summary = json.loads((run / "summary.json").read_text())["full"]

            self.assertEqual(metadata["case_order"], expected_ids)
            self.assertEqual([row["id"] for row in predictions], expected_ids)
            self.assertEqual(summary["cases"], 3)
            self.assertFalse(summary["full_dataset"])
            self.assertEqual(summary["elapsed_seconds"], 0.75)
            self.assertIn("Seconds", (run / "summary.md").read_text())
            self.assertIn("3/20", (run / "summary.md").read_text())

    def test_invalid_ids_fail_before_corpus_or_model_work(self):
        with (
            patch("sys.argv", ["evaluate", "--ids", "T99"]),
            patch.object(evaluate, "prepare_corpus") as prepare,
            patch.object(evaluate, "validate_benchmark") as validate,
            patch.object(evaluate, "verify_once", new_callable=AsyncMock) as verifier,
            redirect_stderr(io.StringIO()),
        ):
            with self.assertRaises(SystemExit) as caught:
                evaluate.main()

        self.assertEqual(caught.exception.code, 2)
        prepare.assert_not_called()
        validate.assert_not_called()
        verifier.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
