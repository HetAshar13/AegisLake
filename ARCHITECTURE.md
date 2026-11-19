# AegisLake architecture

The current demo follows a single synthetic card authorization across settlement and ledger systems. Source payloads are preserved in Bronze Delta. Validation isolates malformed inputs and conflicting versions. Spark reads eligible current versions and joins all three sources on the case identifier. Silver retains the independent amounts, source event IDs, missing legs and triggered rules.

dbt reads current Delta snapshots and builds DuckDB dimensions and facts. Authorizations and dimensions use the shared fixture registry. The Streamlit case queue, match-rate denominator and quarantine view read the generated warehouse. The runner checks independently authored expected outcomes when supplied.

The optional file-ingestion path uses a persistent Spark checkpoint and Bronze table. Silver and Gold run into a new directory for each assessment. Preserve successive output directories to inspect the previous and current case state. This local fixture runner materializes delivery records on the driver. Measure that path as a whole when reporting a local benchmark.

See the [card reconciliation contract](docs/card-reconciliation.md) for money and version semantics.
