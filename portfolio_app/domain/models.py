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
