---
title: Macro Economic Context
---

```sql macro
select * from finance.macro_indicators order by trading_date
```

```sql macro_latest
select * from finance.macro_indicators order by trading_date desc limit 1
```

```sql macro_vs_stocks
select * from finance.macro_vs_stocks
```

```sql regime_perf
select
    rate_regime,
    round(avg(daily_return_pct), 4) as avg_daily_return,
    round(stddev(daily_return_pct), 4) as std_daily_return,
    count(*) as observations
from finance.macro_vs_stocks
group by rate_regime
order by avg_daily_return desc
```

# 🏦 Macro Economic Context

Current macro snapshot from the Federal Reserve (FRED data).

<BigValue data={macro_latest} value=fed_funds_rate title="Fed Funds Rate" fmt="0.00%" />
<BigValue data={macro_latest} value=treasury_yield_10y title="10Y Treasury Yield" fmt="0.00%" />
<BigValue data={macro_latest} value=real_yield_10y title="10Y Real Yield" fmt="0.00%" />
<BigValue data={macro_latest} value=unemployment_rate title="Unemployment Rate" fmt="0.0%" />
<BigValue data={macro_latest} value=breakeven_inflation_10y title="10Y Breakeven Inflation" fmt="0.00%" />

---

## Interest Rate Environment

<LineChart
    data={macro}
    x=trading_date
    y={['fed_funds_rate', 'treasury_yield_10y', 'real_yield_10y', 'breakeven_inflation_10y']}
    title="Interest Rates Over Time (%)"
    yFmt="0.00%"
/>

---

## Labor Market

<LineChart
    data={macro}
    x=trading_date
    y=unemployment_rate
    title="U.S. Unemployment Rate (%)"
    yFmt="0.0%"
/>

---

## Inflation

<LineChart
    data={macro}
    x=trading_date
    y=cpi
    title="Consumer Price Index (CPI)"
    yFmt="#,##0.0"
/>

---

## Stock Returns by Rate Regime

How did the 10 tracked stocks perform during different Federal Funds Rate environments?

<BarChart
    data={regime_perf}
    x=rate_regime
    y=avg_daily_return
    title="Average Daily Return by Rate Regime"
    yFmt="+0.000%"
    colorColumn=avg_daily_return
    colorScale={['#dc2626','#4ade80']}
    labels=true
/>

<DataTable data={regime_perf}>
    <Column id=rate_regime title="Rate Regime" />
    <Column id=avg_daily_return title="Avg Daily Return %" fmt="+0.000%" contentType=delta />
    <Column id=std_daily_return title="Std Dev %" fmt="0.000%" />
    <Column id=observations />
</DataTable>

---

## Treasury Yield vs Stock Volatility

<ScatterPlot
    data={macro_vs_stocks}
    x=treasury_yield_10y
    y=volatility_20d_annualized
    series=ticker
    title="10Y Treasury Yield vs 20D Realized Volatility"
    xFmt="0.00%"
    yFmt="0.0%"
/>

---

> **Data source:** Federal Reserve Bank of St. Louis (FRED API).
> Series: `FEDFUNDS`, `CPIAUCSL`, `UNRATE`, `DGS10`, `T10YIE`, `A191RL1Q225SBEA`.
> Mixed frequencies forward-filled to daily trading dates.
