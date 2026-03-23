{{ config(materialized='table') }}

with prices as (
    select *
    from {{ ref('stg_stock_prices') }}
),
running_extrema as (
    select
        date,
        symbol,
        adj_close,
        max(adj_close) over (
            partition by symbol
            order by date
            rows between unbounded preceding and current row
        ) as running_max_adj_close
    from prices
)

select
    date,
    symbol,
    (adj_close / running_max_adj_close) - 1.0 as drawdown
from running_extrema
