# Evaluation

## Dataset

[The labelled dataset](../data/test_statements.json) contains 20 statements:
seven `SUPPORTED`, seven `CONTRADICTED`, three `OUTDATED`, and three
`NOT_ENOUGH_INFO`. Coverage includes fiscal dates, headcount, revenue, percentages,
customer concentration, the July 19 incident, cash, assets, liabilities, table
scaling, temporal changes, and missing disclosures.

Each case includes an expected verdict, source references, and a rationale. Missing-
information cases use related passages as context rather than proof of corpus-wide
absence. Reference validation checks quotations, PDF pages, and temporal ordering.

## Protocol

| Configuration | Decomposer | Evidence memory | Statements |
|---|---|---|---:|
| `full` | Enabled | Enabled | 20 |
| `no_memory` | Enabled | Disabled | 20 |
| `single_agent` | Disabled | Enabled | 20 |

The complete comparison consists of **60 verification runs over 20 unique claims**.
All configurations use the same ordered cases and total call budgets. Each starts
with an isolated empty memory namespace; evidence can accumulate within that
configuration. Expected labels and reference answers are used for scoring, not
provided to the agents.

```sh
python -m filing_checker.evaluate --validate-only
python -m filing_checker.evaluate --mode all
```

A small diagnostic can be run independently:

```sh
python -m filing_checker.evaluate --mode full --ids T15 T16 T17 T18
```

`--limit` selects the first N cases and cannot be combined with `--ids`. Omit both
for the complete benchmark.

## Metrics and outputs

A prediction is correct only when its status is complete and its verdict matches
the recorded label. Reports include accuracy, completion counts, model calls,
tool calls, input/output tokens, elapsed time, and memory operations.

Each run saves:

```text
results/<run_id>/
  run.json
  summary.json
  summary.md
  full/predictions.json
  no_memory/predictions.json
  single_agent/predictions.json
```

Only selected configurations receive prediction files. Run metadata records the
model, budgets, case order, corpus fingerprint, dataset hash, and source-code hashes.
Predictions are written after each case, so partial runs remain inspectable.

## Final 60-run comparison

The [final benchmark](../results/benchmark/summary.md), run
`20261105T163921Z_96e9b031`, completed **60/60 correct runs**, with no errors or
incomplete results. Source hashes match the application in commit `d6a7e14`.

| Configuration | Accuracy | Completed | Model calls | Tool calls | Tokens | Seconds | Memory reads/writes |
|---|---:|---:|---:|---:|---:|---:|---:|
| Full | 100% | 20/20 | 54 | 74 | 191,196 | 839.5 | 20/18 |
| Memory disabled | 100% | 20/20 | 58 | 78 | 192,919 | 963.1 | 0/0 |
| Decomposer disabled | 100% | 20/20 | 35 | 54 | 158,559 | 772.2 | 20/18 |

Memory reads/writes count persistence operations, not the number of recalled
passages. Predictions include recalled passage IDs and saved-passage counts.

## Original baseline and improvements

The [unchanged original baseline](../results/baseline/summary.md), run
`20261105T132118Z_6c5a757e`, evaluated the application in commit `25edfb1`.
Full-workflow accuracy was 85% with eighteen completed cases; the other two
configurations scored 100%. T09 and T20 exhausted their budgets; T18 incorrectly
used global headcount to refute a smaller regional count. T20's matching fallback
label was scored incorrect because its status was incomplete.

| Configuration | Baseline accuracy | Final accuracy | Token reduction | Elapsed-time change |
|---|---:|---:|---:|---:|
| Full | 85% | 100% | 28.2% | 17.5% lower |
| Memory disabled | 100% | 100% | 19.9% | 11.4% lower |
| Decomposer disabled | 100% | 100% | 30.5% | 8.9% higher |

The changes filter weak memory matches, avoid repeated source text in model
history, and finalize searches that add no new evidence. Validation now handles
quotation styles, direct population scope, wrapped unit disclosures, monetary
precision, comparative year/date columns, and missing annual-period disclosures.
Numerical rejection feedback includes the resolved source value and column so
the model can correct an error instead of repeating the same submission.

## Ablation findings

With memory enabled, the full workflow used
**4 fewer model calls** and
**4 fewer tool calls** than memory-off in this run.
Token use was 0.9% lower and elapsed time was
12.8% lower. Evidence recall still adds
context; memory benefits depend on statement order and relevance, and a recalled
passage alone is not an efficiency gain.

The Decomposer-disabled configuration used 35 model calls versus
54 for the full workflow, with the same 100% development-set accuracy.
It is available through CLI and UI settings. The full multi-agent workflow remains
the default; the comparison makes its planning overhead explicit.

## Additional validation

[Live API results](../results/api_validation/README.md) record twelve additional
statements, all correct and complete, through the actual streaming HTTP endpoint.
These cover paraphrases, metrics, scaling, historical/current balances, regional
scope, forecasts, annual coverage, and comparative financial columns. Labels and
references stay in the evaluation client and are not sent to the service.

[Automated and browser validation](VALIDATION.md) covers 92 tests, a clean
installation, Swagger HTTP 200 responses, single/batch review, and JSON downloads.
The [earlier four-case diagnostic](../results/diagnostic/summary.md) is retained
as a separate selected-subset result.

## Interpretation

These statements form a development benchmark used during iteration, rather than
a held-out test set. All final predictions come from real local model inference;
there is no answer cache or case-ID routing. Corpus and dataset hashes are fixed,
and expected labels are used only for scoring. An incomplete result never earns
accuracy credit.

Elapsed times are single-run measurements on the recorded Apple M5 / 24 GiB
environment with a warm local model, not hardware-independent latency guarantees.
The full workflow used 28.2% fewer tokens and
17.5% less elapsed time than its original baseline while
improving completion and accuracy. This comparison includes implementation changes,
not merely a change to memory settings.

Keyword retrieval, text extraction, and model judgments have practical limits.
Exact citations establish provenance; they do not alone prove semantic entailment
or corpus-wide absence. Optional semantic reranking, OCR, and independent compound-
claim splitting are outside the current implementation. The
[presentation and demo guide](demo/README.md) explain the implementation and
recorded results.
