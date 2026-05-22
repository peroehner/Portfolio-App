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

## Persistence (Phase 1)

Holdings are stored in **SQLite** at `data/pero.db` (gitignored). On first run, the app seeds from `myPortfolio.csv` / `Sample-Portfolio.csv` or the demo mock.

- **Sidebar → Email** — identifies your local user (no password yet).
- **Holdings** — edit `Symbol`, `Shares`, `AvgCost`, `PurchaseDate`, `TargetPrice`, `Currency`, then **Save holdings**.
- **Upload CSV** — replaces positions in the active portfolio and renames it to the file name.
- **Analysis tabs** (Standard / Trends / ROI) stay read-only; they refresh after save or upload.

## Project layout

```
app.py                    # Streamlit entry (calls portfolio_app.main.run)
data/pero.db              # Local SQLite (created at runtime, gitignored)
portfolio_app/
  config.py               # Paths, table columns, DB path
  session_keys.py         # Session keys cleared on reset/refresh
  main.py                 # Page bootstrap and section orchestration
  domain/
    models.py             # User, Portfolio, Position, ActivePortfolio
    columns.py            # ColumnSource registry (user / market / analyst / calc)
  storage/
    database.py           # SQLite schema and connection
    repository.py         # CRUD for users, portfolios, positions
  services/
    session_context.py    # Email, active portfolio, analysis invalidation
    portfolio_service.py  # Load, save, import, bootstrap
  analysis/
    returns.py            # Dividend yield, period returns (5D/1M/6M/12M)
    trends.py             # Swing trend detection (T1–T4)
    fibonacci.py          # Fib levels anchored to main trend leg
    portfolio_build.py    # Build table rows from bulk prices
  data/
    portfolio_loader.py   # CSV parsing, CLI -f, demo mock (bootstrap)
    market_data.py        # Yahoo Finance prices, FX, cached metadata
    metadata.py           # Background analyst field loader
  ui/
    theme.py              # Global CSS and desktop icons
    components.py         # Alt/Shift table clicks, trend icons
    header.py             # Logo and title
    user_sidebar.py       # Email identity
    toolbar.py            # Upload dialog, reset, refresh
    holdings_editor.py    # Editable holdings (st.data_editor)
    portfolio_page.py     # KPI strip, holdings, analysis table
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
