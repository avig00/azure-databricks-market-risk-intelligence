{{ config(materialized='table') }}

with returns as (
    select *
    from {{ ref('silver_daily_returns') }}
)

select
    date,
    symbol,
    daily_return,
    coalesce(stddev_pop(daily_return) over (
        partition by symbol
        order by date
        rows between 6 preceding and current row
    ), 0.0) as rolling_volatility_7d,
    coalesce(stddev_pop(daily_return) over (
        partition by symbol
        order by date
        rows between 29 preceding and current row
    ), 0.0) as rolling_volatility_30d,
    coalesce(stddev_pop(daily_return) over (
        partition by symbol
        order by date
        rows between 89 preceding and current row
    ), 0.0) as rolling_volatility_90d
from returns
