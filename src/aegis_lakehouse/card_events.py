"""Validate synthetic card source records before the three-way join."""

from collections import defaultdict
from datetime import datetime
import json

SOURCES = {
    "authorizations": ("authorized_at", "amount_minor", "currency"),
    "settlements": ("settled_at", "settled_amount_minor", "settled_currency"),
    "ledger": ("posted_at", "ledger_amount_minor", "currency"),
}
CURRENCIES = ("EUR", "USD", "GBP", "JPY", "BHD")


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None
    return parsed if parsed.utcoffset() is not None else None


def validate(source, row):
    time_key, amount_key, currency_key = SOURCES[source]
    for field in ("authorization_id", "event_id"):
        if not isinstance(row.get(field), str) or not row[field].strip():
            return "MISSING_ID"
    if type(row.get("event_version")) is not int or not 0 < row["event_version"] < 2**63:
        return "INVALID_VERSION"
    if not timestamp(row.get(time_key)):
        return "INVALID_TIMESTAMP"
    if type(row.get(amount_key)) is not int or not 0 < row[amount_key] <= 10**15:
        return "INVALID_AMOUNT"
    if row.get(currency_key) not in CURRENCIES:
        return "INVALID_CURRENCY"
    if source == "settlements" and (
        type(row.get("fee_minor")) is not int or not 0 <= row["fee_minor"] <= row[amount_key]
    ):
        return "INVALID_FEE"
    if source == "ledger" and row.get("entry_type") not in ("DEBIT", "CREDIT"):
        return "INVALID_DIRECTION"
    if source == "authorizations" and any(
        not isinstance(row.get(k), str) or not row[k].strip()
        for k in ("customer_id", "merchant_id", "merchant_mcc", "status")
    ):
        return "MISSING_AUTHORIZATION_ATTRIBUTE"
    return None


def select_versions(fixture, as_of):
    """Quarantine invalid/conflicting records and return at most one source row per case."""
    current = {source: [] for source in SOURCES}
    quarantine = []
    for source, (time_key, _, _) in SOURCES.items():
        by_event = defaultdict(dict)

        def quarantine_record(row, payload, reason):
            quarantine.append({
                "source": source,
                "event_id": str(row.get("event_id") or ""),
                "payload": payload,
                "reason": reason,
            })

        for row in fixture[source]:
            payload = json.dumps(row, sort_keys=True)
            reason = validate(source, row)
            if reason:
                quarantine_record(row, payload, reason)
            elif timestamp(row[time_key]) <= as_of:
                by_event[row["event_id"]][payload] = row
        by_case = defaultdict(lambda: defaultdict(list))
        blocked_versions = defaultdict(set)
        for events in by_event.values():
            if len(events) > 1:
                for payload, row in events.items():
                    quarantine_record(row, payload, "CONFLICTING_EVENT_ID")
                    blocked_versions[row["authorization_id"]].add(row["event_version"])
            else:
                payload, row = next(iter(events.items()))
                by_case[row["authorization_id"]][row["event_version"]].append((payload, row))
        for case_id, versions in by_case.items():
            latest = max(set(versions) | blocked_versions[case_id])
            for version, events in versions.items():
                if len(events) > 1:
                    for payload, row in events:
                        quarantine_record(row, payload, "CONFLICTING_CASE_VERSION")
                elif version == latest and version not in blocked_versions[case_id]:
                    current[source].append(events[0][1])
    return current, quarantine
