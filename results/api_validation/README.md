# Live API validation

Run `api_20261105T163412Z_f58afd51` exercised the running FastAPI SSE endpoint
with twelve additional statements from `data/api_smoke_cases.json`. All twelve
returned complete, correct verdicts and finished their event streams.

Only the statement and run settings were sent to the API. Expected verdicts and
source references remained in the client. One fresh evidence-memory namespace
was shared by the ordered requests; budgets were eight model and sixteen tool
calls. These are additional development checks, separate from the twenty-by-three
benchmark, and are not a held-out accuracy estimate.

Reproduce with a running API:

```sh
python -m filing_checker.api_evaluate
```

`run.json` records source hashes and the dataset hash. `predictions.json` contains
reports, citations, usage, and the complete SSE sequences. `environment.json`
records the local reference hardware and model. Latency includes HTTP/service
overhead and should not be compared directly with an isolated CLI benchmark.
