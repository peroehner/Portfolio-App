"""Portfolio load, save, import, and bootstrap."""
import os
from typing import Optional, Tuple

import pandas as pd

from portfolio_app.config import APP_DIR, PORTFOLIO_FILE_CANDIDATES
from portfolio_app.data.portfolio_loader import (
    get_mock_portfolio_df,
    load_portfolio_from_path,
)
from portfolio_app.domain.models import ActivePortfolio, User
from portfolio_app.storage.repository import PortfolioRepository


class PortfolioService:
    def __init__(self, repo: Optional[PortfolioRepository] = None):
        self.repo = repo or PortfolioRepository()

    def get_or_create_user(self, email: str) -> User:
        return self.repo.get_or_create_user(email)

    def remember_last_portfolio(self, user_id: int, portfolio_id: int):
        self.repo.set_last_portfolio(user_id, portfolio_id)

    def ensure_default_portfolio(self, user: User) -> ActivePortfolio:
        portfolio = self.repo.get_user_portfolio(
            user.id, user.last_portfolio_id
        )
        if not portfolio:
            portfolio = self.repo.get_or_create_default_portfolio(user.id)
        positions = self.repo.list_positions(portfolio.id)
        if not positions:
            seed_df, seed_name = self._bootstrap_holdings()
            self.repo.replace_positions(portfolio.id, seed_df)
            if seed_name and portfolio.name == "My Portfolio":
                self.repo.rename_portfolio(portfolio.id, seed_name)
            positions = self.repo.list_positions(portfolio.id)
        holdings = self.repo.positions_to_dataframe(positions)
        return ActivePortfolio(
            portfolio_id=portfolio.id,
            user_id=user.id,
            name=portfolio.name,
            holdings_df=holdings,
        )

    def load_portfolio(self, user_id: int, portfolio_id: int) -> Optional[ActivePortfolio]:
        portfolio = self.repo.get_user_portfolio(user_id, portfolio_id)
        if not portfolio:
            return None
        positions = self.repo.list_positions(portfolio.id)
        holdings = self.repo.positions_to_dataframe(positions)
        return ActivePortfolio(
            portfolio_id=portfolio.id,
            user_id=user_id,
            name=portfolio.name,
            holdings_df=holdings,
        )

    def save_holdings(self, portfolio_id: int, df: pd.DataFrame) -> ActivePortfolio:
        self.repo.replace_positions(portfolio_id, df)
        portfolio = self.repo.get_portfolio(portfolio_id)
        positions = self.repo.list_positions(portfolio_id)
        holdings = self.repo.positions_to_dataframe(positions)
        return ActivePortfolio(
            portfolio_id=portfolio_id,
            user_id=portfolio.user_id,
            name=portfolio.name if portfolio else "My Portfolio",
            holdings_df=holdings,
        )

    def import_csv(self, user_id: int, portfolio_id: int, df: pd.DataFrame, name: Optional[str] = None) -> ActivePortfolio:
        self.repo.replace_positions(portfolio_id, df)
        if name:
            self.repo.rename_portfolio(portfolio_id, name)
        return self.load_portfolio(user_id, portfolio_id)

    @staticmethod
    def _bootstrap_holdings() -> Tuple[pd.DataFrame, str]:
        for filename in PORTFOLIO_FILE_CANDIDATES:
            path = os.path.join(APP_DIR, filename)
            if os.path.exists(path):
                df, basename = load_portfolio_from_path(path)
                return df, os.path.splitext(basename)[0]
        df = get_mock_portfolio_df()
        return df[["Symbol", "Shares", "AvgCost", "PurchaseDate", "TargetPrice", "Currency"]], "Demo Portfolio"
