"""
AegisLake Module 4: Autonomous Multi-Agent Incident Commander
State Schema definition for LangGraph 1.2+
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal, Annotated
from operator import add
from langchain_core.messages import BaseMessage


def merge_dicts(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reducer function to merge state dictionaries without destructive overwrites.

    Implement the dictionary merging logic:
    - If left is empty/falsy, return right
    - If right is empty/falsy, return left
    - Return a new dictionary containing merged keys: {**left, **right}
    """
    if not left:
        return right
    if not right:
        return left
    return {**left, **right}


class IncidentState(TypedDict, total=False):
    """
    Shared State Schema for the AegisLake Incident Commander Graph.
    Acts as the 'Hospital Clipboard' passed and enriched across nodes.

     Define the 7 sections of fields with their exact types:

    1. Metadata & Identifiers:
       - incident_id: str
       - rail_source: Literal["revolut", "ion_group", "internal_lakehouse"]
       - timestamp: str
       - severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNASSIGNED"]

    2. Break Payload & Triage State:
       - break_payload: Dict[str, Any]
       - triage_classification: Optional[str]
       - financial_impact_usd: float
       - affected_assets: List[str]

    3. Forensic & Quarantine Data:
       - quarantine_status: bool
       - quarantine_table_ref: Optional[str]
       - forensic_inspection_results: Dict[str, Any]

    4. Deterministic AST Lineage (SQLglot):
       - ast_lineage_graph: Dict[str, Any]
       - impacted_downstream_pipelines: List[str]
       - root_cause_column: Optional[str]
       - root_cause_table: Optional[str]

    5. Remediation & Dry-Run Validation:
       - proposed_patch: Optional[str]
       - patch_rationale: Optional[str]
       - patch_validation_results: Dict[str, Any]
       - dry_run_success: bool

    6. HITL Governance & Compliance (SOX/DORA):
       - human_reviewer_id: Optional[str]
       - human_approval_status: Literal["PENDING", "APPROVED", "REJECTED"]
       - compliance_audit_logged: bool
       - compliance_signoff_id: Optional[str]

    7. Reducer-managed Append & Merge Fields (Annotated):
       - messages: Annotated[List[BaseMessage], add]
       - audit_trail: Annotated[List[Dict[str, Any]], add]
       - error_state: Annotated[Dict[str, Any], merge_dicts]
       - retry_count: int
    """

    incident_id: str
    rail_source: Literal["revolut", "ion_group", "internal_lakehouse"]
    timestamp: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNASSIGNED"]

    break_payload: Dict[str, Any]
    triage_classification: Optional[str]
    financial_impact_usd: float
    affected_assets: List[str]

    quarantine_status: bool
    quarantine_table_ref: Optional[str]
    forensic_inspection_results: Dict[str, Any]

    ast_lineage_graph: Dict[str, Any]
    impacted_downstream_pipelines: List[str]
    root_cause_column: Optional[str]
    root_cause_table: Optional[str]

    proposed_patch: Optional[str]
    patch_rationale: Optional[str]
    patch_validation_results: Dict[str, Any]
    dry_run_success: bool

    human_reviewer_id: Optional[str]
    human_approval_status: Literal["PENDING", "APPROVED", "REJECTED"]
    compliance_audit_logged: bool
    compliance_signoff_id: Optional[str]

    messages: Annotated[List[BaseMessage], add]
    audit_trail: Annotated[List[Dict[str, Any]], add]
    error_state: Annotated[Dict[str, Any], merge_dicts]
    retry_count: int
