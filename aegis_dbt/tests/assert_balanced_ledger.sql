-- A matched case requires three legs and both same-currency variances equal to zero.
select authorization_id, reconciliation_status
from {{ ref('fact_reconciliation_breaks') }}
where
    case when auth_currency = settled_currency then settled_amount_minor - auth_amount_minor end
        is distinct from discrepancy_amount_minor
    or case when settled_currency = ledger_currency then ledger_amount_minor - settled_amount_minor end
        is distinct from ledger_discrepancy_minor
    or (reconciliation_status = 'MATCHED' and (
        discrepancy_amount_minor is distinct from 0
        or ledger_discrepancy_minor is distinct from 0
        or entry_type is distinct from 'DEBIT'
        or is_actionable_break
    ))
