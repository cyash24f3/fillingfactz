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

## Checked-in results

[The completed diagnostic](../results/diagnostic/summary.md) checks T15–T18:
three temporal claims and one regional-headcount claim. It completed **4/4** with
matching verdicts. This is a **four-statement subset**, not a full-dataset accuracy
claim or a three-configuration comparison.

## Complete 60-run comparison

The [benchmark report](../results/benchmark/summary.md) contains all three
20-statement configurations from run `20261105T132118Z_6c5a757e`.

| Configuration | Accuracy | Completed | Model calls | Tool calls | Tokens | Seconds |
|---|---:|---:|---:|---:|---:|---:|
| Full | 85% | 18/20 | 61 | 81 | 266,260 | 1,017.1 |
| Memory disabled | 100% | 20/20 | 59 | 79 | 240,716 | 1,086.8 |
| Decomposer disabled | 100% | 20/20 | 38 | 58 | 228,157 | 708.9 |

The full configuration got 17 labels correct with complete status. T09 and T20
exhausted the model-call budget; T18 incorrectly contradicted a regional-headcount
claim using company-wide headcount evidence. T20's fallback label matches its
expected label but is scored incorrect because the run is incomplete.

Memory-on used two additional model calls, two additional tool calls, and 10.6%
more tokens than memory-off. The single-agent configuration used 37.7% fewer model
calls and took 30.3% less elapsed time than the full configuration. This small
single-run comparison supports keeping the simpler configuration available; it
does not establish universal superiority or a memory-efficiency gain.

The three observed failure paths are quotation styling, insufficient population-
scope checks, and repeated retrieval inflating message history. Source hashes in
`run.json` preserve the evaluated implementation. Follow-up code changes and
regression checks are separate; these baseline predictions remain unchanged.

## Interpretation

The dataset is a development benchmark used during iteration rather than a held-out
test set. Calls and tokens should be compared alongside accuracy and completion;
lower usage alone does not establish a better verifier. Model/backend behavior,
memory reuse, statement order, and local hardware can affect latency and outcomes.
