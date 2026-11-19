# Execution checkpoints

## Payment contract and fixture

- Base commit d5400876046a12e68faedd3db03d939b83fa6d74 on local branch reconciliation-release.
- Added the synthetic payment contract, deterministic source fixture and expected outcomes.
- Next phase connects the fixture to Spark, Delta, dbt and DuckDB.

## Core implementation

- Added the portable one-command Bronze-to-Gold runner, strict source validation, ledger-aware three-way join, Delta-aware dbt sources, shared dimension registry, analyst UI and CI job.
- The card contract tests and existing non-Spark suite passed locally (47 tests). Ruff passed.
- PySpark started its JVM after moving Ivy and temporary files into the workspace. Windows blocked the Py4J loopback connection with WinError 10013. The full Spark run is pending in an environment that permits loopback.

## Replay implementation and verification

- Added a persistent Spark file checkpoint and a three-run verifier for original delivery, redelivery, and a later ledger correction. The verifier checks that only the EUR 0.10 case changes and that earlier assessments remain inspectable.
- With independently prepared Delta snapshots, dbt built 8 models, passed 38 data tests, and matched all 11 expected case outcomes, dimension identities, and quarantine.
- Confirmed the checked-in Delta table exposes 100 current authorizations while its physical Parquet files contain 200 rows. Added a regression test.
- On this Windows workspace, Ruff and all 48 non-Spark pytest tests passed. GitHub Actions now defines the complete demo build and replay checks. That workflow has not run for this local branch.
- Remaining gates are to run the Spark integration and replay workflow where Java loopback works, then measure reproducible throughput and record the release demo. The independently prepared Delta run validates the warehouse layer only.

## Analyst view check

- Ran the app code against the verified DuckDB warehouse with a test double for Streamlit. The overview reported 2 matched out of 10 assessed cases, 8 actionable breaks, 1 pending case and 1 quarantined record. Selecting card_ledger_short returned a ledger variance of -10 minor units.
- The full Streamlit AppTest also needs local sockets on Windows. Its event loop stalled in socketpair setup in this workspace, so live rendering remains to be checked with the Spark run.
