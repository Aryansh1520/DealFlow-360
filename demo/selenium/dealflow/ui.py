"""UI interaction helpers shared by every flow script.

The DealFlow360 frontend is shadcn/ui + Radix (no `data-testid`s), so selectors
here lean on visible text and ARIA roles — the same things a person reading the
screen would use. Every helper waits; nothing sleeps-then-hopes except the
deliberate `beat()` pauses that pace the recording.
"""

from __future__ import annotations

import time
from typing import Iterable

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import BASE_URL, SLOW

DEFAULT_TIMEOUT = 25


# --------------------------------------------------------------------------- waits
def wait(driver: WebDriver, timeout: int = DEFAULT_TIMEOUT) -> WebDriverWait:
    return WebDriverWait(driver, timeout, poll_frequency=0.25)


def visible(driver: WebDriver, by: str, sel: str, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
    return wait(driver, timeout).until(EC.visibility_of_element_located((by, sel)))


def present(driver: WebDriver, by: str, sel: str, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
    return wait(driver, timeout).until(EC.presence_of_element_located((by, sel)))


def clickable(driver: WebDriver, by: str, sel: str, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
    return wait(driver, timeout).until(EC.element_to_be_clickable((by, sel)))


_LOWER = "abcdefghijklmnopqrstuvwxyz"
_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def wait_for_text(driver: WebDriver, text: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Case-insensitive — the UI upper/lower-cases plenty of labels via CSS, so the
    DOM text rarely matches the rendered casing."""
    needle = _xpath_literal(text.lower())
    xp = f"//*[contains(translate(normalize-space(.), '{_UPPER}', '{_LOWER}'), {needle})]"
    wait(driver, timeout).until(EC.presence_of_element_located((By.XPATH, xp)))


def wait_url_contains(driver: WebDriver, fragment: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    wait(driver, timeout).until(EC.url_contains(fragment))


# ------------------------------------------------------------------------- clicks
def _xpath_literal(s: str) -> str:
    if '"' not in s:
        return f'"{s}"'
    if "'" not in s:
        return f"'{s}'"
    parts = s.split('"')
    return "concat(" + ', \'"\', '.join(f'"{p}"' for p in parts) + ")"


def safe_click(driver: WebDriver, el: WebElement, tries: int = 4) -> None:
    for i in range(tries):
        try:
            driver.execute_script(
                "arguments[0].scrollIntoView({block:'center',inline:'center'});", el
            )
            el.click()
            return
        except StaleElementReferenceException:
            # Caller is expected to re-locate; give up quietly on the last try.
            time.sleep(0.4)
        except ElementClickInterceptedException:
            time.sleep(0.5)
            if i == tries - 1:
                driver.execute_script("arguments[0].click();", el)


def click_locator(driver: WebDriver, by: str, sel: str, *, timeout: int = DEFAULT_TIMEOUT, tries: int = 4) -> None:
    """Find + click, re-finding on staleness (lists that refetch under you)."""
    last: Exception | None = None
    for _ in range(tries):
        try:
            el = clickable(driver, by, sel, timeout)
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            el.click()
            return
        except (StaleElementReferenceException, ElementClickInterceptedException, TimeoutException) as exc:
            last = exc
            time.sleep(0.6)
    if last:
        raise last


def click_button(driver: WebDriver, label: str, *, exact: bool = False, timeout: int = DEFAULT_TIMEOUT) -> WebElement:
    """Click a <button> (or role=button / link styled as one) by its visible text."""
    lit = _xpath_literal(label)
    if exact:
        xp = (
            f"//button[normalize-space()={lit}]"
            f" | //a[@role='button' and normalize-space()={lit}]"
        )
    else:
        xp = (
            f"//button[contains(normalize-space(.), {lit})]"
            f" | //a[@role='button' and contains(normalize-space(.), {lit})]"
            f" | //*[@role='menuitem' and contains(normalize-space(.), {lit})]"
        )
    el = clickable(driver, By.XPATH, xp, timeout)
    safe_click(driver, el)
    return el


def click_by_title(driver: WebDriver, title: str, *, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Click an icon-only control by its `title=` tooltip (e.g. the deal-health
    alert actions)."""
    lit = _xpath_literal(title)
    safe_click(driver, clickable(driver, By.XPATH, f"//*[@title={lit}]", timeout))


def press_escape(driver: WebDriver) -> None:
    from selenium.webdriver.common.action_chains import ActionChains

    ActionChains(driver).send_keys(Keys.ESCAPE).perform()
    time.sleep(0.5)


def close_dialog(driver: WebDriver) -> None:
    """Close whatever Radix dialog / sheet is open (ESC, then the × as a fallback)."""
    press_escape(driver)
    try:
        if driver.find_elements(By.CSS_SELECTOR, "[role='dialog']"):
            btn = driver.find_elements(By.XPATH, "//button[.//*[name()='svg'] and (contains(@class,'absolute') or @aria-label='Close' or normalize-space()='Close')]")
            if btn:
                safe_click(driver, btn[-1])
    except Exception:
        pass
    time.sleep(0.4)


def click_link(driver: WebDriver, text: str, *, timeout: int = DEFAULT_TIMEOUT) -> None:
    lit = _xpath_literal(text)
    xp = f"//a[contains(normalize-space(.), {lit})]"
    safe_click(driver, clickable(driver, By.XPATH, xp, timeout))


def click_dialog_button(driver: WebDriver, label: str, *, exact: bool = False, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Click a button *inside* the open Radix dialog / sheet — avoids matching a
    same-labelled button on the page behind the overlay."""
    lit = _xpath_literal(label)
    inner = f"normalize-space()={lit}" if exact else f"contains(normalize-space(.), {lit})"
    xp = f"({DIALOG}//button[{inner}])[last()]"
    click_locator(driver, By.XPATH, xp, timeout=timeout)


def click_text(driver: WebDriver, text: str, *, timeout: int = DEFAULT_TIMEOUT) -> None:
    lit = _xpath_literal(text)
    xp = f"(//*[contains(normalize-space(.), {lit})])[last()]"
    safe_click(driver, clickable(driver, By.XPATH, xp, timeout))


# ------------------------------------------------------------------- form inputs
def fill(el: WebElement, value: str) -> None:
    el.click()
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.DELETE)
    el.send_keys(str(value))


def fill_by_label(driver: WebDriver, label: str, value: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    lit = _xpath_literal(label)
    xp = (
        f"//label[contains(normalize-space(.), {lit})]/following::input[1]"
        f" | //label[contains(normalize-space(.), {lit})]/..//input"
    )
    fill(visible(driver, By.XPATH, xp, timeout), value)


def fill_placeholder(driver: WebDriver, placeholder_fragment: str, value: str, timeout: int = DEFAULT_TIMEOUT) -> None:
    lit = _xpath_literal(placeholder_fragment)
    xp = f"//input[contains(@placeholder, {lit})] | //textarea[contains(@placeholder, {lit})]"
    fill(visible(driver, By.XPATH, xp, timeout), value)


def set_bps(driver: WebDriver, el: WebElement, percent: float) -> None:
    """Set a `BpsInput` (human percent -> basis points on the wire). Types the
    value, then blurs with TAB so the field clamps and commits, then waits out the
    line-table's 600ms debounce."""
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    el.click()
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.COMMAND, "a")
    el.send_keys(Keys.DELETE)
    for ch in str(percent):
        el.send_keys(ch)
        time.sleep(0.05)
    el.send_keys(Keys.TAB)
    time.sleep(0.9)


def set_money(driver: WebDriver, el: WebElement, amount: float) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    el.click()
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.COMMAND, "a")
    el.send_keys(Keys.DELETE)
    el.send_keys(str(amount))
    el.send_keys(Keys.TAB)
    time.sleep(0.3)


def radix_select(driver: WebDriver, trigger: WebElement, option_text: str, *, timeout: int = DEFAULT_TIMEOUT) -> None:
    """Open a Radix <Select> and pick an option by (partial) visible text.

    Radix renders every option (no virtualisation) but inside a scrolling popper,
    so an off-screen option is present-but-not-clickable-at-point. We wait for
    *presence*, scroll it to centre, then click (JS-click as a fallback). The open
    step retries because the trigger click occasionally lands mid-animation.
    """
    lit = _xpath_literal(option_text)
    opt_xp = f"//*[@role='option'][contains(normalize-space(.), {lit})]"
    for attempt in range(3):
        safe_click(driver, trigger)
        try:
            wait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[role='listbox'],[role='option']"))
            )
            break
        except TimeoutException:
            if attempt == 2:
                raise
            time.sleep(0.5)
    option = present(driver, By.XPATH, opt_xp, timeout)
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", option)
    time.sleep(0.25)
    try:
        option.click()
    except Exception:
        driver.execute_script("arguments[0].click();", option)
    time.sleep(0.4)


def radix_select_by_label(driver: WebDriver, label: str, option_text: str, *, timeout: int = DEFAULT_TIMEOUT) -> None:
    lit = _xpath_literal(label)
    xp = (
        f"//label[contains(normalize-space(.), {lit})]/following::button[@role='combobox'][1]"
        f" | //*[contains(normalize-space(.), {lit})]/following::button[@role='combobox'][1]"
    )
    radix_select(driver, clickable(driver, By.XPATH, xp, timeout), option_text, timeout=timeout)


# -------------------------------------------------------------- caption overlay
_CAPTION_JS = r"""
(function(text, step){
  var id = 'df-caption-bar';
  var bar = document.getElementById(id);
  if(!bar){
    bar = document.createElement('div');
    bar.id = id;
    bar.style.cssText = [
      'position:fixed','left:50%','bottom:24px','transform:translateX(-50%)',
      'z-index:2147483647','max-width:82vw','padding:12px 20px',
      'background:rgba(15,23,42,0.94)','color:#f8fafc','font:600 16px/1.45 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif',
      'border-radius:12px','box-shadow:0 8px 30px rgba(0,0,0,0.35)','pointer-events:none',
      'letter-spacing:0.01em','text-align:center','border:1px solid rgba(148,163,184,0.25)'
    ].join(';');
    document.body.appendChild(bar);
  }
  var prefix = step ? ('<span style="opacity:.6;font-weight:700;margin-right:8px">'+step+'</span>') : '';
  bar.innerHTML = prefix + text;
  bar.style.opacity = '1';
})(arguments[0], arguments[1]);
"""

_CAPTION_HIDE_JS = "var b=document.getElementById('df-caption-bar'); if(b){b.style.opacity='0';}"


class Narrator:
    """Drives the on-screen caption bar across one or more browsers and paces the
    run. `beat()` sets the caption then sleeps `seconds * DF_SLOW`."""

    def __init__(self, *drivers: WebDriver, title: str = "") -> None:
        self.drivers = list(drivers)
        self.title = title
        self._step = 0

    def add(self, *drivers: WebDriver) -> None:
        self.drivers.extend(d for d in drivers if d not in self.drivers)

    def caption(self, text: str, *, step: bool = True) -> None:
        label = ""
        if step:
            self._step += 1
            label = f"{self._step:02d}"
        for d in self.drivers:
            try:
                d.execute_script(_CAPTION_JS, text, label)
            except Exception:
                pass
        stamp = f"[{self.title}] " if self.title else ""
        print(f"{stamp}{('· ' + label + '  ') if label else ''}{text}", flush=True)

    def beat(self, text: str, seconds: float = 2.4, *, step: bool = True) -> None:
        self.caption(text, step=step)
        time.sleep(max(0.0, seconds) * SLOW)

    def hold(self, seconds: float = 2.0) -> None:
        time.sleep(max(0.0, seconds) * SLOW)

    def clear(self) -> None:
        for d in self.drivers:
            try:
                d.execute_script(_CAPTION_HIDE_JS)
            except Exception:
                pass


# --------------------------------------------------------------------- sessions
def open_app(driver: WebDriver, path: str = "/") -> None:
    if not path.startswith("/"):
        path = "/" + path
    driver.get(BASE_URL + path)


def login(driver: WebDriver, creds: tuple[str, str], *, expect: str = "dashboard") -> None:
    """UI login (visible, demo-authentic). `expect` is 'dashboard' for internal
    users or 'portal' for a customer."""
    email, password = creds
    open_app(driver, "/login")
    fill(visible(driver, By.CSS_SELECTOR, "input[type='email']"), email)
    fill(visible(driver, By.CSS_SELECTOR, "input[type='password']"), password)
    click_button(driver, "Sign in")
    wait_url_contains(driver, "/portal" if expect == "portal" else "/dashboard", timeout=20)
    time.sleep(0.8)


def logout(driver: WebDriver) -> None:
    try:
        driver.execute_script(
            "localStorage.removeItem('access_token');localStorage.removeItem('refresh_token');"
        )
    except Exception:
        pass
    open_app(driver, "/login")
    time.sleep(0.5)


def redeem_magic_link(driver: WebDriver, url_or_token: str) -> None:
    """Open a portal magic link (full URL, or just the token)."""
    if url_or_token.startswith("http"):
        driver.get(url_or_token)
    else:
        open_app(driver, f"/portal/access/{url_or_token}")
    wait_url_contains(driver, "/portal/quotations", timeout=20)
    time.sleep(0.8)


# ----------------------------------------------------------------- quote builder
DIALOG = "//*[@role='dialog' or @role='alertdialog']"


def create_quotation(driver: WebDriver, customer_name: str) -> str:
    """From anywhere, open Workspace → Quotations, start a new quote for
    `customer_name`, and return the quotation id from the URL."""
    open_app(driver, "/workspace/quotations")
    click_button(driver, "New quotation")
    # Scope to the dialog — the quotations list has its own status <Select>.
    trigger = clickable(driver, By.XPATH, f"{DIALOG}//button[@role='combobox']")
    radix_select(driver, trigger, customer_name)
    click_button(driver, "Create", exact=True)
    wait(driver, 20).until(lambda d: "/workspace/quotations/" in d.current_url and d.current_url.rstrip("/").split("/")[-1].isdigit())
    return driver.current_url.rstrip("/").split("/")[-1]


def current_quote_reference(driver: WebDriver) -> str:
    """The 'QT-YYYY-NNNNNN' shown in the builder header."""
    el = visible(driver, By.XPATH, "//h1[starts-with(normalize-space(.), 'QT-')]")
    return el.text.strip()


def add_catalogue_product(driver: WebDriver, name: str) -> None:
    """Click a product in the builder's left catalogue panel."""
    search = visible(driver, By.CSS_SELECTOR, "input[placeholder^='Search catalogue']")
    fill(search, name)
    time.sleep(1.0)
    lit = _xpath_literal(name)
    xp = f"//button[.//p[contains(normalize-space(.), {lit})]]"
    safe_click(driver, clickable(driver, By.XPATH, xp))
    time.sleep(1.2)


def line_row(driver: WebDriver, product_name: str) -> WebElement:
    lit = _xpath_literal(product_name)
    return visible(driver, By.XPATH, f"//tr[.//p[contains(normalize-space(.), {lit})]]")


def set_line_discount(driver: WebDriver, product_name: str, percent: float) -> None:
    row = line_row(driver, product_name)
    inp = row.find_element(By.XPATH, ".//input[@inputmode='decimal']")
    set_bps(driver, inp, percent)


def open_decision_trace(driver: WebDriver) -> None:
    click_button(driver, "Why?")
    wait_for_text(driver, "risk contribution", timeout=15)
    time.sleep(1.0)


def set_order_discount(driver: WebDriver, percent: float) -> None:
    """Set the builder's order-level discount and commit it (which re-runs the
    engine / re-gates approval)."""
    inp = visible(driver, By.CSS_SELECTOR, "input[aria-label='Order-level discount percentage']")
    set_bps(driver, inp, percent)
    click_button(driver, "Apply order discount")
    time.sleep(1.5)


def submit_for_approval(driver: WebDriver) -> None:
    click_button(driver, "Submit for Approval")
    click_button(driver, "Submit", exact=True)
    time.sleep(1.5)


def send_to_customer(driver: WebDriver) -> None:
    click_button(driver, "Send to Customer")
    click_button(driver, "Send", exact=True)
    time.sleep(1.5)


# ------------------------------------------------------------------- approvals
def open_first_approval(driver: WebDriver, *, reference: str | None = None) -> None:
    open_app(driver, "/approvals")
    wait_for_text(driver, "Waiting", timeout=15)
    time.sleep(1.0)
    if reference:
        xp = f"//table//tbody//tr[.//*[contains(normalize-space(.), {_xpath_literal(reference)})]]"
    else:
        xp = "//table//tbody//tr[td]"
    click_locator(driver, By.XPATH, xp)
    wait_url_contains(driver, "/approvals/")
    time.sleep(1.2)


def approve_current(driver: WebDriver) -> None:
    click_button(driver, "Approve")
    click_button(driver, "Approve", exact=True)
    time.sleep(1.5)


def reject_current(driver: WebDriver, reason: str) -> None:
    click_button(driver, "Reject")
    fill_by_label(driver, "Reason", reason)
    click_button(driver, "Reject", exact=True)
    time.sleep(1.2)


def return_for_revision(driver: WebDriver, reason: str) -> None:
    click_button(driver, "Return for revision")
    fill_by_label(driver, "Reason", reason)
    click_button(driver, "Return", exact=True)
    time.sleep(1.2)


def each(drivers: Iterable[WebDriver], fn) -> None:
    for d in drivers:
        fn(d)
