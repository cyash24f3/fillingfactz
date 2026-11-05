import json
import unittest

import httpx

from filing_checker.ui_client import parse_batch, parse_sse_lines, stream_check, StreamProtocolError


class ReviewerProtocolTests(unittest.TestCase):
    def test_batch_input_discards_expected_labels_and_other_gold_fields(self):
        text = json.dumps({"statements": [{"statement": "A claim.",
                           "expected_verdict": "SUPPORTED", "reference_ids": ["gold"]}]})
        self.assertEqual(parse_batch(text, json_input=True), ["A claim."])

    def test_multiline_sse_and_heartbeat_comments(self):
        lines = [": heartbeat", 'data: {"type":"step",',
                 'data: "run_id":"r","data":{"event":"model_call"}}', ""]
        self.assertEqual(list(parse_sse_lines(lines))[0]["data"]["event"], "model_call")

    def test_truncated_event_is_rejected(self):
        with self.assertRaises(StreamProtocolError):
            list(parse_sse_lines(['data: {"type":"step","run_id":"r","data":{}}']))

    def test_mixed_run_ids_are_rejected(self):
        events = [{"type": "started", "run_id": "first", "data": {}},
                  {"type": "done", "run_id": "second", "data": {"outcome": "error"}}]
        body = "".join("data: " + json.dumps(event) + "\n\n" for event in events)
        transport = httpx.MockTransport(lambda request: httpx.Response(
            200, headers={"content-type": "text/event-stream"}, text=body))
        with self.assertRaisesRegex(StreamProtocolError, "mixed run IDs"):
            list(stream_check("http://test", {"statement": "A claim."}, transport=transport))

    def test_result_completion_without_a_report_is_rejected(self):
        event = {"type": "done", "run_id": "r", "data": {"outcome": "result"}}
        transport = httpx.MockTransport(lambda request: httpx.Response(
            200, headers={"content-type": "text/event-stream"}, text="data: "+json.dumps(event)+"\n\n"))
        with self.assertRaisesRegex(StreamProtocolError, "without its result"):
            list(stream_check("http://test", {"statement": "A claim."}, transport=transport))


if __name__ == "__main__":
    unittest.main()
