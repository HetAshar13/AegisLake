{{ config(materialized='table') }}

/*
  Dimension: dim_merchants
  Grain: Exactly one row per merchant.
  Purpose: Maps merchant identifiers to Merchant Category Codes (MCC),
           human-readable category names, and fraud risk tiers.
*/

-- TODO [YOUR TURN TO CODE]:
-- 1. Create a CTE `raw_merchants` with seed merchants using UNION ALL:
--    Columns needed:
--      - merchant_id (e.g. 'M_AMZN_01', 'M_UBER_02', 'M_ESSO_03', 'M_TESCO_04', 'M_APPL_05')
--      - merchant_name (e.g. 'Amazon EU', 'Uber Rides', 'Esso Petrol Station', 'Tesco Superstore', 'Apple Retail')
--      - mcc (e.g. '5311', '4121', '5541', '5411', '5732')
--      - country_code (e.g. 'LU', 'NL', 'IT', 'GB', 'IE')
WITH raw_merchants AS(
  SELECT 'M_AMZN' AS merchant_id, 'Amazon EU' AS merchant_name, '5311' AS mcc, 'LU' AS country_code
  UNION ALL SELECT 'M_UBER_02', 'Uber Rides', '4121', 'NL'
  UNION ALL SELECT 'M_ESSO_03', 'Esso Petrol Station', '5541', 'IT'   
  UNION ALL SELECT 'M_TESCO_04', 'Tesco Superstore', '5411', 'GB'
  UNION ALL SELECT 'M_APPL_05', 'Apple Retail', '5732', 'IE'
)

--
-- 2. Select from `raw_merchants`:
--    - Surrogate key: md5(merchant_id) as merchant_key
--    - merchant_id, merchant_name, mcc, country_code
--    - CASE WHEN statement for category_name based on mcc:
--        '5411' -> 'GROCERY'
--        '4121' -> 'TRANSPORT'
--        '5541' -> 'FUEL'
--        '5732' -> 'ELECTRONICS'
--        ELSE 'GENERAL_RETAIL'
--    - CASE WHEN statement for merchant_risk_tier:
--        mcc in ('5541', '5732') -> 'MEDIUM'
--        mcc = '4121' -> 'LOW'
--        ELSE 'LOW'
--    - current_timestamp as created_at

SELECT
  md5(merchant_id) AS merchant_key,
  merchant_id, merchant_name, mcc, country_code,
CASE WHEN mcc = '5411' THEN 'GROCERY'
     WHEN mcc = '4121' THEN 'TRANSPORT'
     WHEN mcc = '5541' THEN 'FUEL'
     WHEN mcc = '5732' THEN 'ELECTRONICS'
     ELSE 'GENERAL_RETAIL' END AS category_name,
CASE WHEN mcc IN ('5541', '5732') THEN 'MEDIUM'
ELSE  'LOW' END AS merchant_risk_tier,
current_timestamp AS created_at
FROM raw_merchants