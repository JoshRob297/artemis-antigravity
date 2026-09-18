"""Antigravity native authentication module for Artemis."""

from artemis.antigravity.constants import (
    ANTIGRAVITY_CLIENT_ID,
    ANTIGRAVITY_CLIENT_SECRET,
    ANTIGRAVITY_SCOPES,
    ANTIGRAVITY_TOKEN_URI,
)
from artemis.antigravity.accounts import (
    AntigravityAccountManager,
    get_account_manager,
)

__all__ = [
    "ANTIGRAVITY_CLIENT_ID",
    "ANTIGRAVITY_CLIENT_SECRET",
    "ANTIGRAVITY_SCOPES",
    "ANTIGRAVITY_TOKEN_URI",
    "AntigravityAccountManager",
    "get_account_manager",
]
