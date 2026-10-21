from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Invoice:
    provider: str
    id: str
    date: datetime | None
    total: str | None  # display value, e.g. "23.45"
    currency: str | None
    title: str
    url: str | None = None  # where the invoice was fetched from
    qr_code: str | None = None  # Portuguese AT fiscal QR string (A:...*B:...*...)
    entity_name: str | None = None  # issuer/payee name, e.g. "Lidl"

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.id}"
