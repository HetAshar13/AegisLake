# AegisLake

A local lakehouse for synthetic card-payment reconciliation. Follow a card payment across authorization, settlement, and ledger records, investigate a discrepancy, and replay a versioned correction against a persistent checkpoint.

[CI checks](https://github.com/HetAshar13/AegisLake/actions/workflows/ci.yml) · [Payment contract](docs/card-reconciliation.md) · [Execution checkpoints](EXECUTION_STATE.md)

[Download the 90-second walkthrough](https://github.com/HetAshar13/AegisLake/actions/runs/44543678552/artifacts/14539656273) (GitHub sign-in required for the Actions artifact).

## Follow one payment

`card_ledger_short` has a EUR 100.00 authorization and settlement, but the ledger initially posts EUR 99.90. The original build reports a ledger variance of −10 minor units. Redelivering identical source events leaves the assessment unchanged. A higher-version ledger event corrects the variance to zero and moves just this case to `MATCHED`. Each run keeps a separate warehouse so you can inspect the before and after results.

## Run it locally

Use Python 3.12 and Java 17. Install the pinned dependencies from the repository root. The first build downloads Spark and DuckDB Delta dependencies.

```bash
python -m pip install -r requirements.txt
export PYTHONPATH=src
python scripts/run_card_demo.py --output runs/card-demo --expected fixtures/card_demo_expected.json
streamlit run src/aegis_ui/app.py
```

In PowerShell, use `$env:PYTHONPATH = "src"` in place of `export`. In Streamlit, select `card_ledger_short` in the case queue or append `?case=card_ledger_short` to the Streamlit URL. The denominator tab shows which cases contributed to the match rate.

To reproduce the original delivery, identical redelivery, and ledger correction, run `python scripts/verify_card_replay.py --output runs/card-replay`. The verifier checks that just one case changes and that the original assessments remain inspectable. Use a fresh output directory for each build. Set `AEGIS_WAREHOUSE` to a run’s `aegislake.duckdb` to open that run in Streamlit.

## What the pipeline verifies

1. Bronze Delta retains source deliveries, including malformed envelopes and duplicates. The pipeline validates event identity, timestamps, and amounts in integer minor units.
2. Spark selects the current version of each source leg, joins by authorization ID, and writes assessments and quarantine to Silver. Amount comparisons require both source legs and a shared currency.
3. dbt reads the active Delta snapshot into DuckDB and builds Gold facts and dimensions. An expected-results fixture checks 11 case outcomes, including mismatches, missing legs, and an overdue settlement.
4. Streamlit reads Gold and quarantine in read-only mode and exposes breaks, source event IDs, and the match-rate denominator.

## Measured batch performance

| Synthetic reconciliation cases | Committed Bronze envelopes | Median wall time | Min–max |
| ---: | ---: | ---: | ---: |
| 1,000 | 2,455 | 19.18 s | 19.08–20.80 s |
| 10,000 | 24,548 | 21.07 s | 20.73–21.34 s |
| 100,000 | 245,455 | 30.29 s | 29.94–30.48 s |

Three measured batches per size on one GitHub-hosted Linux runner, after a warm-up. Each trial starts a new Python process and Spark JVM and uses warm dependency caches. The timer covers reading the fixture, Bronze and Silver Delta writes, the dbt Gold build and tests, and comparison with expected case outcomes. The raw envelope count includes redeliveries and quarantined inputs and was checked independently against the committed Delta snapshot. All nine trials passed the correctness checks.

[Benchmark job and logs](https://github.com/HetAshar13/AegisLake/actions/runs/44449326062) · [Benchmark JSON and Markdown](https://github.com/HetAshar13/AegisLake/actions/runs/44449326062/artifacts/14494249023) · [Benchmark and recording runner](scripts/card_release_evidence.py)

The public demo covers synthetic, single-capture gross settlements. The [payment contract](docs/card-reconciliation.md) explains the posting convention, timing, and event versions. Broker, cloud, and LangGraph integrations are experimental.
