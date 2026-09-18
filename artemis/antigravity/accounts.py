"""Account manager and credential resolver for Antigravity OAuth tokens."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from google.oauth2.credentials import Credentials

from artemis.antigravity.constants import (
    ANTIGRAVITY_CLIENT_ID,
    ANTIGRAVITY_CLIENT_SECRET,
    ANTIGRAVITY_SCOPES,
    ANTIGRAVITY_TOKEN_URI,
)
from artemis.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CONFIG_PATHS = [
    Path.home() / ".config" / "antigravity" / "accounts.json",
    Path.home() / ".config" / "opencode" / "antigravity-accounts.json",
]


class AntigravityAccountManager:
    """Manages multi-account OAuth credentials with hot rotation and auto-refresh."""

    def __init__(self, custom_path: str | None = None):
        self.accounts_path = self._resolve_path(custom_path)
        self.accounts: list[dict[str, Any]] = []
        self.active_index: int = 0
        self.reload()

    def _resolve_path(self, custom_path: str | None) -> Path:
        if custom_path:
            return Path(custom_path).expanduser().resolve()

        env_path = os.environ.get("ANTIGRAVITY_ACCOUNTS_FILE")
        if env_path:
            return Path(env_path).expanduser().resolve()

        for p in DEFAULT_CONFIG_PATHS:
            if p.exists():
                return p

        return DEFAULT_CONFIG_PATHS[0]

    def reload(self) -> None:
        """Reloads accounts from the JSON store."""
        if not self.accounts_path.exists():
            self.accounts = []
            return

        try:
            with open(self.accounts_path, encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                self.accounts = data.get("accounts", [])
                self.active_index = data.get("activeIndex", 0)
            elif isinstance(data, list):
                self.accounts = [a for a in data if isinstance(a, dict)]
                self.active_index = 0

            if self.accounts and self.active_index >= len(self.accounts):
                self.active_index = 0

            logger.info(
                f"Loaded {len(self.accounts)} Antigravity accounts from {self.accounts_path}"
            )
        except (json.JSONDecodeError, OSError, KeyError, TypeError) as e:
            logger.error(f"Failed to load Antigravity accounts from {self.accounts_path}: {e}")
            self.accounts = []

    def get_account_count(self) -> int:
        return len(self.accounts)

    def get_active_email(self) -> str | None:
        if not self.accounts:
            return None
        return self.accounts[self.active_index].get("email")

    def get_credentials(self) -> Credentials | None:
        """Returns a valid Google OAuth Credentials object for the active account."""
        if not self.accounts:
            return None

        account = self.accounts[self.active_index]
        refresh_token = account.get("refreshToken")
        if not refresh_token:
            logger.error(f"Active account {account.get('email')} is missing refreshToken.")
            return None

        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=ANTIGRAVITY_TOKEN_URI,
            client_id=ANTIGRAVITY_CLIENT_ID,
            client_secret=ANTIGRAVITY_CLIENT_SECRET,
            scopes=ANTIGRAVITY_SCOPES,
        )
        return creds

    def rotate_to_next_account(self) -> Credentials | None:
        """Rotates to the next available account on quota exhaustion (429)."""
        if len(self.accounts) <= 1:
            logger.warning("Cannot rotate Antigravity account: only 1 account configured.")
            return self.get_credentials()

        old_email = self.get_active_email()
        self.active_index = (self.active_index + 1) % len(self.accounts)
        new_email = self.get_active_email()
        logger.warning(
            f"Antigravity quota exhausted on {old_email}. Rotated active account to {new_email}."
        )
        return self.get_credentials()


# Global singleton instance
_manager: AntigravityAccountManager | None = None


def get_account_manager() -> AntigravityAccountManager:
    global _manager
    if _manager is None:
        _manager = AntigravityAccountManager()
    return _manager
