from __future__ import annotations

import logging

import requests

from .config import MailHawkConfig
from .models import Invoice

log = logging.getLogger(__name__)


def build_payload(invoice: Invoice) -> dict:
    return {
        "date": invoice.date.strftime("%Y-%m-%d") if invoice.date else None,
        "entityName": invoice.entity_name,
        "description": invoice.title,
        "raw": invoice.qr_code,
    }


class MailHawk:
    """Sends invoices to mail-hawk's POST /api/invoices (stored in Sheets / Actual Budget there)."""

    def __init__(self, cfg: MailHawkConfig):
        self.cfg = cfg
        self.url = f"{cfg.url.rstrip('/')}/api/invoices"
        self._session: requests.Session | None = None

    def __enter__(self):
        self._session = requests.Session()
        self._session.headers.update({"X-API-Key": self.cfg.api_key})
        return self

    def __exit__(self, *exc):
        if self._session:
            self._session.close()

    def send(self, invoice: Invoice) -> bool:
        """True when the invoice is done with: stored, already in mail-hawk, or never sendable."""
        if not invoice.qr_code or not invoice.date:
            # e.g. 2021 Lidl receipts, from before the app included the AT QR code; they will never have one.
            log.warning("Skipping %s (%s): no fiscal QR code or date, won't retry", invoice.key, invoice.title)
            return True
        response = self._session.post(self.url, json=build_payload(invoice), timeout=self.cfg.timeout)
        try:
            body = response.json()
        except ValueError:
            body = {"error": response.text[:300]}
        if response.status_code in (200, 201):
            log.info("mail-hawk %s %s: %s %s (%s)", response.status_code, invoice.key,
                     body.get("status"), body.get("invoiceId"), body.get("message") or body.get("invoiceType"))
            return True
        if response.status_code in (401, 403):
            raise RuntimeError(f"mail-hawk rejected the request ({response.status_code}): {body.get('error')}")
        log.error("mail-hawk %s %s: %s", response.status_code, invoice.key, body)
        return False
