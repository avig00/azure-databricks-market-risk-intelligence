{{ config(materialized='table') }}

with prices as (
    select *
    from {{ ref('stg_stock_prices') }}
)

select
    date,
    symbol,
    coalesce(
        adj_close / lag(adj_close) over (partition by symbol order by date) - 1.0,
        0.0
    ) as daily_return
from prices
