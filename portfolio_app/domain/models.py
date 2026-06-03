"""Core domain records (persistence-agnostic)."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class User:
    id: int
    email: str
    last_portfolio_id: Optional[int]
    display_name: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


@dataclass(frozen=True)
class Portfolio:
    id: int
    user_id: int
    name: str
    updated_at: Optional[datetime] = None


@dataclass(frozen=True)
class Position:
    id: int
    portfolio_id: int
    symbol: str
    shares: float
    avg_cost: float
    purchase_date: Optional[datetime]
    target_price: float
    currency: str
    sort_order: int = 0


@dataclass
class ActivePortfolio:
    """Portfolio loaded for the current app session."""

    portfolio_id: int
    user_id: int
    name: str
    holdings_df: pd.DataFrame


SYNC_STATUS_NEVER = "never"
SYNC_STATUS_SUCCESS = "success"
SYNC_STATUS_PARTIAL = "partial"
SYNC_STATUS_FAILED = "failed"


@dataclass(frozen=True)
class PortfolioSyncState:
    portfolio_id: int
    last_sync_at: Optional[datetime] = None
    last_sync_status: str = SYNC_STATUS_NEVER
    last_sync_error: Optional[str] = None
    symbols_requested: Optional[int] = None
    symbols_succeeded: Optional[int] = None


@dataclass(frozen=True)
class SymbolFinancialSnapshot:
    portfolio_id: int
    symbol: str
    synced_at: datetime
    price: Optional[float] = None
    change_pct: Optional[float] = None
    div_yield: Optional[float] = None
    est_target: Optional[float] = None
    trailing_pe: Optional[float] = None
    forward_pe: Optional[float] = None
    peg: Optional[float] = None
    rev_growth_pct: Optional[float] = None
    op_margin_pct: Optional[float] = None
    returns_5d: Optional[float] = None
    returns_1m: Optional[float] = None
    returns_6m: Optional[float] = None
    returns_12m: Optional[float] = None
    payload_json: Optional[str] = None
