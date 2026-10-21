"""Download all Lidl receipts into a single JSON file.

    python -m tools.lidl_receipt    # update data.json with any new receipts

Each entry holds the ticket list summary (currency, article count, ...) and the full receipt
(store, printed receipt HTML, fiscal codes, ...). Receipts already in the file are not refetched.
"""
from __future__ import annotations

import json
import os

from invoices.config import database_path
from invoices.providers.lidl import LidlProvider
from invoices.state import State

OUT_DIR = os.environ.get("RECEIPTS_DIR", "./data/receipts")
JSON_FILE = os.environ.get("RECEIPTS_JSON", os.path.join(OUT_DIR, "data.json"))


def _load() -> dict[str, dict]:
    if not os.path.exists(JSON_FILE) or os.path.getsize(JSON_FILE) == 0:
        return {}
    with open(JSON_FILE) as f:
        return {entry["id"]: entry for entry in json.load(f)}


def _save(entries: dict[str, dict]) -> None:
    ordered = sorted(entries.values(), key=lambda e: (e["summary"] or {}).get("date") or "", reverse=True)
    tmp = f"{JSON_FILE}.tmp"
    with open(tmp, "w") as f:
        json.dump(ordered, f, indent=2, ensure_ascii=False)
    os.replace(tmp, JSON_FILE)


def main() -> None:
    provider = LidlProvider(State(database_path()))
    os.makedirs(OUT_DIR, exist_ok=True)

    entries = _load()
    refs = provider.list_refs()
    new = [ref for ref in refs if ref.id not in entries]
    print(f"{len(refs)} receipts, {len(entries)} already in {JSON_FILE}, {len(new)} to fetch")

    for n, ref in enumerate(new, 1):
        try:
            ticket = provider.api.ticket(ref.id)
        finally:
            provider._save_token()
        entries[ref.id] = {"id": ref.id, "summary": ref.raw, "ticket": ticket}
        _save(entries)  # after every receipt, so an interrupted run keeps its progress
        print(f"[{n}/{len(new)}] {ref.date} {ticket.get('totalAmount')} {(ticket.get('store') or {}).get('name')}")

    print(f"{len(entries)} receipts saved to {JSON_FILE}")


if __name__ == "__main__":
    main()
