from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date


def _env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(name, default)
    if required and not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def database_path() -> str:
    """Where the state database lives: DB_PATH, or state.db inside DATA_DIR (default ./data)."""
    return _env("DB_PATH") or os.path.join(_env("DATA_DIR", "./data"), "state.db")


@dataclass
class MailHawkConfig:
    url: str
    api_key: str
    timeout: int


@dataclass
class Config:
    providers: list[str]
    database_path: str
    dry_run: bool
    since: date | None
    mailhawk: MailHawkConfig


def load() -> Config:
    since = _env("SINCE_DATE")
    return Config(
        providers=[p.strip().lower() for p in _env("PROVIDERS", "lidl").split(",") if p.strip()],
        database_path=database_path(),
        dry_run=_bool("DRY_RUN", False),
        since=date.fromisoformat(since) if since else None,
        mailhawk=_mailhawk(),
    )


def _mailhawk() -> MailHawkConfig:
    return MailHawkConfig(
        url=_env("MAILHAWK_URL", required=True),
        api_key=_env("MAILHAWK_API_KEY", required=True),
        timeout=int(_env("MAILHAWK_TIMEOUT", "30")),
    )
