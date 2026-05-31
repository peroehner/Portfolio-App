# Personal Portfolio Screener

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

Holdings are stored in **SQLite** at `data/pero.db` (gitignored). Each user can have **multiple named portfolios**.

- **Header → Account** — email identifies your local user (no password yet).
- **Startup** — opens your **last used** portfolio; if you have none, a one-time **Demo Portfolio** (mock data) is created.
- **Portfolio bar** — switch portfolios, **rename**, **New** (empty), or **↺** reload from database.
- **📁 CSV import** — choose a **portfolio name** (defaults to the file name). If that name already exists, you must confirm **replace** (holdings are overwritten).
- **Build manually** — **New** → **ROI** view → **Add symbol** → edit cells → **Save portfolio**.
- **ROI view** — edit user columns; Standard/Trends are read-only for analysis.

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
    components.py         # Trend icons, selection preserve helper
    header.py             # Logo and title
    user_sidebar.py       # Email identity
    toolbar.py            # Upload dialog, reset, refresh
    holdings.py           # Holdings draft/save helpers
    table.py              # Analysis views; ROI inline edit, add symbol, row select
    portfolio_page.py     # KPI strip, analysis table
    detail_panel.py       # Chart, Fib window, export sidebar
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
- Table selection: click = select only that row, Shift = range, Alt/Option = toggle that row only.
- Pause large feature work on `app.py` while refactor branches are active; branch from updated `main` for small fixes.
