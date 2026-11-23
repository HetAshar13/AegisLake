# Execution checkpoints

## Payment contract and fixture

- Defined synthetic, single-capture card reconciliation with a gross ledger posting in integer minor units.
- Added a deterministic source fixture and independently specified outcomes for 11 cases, unknown dimension IDs, and quarantine.

## Bronze to Gold

- Built the one-command Spark and Delta pipeline, version-aware three-way reconciliation, shared dimensions, and dbt models in DuckDB.
- Verified the active Delta snapshot separately from the underlying physical Parquet files.
- The [full Linux CI run](https://github.com/HetAshar13/AegisLake/actions/runs/44541926450) passed 60 Python tests and built 8 dbt models with 38 data tests. It checked all 11 fixture outcomes and exercised the Streamlit analyst view.

## Replay and analyst demo

- Reused one Bronze checkpoint across original delivery, identical redelivery, and a delayed ledger correction. The first two assessments match. The higher-version posting resolves exactly one discrepancy from −10 to 0 minor units, and the earlier warehouse remains available.
- The analyst view exposes each match-rate denominator, raw source event IDs, and quarantined input. The initial synthetic demo has 2 matched out of 10 assessed, 8 actionable breaks, 1 pending case, and 1 quarantined input.
- The release checks replayed the scenario, opened both snapshots in Chromium and repeated the benchmark.

## Benchmark and release

- The [recorded benchmark](https://github.com/HetAshar13/AegisLake/actions/runs/44449326062) passed all nine measured trials. The largest batch had 100,000 synthetic reconciliation cases, 245,455 committed Bronze envelopes, and a 30.29-second median for the full build and correctness checks.
- The README documents the supported payment model, quickstart, measurement boundary, and evidence. The [GitHub release](https://github.com/HetAshar13/AegisLake/releases/tag/v0.1.0) packages the recording and benchmark reports.
