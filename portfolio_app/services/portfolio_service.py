"""Portfolio load, save, import, bootstrap, and switching."""
import pandas as pd

from portfolio_app.data.portfolio_loader import get_mock_portfolio_df
from portfolio_app.domain.models import ActivePortfolio, Portfolio, User
from portfolio_app.storage.repository import PortfolioRepository

_EMPTY_HOLDINGS_COLUMNS = [
    "Symbol", "Shares", "AvgCost", "PurchaseDate", "TargetPrice", "Currency"
]


class PortfolioService:
    def __init__(self, repo: PortfolioRepository | None = None):
        self.repo = repo or PortfolioRepository()

    def get_or_create_user(self, email: str) -> User:
        return self.repo.get_or_create_user(email)

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

    def save_holdings(self, portfolio_id: int, df: pd.DataFrame) -> ActivePortfolio:
        self.repo.replace_positions(portfolio_id, df)
        portfolio = self.repo.get_portfolio(portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found.")
        return self._active_from_portfolio(portfolio)

    def import_csv_to_portfolio(
        self,
        user_id: int,
        name: str,
        df: pd.DataFrame,
        *,
        replace_existing: bool,
    ) -> ActivePortfolio:
        """
        Import CSV holdings into a named portfolio.
        If the name exists, replace_existing must be True or ValueError is raised.
        """
        name = name.strip()
        if not name:
            raise ValueError("Portfolio name is required.")

        existing = self.repo.find_portfolio_by_name(user_id, name)
        if existing:
            if not replace_existing:
                raise ValueError(f'A portfolio named "{name}" already exists.')
            self.repo.replace_positions(existing.id, df)
            self.remember_last_portfolio(user_id, existing.id)
            return self._active_from_portfolio(existing)

        portfolio = self.repo.create_portfolio(user_id, name)
        self.repo.replace_positions(portfolio.id, df)
        self.remember_last_portfolio(user_id, portfolio.id)
        return self._active_from_portfolio(portfolio)
