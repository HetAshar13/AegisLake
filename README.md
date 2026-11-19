# AegisLake

A local lakehouse demo for synthetic card-payment reconciliation. It compares authorizations, gross settlements, and ledger postings, then exposes unresolved cases and source event IDs in Streamlit.

## Run the demo

Use Python 3.12, Java 17, and a Spark-compatible environment. Install the pinned dependencies with `pip install -r requirements.txt`. Initial Spark and DuckDB setup may download the Delta dependencies.

From the repository root, set `PYTHONPATH=src` (`$env:PYTHONPATH='src'` in PowerShell).

```bash
python scripts/run_card_demo.py --output runs/card-demo --expected fixtures/card_demo_expected.json
streamlit run src/aegis_ui/app.py
```

Choose a fresh output directory for each rebuild. Set `AEGIS_WAREHOUSE` to that run's `aegislake.duckdb` to inspect an alternate run in Streamlit.

Run `python scripts/verify_card_replay.py --output runs/card-replay` to deliver the fixture twice, then supply a
versioned correction with the same authorization ID. Each step uses its own warehouse and the same Bronze
checkpoint. Run the steps sequentially when sharing a checkpoint. The verifier compares the three assessments
and checks that only the €0.10 case changes.

Select `card_ledger_short` in the case queue. The authorization and settlement each equal EUR 100.00 and the ledger recorded EUR 99.90. The case reports a EUR 0.10 ledger discrepancy. The dashboard's denominator tab lists each assessed case used in the match rate.

## Data flow

1. The runner stores delivered source payloads in Bronze Delta and validates event identities, timestamps and minor-unit amounts.
2. Spark joins one current event per source and authorization ID, then writes Silver assessments and quarantine. Missing legs and incompatible currencies retain null variances.
3. dbt reads the active Delta snapshot into DuckDB and builds the facts and dimensions. The runner can compare the resulting case outcomes with the independent fixture.
4. Streamlit reads the generated Gold tables and quarantine in read-only mode.

The [card contract](docs/card-reconciliation.md) describes the supported rail, gross posting convention, deadlines and event versions. The repository also includes experimental integrations for brokers, cloud deployment, and LangGraph human review.
