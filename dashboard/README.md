# Dashboard

An [Evidence](https://evidence.dev) project that renders the marts built by the dbt project in `../transform`.

- `pages/` holds the Markdown pages: overview (`index.md`), `stocks/`, `macro/` and `briefing.md`.
- `sources/finance/` holds the SQL that Evidence runs against the warehouse. `connection.yaml` points at the local DuckDB file `../data/processed/finance.duckdb`.
- `tests/dashboard.spec.js` holds the Playwright smoke tests.

`pages/briefing.md` is a placeholder. `generate_briefing.py` in the repository root overwrites it.

```bash
npm ci
npm run sources    # run the source queries against the DuckDB file
npm run dev        # Evidence dev server
npm run build      # static site
```

The pipeline has to be run first so that the DuckDB file exists. See the README in the repository root.
