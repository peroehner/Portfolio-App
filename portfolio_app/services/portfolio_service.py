"""Portfolio load, save, import, bootstrap, and switching."""
import pandas as pd

from portfolio_app.data.portfolio_loader import get_mock_portfolio_df
from portfolio_app.domain.models import ActivePortfolio, Portfolio, User
from portfolio_app.services.import_engine import (
    ImportApplyResult,
    ImportMode,
    ImportPreview,
    apply_import,
    build_import_preview,
    parse_csv_preflight,
)
from portfolio_app.storage.repository import PortfolioRepository

_EMPTY_HOLDINGS_COLUMNS = [
    "Symbol", "Shares", "AvgCost", "PurchaseDate", "TargetPrice", "Currency"
]


class PortfolioService:
    def __init__(self, repo: PortfolioRepository | None = None):
        self.repo = repo or PortfolioRepository()

    def get_or_create_user(self, email: str) -> User:
        return self.repo.get_or_create_user(email)

    def list_users(self) -> list[User]:
        return self.repo.list_users()

    def remember_last_portfolio(self, user_id: int, portfolio_id: int):
        self.repo.set_last_portfolio(user_id, portfolio_id)

    def list_portfolios(self, user_id: int) -> list[Portfolio]:
        return self.repo.list_portfolios(user_id)

    def find_portfolio_by_name(self, user_id: int, name: str) -> Portfolio | None:
        return self.repo.find_portfolio_by_name(user_id, name)

    @staticmethod
    def _empty_holdings_df() -> pd.DataFrame:
        return pd.DataFrame(columns=_EMPTY_HOLDINGS_COLUMNS)

    def _active_from_portfolio(self, portfolio: Portfolio) -> ActivePortfolio:
        positions = self.repo.list_positions(portfolio.id)
        holdings = (
            self.repo.positions_to_dataframe(positions)
            if positions
            else self._empty_holdings_df()
        )
        return ActivePortfolio(
            portfolio_id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            holdings_df=holdings,
        )

    def bootstrap_user_portfolio(self, user: User) -> ActivePortfolio:
        """
        Load the user's last portfolio, or the most recent one.
        If the user has no portfolios, create a one-time demo portfolio (mock data).
        """
        portfolios = self.repo.list_portfolios(user.id)
        if not portfolios:
            portfolio = self.repo.create_portfolio(user.id, "Demo Portfolio")
            mock_df = get_mock_portfolio_df()[
                ["Symbol", "Shares", "AvgCost", "PurchaseDate", "TargetPrice", "Currency"]
            ]
            self.repo.replace_positions(portfolio.id, mock_df)
            self.remember_last_portfolio(user.id, portfolio.id)
            return self._active_from_portfolio(portfolio)

        portfolio = self.repo.get_user_portfolio(user.id, user.last_portfolio_id)
        if not portfolio:
            portfolio = portfolios[0]
        self.remember_last_portfolio(user.id, portfolio.id)
        return self._active_from_portfolio(portfolio)

    def load_portfolio(self, user_id: int, portfolio_id: int) -> ActivePortfolio | None:
        portfolio = self.repo.get_user_portfolio(user_id, portfolio_id)
        if not portfolio:
            return None
        return self._active_from_portfolio(portfolio)

    def create_empty_portfolio(self, user_id: int, name: str) -> ActivePortfolio:
        portfolio = self.repo.create_portfolio(user_id, name)
        self.repo.replace_positions(portfolio.id, self._empty_holdings_df(), allow_empty=True)
        self.remember_last_portfolio(user_id, portfolio.id)
        return self._active_from_portfolio(portfolio)

    def rename_portfolio(self, user_id: int, portfolio_id: int, name: str) -> ActivePortfolio:
        self.repo.rename_portfolio(user_id, portfolio_id, name)
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found.")
        return self._active_from_portfolio(portfolio)

    def delete_portfolio(self, user_id: int, portfolio_id: int) -> ActivePortfolio:
        """
        Delete one portfolio and return the next active portfolio for that user.

        Always leaves the user with at least one portfolio by bootstrapping when needed.
        """
        self.repo.delete_portfolio(user_id, portfolio_id)
        user = self.repo.get_user(user_id)
        if not user:
            raise ValueError("User not found.")
        return self.bootstrap_user_portfolio(user)

    def save_holdings(self, portfolio_id: int, df: pd.DataFrame) -> ActivePortfolio:
        self.repo.replace_positions(portfolio_id, df)
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found.")
        return self._active_from_portfolio(portfolio)

    def save_as_portfolio(
        self,
        user_id: int,
        source_portfolio_id: int,
        new_name: str,
        holdings_df: pd.DataFrame,
    ) -> ActivePortfolio:
        """
        Clone holdings (§6 consolidated on write) and financial snapshots into a new portfolio.
        """
        source = self.repo.get_user_portfolio(user_id, source_portfolio_id)
        if not source:
            raise ValueError("Source portfolio not found.")
        portfolio = self.repo.create_portfolio(user_id, new_name)
        self.repo.replace_positions(
            portfolio.id,
            holdings_df,
            allow_empty=holdings_df.empty,
        )
        self.repo.copy_symbol_snapshots(source_portfolio_id, portfolio.id)
        self.repo.copy_symbol_ta_woi(source_portfolio_id, portfolio.id)
        keep_symbols = holdings_df["Symbol"].astype(str).str.strip().str.upper().tolist()
        self.repo.prune_symbol_snapshots(portfolio.id, keep_symbols)
        source_sync = self.repo.get_sync_state(source_portfolio_id)
        self.repo.update_sync_state(
            portfolio.id,
            last_sync_at=source_sync.last_sync_at,
            last_sync_status=source_sync.last_sync_status,
            last_sync_error=source_sync.last_sync_error,
            symbols_requested=source_sync.symbols_requested,
            symbols_succeeded=source_sync.symbols_succeeded,
        )
        self.remember_last_portfolio(user_id, portfolio.id)
        return self._active_from_portfolio(portfolio)

    def _holdings_df_for_portfolio(self, portfolio_id: int) -> pd.DataFrame:
        positions = self.repo.list_positions(portfolio_id)
        if not positions:
            return self._empty_holdings_df()
        return self.repo.positions_to_dataframe(positions)

    def preview_csv_import(
        self,
        portfolio_id: int,
        raw_csv: pd.DataFrame,
        mode: ImportMode,
    ) -> ImportPreview:
        current = self._holdings_df_for_portfolio(portfolio_id)
        csv_df, rejected = parse_csv_preflight(raw_csv)
        return build_import_preview(current, csv_df, mode, rejected)

    def import_csv_into_portfolio(
        self,
        portfolio_id: int,
        raw_csv: pd.DataFrame,
        mode: ImportMode,
        *,
        allow_empty_replace: bool = False,
    ) -> tuple[ActivePortfolio, ImportApplyResult]:
        """Apply replace or merge import into an existing portfolio (Phase 2)."""
        current = self._holdings_df_for_portfolio(portfolio_id)
        csv_df, rejected = parse_csv_preflight(raw_csv)
        applied = apply_import(
            current,
            csv_df,
            mode,
            rejected,
            allow_empty_replace=allow_empty_replace,
        )
        self.repo.replace_positions(
            portfolio_id,
            applied.holdings_df,
            allow_empty=applied.holdings_df.empty,
        )
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found.")
        return self._active_from_portfolio(portfolio), applied
