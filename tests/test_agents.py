"""
AegisLake Module 4: Autonomous Multi-Agent Incident Commander Tests
Verifies Agent State, Reducers, AST Lineage, Forensic Tools, and Graph Execution.
"""

import pytest
from operator import add
from typing import get_type_hints


def test_state_schema_imports():
    """Verify that IncidentState and merge_dicts can be imported cleanly."""
    from aegis_agent.state import IncidentState, merge_dicts

    assert IncidentState is not None
    assert callable(merge_dicts)


def test_merge_dicts_reducer():
    """Verify the non-destructive dictionary merger used for error state tracking."""
    from aegis_agent.state import merge_dicts

    # Case 1: Merge distinct dicts
    d1 = {"node_1_err": "connection timeout"}
    d2 = {"node_2_err": "syntax error"}
    merged = merge_dicts(d1, d2)
    assert merged == {"node_1_err": "connection timeout", "node_2_err": "syntax error"}

    # Case 2: Left empty
    assert merge_dicts({}, d2) == d2

    # Case 3: Right empty
    assert merge_dicts(d1, {}) == d1

    # Case 4: Overwrite specific key update
    d3 = {"node_1_err": "resolved"}
    merged_update = merge_dicts(d1, d3)
    assert merged_update["node_1_err"] == "resolved"


def test_incident_state_instantiation():
    """Verify IncidentState instantiates and supports total=False partial initialization."""
    from aegis_agent.state import IncidentState

    initial_state: IncidentState = {
        "incident_id": "INC-2026-001",
        "rail_source": "revolut",
        "timestamp": "2026-11-07T12:00:00Z",
        "severity": "CRITICAL",
        "financial_impact_usd": 150000.50,
        "affected_assets": ["fact_reconciliation_breaks", "silver_authorizations"],
        "quarantine_status": True,
        "human_approval_status": "PENDING",
        "audit_trail": [{"step": "triage", "action": "flagged_critical", "timestamp": "2026-11-07T12:00:01Z"}],
        "error_state": {},
        "retry_count": 0,
    }

    assert initial_state["incident_id"] == "INC-2026-001"
    assert initial_state["severity"] == "CRITICAL"
    assert initial_state["human_approval_status"] == "PENDING"
    assert len(initial_state["audit_trail"]) == 1


def test_incident_state_required_fields_present():
    """Verify that all enterprise governance, lineage, and remediation fields exist in IncidentState annotations."""
    from aegis_agent.state import IncidentState

    annotations = IncidentState.__annotations__

    expected_fields = [
        # Metadata
        "incident_id",
        "rail_source",
        "timestamp",
        "severity",
        # Break & Triage
        "break_payload",
        "triage_classification",
        "financial_impact_usd",
        "affected_assets",
        # Forensic
        "quarantine_status",
        "quarantine_table_ref",
        "forensic_inspection_results",
        # AST Lineage
        "ast_lineage_graph",
        "impacted_downstream_pipelines",
        "root_cause_column",
        "root_cause_table",
        # Remediation
        "proposed_patch",
        "patch_rationale",
        "patch_validation_results",
        "dry_run_success",
        # HITL & Compliance
        "human_reviewer_id",
        "human_approval_status",
        "compliance_audit_logged",
        "compliance_signoff_id",
        # Reducer / Message fields
        "messages",
        "audit_trail",
        "error_state",
        "retry_count",
    ]

    missing_fields = [f for f in expected_fields if f not in annotations]
    assert not missing_fields, f"IncidentState is missing required enterprise fields: {missing_fields}"


# =====================================================================
# Step 4.2 Tests: Deterministic SQLglot AST Lineage Tool
# =====================================================================


def test_extract_column_lineage_ctes_and_scaling():
    """Verify AST lineage tracing across CTEs, column expressions, and table joins."""
    from aegis_agent.tools.lineage_parser import extract_column_lineage

    dbt_sql = """
    WITH base_breaks AS (
        SELECT 
            transaction_id,
            raw_amount * 100 AS discrepancy_amount_scaled,
            counterparty_id
        FROM stg_silver_authorizations
    ),
    enriched_breaks AS (
        SELECT 
            b.transaction_id,
            b.discrepancy_amount_scaled,
            c.currency_code
        FROM base_breaks b
        LEFT JOIN dim_currencies c ON b.counterparty_id = c.id
    )
    SELECT * FROM enriched_breaks
    """

    schema_map = {
        "stg_silver_authorizations": {
            "transaction_id": "varchar",
            "raw_amount": "decimal",
            "counterparty_id": "varchar",
        },
        "dim_currencies": {"id": "varchar", "currency_code": "varchar"},
    }

    result = extract_column_lineage(
        sql_query=dbt_sql, target_column="discrepancy_amount_scaled", dialect="duckdb", schema=schema_map
    )

    assert result["status"] == "SUCCESS"
    assert result["target_column"] == "discrepancy_amount_scaled"
    assert "raw_amount" in result["source_columns"]
    assert "stg_silver_authorizations" in result["upstream_tables"]
    assert any("raw_amount * 100" in expr for expr in result["expression_history"])


def test_extract_column_lineage_failure_handling():
    """Verify that syntax errors in SQL produce a graceful error response instead of crashing."""
    from aegis_agent.tools.lineage_parser import extract_column_lineage

    invalid_sql = "SELECT FROM WHERE;"
    result = extract_column_lineage(sql_query=invalid_sql, target_column="non_existent_col", dialect="duckdb")

    assert result["status"] == "FAILED"
    assert "error_message" in result


# =====================================================================
# Step 4.3 Tests: Forensic Inspector Tool
# =====================================================================


def test_fetch_worst_reconciliation_break_live():
    """Verify querying real break records from DuckDB lakehouse mart."""
    from aegis_agent.tools.forensic_inspector import fetch_worst_reconciliation_break

    worst = fetch_worst_reconciliation_break(db_path="aegis_dbt/aegislake_warehouse.duckdb")
    assert worst is not None
    assert "authorization_id" in worst
    assert worst["is_actionable_break"] is True
    assert "discrepancy_amount_scaled" in worst
    assert abs(worst["discrepancy_amount_scaled"]) > 0


def test_fetch_break_forensics_live():
    """Verify deep-dive forensic inspection of a real transaction."""
    from aegis_agent.tools.forensic_inspector import fetch_break_forensics

    forensics = fetch_break_forensics("AUTH_002", db_path="aegis_dbt/aegislake_warehouse.duckdb")
    assert forensics["status"] == "SUCCESS"
    assert forensics["authorization_id"] == "AUTH_002"
    assert forensics["reconciliation_status"] == "BREAK_AMOUNT_MISMATCH"
    assert forensics["discrepancy_amount_minor"] == -4900


def test_fetch_break_forensics_not_found():
    """Verify graceful handling when an unknown authorization_id is requested."""
    from aegis_agent.tools.forensic_inspector import fetch_break_forensics

    forensics = fetch_break_forensics("AUTH_NONEXISTENT_9999", db_path="aegis_dbt/aegislake_warehouse.duckdb")
    assert forensics["status"] == "NOT_FOUND"


# =====================================================================
# Step 4.4 Tests: Multi-Agent StateGraph & HITL Gate
# =====================================================================


def test_build_incident_commander_graph():
    """Verify graph compiles cleanly with MemorySaver checkpointer."""
    from aegis_agent.graph import build_incident_commander_graph

    graph = build_incident_commander_graph()
    assert graph is not None


def test_graph_execution_hitl_interrupt_and_approval():
    """Verify end-to-end execution: Triage -> Lineage -> Remediation -> HITL Interrupt -> Approval -> Compliance."""
    from aegis_agent.graph import build_incident_commander_graph
    from langgraph.types import Command

    graph = build_incident_commander_graph()
    config = {"configurable": {"thread_id": "thread-revolut-approval-001"}}

    initial_state = {
        "incident_id": "INC-2026-9921",
        "rail_source": "revolut",
        "timestamp": "2026-11-07T12:00:00Z",
        "break_payload": {
            "authorization_id": "AUTH_004",
            "discrepancy_amount_scaled": -65.0,
            "reconciliation_status": "BREAK_UNMATCHED_AUTHORIZATION",
        },
        "human_approval_status": "PENDING",
        "compliance_audit_logged": False,
        "audit_trail": [],
    }

    # Step 1: Run graph until human_review_node triggers an interrupt
    events = list(graph.stream(initial_state, config))
    assert len(events) > 0

    # Inspect state at interrupt point
    snapshot = graph.get_state(config)
    assert snapshot.next == ("human_review_node",)
    assert snapshot.values["severity"] == "CRITICAL"
    assert snapshot.values["quarantine_status"] is True
    assert snapshot.values["dry_run_success"] is True

    # Step 2: Resume execution with human approval
    resume_cmd = Command(resume={"status": "APPROVED", "reviewer_id": "lead_auditor_het"})
    resumed_events = list(graph.stream(resume_cmd, config))
    assert len(resumed_events) > 0

    # Verify finalized compliance state
    final_snapshot = graph.get_state(config)
    assert final_snapshot.values["human_approval_status"] == "APPROVED"
    assert final_snapshot.values["compliance_audit_logged"] is True
    assert "SOX-COMPLIANCE-INC-2026-9921" in final_snapshot.values["compliance_signoff_id"]


def test_graph_execution_hitl_rejection():
    """Verify that rejecting the patch terminates the workflow without logging compliance signoff."""
    from aegis_agent.graph import build_incident_commander_graph
    from langgraph.types import Command

    graph = build_incident_commander_graph()
    config = {"configurable": {"thread_id": "thread-revolut-rejection-002"}}

    initial_state = {
        "incident_id": "INC-2026-9922",
        "rail_source": "revolut",
        "timestamp": "2026-11-07T12:00:00Z",
        "break_payload": {
            "authorization_id": "AUTH_002",
            "discrepancy_amount_scaled": -49.0,
            "reconciliation_status": "BREAK_AMOUNT_MISMATCH",
        },
        "human_approval_status": "PENDING",
        "compliance_audit_logged": False,
        "audit_trail": [],
    }

    # Run until interrupt
    list(graph.stream(initial_state, config))

    # Resume with REJECTION
    resume_cmd = Command(resume={"status": "REJECTED", "reviewer_id": "lead_auditor_het"})
    list(graph.stream(resume_cmd, config))

    final_snapshot = graph.get_state(config)
    assert final_snapshot.values["human_approval_status"] == "REJECTED"
    assert final_snapshot.values["compliance_audit_logged"] is False
