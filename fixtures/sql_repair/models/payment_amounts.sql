select
    case_id,
    currency,
    case when currency = 'EUR' then amount_minor * 100 else amount_minor end as reported_minor
from {{ ref('payment_input') }}
