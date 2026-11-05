# Saved results

## Complete benchmark

`benchmark/` preserves run `20261105T132118Z_6c5a757e`: 20 statements in each of
three configurations, for 60 verification runs.

- [Summary table](benchmark/summary.md)
- [Structured metrics](benchmark/summary.json)
- [Full-workflow predictions](benchmark/full/predictions.json)
- [Memory-off predictions](benchmark/no_memory/predictions.json)
- [Single-agent predictions](benchmark/single_agent/predictions.json)
- [Run configuration and source hashes](benchmark/run.json)

Full accuracy is 85%; memory-off and single-agent accuracy are 100% on this
development dataset. Incomplete results are counted as incorrect. See
[Evaluation](../docs/EVALUATION.md) for the interpretation and failure analysis.

## Focused diagnostic

`diagnostic/` preserves completed run `20261105T131412Z_b232e132`, covering T15,
T16, T17, and T18 in the full configuration. All four cases completed with matching
verdicts. This is a selected subset, not a full-benchmark score.

- [Diagnostic metrics](diagnostic/summary.md)
- [Predictions and traces](diagnostic/full/predictions.json)

Timestamped local experiment directories are ignored by Git. Published snapshots
are immutable; follow-up runs use separate directories and identify their source
version and procedure.
