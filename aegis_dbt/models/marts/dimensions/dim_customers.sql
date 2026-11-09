{{ config(materialized='table') }}

/*
  Dimension: dim_customers (SCD Type 2)
  Grain: Exactly one row per customer version.
  Purpose: Preserves historical changes in customer KYC tiers, risk scores,
           and legal metadata over time for forensic auditability.
*/

-- TODO [YOUR TURN TO CODE]:
-- 1. Create a CTE `raw_customers` with 5 seed rows using UNION ALL:
--    (Notice Alice and Bob each have 2 historical versions!)
--    Columns needed:
--      - customer_id: string
--      - customer_name: string
--      - kyc_tier: string ('TIER_1_BASIC', 'TIER_2_STANDARD', 'TIER_3_ENHANCED')
--      - risk_score: integer (1 to 100)
--      - valid_from: string timestamp (e.g. '2026-01-01 00:00:00')
--      - valid_to: string timestamp or NULL (e.g. '2026-06-01 00:00:00' or cast(null as varchar))
WITH raw_customers AS (
 SELECT 'CUST_ALICE_01' AS customer_id, 'Alice Rossi' AS customer_name, 'TIER_1_BASIC' AS kyc_tier, 25 AS risk_score, '2026-01-01 00:00:00' AS valid_from, '2026-06-01 00:00:00' AS valid_to
 UNION ALL SELECT 'CUST_ALICE_01', 'Alice Rossi', 'TIER_3_ENHANCED', 15, '2026-06-01 00:00:00', cast(null as varchar)
 UNION ALL SELECT 'CUST_BOB_02', 'Bob Smith', 'TIER_1_BASIC', 85, '2026-02-15 00:00:00', '2026-08-01 00:00:00'
 UNION ALL SELECT 'CUST_BOB_02', 'Bob Smith', 'TIER_2_STANDARD', 45, '2026-08-01 00:00:00', cast(null as varchar)
 UNION ALL SELECT 'CUST_CHARLIE_03', 'Charlie Brown', 'TIER_2_STANDARD', 30, '2026-03-10 00:00:00', cast(null as varchar)
)

--
--    Rows to create:
--      - Alice V1: ('CUST_ALICE_01', 'Alice Rossi', 'TIER_1_BASIC', 25, '2026-01-01 00:00:00', '2026-06-01 00:00:00')
--      - Alice V2: ('CUST_ALICE_01', 'Alice Rossi', 'TIER_3_ENHANCED', 15, '2026-06-01 00:00:00', cast(null as varchar))
--      - Bob V1:   ('CUST_BOB_02', 'Bob Smith', 'TIER_1_BASIC', 85, '2026-02-15 00:00:00', '2026-08-01 00:00:00')
--      - Bob V2:   ('CUST_BOB_02', 'Bob Smith', 'TIER_2_STANDARD', 45, '2026-08-01 00:00:00', cast(null as varchar))
--      - Charlie:  ('CUST_CHARLIE_03', 'Charlie Brown', 'TIER_2_STANDARD', 30, '2026-03-10 00:00:00', cast(null as varchar))
--
-- 2. Select from `raw_customers`:
--    - Surrogate key: md5(customer_id || '_' || valid_from) as customer_key
--    - customer_id, customer_name, kyc_tier, risk_score
--    - cast(valid_from as timestamp) as valid_from
--    - cast(valid_to as timestamp) as valid_to
--    - (valid_to is null) as is_current  (Or use CASE WHEN valid_to is null then true else false end)
--    - current_timestamp as created_at
SELECT 
md5(customer_id || '_' || valid_from) AS customer_key,
customer_id, customer_name, kyc_tier, risk_score,
cast(valid_from as timestamp) AS valid_from,
cast(valid_to as timestamp) AS valid_to,
CASE WHEN valid_to IS NULL THEN TRUE ELSE FALSE END AS is_current,
current_timestamp AS created_at
FROM raw_customers