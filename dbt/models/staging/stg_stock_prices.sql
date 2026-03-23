{{ config(materialized='view') }}

select
    cast(date as date) as date,
    symbol,
    cast(open as double) as open,
    cast(high as double) as high,
    cast(low as double) as low,
    cast(close as double) as close,
    cast(adj_close as double) as adj_close,
    cast(volume as bigint) as volume
from {{ source('bronze', 'stock_prices') }}
