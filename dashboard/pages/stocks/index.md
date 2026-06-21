---
title: Stock Deep Dive
---

```sql tickers
select distinct ticker from finance.price_history order by ticker
```

<Dropdown data={tickers} name=ticker value=ticker title="Select Ticker">
    <DropdownOption value="AAPL" valueLabel="AAPL (Default)" />
</Dropdown>

```sql stock_info
select
    ticker,
    company_name,
    sector,
    industry,
    market_cap_category,
    exchange
from finance.latest_snapshot
where ticker = '${inputs.ticker.value}'
```

```sql history
select * from finance.price_history
where ticker = '${inputs.ticker.value}'
order by trading_date
```

```sql monthly
select * from finance.monthly_returns
where ticker = '${inputs.ticker.value}'
order by month
```

```sql stats
select
    ticker,
    round(min(close_price), 2) as low_52w,
    round(max(close_price), 2) as high_52w,
    round(avg(close_price), 2) as avg_close,
    round(avg(volume), 0)       as avg_volume,
    round(avg(daily_return_pct), 4) as avg_daily_return,
    round(stddev(daily_return_pct), 4) as std_daily_return,
    count(*) as trading_days
from finance.price_history
where ticker = '${inputs.ticker.value}'
  and trading_date >= (select max(trading_date) - interval '365 days' from finance.price_history)
group by ticker
```

# {inputs.ticker.value} — Stock Deep Dive

<BigValue data={stock_info} value=company_name title="Company" />
<BigValue data={stock_info} value=sector title="Sector" />
<BigValue data={stock_info} value=industry title="Industry" />
<BigValue data={stock_info} value=exchange title="Exchange" />

<BigValue data={stats} value=low_52w title="52W Low" fmt="$#,##0.00" />
<BigValue data={stats} value=high_52w title="52W High" fmt="$#,##0.00" />
<BigValue data={stats} value=avg_daily_return title="Avg Daily Return" fmt="+0.000%" />
<BigValue data={stats} value=trading_days title="Trading Days" />

---

## Price History with Moving Averages

<LineChart
    data={history}
    x=trading_date
    y={['close_price', 'sma_30d', 'sma_200d']}
    title="{inputs.ticker.value} Close Price vs 30D / 200D SMA"
    yFmt="$#,##0.00"
    labels=true
/>

---

## Daily Volume

<BarChart
    data={history}
    x=trading_date
    y=volume
    title="{inputs.ticker.value} Daily Volume"
    yFmt="#,##0"
/>

---

## Daily Return Distribution

<BarChart
    data={history}
    x=trading_date
    y=daily_return_pct
    title="{inputs.ticker.value} Daily Return (%)"
    yFmt="+0.00%"
    colorColumn=daily_return_pct
    colorScale={['#dc2626','#4ade80']}
/>

---

## Monthly Returns

<DataTable data={monthly}>
    <Column id=month fmt="MMM yyyy" />
    <Column id=monthly_return_pct title="Return %" fmt="+0.00%" contentType=delta />
    <Column id=trading_days />
</DataTable>

---

## 20-Day Realized Volatility

<LineChart
    data={history}
    x=trading_date
    y=volatility_20d_annualized
    title="{inputs.ticker.value} 20D Annualized Realized Volatility"
    yFmt="0.0%"
/>
