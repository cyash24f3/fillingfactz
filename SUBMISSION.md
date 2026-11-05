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
| Architecture diagram and module map | [Architecture](docs/ARCHITECTURE.md), [editable Excalidraw board](docs/architecture/README.md) |
| MERMAID adaptation and design rationale | [Design](docs/DESIGN.md) |
| Three reference PDFs and source metadata | `data/raw/`, `data/filings.json` |
| Twenty labelled statements and references | `data/test_statements.json` |
| Benchmark protocol | [Evaluation](docs/EVALUATION.md) |
| Complete benchmark predictions and metrics | `results/benchmark/` |
| Baseline comparison | `results/baseline/` |
| Live API validation | `results/api_validation/`, [Validation](docs/VALIDATION.md) |
| Requirements map | [Requirements](docs/REQUIREMENTS.md) |
| Focused diagnostic predictions and metrics | `results/diagnostic/` |
| Automated tests | `tests/` |
| Dependencies | `pyproject.toml`, `requirements-lock.txt` |

## Verification status

- **60/60 benchmark runs pass:** twenty statements in each of three configurations,
  with complete status, matching verdicts, source evidence, traces, and usage.
- **92 automated tests pass**, including a fresh installation from pinned dependencies.
- All twenty labelled cases and their seventeen shared source references validate
  against the included PDFs.
- **12/12 additional live API checks pass** with completed SSE streams.
- FastAPI, Swagger requests, Streamlit single and batch reviews, and JSON report
  downloads were exercised successfully.
- GitHub Actions runs automated tests and source-reference validation on Python 3.12.

The [evaluation report](docs/EVALUATION.md) compares accuracy, calls, tokens,
elapsed time, memory operations, and the unchanged original baseline. Results
identify the evaluated source hashes and local model environment.

The presentation/demo remains deferred; the runnable application, architecture,
documentation, test statements, and measured results are included.
