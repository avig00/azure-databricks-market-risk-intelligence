{{ config(materialized='view') }}

select
    cast(date as date) as date,
    series_id,
    cast(value as double) as value
from {{ source('bronze', 'macro_indicators') }}
