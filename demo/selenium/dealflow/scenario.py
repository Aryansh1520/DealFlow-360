"""Boilerplate every flow script shares: banner, browser lifecycle, error
screenshots, and the DF_KEEP_OPEN hold-at-end behaviour.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import pathlib
import sys
import traceback

from selenium.webdriver.remote.webdriver import WebDriver

from . import api
from .config import KEEP_OPEN
from .driver import TwoUp, new_browser

_SHOTS = pathlib.Path(__file__).resolve().parent.parent / "screenshots"


def _dump(driver: WebDriver, tag: str) -> None:
    _SHOTS.mkdir(exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = _SHOTS / f"{tag}-{stamp}.png"
    with contextlib.suppress(Exception):
        driver.save_screenshot(str(path))
        print(f"  screenshot: {path}", flush=True)


def _preflight() -> None:
    if not api.health():
        print(
            "\n  Backend health check failed at "
            f"{api.API_URL.replace('/api/v1', '')}/health.\n"
            "  Start the stack first:  docker compose up -d\n",
            file=sys.stderr,
        )
        sys.exit(2)


@contextlib.contextmanager
def single(title: str, *, position=(60, 40)):
    """One-browser flow. Yields (driver, done) — call done()… actually just yields
    the driver; teardown is automatic."""
    _preflight()
    _banner(title)
    driver = new_browser(position=position, maximize=True)
    tag = _slug(title)
    try:
        yield driver
        print(f"\n  ✅ {title} — complete.\n", flush=True)
        _hold_or_quit([driver])
    except BaseException:  # noqa: BLE001 — we re-raise
        print(f"\n  ❌ {title} — failed:\n", flush=True)
        traceback.print_exc()
        _dump(driver, tag)
        _hold_or_quit([driver], failed=True)
        raise


@contextlib.contextmanager
def two_up(title: str):
    """Two-browser flow (left = rep, right = customer, by convention)."""
    _preflight()
    _banner(title)
    pair = TwoUp().open()
    tag = _slug(title)
    try:
        yield pair
        print(f"\n  ✅ {title} — complete.\n", flush=True)
        _hold_or_quit([pair.left, pair.right])
    except BaseException:  # noqa: BLE001
        print(f"\n  ❌ {title} — failed:\n", flush=True)
        traceback.print_exc()
        _dump(pair.left, tag + "-left")
        _dump(pair.right, tag + "-right")
        _hold_or_quit([pair.left, pair.right], failed=True)
        raise


def _hold_or_quit(drivers, *, failed: bool = False) -> None:
    if KEEP_OPEN or failed:
        try:
            input("  (browser left open — press Enter to close) ")
        except EOFError:
            pass
    for d in drivers:
        with contextlib.suppress(Exception):
            d.quit()


def _banner(title: str) -> None:
    line = "─" * (len(title) + 6)
    print(f"\n┌{line}┐\n│   {title}   │\n└{line}┘\n", flush=True)


def _slug(title: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in title.lower()).strip("-")
