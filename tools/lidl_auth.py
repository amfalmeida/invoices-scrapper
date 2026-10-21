"""Lidl Plus login. Stores the refresh token in .env and in the service state.

Opens a browser (Firefox, Chrome, Edge or Chromium) on the Lidl login page; you log in by hand
(phone/email, password, 2FA, legal terms) and the OAuth code is captured from the final redirect.
This survives Lidl login page redesigns, which break lidl-plus' scripted login.

    python -m tools.lidl_auth
"""
from __future__ import annotations

import os
import re
import shutil
import time

from lidlplus import LidlPlusApi

from invoices.config import database_path
from invoices.providers.lidl import TOKEN_KEY
from invoices.state import State

ENV_FILE = os.environ.get("ENV_FILE", ".env")
LOGIN_TIMEOUT = int(os.environ.get("LIDL_LOGIN_TIMEOUT", "600"))

FIREFOX_PATHS = [
    "/Applications/Firefox.app/Contents/MacOS/firefox",
    os.path.expanduser("~/Applications/Firefox.app/Contents/MacOS/firefox"),
    "/usr/bin/firefox",
    "/snap/bin/firefox",
]


def _firefox_binary() -> str | None:
    if os.environ.get("FIREFOX_BINARY"):
        return os.environ["FIREFOX_BINARY"]
    return next((p for p in FIREFOX_PATHS if os.path.exists(p)), None) or shutil.which("firefox")


class AuthApi(LidlPlusApi):
    def _init_firefox(self, headless=True):
        """lidl-plus hardcodes /usr/bin/firefox and uses the removed Selenium 3 Firefox API,
        so Firefox only works on Linux. Start it with the Selenium 4 API instead."""
        from getuseragent import UserAgent
        from selenium.webdriver.firefox.service import Service
        from seleniumwire import webdriver
        from webdriver_manager.firefox import GeckoDriverManager

        binary = _firefox_binary()
        if not binary:
            raise RuntimeError("Firefox not found (set FIREFOX_BINARY)")
        options = webdriver.FirefoxOptions()
        options.binary_location = binary
        if headless:
            options.add_argument("-headless")
        options.set_preference("general.useragent.override", UserAgent(self._OS.lower()).Random())
        return webdriver.Firefox(service=Service(GeckoDriverManager().install()), options=options)

    def interactive_login(self, timeout: int = LOGIN_TIMEOUT) -> None:
        browser = self._get_browser(headless=False)
        try:
            browser.get(self._register_link)
            print("Log in to Lidl Plus in the browser window (including the verification code).")
            print(f"Waiting up to {timeout // 60} minutes...")
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if code := self._find_code(browser):
                    self._authorization_code(code)
                    return
                time.sleep(1)
            raise SystemExit("Timed out waiting for the Lidl login to finish")
        finally:
            try:
                browser.quit()
            except Exception:  # noqa: BLE001 - browser may already be closed by the user
                pass

    def _find_code(self, browser) -> str | None:
        # After login, Lidl redirects to com.lidlplus.app://callback?code=...; the browser can't open
        # that URL, but selenium-wire still sees the redirect's Location header.
        for request in reversed(browser.requests):
            if not request.url.startswith(f"{self._AUTH_API}/connect") or not request.response:
                continue
            location = request.response.headers.get("Location", "")
            if match := re.search(r"[?&]code=([^&#]+)", location):
                return match.group(1)
        return None


def _write_env(key: str, value: str) -> None:
    lines = open(ENV_FILE).read().splitlines() if os.path.exists(ENV_FILE) else []
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for i, line in enumerate(lines):
        if pattern.match(line):
            lines[i] = f"{key}={value}"
            break
    else:
        lines.append(f"{key}={value}")
    with open(ENV_FILE, "w") as f:
        f.write("\n".join(lines) + "\n")


def main() -> None:
    api = AuthApi(
        language=os.environ.get("LIDL_LANGUAGE") or "pt",
        country=os.environ.get("LIDL_COUNTRY") or "PT",
    )
    api.interactive_login()
    token = api.refresh_token
    if not token:
        raise SystemExit("Login finished but no refresh token was returned")

    _write_env("LIDL_REFRESH_TOKEN", token)
    # The persisted token takes precedence over .env, so replace it too.
    State(database_path()).set(TOKEN_KEY, token)
    print(f"Refresh token saved to {ENV_FILE} and the service state.")


if __name__ == "__main__":
    main()
