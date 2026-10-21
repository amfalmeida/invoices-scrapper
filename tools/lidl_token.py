"""Print a Lidl Plus access token (for curl etc.), persisting the rotated refresh token.

    python -m tools.lidl_token
"""
from __future__ import annotations

import os
import sys

from invoices.config import database_path
from invoices.providers.lidl import LidlProvider
from invoices.state import State


def main() -> None:
    provider = LidlProvider(State(database_path()))
    try:
        provider.api._default_headers()  # renews the access token
    finally:
        provider._save_token()
    print(f"expires {provider.api._expires:%Y-%m-%d %H:%M} UTC", file=sys.stderr)
    print(provider.api._token)


if __name__ == "__main__":
    main()
