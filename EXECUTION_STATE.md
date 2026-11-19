# Execution checkpoints

## Payment contract and fixture

- Base commit d5400876046a12e68faedd3db03d939b83fa6d74 on local branch reconciliation-release.
- Added the synthetic payment contract, deterministic source fixture and expected outcomes.
- Next phase connects the fixture to Spark, Delta, dbt and DuckDB.

## Core implementation

- Added the portable one-command Bronze-to-Gold runner, strict source validation, ledger-aware three-way join, Delta-aware dbt sources, shared dimension registry, analyst UI and CI job.
- The card contract tests and existing non-Spark suite passed locally (47 tests). Ruff passed.
- PySpark started its JVM after moving Ivy and temporary files into the workspace. Windows blocked the Py4J loopback connection with WinError 10013. The full Spark run is pending in an environment that permits loopback.
