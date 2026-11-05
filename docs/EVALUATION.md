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

The full 60-run comparison is in progress and will be published after completion.
Generated benchmark output and local experiment history remain outside the curated
repository report until that update.

## Interpretation

The dataset is a development benchmark used during iteration rather than a held-out
test set. Calls and tokens should be compared alongside accuracy and completion;
lower usage alone does not establish a better verifier. Model/backend behavior,
memory reuse, statement order, and local hardware can affect latency and outcomes.
