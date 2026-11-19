select
    authorization_id,
    customer_id,
    merchant_id,
    merchant_mcc,
    currency as currency_code,
    amount_minor as auth_amount_minor,
    status as auth_status,
    cast(authorized_at as timestamp) as authorized_at
from {{ source('delta_lakehouse', 'silver_authorizations') }}
