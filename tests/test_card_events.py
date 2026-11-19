from copy import deepcopy
import json
from pathlib import Path

from aegis_lakehouse.card_events import select_versions, timestamp


def demo_fixture():
    return json.loads((Path(__file__).resolve().parents[1] / "fixtures/card_demo.json").read_text())


def test_fixture_quarantines_malformed_amount_and_deduplicates_redelivery():
    fixture = demo_fixture()
    current, quarantine = select_versions(fixture, timestamp(fixture["as_of"]))
    assert [(r["event_id"], r["reason"]) for r in quarantine] == [("auth_card_malformed", "INVALID_AMOUNT")]
    for source, rows in current.items():
        assert len({r["authorization_id"] for r in rows}) == len(rows), source
    assert len([r for r in current["ledger"] if r["authorization_id"] == "card_clean"]) == 1


def test_future_correction_and_identical_delivery_have_distinct_effects():
    fixture = demo_fixture()
    original = next(r for r in fixture["ledger"] if r["authorization_id"] == "card_ledger_short")
    correction = dict(original, event_id="ledger_correction", event_version=2,
                      posted_at="2026-11-07T12:01:00Z", ledger_amount_minor=10000)
    fixture["ledger"].extend([correction, deepcopy(correction)])
    before, _ = select_versions(fixture, timestamp(fixture["as_of"]))
    after, _ = select_versions(fixture, timestamp("2026-11-07T12:01:00Z"))
    assert [r for r in before["ledger"] if r["authorization_id"] == "card_ledger_short"] == [original]
    assert [r for r in after["ledger"] if r["authorization_id"] == "card_ledger_short"] == [correction]


def test_conflicting_deliveries_are_quarantined():
    fixture = demo_fixture()
    event = fixture["ledger"][0]
    fixture["ledger"].append(dict(event, ledger_amount_minor=9900))
    current, quarantine = select_versions(fixture, timestamp(fixture["as_of"]))
    assert event["authorization_id"] not in {r["authorization_id"] for r in current["ledger"]}
    assert [r["reason"] for r in quarantine if r["event_id"] == event["event_id"]] == [
        "CONFLICTING_EVENT_ID", "CONFLICTING_EVENT_ID"
    ]
