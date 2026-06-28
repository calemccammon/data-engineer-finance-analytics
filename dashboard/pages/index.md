---
title: Finance Analytics Dashboard
---

```sql latest
select * from finance.latest_snapshot
```

```sql sector
select * from finance.sector_summary
```

```sql performance
select * from finance.performance_52w
```

```sql market_summary
select
    count(*) as num_stocks,
    round(avg(daily_return_pct), 3) as avg_daily_return,
    sum(case when daily_return_pct > 0 then 1 else 0 end) as gainers,
    sum(case when daily_return_pct < 0 then 1 else 0 end) as losers,
    max(as_of_date) as as_of_date
from finance.latest_snapshot
```

# Finance Analytics Dashboard

**As of {market_summary[0].as_of_date}** &nbsp;|&nbsp; 10 S&P 500 stocks · Real market data via Yahoo Finance & FRED

<BigValue data={market_summary} value=avg_daily_return title="Avg Daily Return %" fmt="+0.000%;-0.000%" />
<BigValue data={market_summary} value=gainers title="Gainers Today" />
<BigValue data={market_summary} value=losers title="Losers Today" />
<BigValue data={market_summary} value=num_stocks title="Stocks Tracked" />

---

## 52-Week Performance

```sql best
select ticker, company_name, return_52w_pct from finance.performance_52w order by return_52w_pct desc limit 1
```
```sql worst
select ticker, company_name, return_52w_pct from finance.performance_52w order by return_52w_pct asc limit 1
```

<BigValue data={best} value=return_52w_pct title="Best Performer (52W)" fmt="+0.0%;-0.0%" />
<BigValue data={worst} value=return_52w_pct title="Worst Performer (52W)" fmt="+0.0%;-0.0%" />

<BarChart
    data={performance}
    x=ticker
    y=return_52w_pct
    title="52-Week Return by Ticker (%)"
    yFmt="+0.0%;-0.0%"
    colorColumn=return_52w_pct
    colorScale={['#dc2626','#f97316','#facc15','#4ade80','#16a34a']}
    labels=true
/>

---

## Today's Snapshot

<DataTable data={latest} rows=10>
    <Column id=ticker />
    <Column id=company_name />
    <Column id=sector />
    <Column id=latest_close title="Close" fmt="$#,##0.00" />
    <Column id=daily_return_pct title="Daily Ret %" fmt="+0.00%;-0.00%" contentType=delta />
    <Column id=volatility_20d_pct title="20D Vol %" fmt="0.0%" />
    <Column id=sma_30d title="SMA 30D" fmt="$#,##0.00" />
    <Column id=market_cap_category title="Mkt Cap" />
</DataTable>

---

## Sector Performance

<BarChart
    data={sector}
    x=sector
    y=avg_daily_return_pct
    title="Average Daily Return by Sector (%)"
    yFmt="+0.000%;-0.000%"
    colorColumn=avg_daily_return_pct
    colorScale={['#dc2626','#4ade80']}
    labels=true
/>

<DataTable data={sector}>
    <Column id=sector />
    <Column id=num_stocks />
    <Column id=avg_daily_return_pct title="Avg Daily Ret %" fmt="+0.000%;-0.000%" contentType=delta />
    <Column id=avg_volatility_20d_pct title="Avg Vol %" fmt="0.0%" />
    <Column id=avg_pct_above_200sma title="% Above 200D SMA" fmt="+0.0%;-0.0%" />
</DataTable>

---

## Pages
- [🤖 AI Market Briefing](/briefing) — Gemini-generated daily commentary
- [📈 Stock Deep Dive](/stocks) — price charts, moving averages, volume
- [🏦 Macro Context](/macro) — FRED indicators and rate environment
