# Pero Portfolio & Trend Analyzer

Streamlit app for portfolio overview, trend detection, Fibonacci levels, and technical export.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Optional CLI portfolio file:

```bash
streamlit run app.py -- -f myPortfolio.csv
```

## Project layout

```
app.py                    # Streamlit entry (calls portfolio_app.main.run)
portfolio_app/
  config.py               # Paths, table columns, history periods
  session_keys.py         # Session keys cleared on reset/refresh
  main.py                 # Page bootstrap and section orchestration
  analysis/
    returns.py            # Dividend yield, period returns (5D/1M/6M/12M)
    trends.py             # Swing trend detection (T1–T4)
    fibonacci.py          # Fib levels anchored to main trend leg
    portfolio_build.py    # Build table rows from bulk prices
  data/
    portfolio_loader.py   # CSV upload, CLI -f, default files, demo mock
    market_data.py        # Yahoo Finance prices, FX, cached metadata
    metadata.py           # Background analyst field loader
  ui/
    theme.py              # Global CSS and desktop icons
    components.py         # Alt/Shift table clicks, trend icons
    header.py             # Logo and title
    toolbar.py            # Upload, reset, refresh
    portfolio_page.py     # KPI strip, table, portfolio load
    detail_panel.py       # Chart, Fib window, export sidebar
    table.py              # Tabbed views and row selection
    table_style.py        # Green/red cell gradients
    charts.py             # Plotly price + trend overlay
    export.py             # Multi-symbol Gemini export text
static/                   # Logo, manifest (served at /static/…)
```

## Branches

- **main** — stable releases
- **refactor/modularize-app** — modular structure (merge when tested)

## CSV format

Semicolon-separated (`;`), columns include: `Symbol`, `Shares`, `AvgCost`, `PurchaseDate`, `TargetPrice`, `Currency`.

## Development notes

- Fibonacci uses **T1** (strongest trend leg in the Re-Analyse window), not full-window high/low.
- Table selection: click = single row, Shift = range, Alt = toggle, uncheck = remove from export.
- Pause large feature work on `app.py` while refactor branches are active; branch from updated `main` for small fixes.
