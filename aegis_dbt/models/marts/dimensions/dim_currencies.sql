{{ config(materialized='table') }}

/*
  Dimension: dim_currencies
  Grain: Exactly one row per supported ISO-4217 currency.
  Purpose: Governs minor-unit exponent scaling and zero-decimal handling
           for all downstream financial reconciliation facts.
*/

-- TODO [YOUR TURN TO CODE]:
-- 1. Create a CTE `raw_currencies` with 5 rows using `UNION ALL`:
--    - ('EUR', 'Euro', 2, 'Cent')
--    - ('USD', 'US Dollar', 2, 'Cent')
--    - ('GBP', 'British Pound', 2, 'Penny')
--    - ('JPY', 'Japanese Yen', 0, 'Yen')
--    - ('BHD', 'Bahraini Dinar', 3, 'Fils')
WITH raw_currencies AS (
SELECT 'EUR' AS currency_code, 'Euro' AS currency_name, 2 AS currency_exponent, 'Cent' AS subdivision_name
UNION ALL SELECT 'USD', 'US Dollar', 2, 'Cent'
UNION ALL SELECT 'GBP', 'British Pound', 2, 'Penny'
UNION ALL SELECT 'JPY', 'Japanese Yen', 0, 'Yen'
UNION ALL SELECT 'BHD', 'Bahraini Dinar', 3, 'Fils'
)
--
-- 2. Select from `raw_currencies`:
--    - md5(currency_code) as currency_key (Surrogate Key)
--    - currency_code
--    - currency_name
--    - currency_exponent
--    - subdivision_name
--    - case when currency_exponent = 0 then true else false end as is_zero_decimal
--    - current_timestamp as created_at
SELECT
    md5(currency_code) AS currency_key,
    currency_code,
    currency_name,
    currency_exponent,
    subdivision_name,
    CASE WHEN currency_exponent = 0 THEN TRUE ELSE FALSE END AS is_zero_decimal,
    current_timestamp AS created_at
FROM raw_currencies 
