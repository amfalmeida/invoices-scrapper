"""Entrypoint for the container and the Home Assistant add-on.

Home Assistant passes the add-on options as /data/options.json; they are mapped onto the
environment variables that invoices.config reads. Without that file (docker compose, local runs)
the environment from .env is used as-is.
"""
import json
import os
import time

OPTIONS_FILE = "/data/options.json"

# add-on option -> environment variable
ENV_MAP = {
    "providers": "PROVIDERS",
    "timezone": "TZ",
    "database_path": "DB_PATH",
    "mailhawk_url": "MAILHAWK_URL",
    "mailhawk_api_key": "MAILHAWK_API_KEY",
    "mailhawk_timeout": "MAILHAWK_TIMEOUT",
    "lidl_refresh_token": "LIDL_REFRESH_TOKEN",
    "lidl_language": "LIDL_LANGUAGE",
    "lidl_country": "LIDL_COUNTRY",
    "lidl_entity_name": "LIDL_ENTITY_NAME",
    "lidl_app_version": "LIDL_APP_VERSION",
    "since_date": "SINCE_DATE",
    "dry_run": "DRY_RUN",
    "log_level": "LOG_LEVEL",
}


def load_options() -> None:
    if not os.path.exists(OPTIONS_FILE):
        return
    with open(OPTIONS_FILE) as f:
        options = json.load(f)
    for option, env in ENV_MAP.items():
        value = options.get(option)
        if value is None or value == "" or value == []:
            continue  # empty options fall back to the defaults in invoices.config
        if isinstance(value, list):
            value = ",".join(str(v) for v in value)
        elif isinstance(value, bool):
            value = "true" if value else "false"
        os.environ[env] = str(value)


if __name__ == "__main__":
    load_options()
    if os.environ.get("TZ"):
        time.tzset()  # so log timestamps use the configured timezone
    from invoices.__main__ import main

    main()
