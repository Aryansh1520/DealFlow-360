"""Chrome factory + window tiling.

Two-actor flows (rep + customer, or two rep sessions) need genuinely separate
browser sessions, not two tabs — they must not share a login. We give each its own
Chrome process with a private `--user-data-dir`, and tile them side by side so the
whole negotiation is visible in one screen capture.
"""

from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from dataclasses import dataclass, field

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from .config import HEADLESS, WINDOW_HEIGHT, WINDOW_WIDTH

_TMP_PROFILES: list[str] = []


def _screen_size(driver: webdriver.Chrome) -> tuple[int, int]:
    try:
        w, h = driver.execute_script(
            "return [window.screen.availWidth, window.screen.availHeight];"
        )
        return int(w), int(h)
    except Exception:
        return 1440, 820


def _cleanup_profiles() -> None:
    for path in _TMP_PROFILES:
        shutil.rmtree(path, ignore_errors=True)


atexit.register(_cleanup_profiles)


def _make_options(position: tuple[int, int], size: tuple[int, int]) -> Options:
    opts = Options()
    profile = tempfile.mkdtemp(prefix="dealflow-chrome-")
    _TMP_PROFILES.append(profile)
    opts.add_argument(f"--user-data-dir={profile}")
    opts.add_argument(f"--window-size={size[0]},{size[1]}")
    opts.add_argument(f"--window-position={position[0]},{position[1]}")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-save-password-bubble")
    # Kill the "Save password?" / "Change your password" / data-breach bubbles that
    # otherwise pop over the UI right after every login and block the recording.
    opts.add_argument(
        "--disable-features="
        "Translate,MediaRouter,"
        "PasswordManagerOnboarding,PasswordLeakDetection,"
        "AutofillServerCommunication,PasswordCheckBulkLeakCheck,"
        "InsecureDownloadWarnings"
    )
    opts.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.password_manager_leak_detection": False,
            "autofill.profile_enabled": False,
            "autofill.credit_card_enabled": False,
        },
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    if HEADLESS:
        opts.add_argument("--headless=new")
    return opts


def new_browser(
    *,
    position: tuple[int, int] = (40, 40),
    size: tuple[int, int] | None = None,
    maximize: bool = False,
) -> webdriver.Chrome:
    """A fresh Chrome with its own profile. `maximize=True` fills the whole
    screen — used for single-actor flows; two-actor flows pass an explicit size
    so the pair tiles."""
    size = size or (WINDOW_WIDTH, WINDOW_HEIGHT)
    opts = _make_options(position, size)
    if maximize and not HEADLESS:
        opts.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(), options=opts)
    if maximize and not HEADLESS:
        try:
            driver.maximize_window()
        except Exception:
            w, h = _screen_size(driver)
            driver.set_window_rect(x=0, y=0, width=w, height=h)
    else:
        driver.set_window_position(*position)
        driver.set_window_size(*size)
    return driver


@dataclass
class TwoUp:
    """A left/right pair of independent browsers for two-actor flows."""

    left: webdriver.Chrome = field(default=None)  # type: ignore[assignment]
    right: webdriver.Chrome = field(default=None)  # type: ignore[assignment]

    def open(self, *, gap: int = 8, margin: int = 8) -> "TwoUp":
        """Tile two windows to fill the actual screen — each gets exactly half the
        available width and the full available height, so both sessions are fully
        visible in one screen capture. `DF_WIN_W` still overrides the per-window
        width if you want a specific size."""
        self.left = new_browser(position=(margin, margin))
        screen_w, screen_h = _screen_size(self.left)

        override = int(os.environ["DF_WIN_W"]) if "DF_WIN_W" in os.environ else None
        half_w = override or max(560, (screen_w - 2 * margin - gap) // 2)
        height = max(600, screen_h - 2 * margin)

        left_x = margin
        right_x = margin + half_w + gap
        # If a hard override pushes the pair off-screen, fall back to an even split.
        if right_x + half_w > screen_w:
            half_w = (screen_w - 2 * margin - gap) // 2
            right_x = margin + half_w + gap

        self.left.set_window_rect(x=left_x, y=margin, width=half_w, height=height)
        self.right = new_browser(position=(right_x, margin), size=(half_w, height))
        self.right.set_window_rect(x=right_x, y=margin, width=half_w, height=height)
        # A quick re-assert — some window managers ignore the first rect during launch.
        self.left.set_window_rect(x=left_x, y=margin, width=half_w, height=height)
        return self

    def quit(self) -> None:
        for d in (self.left, self.right):
            try:
                if d is not None:
                    d.quit()
            except Exception:
                pass
