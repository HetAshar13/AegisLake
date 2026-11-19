select
    md5(merchant_id) as merchant_key,
    merchant_id,
    merchant_name,
    mcc,
    country_code,
    case mcc
        when '5411' then 'GROCERY'
        when '4121' then 'TRANSPORT'
        when '5541' then 'FUEL'
        when '5732' then 'ELECTRONICS'
        else 'GENERAL_RETAIL'
    end as category_name,
    case when mcc in ('5541', '5732') then 'MEDIUM' else 'LOW' end as merchant_risk_tier,
    current_timestamp as created_at
from {{ source('delta_lakehouse', 'merchants') }}
