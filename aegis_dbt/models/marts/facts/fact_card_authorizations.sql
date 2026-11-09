{{ config(materialized='table') }}

/*
  Fact: fact_card_authorizations
  Grain: Exactly one row per card authorization attempt.
  Type: Transactional Fact Table.
  Purpose: Connects payment measurements (minor and scaled amounts) to
           surrogate foreign keys from dimensions, with point-in-time
           customer KYC resolution.
*/

-- TODO [YOUR TURN TO CODE]:
-- 1. Create a CTE `raw_authorizations` with 5 seed transactions using UNION ALL:
--    Columns:
--      - authorization_id: string
--      - customer_id: string
--      - merchant_id: string
--      - currency_code: string
--      - auth_amount_minor: bigint
--      - auth_status: string ('APPROVED', 'DECLINED')
--      - authorized_at: string
--
--    Rows to create:
--      - ('AUTH_001', 'CUST_ALICE_01', 'M_AMZN', 'EUR', 4500, 'APPROVED', '2026-03-15 14:30:00')
--      - ('AUTH_002', 'CUST_ALICE_01', 'M_APPL_05', 'EUR', 129900, 'APPROVED', '2026-07-20 10:15:00')
--      - ('AUTH_003', 'CUST_BOB_02', 'M_UBER_02', 'USD', 2450, 'APPROVED', '2026-04-10 18:00:00')
--      - ('AUTH_004', 'CUST_BOB_02', 'M_ESSO_03', 'EUR', 6500, 'APPROVED', '2026-09-05 08:45:00')
--      - ('AUTH_005', 'CUST_CHARLIE_03', 'M_TESCO_04', 'GBP', 3200, 'APPROVED', '2026-05-12 12:00:00')
  
WITH raw_authorizations AS (
    SELECT * FROM {{ ref('stg_silver_authorizations') }}
)
-- 2. In the final SELECT, join `raw_authorizations` with the dimensions:
--    - JOIN {{ ref('dim_currencies') }} c ON a.currency_code = c.currency_code
--    - JOIN {{ ref('dim_merchants') }} m ON a.merchant_id = m.merchant_id
--    - JOIN {{ ref('dim_customers') }} cust ON a.customer_id = cust.customer_id
--        AND cast(a.authorized_at as timestamp) >= cust.valid_from
--        AND (cast(a.authorized_at as timestamp) < cust.valid_to OR cust.valid_to IS NUL

-- 3. Select columns:
--    - md5(a.authorization_id) as authorization_key (Surrogate Key)
--    - a.authorization_id (Degenerate Dimension)
--    - cust.customer_key (Foreign Key)
--    - m.merchant_key (Foreign Key)
--    - c.currency_key (Foreign Key)
--    - a.auth_amount_minor (Metric in minor units)
--    - (cast(a.auth_amount_minor as double) / power(10, c.currency_exponent)) as auth_amount_scaled
--    - a.auth_status
--    - cast(a.authorized_at as timestamp) as authorized_at
--    - current_timestamp as created_at
SELECT
md5(a.authorization_id) AS authorization_key,
a.authorization_id,  cust.customer_key, m.merchant_key, c.currency_key, a.auth_amount_minor,
(cast(a.auth_amount_minor as double) / power(10, c.currency_exponent)) AS auth_amount_scaled,
a.auth_status, cast(a.authorized_at as timestamp) AS authorized_at,
current_timestamp AS created_at
FROM raw_authorizations a

LEFT JOIN {{ ref('dim_currencies') }} c ON a.currency_code = c.currency_code
LEFT JOIN {{ ref('dim_merchants') }} m ON a.merchant_id = m.merchant_id
LEFT JOIN {{ ref('dim_customers') }} cust ON a.customer_id = cust.customer_id
AND cast(a.authorized_at as timestamp) >= cust.valid_from AND (cast(a.authorized_at as timestamp) < cust.valid_to OR cust.valid_to IS NULL)