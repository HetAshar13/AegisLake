select
    md5(customer_id || '_' || valid_from) as customer_key,
    customer_id,
    customer_name,
    kyc_tier,
    risk_score,
    cast(valid_from as timestamp) as valid_from,
    cast(null as timestamp) as valid_to,
    true as is_current,
    current_timestamp as created_at
from {{ source('delta_lakehouse', 'customers') }}
