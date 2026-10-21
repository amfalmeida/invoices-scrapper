# invoices-scrapper

Fetches invoices/receipts from several providers on a schedule and sends each new one to
[mail-hawk](../mail-hawk).
Sent invoices are tracked in a SQLite database (`DB_PATH`, default `$DATA_DIR/state.db`), so each one is only sent once.

## mail-hawk

Each invoice is posted to `POST {MAILHAWK_URL}/api/invoices` with the `X-API-Key` header:

```json
{"date": "2026-10-19", "entityName": "Lidl", "raw": "A:503340855*B:999999990*C:PT*D:FS*..."}
```

`raw` is the receipt's Portuguese AT fiscal QR code. mail-hawk must have `APP_API_ENABLED=true` and
`APP_API_KEY` set to the same value as `MAILHAWK_API_KEY`. 200/201 mark the invoice as sent; other errors are
logged and retried on the next run. Receipts without a fiscal QR code (Lidl receipts from 2021) are skipped.

## Providers

| Name   | Library                                                  | Required env              |
|--------|----------------------------------------------------------|---------------------------|
| `lidl` | [lidl-plus](https://github.com/Andre0512/lidl-plus)      | `LIDL_REFRESH_TOKEN`, `LIDL_LANGUAGE`, `LIDL_COUNTRY` |

`make lidl-receipt` saves every receipt to `./data/receipts/data.json`.

## Setup

1. Get a Lidl Plus refresh token (needs Firefox or Chrome, so do it on your machine, not in the container):

   ```bash
   make lidl-auth
   ```

   A browser window opens on the Lidl login page. Log in normally (phone, password, verification
   code). Once Lidl redirects back to the app, the window closes and the token is saved to `.env`
   and the state database.

2. Configure:

   ```bash
   cp .env.example .env   # fill in MAILHAWK_URL/MAILHAWK_API_KEY + Lidl settings
   ```

   Set `SINCE_DATE` if you don't want your whole purchase history sent on the first run.
   Try `DRY_RUN=true` first to see what would be sent.

3. Run:

   ```bash
   docker compose up -d --build
   docker compose logs -f
   ```

> **Note:** Lidl rotates the refresh token every time it is used. The service stores the latest
> token in the state database, so keep that file (on Home Assistant: `/share/invoices-scrapper/state.db`). If you delete it, generate a fresh token
> with `make lidl-auth`, because the one in `.env` will have expired.

## Home Assistant add-on

The repo root is also a Home Assistant add-on repository (`repository.yaml`, `config.yaml`). Home
Assistant pulls the image that `.github/workflows/build.yaml` publishes to `ghcr.io/amfalmeida/invoices-scrapper`
on each `v*` tag. Make the GHCR package public, or Home Assistant can't pull it.

1. Settings > Add-ons > Add-on Store > ⋮ > Repositories, add `https://github.com/amfalmeida/invoices-scrapper`.
2. Install **Invoices Scrapper** from the new repository section.
3. Set the options in the add-on's Configuration tab:
   - `database_path`: where the sent-invoice database lives. Default `/share/invoices-scrapper/state.db`.
   - `mailhawk_url` and `mailhawk_api_key`: use the LAN address of the machine running mail-hawk
     (`host.docker.internal` does not exist on Home Assistant).
   - `lidl_refresh_token`: run `make lidl-auth` on your desktop and paste the token from `.env`.
     Lidl rotates it on use, and the service keeps the latest one in the database after that. Don't run
     the desktop and the add-on against the same Lidl account at the same time, or one of them will
     lose the token.
4. Create the automation below so the add-on runs every day. Starting it does one pass and exits.
   Repository add-ons get a prefixed slug, so copy the real one from the add-on's info page
   (`<hash>_invoices_scrapper`) into `addon`. Use Settings > Automations > Create > Edit in YAML:

   ```yaml
   alias: Invoices scrapper daily
   triggers:
     - trigger: time
       at: 07:00:00
   actions:
     - action: hassio.addon_start
       data:
         addon: <hash>_invoices_scrapper
   mode: single
   ```

   Add one `triggers` entry per run time. To change the time, edit the automation. The add-on's
   Logs tab shows each run.

## Makefile

Run `make help` to see all targets. The usual flow:

```bash
make env        # create .env, then edit it (MAILHAWK_*, LIDL_LANGUAGE, LIDL_COUNTRY)
make lidl-auth  # log in to Lidl Plus; writes LIDL_REFRESH_TOKEN to .env and ./data
make dry-run    # one pass in docker, logs what would be sent
make up         # start the service
make logs
```

Local (non-docker) equivalents: `make local`, `make local-once`, `make local-dry-run`.
With Podman, use `make up COMPOSE="podman compose"`.

## Adding a provider

1. Create `invoices/providers/<name>.py` with a `Provider` subclass that implements
   `list_refs()` (lightweight list of invoice ids/dates) and `fetch(ref)` (returns an `Invoice`).
2. Register it in `invoices/providers/__init__.py` under `REGISTRY`.
3. Add it to `PROVIDERS` in `.env`.

Use `self.state.get/set` to persist provider data such as tokens.
