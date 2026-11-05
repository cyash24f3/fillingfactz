# Saved results

## Final benchmark

`benchmark/` preserves run `20261105T163921Z_96e9b031`: twenty statements in each
of three configurations, **60/60 correct and complete runs**.

- [Summary](benchmark/summary.md)
- [Structured metrics](benchmark/summary.json)
- [Full-workflow predictions](benchmark/full/predictions.json)
- [Memory-off predictions](benchmark/no_memory/predictions.json)
- [Single-agent predictions](benchmark/single_agent/predictions.json)
- [Run configuration and source hashes](benchmark/run.json)
- [Reference environment](benchmark/environment.json)

## Preserved baseline

`baseline/` contains the unchanged original sixty-run measurements from
`20261105T132118Z_6c5a757e`: full 85%, memory-off 100%, single-agent 100%.
Failures and incomplete reports are retained. See [Evaluation](../docs/EVALUATION.md)
for changes, measured improvements, and ablation findings.

## Interface checks and earlier diagnostics

- [Additional live API validation](api_validation/README.md): twelve statements,
  twelve complete correct reports, with saved SSE events.
- [Earlier focused diagnostic](diagnostic/summary.md): T15–T18, four matching
  completed verdicts; a selected subset rather than a complete benchmark.

Timestamped local experiment directories remain ignored by Git. Published result
snapshots retain their original predictions and identify their evaluated source.
