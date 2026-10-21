from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date

from ..models import Invoice
from ..state import State


@dataclass
class InvoiceRef:
    id: str
    date: date | None
    raw: object = None  # provider-specific summary, passed back to fetch()


class Provider(ABC):
    name: str

    def __init__(self, state: State):
        self.state = state

    @abstractmethod
    def list_refs(self) -> list[InvoiceRef]:
        """Return a lightweight reference for every invoice available."""

    @abstractmethod
    def fetch(self, ref: InvoiceRef) -> Invoice:
        """Download the full invoice."""

    def new_invoices(self, is_sent: Callable[[str], bool], since: date | None = None) -> Iterator[Invoice]:
        for ref in self.list_refs():
            if is_sent(f"{self.name}:{ref.id}"):
                continue
            if since and ref.date and ref.date < since:
                continue
            yield self.fetch(ref)
