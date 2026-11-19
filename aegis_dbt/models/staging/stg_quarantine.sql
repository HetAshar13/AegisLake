{{ config(materialized='table') }}

select source, event_id, payload, reason from {{ source('delta_lakehouse', 'quarantine') }}
