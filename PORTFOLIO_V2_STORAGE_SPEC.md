# Portfolio Compass — Storage V2 Specification (Phase 0)

**Status:** Draft for review  
**Branch target:** `feature/portfolio-v2-next`  
**Last updated:** 2026-06-02  

This document is the **Phase 0 contract**: definitions, rules, and acceptance cases that later phases must implement without reinterpretation. No major implementation work is expected in Phase 0 beyond agreeing on this spec.

---

## 1. Goals

1. **Current portfolio is the source of truth** — identified by stable `(user_id, portfolio_id)`; display name is mutable.
2. **CSV is transport only** — import/export format, never runtime canonical state.
3. **User-edited holdings and imported holdings follow the same pipeline** — normalize → consolidate → persist.
4. **Market/analyst enrichment is persisted** with a visible **last sync** timestamp; external APIs run only on explicit user refresh (not on every app start).
5. **UI separates Portfolio (DB) actions from File (CSV) actions** with distinct affordances.
6. **Email verification** comes later; existing email → user mapping must remain compatible (Phase 6).

---

## 2. Non-goals (Phase 0)

- Multi-device cloud sync beyond local SQLite.
- Real-time streaming prices.
- Email verification / auth hardening (deferred to Phase 6).
- Changing CSV column layout or separator (`;` stays).

---

## 3. Terminology

| Term | Meaning |
|------|---------|
| **Current portfolio** | The portfolio selected in the UI (`portfolio_id`), loaded for this session. |
| **Holdings** | User-owned fields only: Symbol, Shares, AvgCost, PurchaseDate, TargetPrice, Currency. |
| **Canonical holding** | At most **one row per symbol** per portfolio in the database. |
| **Draft** | Unsaved in-memory edits (`holdings_draft_{portfolio_id}`); overrides DB until Save or Reload. |
| **Enrichment** | Market/analyst/calculated columns shown in screener tables (not stored in `positions`). |
| **Sync** | User-triggered fetch of external financial data for the current portfolio’s symbols. |
| **Replace import** | CSV becomes the full new holdings set for the current portfolio (symbols not in CSV are removed). |
| **Merge import** | CSV rows are combined with existing holdings symbol-by-symbol; symbols only in DB are kept. |

---

## 4. Current state (baseline)

| Area | Today | Gap vs target |
|------|--------|----------------|
| Portfolios | SQLite `users`, `portfolios`, `positions`; `last_portfolio_id` on user | Align import target to **current** portfolio; add sync metadata tables |
| Positions | `UNIQUE (portfolio_id, symbol)` — one row per symbol | Editor may show multiple rows per symbol in draft only |
| CSV import | Dialog imports into a **named** portfolio (create or replace-by-name) | Should import into **current** portfolio with replace/merge modes |
| CSV on startup | `myPortfolio.csv` / CLI `-f` may load before DB | Remove implicit CSV as runtime source after bootstrap |
| Enrichment | Streamlit `st.cache_data` + session `all_results` | Persist per-symbol snapshot + portfolio `last_sync_at` |
| Reload | Clears draft, reruns app; may still refetch metadata depending on flags | Reload = DB holdings + persisted enrichment, no network |
| Refresh | Toolbar sync button refetches Yahoo data | Must update persisted snapshot + `last_sync_at` |
| Consolidation | `merge_duplicate_symbol_rows()` — N rows per symbol → one | Reuse as single algorithm (see §6) |

**Existing consolidation implementation** (to preserve): `portfolio_app/data/portfolio_loader.py` → `merge_duplicate_symbol_rows`.

---

## 5. Data model (target)

### 5.1 Existing tables (unchanged identifiers)

```
users (id, email, display_name, status, last_portfolio_id, last_login_at, created_at)
portfolios (id, user_id, name, updated_at)   -- UNIQUE (user_id, name)
positions (id, portfolio_id, symbol, shares, avg_cost, purchase_date, target_price, currency, sort_order)
                                          -- UNIQUE (portfolio_id, symbol)
```

- **`portfolio_id` never changes** on rename.
- **`updated_at`** on `portfolios` updates when holdings are saved or import/replace/merge commits.

### 5.2 New tables (Phase 1)

```sql
-- Portfolio-level sync bookkeeping
CREATE TABLE portfolio_sync_state (
    portfolio_id INTEGER PRIMARY KEY,
    last_sync_at TEXT,              -- ISO-8601 UTC
    last_sync_status TEXT NOT NULL DEFAULT 'never',  -- never | success | partial | failed
    last_sync_error TEXT,
    symbols_requested INTEGER,
    symbols_succeeded INTEGER,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);

-- Per-symbol persisted enrichment (post-refresh)
CREATE TABLE symbol_financial_snapshot (
    portfolio_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    synced_at TEXT NOT NULL,
    price REAL,
    change_pct REAL,
    div_yield REAL,
    est_target REAL,
    trailing_pe REAL,
    forward_pe REAL,
    peg REAL,
    rev_growth_pct REAL,
    op_margin_pct REAL,
    returns_5d REAL,
    returns_1m REAL,
    returns_6m REAL,
    returns_12m REAL,
    payload_json TEXT,              -- optional overflow for future fields
    PRIMARY KEY (portfolio_id, symbol),
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
);
```

**Design choice:** One **portfolio-level** `last_sync_at` (what the KPI strip shows) plus **per-symbol** `synced_at` for partial failures and debugging. On successful full refresh, all requested symbols get the same `synced_at`; `portfolio_sync_state.last_sync_at` matches that batch time.

### 5.3 What is stored where

| Data | Storage | Notes |
|------|---------|--------|
| Holdings (6 columns) | `positions` | Only user data in DB |
| Valuation P-Scores, grades | Recomputed from persisted analyst fields + holdings on display | Not duplicated in DB unless added to `payload_json` later |
| TA (trends, Fib) | Session only | Depends on chart window; not part of sync persistence |
| KPI totals (Value, Cost, Target, Div Income) | Derived at render from holdings + snapshots | May cache in session for performance |

---

## 6. Symbol consolidation (N rows per symbol)

**When:** After CSV parse, on **Save portfolio**, and after **merge import** (per-symbol).  
**Function:** `merge_duplicate_symbol_rows(df)` — single implementation, no alternate paths.  
*(Name refers to duplicate **symbol keys**, not “only two rows”.)*

Applies to **any N ≥ 2** rows sharing the same `Symbol` (case-insensitive, trimmed)—e.g. five separate purchase lots in a CSV or in the edit draft. One row per symbol passes through unchanged.

Given those N rows for one symbol:

| Field | Rule |
|-------|------|
| **Shares** | Sum of all lots |
| **AvgCost** | Share-weighted average: `Σ(sharesᵢ × AvgCostᵢ) / Σ(sharesᵢ)` if `Σ shares > 0`, else arithmetic mean of costs |
| **TargetPrice** | Same share-weighted average as AvgCost |
| **PurchaseDate** | **Earliest** non-null date among lots |
| **Currency** | Currency of the lot with the **largest share count**; tie → first row in group order |

**DB constraint:** After consolidation, persist at most one `positions` row per symbol.

**Editor (Phase 3):** The edit expander **may show multiple rows per symbol** while editing. Consolidation runs **only on Save** (or import commit), not on each keystroke.

---

## 7. CSV format & parsing

- Separator: `;`
- Columns (required): `Symbol`, `Shares`, `AvgCost`, `PurchaseDate`, `TargetPrice`, `Currency`
- Parsing: `portfolio_loader` locale rules (European thousands on **Shares** only; prices always decimal)
- Pre-consolidation: normalize symbols (uppercase, trim), drop blank symbols
- Post-parse: `merge_duplicate_symbol_rows` **within the CSV** before replace/merge logic

**Rejected rows (preflight):** missing symbol, negative shares, unparseable required numerics → listed in import preview; other valid rows may still proceed (configurable: default **skip bad rows, import good rows**).

---

## 8. Import modes (current portfolio)

Import always targets the **current portfolio** (`portfolio_id` in session). The CSV file name is **not** used to rename or create a portfolio unless the user explicitly uses **Save as new portfolio** (§10).

### 8.1 Replace

1. Parse & validate CSV → `import_df` (consolidated within file).
2. Delete all `positions` for `portfolio_id`.
3. Insert `import_df` rows.
4. Update `portfolios.updated_at`.
5. Clear holdings draft and table selection.
6. **Do not** auto-run sync; enrichment may be stale until user refreshes.
7. Clear or mark enrichment snapshots for symbols removed; delete snapshots for symbols no longer in portfolio.

### 8.2 Merge

For each symbol `S` after CSV internal consolidation:

| Case | Action |
|------|--------|
| `S` only in CSV | Insert new position |
| `S` only in DB | **Keep** existing position unchanged |
| `S` in both | Combine the DB holding with **all CSV lots for S** (N_csv rows, often pre-merged to one row per symbol within the file) into one frame and apply **§6** across every lot → one canonical row |

**Not in CSV ≠ deleted** (unlike replace).

### 8.3 Field-level merge (symbol in both)

There is no “CSV wins” per field. DB and CSV rows are **lots** in one list; §6 runs over **N = N_db + N_csv** rows (N_db is 1 today; N_csv can be many before CSV-internal consolidation).

- Example (N = 2): DB `AAPL 100@150` + CSV `AAPL 50@200` → `AAPL 150@166.67` (weighted cost), earliest purchase date, currency from largest lot.
- Example (N > 2): DB `MSFT 100@300` + CSV with three `MSFT` lots → one `MSFT` row; shares and costs use the same weighted rules as §6 across all four lots.

### 8.4 Currency mismatch

Symbol is the only key today (`UNIQUE (portfolio_id, symbol)`). If DB has `SAP` EUR and CSV has `SAP` USD, merge still runs as one symbol; **currency after merge** follows §6 (largest lot). Preflight **warning** in import preview: “SAP: currency USD (CSV) vs EUR (portfolio) — merged row will use EUR”.

### 8.5 Post-import

- No session keys referencing upload filename, `uploaded_portfolio_df`, or CLI path.
- User sees toast: “Imported N symbols (merge|replace). Last sync: … (unchanged until refresh).”

### 8.6 Export

- Filename: `{PortfolioName}.csv` via `portfolio_export_filename(name)`
- Content: current holdings (draft if unsaved? **No** — export uses **last saved DB** unless user confirms “export including unsaved edits”; default **saved only**)
- Format: semicolon CSV, same six columns as import

---

## 9. Portfolio (DB) operations

| Action | Behavior |
|--------|----------|
| **Switch portfolio** | Load holdings from DB; load `portfolio_sync_state` + snapshots; clear draft; do not call Yahoo |
| **New** | Create empty portfolio, switch to it, remember as `last_portfolio_id` |
| **Rename** | Update `portfolios.name` only; `portfolio_id` unchanged; tooltips use new name on next render |
| **Delete** | Remove portfolio + cascaded positions/sync/snapshots; switch to another (bootstrap demo if last) |
| **Save** | Draft → validate → consolidate §6 → `replace_positions` → clear draft → `updated_at` now |
| **Reload** | If draft exists → confirm discard → reload holdings + snapshots from DB → rebuild display from snapshots (no network) |
| **Save as…** | New `portfolio_id`, copy consolidated holdings from current (draft saved first or prompt); optional: copy `symbol_financial_snapshot` with same data and `synced_at` (recommended **yes** for instant KPIs) |
| **Slice / subset** | User deletes rows in editor → Save on current, **or** Save as… new portfolio (preferred for “new slice”) |

**Tooltips:** Always interpolate **current portfolio display name** (the one in the selector), e.g. `Rename "BigThing Portfolio"`, not a stale or “active” alias.

---

## 10. Sync & refresh

### 10.1 Startup

1. Resolve user by email (existing sidebar identity).
2. Load `users.last_portfolio_id` (or most recently updated portfolio).
3. Load holdings + `portfolio_sync_state` + `symbol_financial_snapshot`.
4. Build screener table from **persisted snapshots** (stale data is acceptable).
5. Show KPI strip including **Last sync: {local time}** or **Never synced**.
6. **Do not** call Yahoo on startup.

### 10.2 Refresh (user clicks sync)

1. Set status `in_progress` (UI spinner / “Loading financial data…”).
2. For each symbol in current holdings: fetch market + analyst fields (existing loaders).
3. Upsert `symbol_financial_snapshot` rows; set `synced_at = now()`.
4. Update `portfolio_sync_state` (`last_sync_at`, counts, `success` / `partial` / `failed`).
5. Rebuild `all_results` from holdings + snapshots.
6. Recalculate derived columns (P-Scores, KPI totals) in memory.

### 10.3 Staleness UI

- KPI strip: `Last sync: 2 Jun 2026, 09:42` (local timezone).
- Optional per-symbol indicator if `synced_at` &lt; portfolio `last_sync_at` (partial batch) — Phase 5.
- If never synced: enable refresh CTA; table shows holdings with “—” for market columns.

---

## 11. UI grouping (Phase 4 reference)

### Portfolio (DB) — primary styling

- Selector: portfolio name
- **New** | **Rename** | **Delete** (tooltips reference current name)
- **Save** | **Reload**
- **Edit portfolio** expander (holdings columns only)

### File (CSV) — distinct styling (e.g. outlined / secondary color)

- **Import…** → dialog: radio **Replace current portfolio** | **Merge into current portfolio**; file picker; **preview** (added/updated/removed/unchanged/rejected); confirm
- **Export** → download `{Name}.csv`

**Remove from default toolbar:** import-by-portfolio-name, implicit “uploaded file” state, mixing export with DB icon row without labels.

---

## 12. Session state cleanup

Keys to **remove** after import/switch (no CSV heritage):

- `uploaded_portfolio_df`, `uploaded_portfolio_name`, `uploaded_portfolio_cache_key`
- `upload_pending_*`, `upload_replace_confirmed`
- CLI/default CSV auto-load as **session source** (files remain valid only for explicit Import or dev `-f` with documented dev-only behavior)

Keys to **keep**:

- `holdings_draft_{portfolio_id}`, `active_portfolio_id`, `portfolio_selector`, analysis/selection keys

---

## 13. Acceptance test cases

### AT-1: Replace import

**DB before:** `MSFT 10@300`, `AAPL 100@150`  
**CSV:**

```csv
Symbol;Shares;AvgCost;PurchaseDate;TargetPrice;Currency
AAPL;50;200;2025-01-01;250;USD
GOOGL;20;140;2024-06-01;200;USD
```

**Replace → DB after:** `AAPL 50@200`, `GOOGL 20@140` (MSFT gone).

---

### AT-2: Merge import (symbol overlap)

**DB:** `AAPL 100@150`, `PurchaseDate 2024-01-01`  
**CSV:** `AAPL;50;200;2025-06-01;250;USD`  

**Merge → one row:**  
- Shares: 150  
- AvgCost: (100×150 + 50×200) / 150 = **166.67**  
- TargetPrice: weighted similarly  
- PurchaseDate: **2024-01-01** (earliest)  
- Currency: USD  

---

### AT-3: CSV with N lots per symbol (European shares)

**CSV:**

```csv
SAP;1.500;125,50;2024-01-15;200,00;EUR
SAP;500;130,00;2025-03-01;210,00;EUR
```

**After parse + §6:** one `SAP` row, Shares **2000**, weighted AvgCost/Target, PurchaseDate **2024-01-15**.

---

### AT-4: Editor with N rows per symbol then Save

**Draft (N = 2 for TSLA):**

| Symbol | Shares | AvgCost | PurchaseDate |
|--------|--------|---------|--------------|
| TSLA | 10 | 200 | 2023-01-01 |
| TSLA | 5 | 250 | 2024-01-01 |

**Save → DB:** one `TSLA` — Shares 15, AvgCost 216.67, PurchaseDate 2023-01-01.

Same rules apply for N = 5+ lots per symbol in the draft (e.g. five `MSFT` rows → one consolidated `MSFT` on Save).

---

### AT-5: Reload with unsaved draft

**DB:** `AAPL 100@150`  
**Draft:** `AAPL 200@160` (unsaved)  

**Reload + confirm discard →** display `AAPL 100@150`; draft cleared; snapshots unchanged; no Yahoo calls.

---

### AT-6: Startup after prior sync

**Given:** `last_sync_at = 2026-06-01T08:00:00Z`, snapshots for all symbols  
**On app start:** table shows snapshot prices; KPI shows Last sync 1 Jun 2026; no network until Refresh.

---

### AT-7: Save as new portfolio

**Current:** `BigThing` with 33 symbols + snapshots  
**Save as → `BigThing 2026`:** new `portfolio_id`, 33 positions copied, snapshots copied, `last_portfolio_id` updated, selector shows new name.

---

## 14. Open decisions (need sign-off)

| # | Question | Proposal (default) |
|---|----------|-------------------|
| D1 | Import: allow creating a **new** portfolio from CSV (by name) in addition to current-portfolio modes? | **Secondary:** only via **Save as** after import-to-current, or optional “Import to new portfolio…” in File menu |
| D2 | Export with unsaved draft? | **Saved DB only**; optional checkbox “Include unsaved edits” |
| D3 | Merge: symbol in CSV with **zero shares** | Treat as **delete symbol** or reject row? Default: **reject with warning** (do not silently delete) |
| D4 | Replace import on empty CSV | Clear all holdings (allow empty portfolio) with confirm | 
| D5 | Partial refresh failure | Keep prior snapshot per symbol; portfolio status `partial`; show count in UI |
| D6 | Dev CLI `-f file.csv` | **Dev-only:** loads into session for debugging, not written to DB until explicit Import/Save |
| D7 | Clone snapshots on Save as | **Yes** — clone holdings + snapshots |

---

## 15. Phased delivery map

| Phase | Deliverable |
|-------|-------------|
| **0** | This spec agreed |
| **1** | Schema migration + repository API for sync/snapshots |
| **2** | Import engine: replace/merge + preflight preview (pure functions + tests) |
| **3** | Edit model: multi-row draft, Save consolidates, view-independent editor |
| **4** | UI: DB vs File groups, import dialog redesign |
| **5** | Startup from snapshots, Last sync in KPI, refresh persists |
| **6** | Email verification compatibility shim |

---

## 16. Implementation notes (for Phase 1+)

- Reuse `PortfolioRepository.replace_positions` after producing consolidated DataFrame.
- Extract `ImportService.apply(mode, portfolio_id, csv_df) -> ImportResult` with counts for preview UI.
- `ImportResult`: `{added, updated, removed, unchanged, rejected: [{row, reason}]}`.
- Tests live in `tests/` (new): AT-1 through AT-4 as unit tests without Streamlit.
- Migration: `init_database()` version bump or Alembic-style `PRAGMA user_version`.

---

## 17. Review checklist

Before Phase 1 starts, confirm:

- [ ] Replace vs merge behavior matches expectations (especially **merge keeps symbols not in CSV**).
- [ ] §6 consolidation rules are acceptable for edit and import.
- [ ] Persisted enrichment field list (§5.2) is sufficient for v1.
- [ ] Export uses saved DB by default (D2).
- [ ] Open decisions D1–D7 resolved or accepted as proposed.

---

*End of Phase 0 spec.*
