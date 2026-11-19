select
    md5(r.authorization_id) as break_key,
    r.* exclude (discrepancy_amount),
    c.currency_key,
    r.discrepancy_amount as discrepancy_amount_minor,
    cast(r.discrepancy_amount as double) / power(10, c.currency_exponent) as discrepancy_amount_scaled,
    current_timestamp as created_at
from {{ ref('stg_silver_reconciliation_breaks') }} r
left join {{ ref('dim_currencies') }} c on r.currency = c.currency_code
