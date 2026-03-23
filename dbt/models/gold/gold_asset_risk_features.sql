{{ config(materialized='table') }}

with volatility as (
    select *
    from {{ ref('silver_volatility_metrics') }}
),
drawdowns as (
    select *
    from {{ ref('silver_asset_drawdowns') }}
),
correlations as (
    select
        cast(date as date) as date,
        avg(correlation) as mean_correlation
    from {{ source('silver_upstream', 'market_correlations') }}
    group by 1
),
macro_daily as (
    with macro_enriched as (
        select
            date,
            series_id,
            abs(
                coalesce(
                    value / lag(value) over (partition by series_id order by date) - 1.0,
                    0.0
                )
            ) as macro_shock_score
        from {{ ref('stg_macro_indicators') }}
    )
    select
        date,
        avg(macro_shock_score) as macro_shock_score
    from macro_enriched
    group by 1
)

select
    v.date,
    v.symbol,
    v.daily_return,
    v.rolling_volatility_7d,
    v.rolling_volatility_30d,
    v.rolling_volatility_90d,
    d.drawdown,
    coalesce(avg(v.daily_return) over (
        partition by v.symbol
        order by v.date
        rows between 13 preceding and current row
    ), 0.0) as momentum_signal,
    c.mean_correlation,
    coalesce(m.macro_shock_score, 0.0) as macro_shock_score,
    coalesce(c.mean_correlation, 0.0) as correlation_spike,
    lead(v.rolling_volatility_7d, 7) over (partition by v.symbol order by v.date) as future_volatility_7d
from volatility v
left join drawdowns d
    on v.date = d.date and v.symbol = d.symbol
left join correlations c
    on v.date = c.date
left join macro_daily m
    on v.date = m.date
