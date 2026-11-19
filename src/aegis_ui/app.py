"""Analyst view for the generated card reconciliation warehouse."""

import os
from pathlib import Path

import duckdb
import streamlit as st

st.set_page_config(page_title="AegisLake", layout="wide")
st.title("AegisLake")
st.caption("Synthetic card-payment reconciliation")

warehouse = Path(os.environ.get("AEGIS_WAREHOUSE", "runs/card-demo/aegislake.duckdb"))
if not warehouse.is_file():
    st.info("Build the card demo warehouse to view case assessments. See the README for the build command.")
    st.stop()

try:
    with duckdb.connect(str(warehouse), read_only=True) as db:
        cases = db.execute("""
            select r.*, coalesce(m.merchant_name, '') as merchant_name
            from fact_reconciliation_breaks r
            left join fact_card_authorizations a using (authorization_id)
            left join dim_merchants m on a.merchant_key = m.merchant_key
            order by r.is_actionable_break desc, r.authorization_id
        """).df()
        quarantine = db.execute("select * from stg_quarantine order by source, event_id").df()
except duckdb.Error:
    st.error("This warehouse is unavailable or its build is incomplete. Select a completed demo run.")
    st.stop()

if cases.empty:
    st.info("This run has no reconciliation cases.")
    st.stop()

st.caption(f"Run {warehouse.parent.name} · Assessed at {cases['reconciled_at'].max()} UTC")
matched = cases["reconciliation_status"].eq("MATCHED")
actionable = cases["is_actionable_break"]
assessed = cases[matched | actionable]
pending = cases["reconciliation_status"].eq("PENDING")
rate = f"{matched.sum() / len(assessed):.1%}" if len(assessed) else "Unavailable"
cards = st.columns(4)
cards[0].metric("Match rate among assessed cases", rate)
cards[1].metric("Actionable breaks", int(actionable.sum()))
cards[2].metric("Pending cases", int(pending.sum()))
cards[3].metric("Quarantined records", len(quarantine))

queue, scope, rejected = st.tabs(["Case queue", "Match rate denominator", "Quarantine"])
columns = ["authorization_id", "reconciliation_status", "merchant_name", "currency", "ledger_discrepancy_minor"]
with queue:
    requested_case = st.query_params.get("case")
    linked_case = cases["authorization_id"].eq(requested_case)
    filter_breaks = st.toggle("Actionable breaks only", value=not bool((linked_case & ~actionable).any()))
    filtered = cases[actionable] if filter_breaks else cases
    st.dataframe(filtered[columns], hide_index=True)
    if len(filtered):
        case_ids = filtered["authorization_id"].tolist()
        index = case_ids.index(requested_case) if requested_case in case_ids else 0
        selected = st.selectbox("Inspect a case", case_ids, index=index)
        case = filtered.loc[filtered["authorization_id"].eq(selected)].iloc[0]
        st.subheader(case["reconciliation_status"])
        if case["merchant_id"] is not None and not case["merchant_name"]:
            st.warning(f"Merchant ID {case['merchant_id']} was absent from this run's registry.")
        st.dataframe([
            {"Source": "Authorization", "Event ID": case["auth_event_id"],
             "Amount (minor units)": case["auth_amount_minor"], "Currency": case["auth_currency"]},
            {"Source": "Settlement", "Event ID": case["settlement_event_id"],
             "Amount (minor units)": case["settled_amount_minor"], "Currency": case["settled_currency"]},
            {"Source": "Ledger", "Event ID": case["ledger_event_id"],
             "Amount (minor units)": case["ledger_amount_minor"], "Currency": case["ledger_currency"]},
        ], hide_index=True)
        st.write(f"Checks flagged: {', '.join(case['break_reasons']) or 'None'}")
        st.write("Settlement fee (minor units)", case["fee_minor"])
        st.write("Ledger minus settlement (minor units)", case["ledger_discrepancy_minor"])
with scope:
    st.write(f"{matched.sum()} matched of {len(assessed)} assessed cases.")
    st.dataframe(assessed[columns], hide_index=True)
with rejected:
    st.dataframe(quarantine, hide_index=True)
