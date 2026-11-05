# Submission overview

## Project

A local, evidence-grounded fact checker for statements about CrowdStrike. The
application combines a LangGraph Decomposer and Executor with searchable SEC
filings, persistent evidence memory, a streaming FastAPI service, and a Streamlit
reviewer interface.

## Repository contents

| Deliverable | Location |
|---|---|
| Application and CLI | `filing_checker/`, `main.py`, `workflow.py` |
| Reviewer interface | `streamlit_app.py` |
| Setup and run instructions | [README](README.md) |
| Architecture diagram and module map | [Architecture](docs/ARCHITECTURE.md) |
| MERMAID adaptation and design rationale | [Design](docs/DESIGN.md) |
| Three reference PDFs and source metadata | `data/raw/`, `data/filings.json` |
| Twenty labelled statements and references | `data/test_statements.json` |
| Benchmark protocol | [Evaluation](docs/EVALUATION.md) |
| Complete benchmark predictions and metrics | `results/benchmark/` |
| Focused diagnostic predictions and metrics | `results/diagnostic/` |
| Automated tests | `tests/` |
| Dependencies | `pyproject.toml`, `requirements-lock.txt` |

## Verification status

- 44 automated code checks pass without model inference.
- All 20 labelled cases and their 17 shared source references validate against
  the included PDFs.
- The checked-in four-case diagnostic completes with all four verdicts matching
  the expected labels.
- The complete 60-run benchmark is included: full 85%, memory-off 100%, and
  Decomposer-off 100%, with completion, usage, evidence, and per-case traces.

The full comparison records the evaluated source snapshot. Focused diagnostics
and follow-up changes are documented separately; no memory savings are claimed
for this baseline run.
