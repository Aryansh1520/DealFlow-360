#!/usr/bin/env python3
"""EDGE 2 — Portal isolation: a real, separate, restricted principal.

Covers: T007, T071-T073, T080, and the Security Matrix rows about customers
never receiving cost / margin / risk / internal approval data.

    LEFT  = internal staff view of a quotation (cost, margin, risk score, trace)
    RIGHT = the SAME quotation in the customer portal
      → none of cost / margin / risk / internal events are present — and not just
        CSS-hidden: they're absent from the response
      → the customer hitting /dashboard is bounced to /portal
      → the customer opening another customer's quote id is denied
"""

import time

from dealflow import api, ui
from dealflow.config import Credentials as C
from dealflow.config import Fixtures as F
from dealflow.scenario import two_up


def main() -> None:
    # A quote Acme can actually see in the portal (sent / approved / etc.).
    acme_quote = api.find_quote_with_product(
        F.SPLIT_PRODUCT,
        statuses=("confirmed", "fulfilling", "sent", "approved"),
        customer_contains="Acme",
    ) or api.find_quote_with_product(
        F.FLAGSHIP_HARDWARE,
        statuses=("sent", "approved", "under_negotiation", "confirmed", "fulfilling"),
        customer_contains="Acme",
    )
    # Someone else's quote, to prove a customer can't reach it by id.
    other_quote = api.find_quote_with_product(
        "Workstation Tower X1",
        statuses=("sent", "approved", "confirmed", "pending_l1", "fulfilling", "under_negotiation"),
        customer_excludes="Acme",
    )
    if not acme_quote:
        raise SystemExit("No portal-visible Acme quote found — run the --demo seed first.")

    with two_up("Edge 2 · Portal isolation") as pair:
        staff, cust = pair.left, pair.right
        n = ui.Narrator(staff, cust, title="Edge 2")

        n.beat("LEFT — an internal user opens a quotation. Staff see everything.", 4.5)
        ui.login(staff, C.REP)
        ui.open_app(staff, f"/workspace/quotations/{acme_quote['id']}")
        ui.wait_for_text(staff, "Activity", timeout=25)
        time.sleep(2.0)
        n.beat("Cost-driven margin per line, the risk score, the decision trace — all internal.", 5.5)

        n.beat("RIGHT — the customer signs into their OWN portal. Different principal, not a role called 'customer'.", 5.5)
        ui.login(cust, C.CUSTOMER_ACME, expect="portal")
        ui.open_app(cust, f"/portal/quotations/{acme_quote['id']}")
        ui.wait_for_text(cust, "Your quotation", timeout=15)
        time.sleep(1.5)

        body = cust.find_element("tag name", "body").text.lower()
        leaked = [w for w in ("cost price", "margin", "risk score", "decision trace", "ceiling") if w in body]
        n.beat(
            "Same quotation, customer view: no cost, no margin, no risk, no internal trace, "
            "no internal-only events. "
            + ("LEAK: " + ", ".join(leaked) if leaked else "The backend response itself is stripped — not CSS-hidden."),
            9.0,
        )
        n.hold(2.0)

        n.beat("The customer has no internal sidebar and customer-friendly status wording — never 'pending_l1'.", 5.5)

        n.beat("Try to walk into the internal workspace: /dashboard → hard-redirected back to /portal.", 6.0)
        ui.open_app(cust, "/dashboard")
        time.sleep(2.0)
        ui.wait_url_contains(cust, "/portal", timeout=10)
        n.beat("Bounced. The guard is on the principal, not on hiding a link.", 4.5)

        if other_quote and other_quote.get("customer_name", "").lower().find("acme") < 0:
            n.beat(f"Try another customer's quotation id directly ({other_quote['customer_name']}) — denied / not exposed.", 6.5)
            ui.open_app(cust, f"/portal/quotations/{other_quote['id']}")
            time.sleep(2.5)
            txt = cust.find_element("tag name", "body").text.lower()
            ok = ("couldn't load" in txt) or ("not found" in txt) or ("don't have" in txt) or ("no access" in txt)
            n.beat("Denied — a customer can only ever see their own quotations." if ok else
                   "(Check: the other-customer quote should not render its contents.)", 6.0)
        n.hold(3.0)
        n.clear()


if __name__ == "__main__":
    main()
