"""Resolve session identity by email — compatible with future verification."""
from __future__ import annotations

import streamlit as st

from portfolio_app.domain.models import User
from portfolio_app.domain.user_identity import (
    ACCOUNT_SELECTABLE_STATUSES,
    USER_STATUS_ACTIVE,
    USER_STATUS_PENDING_VERIFICATION,
    USER_STATUS_VERIFIED,
    normalize_email,
    validate_email_format,
)
from portfolio_app.storage.repository import PortfolioRepository


class UserIdentityService:
    """Email → user_id mapping; stable across portfolio operations."""

    def __init__(self, repo: PortfolioRepository | None = None):
        self.repo = repo or PortfolioRepository()

    def normalize_email(self, email: str) -> str:
        return normalize_email(email)

    def validate_email(self, email: str) -> tuple[bool, str]:
        return validate_email_format(email)

    def resolve_user(self, email: str, *, create: bool = True) -> User:
        """
        Load or create the SQLite user for this email.

        Same normalized email always yields the same user.id (AT-8).
        """
        normalized = normalize_email(email)
        ok, err = validate_email_format(normalized)
        if not ok:
            raise ValueError(err)
        if create:
            return self.repo.get_or_create_user(normalized)
        user = self.repo.get_user_by_email(normalized)
        if not user:
            raise ValueError("User not found.")
        return user

    def get_user_by_email(self, email: str) -> User | None:
        return self.repo.get_user_by_email(normalize_email(email))

    def list_known_users(self) -> list[User]:
        """Users offered in the account switcher."""
        return self.repo.list_users(statuses=ACCOUNT_SELECTABLE_STATUSES)

    def is_verification_required(self, user: User) -> bool:
        """True when a future auth gate would block until email is verified."""
        return user.status == USER_STATUS_PENDING_VERIFICATION

    def is_verified(self, user: User) -> bool:
        return user.status in (USER_STATUS_VERIFIED, USER_STATUS_ACTIVE)

    def mark_email_verified(self, user_id: int) -> User:
        """Hook for a future verification flow — no-op for local-only use today."""
        return self.repo.update_user_status(user_id, USER_STATUS_VERIFIED)

    def mark_pending_verification(self, user_id: int) -> User:
        """Hook for a future sign-up flow."""
        return self.repo.update_user_status(user_id, USER_STATUS_PENDING_VERIFICATION)


def get_user_identity_service() -> UserIdentityService:
    if "user_identity_service" not in st.session_state:
        st.session_state.user_identity_service = UserIdentityService()
    return st.session_state.user_identity_service
