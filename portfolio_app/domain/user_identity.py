"""Email identity rules — single normalization path for DB and session (Phase 6)."""
from __future__ import annotations

import re

# User.status values (SQLite users.status)
USER_STATUS_ACTIVE = "active"
USER_STATUS_PENDING_VERIFICATION = "pending_verification"
USER_STATUS_VERIFIED = "verified"
USER_STATUS_SUSPENDED = "suspended"

# Local dev default; maps to a stable SQLite user row via get_or_create_user.
DEFAULT_LOCAL_EMAIL = "user@local"

# Accounts shown in the header switcher (includes pending until verification ships).
ACCOUNT_SELECTABLE_STATUSES = (
    USER_STATUS_ACTIVE,
    USER_STATUS_VERIFIED,
    USER_STATUS_PENDING_VERIFICATION,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")


def normalize_email(email: str) -> str:
    """Canonical email key for users.email (lowercase, trimmed)."""
    return (email or "").strip().lower()


def validate_email_format(email: str) -> tuple[bool, str]:
    """
    Validate email before create/switch.

    Returns (ok, error_message). error_message is empty when ok.
    """
    normalized = normalize_email(email)
    if not normalized:
        return False, "Enter an email address."
    if not _EMAIL_RE.match(normalized):
        return False, "Enter a valid email (e.g. name@example.com)."
    return True, ""


def display_name_from_email(email: str) -> str:
    """Default display_name when none is stored."""
    prefix = normalize_email(email).split("@")[0].strip()
    return prefix or "User"
