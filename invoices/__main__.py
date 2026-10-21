import logging
import os

from . import config
from .mailhawk import MailHawk, build_payload
from .providers import build
from .state import State

log = logging.getLogger("invoices")


def run_once(cfg: config.Config, state: State) -> None:
    providers = build(cfg.providers, state)
    hawk = None
    try:
        for provider in providers:
            try:
                sent = 0
                for invoice in provider.new_invoices(state.is_sent, cfg.since):
                    if cfg.dry_run:
                        if invoice.qr_code and invoice.date:
                            detail = build_payload(invoice)
                        else:
                            detail = "-> skip, no fiscal QR code"
                        log.info("[dry-run] would send %s (%s) %s", invoice.key, invoice.title, detail)
                        sent += 1
                        continue
                    if hawk is None:  # only connect when there's something to send
                        hawk = MailHawk(cfg.mailhawk).__enter__()
                    if hawk.send(invoice):
                        state.mark_sent(invoice.key)
                        sent += 1
                verb = "to send" if cfg.dry_run else "sent to mail-hawk"
                log.info("%s: %d new invoice(s) %s", provider.name, sent, verb)
            except Exception:
                log.exception("Provider %s failed", provider.name)
    finally:
        if hawk:
            hawk.__exit__(None, None, None)


def main() -> None:
    """One pass, then exit. When to run is decided by the caller (Home Assistant automation, cron)."""
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    cfg = config.load()
    run_once(cfg, State(cfg.database_path))


if __name__ == "__main__":
    main()
