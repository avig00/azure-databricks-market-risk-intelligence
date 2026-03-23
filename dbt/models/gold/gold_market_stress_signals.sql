{{ config(materialized='table') }}

with portfolio_metrics as (
    select *
    from {{ ref('gold_portfolio_risk_metrics') }}
)

select
    date,
    portfolio_volatility as avg_volatility_30d,
    expected_drawdown as drawdown,
    correlation_spike,
    macro_shock_score,
    (portfolio_volatility * 0.4)
        + (abs(expected_drawdown) * 0.2)
        + (greatest(correlation_spike, 0.0) * 0.2)
        + (greatest(macro_shock_score, 0.0) * 0.2) as market_stress_index
from portfolio_metrics
