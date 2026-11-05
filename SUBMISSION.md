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
| Completed diagnostic predictions and metrics | `results/diagnostic/` |
| Automated tests | `tests/` |
| Dependencies | `pyproject.toml`, `requirements-lock.txt` |

## Verification status

- 44 automated code checks pass without model inference.
- All 20 labelled cases and their 17 shared source references validate against
  the included PDFs.
- The checked-in four-case diagnostic completes with all four verdicts matching
  the expected labels.
- The full benchmark evaluates 20 statements across three configurations, for
  60 runs. That comparison is being generated separately from this repository snapshot.

The diagnostic report is explicitly scoped to its selected cases. Final benchmark
accuracy, usage, and memory savings will be reported from the complete comparison.
