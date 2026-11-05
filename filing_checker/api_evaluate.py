"""Exercise the running HTTP/SSE interface with additional labelled statements.

Start the FastAPI server first, then run ``python -m filing_checker.api_evaluate``.
Gold labels and references stay in this client; only statement and run settings
are sent to the service. This supplements the separate 20-by-3 benchmark.
"""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from filing_checker.config import PROJECT_ROOT, MODEL_NAME
from filing_checker.ui_client import stream_check


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    response = httpx.get(args.api.rstrip("/") + "/health", timeout=5)
    response.raise_for_status()
    dataset = PROJECT_ROOT / "data" / "api_smoke_cases.json"
    cases = json.loads(dataset.read_text())["statements"]
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:8]
    output = PROJECT_ROOT / "results" / ("api_" + run_id)
    output.mkdir(parents=True)

    def save(name, value):
        (output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")

    metadata = {
        "status": "running", "model": MODEL_NAME,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip(),
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in (PROJECT_ROOT / "filing_checker").glob("*.py")},
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "case_order": [case["id"] for case in cases],
        "method": "Live POST /verify/stream; additional statements, full configuration, "
                  "fresh shared memory namespace, sequential requests, budgets 8/16. "
                  "Expected labels and references are scored only in this client.",
    }
    save("run.json", metadata)
    rows = []
    for case in cases:
        events, result, error = [], None, None
        try:
            for event in stream_check(args.api, {
                "statement": case["statement"], "use_decomposer": True,
                "use_memory": True, "memory_namespace": "api_validation_" + run_id,
                "max_model_calls": 8, "max_tool_calls": 16,
            }):
                events.append(event)
                if event["type"] == "result":
                    result = event["data"]
                elif event["type"] == "error":
                    error = event["data"]
        except Exception as caught:
            error = str(caught)
        complete_stream = bool(events and events[-1]["type"] == "done"
                               and events[-1]["data"].get("outcome") == "result")
        correct = bool(not error and complete_stream and result
                       and result["status"] == "complete"
                       and result["verdict"] == case["expected_verdict"])
        rows.append({**case, "correct": correct, "result": result,
                     "error": error, "events": events})
        save("predictions.json", rows)
        print(f"{case['id']}: expected={case['expected_verdict']} "
              f"got={result['verdict'] if result else 'ERROR'} correct={correct}", flush=True)
    metadata.update(status="finished", all_correct=all(row["correct"] for row in rows))
    save("run.json", metadata)
    save("summary.json", {"cases": len(rows), "correct": sum(row["correct"] for row in rows),
                          "all_streams_finished": all(row["events"] and row["events"][-1]["type"] == "done" for row in rows)})
    print(f"Results: {output}", flush=True)
    raise SystemExit(0 if metadata["all_correct"] else 1)


if __name__ == "__main__":
    main()
