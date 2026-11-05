# Complete benchmark snapshot

Run: `20261105T163921Z_96e9b031`.

All twenty statements completed with matching verdicts in all three configurations:
**60/60 correct verification runs**. This directory preserves the evaluator's
unmodified predictions, configuration metadata, and summaries.

Application-source hashes in `run.json` match commit `d6a7e14`. Documentation and
result publication do not change the evaluated application files. The earlier
baseline remains separate under `../baseline/`.

Each configuration started with an isolated empty evidence-memory namespace,
used the same ordered statements, and retained budgets of eight model calls and
sixteen tool calls. Expected labels were used for scoring only. The reference
environment and model digest are recorded in `environment.json`.
