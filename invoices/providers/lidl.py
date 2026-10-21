from __future__ import annotations

import logging
import os
from datetime import datetime

import requests
from lidlplus import LidlPlusApi

from ..models import Invoice
from .base import InvoiceRef, Provider

log = logging.getLogger(__name__)

TOKEN_KEY = "lidl.refresh_token"
TICKETS_API = "https://tickets.lidlplus.com/api"
# The tickets API silently drops requests with lidl-plus' fake "999.99.9" app version.
# Bump this to a recent Lidl Plus app release if requests start failing again.
DEFAULT_APP_VERSION = "16.45.5"


class LidlApi(LidlPlusApi):
    """lidl-plus with a real App-Version and the current ticket endpoints
    (v2 list, v3 detail; v2 detail now returns 400)."""

    _TIMEOUT = 30

    def __init__(self, *args, app_version: str = DEFAULT_APP_VERSION, **kwargs):
        super().__init__(*args, **kwargs)
        self._app_version = app_version

    def _default_headers(self):
        return {**super()._default_headers(), "App-Version": self._app_version}

    def _get(self, url: str) -> dict:
        response = requests.get(url, headers=self._default_headers(), timeout=self._TIMEOUT)
        response.raise_for_status()
        return response.json()

    def tickets(self, only_favorite=False):
        tickets, page = [], 1
        while True:
            data = self._get(
                f"{TICKETS_API}/v2/{self._country}/tickets"
                f"?pageNumber={page}&onlyFavorite={str(only_favorite).lower()}"
            )
            batch = data.get("tickets") or []
            tickets += batch
            if not batch or len(tickets) >= int(data.get("totalCount", 0)):
                return tickets
            page += 1

    def ticket_url(self, ticket_id) -> str:
        return f"{TICKETS_API}/v3/{self._country}/tickets/{ticket_id}"

    def ticket(self, ticket_id):
        return self._get(self.ticket_url(ticket_id))


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _currency(data: dict) -> str | None:
    cur = data.get("currency")
    if isinstance(cur, dict):
        return cur.get("code") or cur.get("symbol")
    return cur


class LidlProvider(Provider):
    name = "lidl"

    def __init__(self, state):
        super().__init__(state)
        # Lidl rotates the refresh token on every renewal, so the persisted one wins over the env one.
        token = state.get(TOKEN_KEY) or os.environ.get("LIDL_REFRESH_TOKEN")
        if not token:
            raise SystemExit("LIDL_REFRESH_TOKEN is not set (get one with `make lidl-auth`)")
        self.api = LidlApi(
            language=os.environ.get("LIDL_LANGUAGE") or "pt",
            country=os.environ.get("LIDL_COUNTRY") or "PT",
            refresh_token=token,
            app_version=os.environ.get("LIDL_APP_VERSION") or DEFAULT_APP_VERSION,
        )

    def _save_token(self) -> None:
        token = self.api.refresh_token
        if token and token != self.state.get(TOKEN_KEY):
            self.state.set(TOKEN_KEY, token)
            log.debug("Persisted rotated Lidl refresh token")

    def list_refs(self) -> list[InvoiceRef]:
        try:
            tickets = self.api.tickets()
        finally:
            self._save_token()
        refs = []
        for t in tickets:
            dt = _parse_date(t.get("date"))
            refs.append(InvoiceRef(id=str(t["id"]), date=dt.date() if dt else None, raw=t))
        log.info("Lidl: %d tickets available", len(refs))
        return refs

    def fetch(self, ref: InvoiceRef) -> Invoice:
        try:
            ticket = self.api.ticket(ref.id)
        finally:
            self._save_token()

        dt = _parse_date(ticket.get("date")) or _parse_date((ref.raw or {}).get("date"))
        total = ticket.get("totalAmount", (ref.raw or {}).get("totalAmount"))
        # v3 receipts have no currency field; only the ticket list does.
        currency = _currency(ticket) or _currency(ref.raw or {}) or os.environ.get("LIDL_CURRENCY") or "EUR"
        store = ticket.get("store") or {}
        store_name = store.get("name") or "Lidl"
        day = dt.strftime("%Y-%m-%d") if dt else "unknown-date"
        fiscal = next((c.get("code") for c in ticket.get("codes") or [] if c.get("codeType") == "Fiscal"), None)

        return Invoice(
            provider=self.name,
            id=ref.id,
            date=dt,
            total=None if total is None else str(total),
            currency=currency,
            title=f"Lidl {store_name} {day}",
            url=self.api.ticket_url(ref.id),
            qr_code=fiscal,
            entity_name=os.environ.get("LIDL_ENTITY_NAME") or "Lidl",
        )

