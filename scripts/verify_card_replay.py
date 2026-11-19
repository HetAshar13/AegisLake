"""Exercise redelivery and a late correction across three Spark processes."""

import argparse
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys

import duckdb

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/card_demo.json"
EXPECTED = ROOT / "fixtures/card_demo_expected.json"


def build(workspace, name, fixture, expected):
    output = workspace / name
    subprocess.run([
        sys.executable, str(ROOT / "scripts/run_card_demo.py"),
        "--fixture", str(fixture), "--expected", str(expected), "--output", str(output),
        "--checkpoint-dir", str(workspace / "stream"),
    ], check=True)
    return output / "aegislake.duckdb"


def snapshot(path):
    with duckdb.connect(str(path), read_only=True) as db:
        return db.execute("""
            select authorization_id, reconciliation_status, discrepancy_amount_minor,
                   ledger_discrepancy_minor, ledger_event_id
            from fact_reconciliation_breaks
            order by authorization_id
        """).fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    workspace = args.output.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    original = build(workspace, "01_original", FIXTURE, EXPECTED)
    duplicate = build(workspace, "02_replay", FIXTURE, EXPECTED)
    before = snapshot(original)
    assert snapshot(duplicate) == before, "Redelivery changed the assessed cases"

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    amended = deepcopy(fixture)
    amended["as_of"] = "2026-11-07T12:01:00Z"
    for source in ("authorizations", "settlements", "ledger"):
        amended[source] = []
    ledger = next(row for row in fixture["ledger"] if row["authorization_id"] == "card_ledger_short")
    amended["ledger"].append(dict(
        ledger, event_id="ledger_card_ledger_short_corrected", event_version=2,
        posted_at=amended["as_of"], ledger_amount_minor=10000,
    ))
    updated = json.loads(EXPECTED.read_text(encoding="utf-8"))
    updated["cases"]["card_ledger_short"] = {"status": "MATCHED", "settlement_delta": 0, "ledger_delta": 0}
    update_path = workspace / "correction.json"
    expected_path = workspace / "expected_after_correction.json"
    update_path.write_text(json.dumps(amended, indent=2), encoding="utf-8")
    expected_path.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    corrected = build(workspace, "03_correction", update_path, expected_path)

    after = snapshot(corrected)
    changed = [(left, right) for left, right in zip(before, after, strict=True) if left != right]
    assert changed == [(
        ("card_ledger_short", "BREAK_LEDGER_AMOUNT_MISMATCH", 0, -10, "ledger_card_ledger_short"),
        ("card_ledger_short", "MATCHED", 0, 0, "ledger_card_ledger_short_corrected"),
    )], changed
    assert snapshot(original) == before, "Original assessment was modified"
    print("Verified replay, checkpoint restart and one late correction")


if __name__ == "__main__":
    main()
