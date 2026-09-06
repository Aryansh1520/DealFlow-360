"""Tiny read-only backend client — used by scripts only to *locate* a seeded
fixture (e.g. "a confirmed quote with a two-warehouse split") so the UI part of
the script can start from a known place. No third-party deps: stdlib urllib.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import API_URL, Credentials


def _request(method: str, path: str, token: str | None = None, body: dict | None = None) -> Any:
    url = API_URL + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:  # surface the backend's message
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} -> {exc.code}: {detail}") from None
    # The API wraps most successful bodies in {success, message, data}.
    if isinstance(payload, dict) and "data" in payload and set(payload) <= {"success", "message", "data"}:
        return payload["data"]
    return payload


def token_for(creds: tuple[str, str]) -> str:
    email, password = creds
    data = _request("POST", "/auth/login", body={"email": email, "password": password})
    return data["access_token"]


def quotations(token: str, *, status: str | None = None, q: str | None = None, page_size: int = 50) -> list[dict]:
    query = f"?page=1&page_size={page_size}"
    if status:
        query += f"&status={status}"
    if q:
        query += f"&q={urllib.parse.quote(q)}"
    return _request("GET", "/quotations" + query, token).get("items", [])


def find_quotation(
    creds: tuple[str, str] = Credentials.REP,
    *,
    status: str | None = None,
    customer_contains: str | None = None,
    product_hint: str | None = None,
) -> dict | None:
    """Return the newest quotation matching the filters, or None."""
    token = token_for(creds)
    items = quotations(token, status=status)
    for item in items:
        if customer_contains and customer_contains.lower() not in (item.get("customer_name") or "").lower():
            continue
        return item
    return None


def quotation_detail(token: str, quote_id: int) -> dict:
    return _request("GET", f"/quotations/{quote_id}", token)


def find_quote_with_product(
    product_name: str,
    *,
    statuses: tuple[str, ...] = ("confirmed", "fulfilling", "approved", "sent"),
    customer_contains: str | None = None,
    customer_excludes: str | None = None,
    creds: tuple[str, str] = Credentials.REP,
) -> dict | None:
    """Newest quotation in one of `statuses` that has a line whose product name
    contains `product_name` (and, optionally, matches / excludes a customer name).
    Returns the full detail dict (with `lines`)."""
    token = token_for(creds)
    for status in statuses:
        for item in quotations(token, status=status, page_size=50):
            name = (item.get("customer_name") or "").lower()
            if customer_contains and customer_contains.lower() not in name:
                continue
            if customer_excludes and customer_excludes.lower() in name:
                continue
            detail = quotation_detail(token, item["id"])
            for line in detail.get("lines", []):
                if product_name.lower() in (line.get("product_name") or "").lower():
                    return detail
    return None


def health() -> bool:
    try:
        with urllib.request.urlopen(API_URL.replace("/api/v1", "") + "/health", timeout=8) as resp:
            return resp.status == 200
    except Exception:
        return False
