"""Portfolio-relative P-Scores and grades for Valuation Growth view."""
from __future__ import annotations

import math
from typing import Any, Mapping, Optional

# Raw metric keys (fractions for growth / margin)
METRIC_TRAILING_PE = "trailing_pe"
METRIC_FORWARD_PE = "forward_pe"
METRIC_PEG = "peg_ratio"
METRIC_REVENUE_GROWTH = "revenue_growth"
METRIC_OPERATING_MARGIN = "operating_margin"

# Display / session keys
COL_TRAILING_PE = "Trailing P/E"
COL_FORWARD_PE = "Forward P/E"
COL_PEG = "PEG"
COL_REV_GROWTH = "Rev Growth %"
COL_OP_MARGIN = "Op Margin %"
COL_PEG_PSCORE = "PEG P-Score"
COL_REV_PSCORE = "Rev P-Score"
COL_MARGIN_PSCORE = "Margin P-Score"
COL_PSCORE = "P-Score"
COL_GRADE = "Grade"

VALUATION_RAW_COLUMNS = (
    COL_TRAILING_PE,
    COL_FORWARD_PE,
    COL_PEG,
    COL_REV_GROWTH,
    COL_OP_MARGIN,
)

VALUATION_SCORE_COLUMNS = (
    COL_PEG_PSCORE,
    COL_REV_PSCORE,
    COL_MARGIN_PSCORE,
    COL_PSCORE,
    COL_GRADE,
)

VALUATION_ALL_COLUMNS = VALUATION_RAW_COLUMNS + VALUATION_SCORE_COLUMNS

# Clamp raw yfinance values into these bands before peer P-Score comparison.
PEG_SCORE_MIN = 0.0
PEG_SCORE_MAX = 10.0
REV_GROWTH_SCORE_MIN = -0.10  # -10% YoY
REV_GROWTH_SCORE_MAX = 5.0  # 500% YoY
OP_MARGIN_SCORE_MIN = -2.5  # -250%
OP_MARGIN_SCORE_MAX = 1.0  # 100%

SCORING_BOUNDS_LABEL = (
    f"PEG {PEG_SCORE_MIN:g}–{PEG_SCORE_MAX:g} · "
    f"Rev {REV_GROWTH_SCORE_MIN * 100:.0f}%–{REV_GROWTH_SCORE_MAX * 100:.0f}% · "
    f"OpM {OP_MARGIN_SCORE_MIN * 100:.0f}%–{OP_MARGIN_SCORE_MAX * 100:.0f}%"
)


def _finite(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    return f


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _clamp_for_scoring(metric: str, value: Optional[float]) -> Optional[float]:
    """Range-bound a metric for peer comparison (display values stay unclamped)."""
    v = _finite(value)
    if v is None:
        return None
    if metric == METRIC_PEG:
        return _clamp(v, PEG_SCORE_MIN, PEG_SCORE_MAX)
    if metric == METRIC_REVENUE_GROWTH:
        return _clamp(v, REV_GROWTH_SCORE_MIN, REV_GROWTH_SCORE_MAX)
    if metric == METRIC_OPERATING_MARGIN:
        return _clamp(v, OP_MARGIN_SCORE_MIN, OP_MARGIN_SCORE_MAX)
    return v


def _peer_percentile(
    values: list[float],
    value: float,
    *,
    higher_is_better: bool = True,
) -> Optional[float]:
    """
  Return 0–100: share of peers this symbol beats within the portfolio.

  PEG uses higher_is_better=False (lower PEG → higher score).
  """
    if len(values) < 2:
        return None
    if higher_is_better:
        beats = sum(1 for v in values if v < value)
    else:
        beats = sum(1 for v in values if v > value)
    return 100.0 * beats / (len(values) - 1)


def _grade_from_rank(rank: int, n: int) -> str:
    """rank 1 = best within portfolio."""
    if n <= 0:
        return "-"
    if n == 1:
        return "A"
    pct = (n - rank) / n
    if pct >= 0.8:
        return "A"
    if pct >= 0.6:
        return "B"
    if pct >= 0.4:
        return "C"
    if pct >= 0.2:
        return "D"
    return "F"


def metrics_from_row(data: Mapping[str, Any]) -> dict[str, Optional[float]]:
    """Extract raw metrics from an analysis row (growth/margin stored as %)."""
    rev = _finite(data.get(COL_REV_GROWTH))
    margin = _finite(data.get(COL_OP_MARGIN))
    return {
        METRIC_TRAILING_PE: _finite(data.get(COL_TRAILING_PE)),
        METRIC_FORWARD_PE: _finite(data.get(COL_FORWARD_PE)),
        METRIC_PEG: _finite(data.get(COL_PEG)),
        METRIC_REVENUE_GROWTH: rev / 100.0 if rev is not None else None,
        METRIC_OPERATING_MARGIN: margin / 100.0 if margin is not None else None,
    }


def raw_metrics_to_display(raw: Mapping[str, Optional[float]]) -> dict[str, Any]:
    """Map fetched metrics to table display columns (scores filled after full load)."""
    rev = raw.get(METRIC_REVENUE_GROWTH)
    margin = raw.get(METRIC_OPERATING_MARGIN)
    return {
        COL_TRAILING_PE: raw.get(METRIC_TRAILING_PE),
        COL_FORWARD_PE: raw.get(METRIC_FORWARD_PE),
        COL_PEG: raw.get(METRIC_PEG),
        COL_REV_GROWTH: rev * 100.0 if rev is not None else None,
        COL_OP_MARGIN: margin * 100.0 if margin is not None else None,
        COL_PEG_PSCORE: None,
        COL_REV_PSCORE: None,
        COL_MARGIN_PSCORE: None,
        COL_PSCORE: None,
        COL_GRADE: None,
    }


def _scoring_values_by_symbol(
    metrics_by_symbol: Mapping[str, Mapping[str, Optional[float]]],
) -> dict[str, dict[str, Optional[float]]]:
    """Per-symbol metrics clamped into P-Score bands."""
    out: dict[str, dict[str, Optional[float]]] = {}
    for symbol, m in metrics_by_symbol.items():
        out[symbol] = {
            METRIC_PEG: _clamp_for_scoring(METRIC_PEG, m.get(METRIC_PEG)),
            METRIC_REVENUE_GROWTH: _clamp_for_scoring(
                METRIC_REVENUE_GROWTH, m.get(METRIC_REVENUE_GROWTH)
            ),
            METRIC_OPERATING_MARGIN: _clamp_for_scoring(
                METRIC_OPERATING_MARGIN, m.get(METRIC_OPERATING_MARGIN)
            ),
        }
    return out


def compute_portfolio_p_scores(
    metrics_by_symbol: Mapping[str, Mapping[str, Optional[float]]],
) -> dict[str, dict[str, Any]]:
    """
    Peer percentiles (0–100) vs all symbols with data in this portfolio.

    Raw metrics are clamped to SCORING_BOUNDS before comparison so exotic
    yfinance values do not distort peer rankings.
    """
    symbols = list(metrics_by_symbol.keys())
    if not symbols:
        return {}

    scored = _scoring_values_by_symbol(metrics_by_symbol)

    peg_vals = [
        scored[s][METRIC_PEG]
        for s in symbols
        if scored[s][METRIC_PEG] is not None
    ]
    rev_vals = [
        scored[s][METRIC_REVENUE_GROWTH]
        for s in symbols
        if scored[s][METRIC_REVENUE_GROWTH] is not None
    ]
    margin_vals = [
        scored[s][METRIC_OPERATING_MARGIN]
        for s in symbols
        if scored[s][METRIC_OPERATING_MARGIN] is not None
    ]

    out: dict[str, dict[str, Any]] = {}
    composites: dict[str, float] = {}

    for symbol in symbols:
        sv = scored[symbol]
        peg = sv[METRIC_PEG]
        rev = sv[METRIC_REVENUE_GROWTH]
        margin = sv[METRIC_OPERATING_MARGIN]

        peg_pct = (
            _peer_percentile(peg_vals, peg, higher_is_better=False)
            if peg is not None and peg_vals
            else None
        )
        rev_pct = (
            _peer_percentile(rev_vals, rev, higher_is_better=True)
            if rev is not None and rev_vals
            else None
        )
        margin_pct = (
            _peer_percentile(margin_vals, margin, higher_is_better=True)
            if margin is not None and margin_vals
            else None
        )

        parts = [p for p in (rev_pct, margin_pct, peg_pct) if p is not None]
        composite = sum(parts) / len(parts) if parts else None

        out[symbol] = {
            COL_PEG_PSCORE: peg_pct,
            COL_REV_PSCORE: rev_pct,
            COL_MARGIN_PSCORE: margin_pct,
            COL_PSCORE: composite,
            COL_GRADE: None,
        }
        if composite is not None:
            composites[symbol] = composite

    if composites:
        ranked = sorted(composites.items(), key=lambda x: x[1], reverse=True)
        n = len(ranked)
        for rank, (symbol, _) in enumerate(ranked, start=1):
            out[symbol][COL_GRADE] = _grade_from_rank(rank, n)

    return out


def _fmt_score(value: Any, *, decimals: int = 0) -> str:
    f = _finite(value)
    if f is None:
        return "—"
    if decimals == 0:
        return f"{f:.0f}"
    return f"{f:.{decimals}f}"


def _fmt_raw_pct(fraction: Optional[float]) -> str:
    f = _finite(fraction)
    if f is None:
        return "—"
    return f"{f * 100:.1f}%"


def _portfolio_headline_metrics(
    peg_vals: list[float],
    rev_vals: list[float],
    margin_vals: list[float],
) -> str:
    """Equal-weighted portfolio means (after clamp) for the legend headline."""

    def _mean_peg(values: list[float]) -> str:
        if not values:
            return "—"
        return f"{sum(values) / len(values):.1f}"

    def _mean_pct(values: list[float]) -> str:
        if not values:
            return "—"
        return f"{sum(values) / len(values) * 100:.0f}%"

    return (
        f"PEG {_mean_peg(peg_vals)} · "
        f"Rev {_mean_pct(rev_vals)} · "
        f"OpM {_mean_pct(margin_vals)}"
    )


def _fmt_scored_raw(
    label: str,
    raw: Optional[float],
    scored: Optional[float],
    *,
    as_percent: bool = False,
) -> str:
    if raw is None:
        return f"{label}=—"
    if scored is None:
        scored = raw
    if as_percent:
        raw_s, scored_s = _fmt_raw_pct(raw), _fmt_raw_pct(scored)
    else:
        raw_s, scored_s = f"{raw:.2f}", f"{scored:.2f}"
    if abs(raw - scored) > 1e-9:
        return f"{label}={raw_s} (scored {scored_s})"
    return f"{label}={raw_s}"


def format_symbol_score_line(data: Mapping[str, Any]) -> str:
    """One holding: scores plus raw vs clamped inputs used for checking."""
    sym = data.get("Symbol", "?")
    m = metrics_from_row(data)
    peg_raw = m[METRIC_PEG]
    rev_raw = m[METRIC_REVENUE_GROWTH]
    margin_raw = m[METRIC_OPERATING_MARGIN]
    peg_scored = _clamp_for_scoring(METRIC_PEG, peg_raw)
    rev_scored = _clamp_for_scoring(METRIC_REVENUE_GROWTH, rev_raw)
    margin_scored = _clamp_for_scoring(METRIC_OPERATING_MARGIN, margin_raw)
    return (
        f"{sym}: PEG P-Score {_fmt_score(data.get(COL_PEG_PSCORE))} · "
        f"Rev {_fmt_score(data.get(COL_REV_PSCORE))} · "
        f"Mgn {_fmt_score(data.get(COL_MARGIN_PSCORE))} · "
        f"P-Score {_fmt_score(data.get(COL_PSCORE), decimals=1)} ({data.get(COL_GRADE) or '—'}) "
        f"| {_fmt_scored_raw('PEG', peg_raw, peg_scored)} "
        f"{_fmt_scored_raw('Rev', rev_raw, rev_scored, as_percent=True)} "
        f"{_fmt_scored_raw('OpM', margin_raw, margin_scored, as_percent=True)}"
    )


def build_valuation_legend_sections(
    all_results: list,
    *,
    portfolio_name: str,
    valuation_loaded: bool,
    selected_symbols: Optional[list[str]] = None,
) -> tuple[str, list[str], list[str]]:
    """
    Return (headline, detail_lines, per_holding_lines) for the Valuation Growth legend.

    headline: always visible under the table
    detail_lines + per_holding_lines: shown inside the expander only
    """
    n_holdings = len(all_results)
    display_name = (portfolio_name or "Portfolio").strip() or "Portfolio"

    metrics_by_symbol = {
        item["data"]["Symbol"]: metrics_from_row(item["data"]) for item in all_results
    }
    scored = _scoring_values_by_symbol(metrics_by_symbol)
    peg_vals = [m[METRIC_PEG] for m in scored.values() if m[METRIC_PEG] is not None]
    rev_vals = [
        m[METRIC_REVENUE_GROWTH]
        for m in scored.values()
        if m[METRIC_REVENUE_GROWTH] is not None
    ]
    margin_vals = [
        m[METRIC_OPERATING_MARGIN]
        for m in scored.values()
        if m[METRIC_OPERATING_MARGIN] is not None
    ]

    if valuation_loaded and (peg_vals or rev_vals or margin_vals):
        headline_metrics = _portfolio_headline_metrics(peg_vals, rev_vals, margin_vals)
    else:
        headline_metrics = "PEG — · Rev — · OpM —"

    headline = f"Calculated P-Score for **'{display_name}'**: {headline_metrics}"

    detail: list[str] = [
        f"P-Scores are percentiles **0–100** vs all holdings with data in this portfolio "
        f"({n_holdings} symbols loaded, not only selected rows). "
        "**100** = beats every peer for that metric. "
        "Formula: 100 × (number of peers with a worse value) ÷ (n−1). "
        "**PEG P-Score** uses lower-is-better PEG. "
        f"Values are clamped to scoring bands before ranking: **{SCORING_BOUNDS_LABEL}**."
    ]

    if not valuation_loaded:
        detail.append(
            "Per-holding P-Scores appear after **Valuation data loaded** (see progress bar)."
        )
        return headline, detail, []

    selected_set = {s.upper() for s in (selected_symbols or [])}
    holdings_lines: list[str] = []
    for item in sorted(all_results, key=lambda x: str(x["data"].get("Symbol", ""))):
        sym = str(item["data"].get("Symbol", "")).upper()
        prefix = "▸ " if sym in selected_set else "  "
        holdings_lines.append(prefix + format_symbol_score_line(item["data"]))

    if selected_set:
        detail.append("Lines marked **▸** in the list below are selected in the table.")

    return headline, detail, holdings_lines
