#!/usr/bin/env python3
"""FLOW 2 — Live two-window negotiation (the "demo money shot").

Covers: T070-T077 (portal), T078-T081 (SSE), T110 (full rep + customer flow).

Two independent browser sessions, side by side:

    LEFT  = Riya (Sales Rep)          RIGHT = Acme Corp (customer portal)

    Rep sends an approved quote  →  customer counters for a bigger discount
      →  rep's screen updates WITHOUT a refresh
      →  rep reviews the counter into the order discount and applies it
      →  the decision engine re-runs and the quote RE-ENTERS approval on its own
      →  manager approves  →  customer sees the truthful current status
"""

import time

from dealflow import ui
from dealflow.config import Credentials as C
from dealflow.config import Fixtures as F
from dealflow.scenario import two_up


def main() -> None:
    with two_up("Flow 2 · Live negotiation") as pair:
        rep, cust = pair.left, pair.right
        n = ui.Narrator(rep, cust, title="Flow 2")

        # ---- LEFT: rep prepares and sends a clean, in-policy quote -------------
        n.beat("LEFT window — Riya signs in as the Sales Rep.", 3.5)
        ui.login(rep, C.REP)

        n.beat("She builds a straightforward quote for Acme Corp — no discounts, well within policy.", 3.5)
        qid = ui.create_quotation(rep, F.ACME)
        ref = ui.current_quote_reference(rep)
        ui.add_catalogue_product(rep, F.FLAGSHIP_HARDWARE)
        ui.add_catalogue_product(rep, F.FLAGSHIP_SERVICE)

        n.beat("Submit — it's inside every ceiling, so the engine auto-approves it. No queue.", 4.5)
        ui.submit_for_approval(rep)

        n.beat("Re-open the approved quote and send it to the customer's portal.", 4.0)
        ui.open_app(rep, f"/workspace/quotations/{qid}")
        ui.send_to_customer(rep)
        n.caption("The 'Live' indicator top-right is connected — customer actions will arrive with no refresh.")
        n.hold(2.0)

        # ---- RIGHT: customer opens the portal ---------------------------------
        n.beat("RIGHT window — the customer signs into their own portal. Separate principal, restricted view.", 4.5)
        ui.login(cust, C.CUSTOMER_ACME, expect="portal")

        n.beat("They open the quotation Riya just sent. No cost, no margin, no risk score — customer language only.", 5.0)
        ui.open_app(cust, "/portal/quotations")
        ui.click_locator(cust, "xpath", f"//a[.//*[contains(normalize-space(.), {ui._xpath_literal(ref)})]]")
        ui.wait_for_text(cust, "Your quotation", timeout=15)
        n.hold(2.0)

        # ---- RIGHT: customer sends a counter-offer ---------------------------
        n.beat("The customer asks for an overall 18% discount and leaves a note.", 4.5)
        bps = ui.visible(cust, "xpath", "//input[@inputmode='decimal']")
        ui.set_bps(cust, bps, 18)
        ui.fill_placeholder(cust, "note for your rep", "Budget approved for 18% — can you meet us there?")
        ui.click_button(cust, "Send counter-offer")
        n.beat("Sent. Nothing on the quote changes yet — it's a request, not an edit.", 4.0)

        # ---- LEFT: rep sees it live, no refresh -----------------------------
        n.caption("Watch the LEFT window — no one touched it.")
        ui.wait_for_text(rep, "requested a", timeout=30)
        n.beat("The counter-offer just appeared on the rep's screen. No refresh, no polling — live over SSE.", 6.0)

        n.beat("Riya reviews the 18% into the order-discount field — she confirms it herself, it's never auto-applied.", 5.0)
        ui.click_button(rep, "Review 18")
        time.sleep(1.0)
        ui.click_button(rep, "Apply order discount")
        n.hold(2.0)

        # ---- The self-governing bit ---------------------------------------
        ui.wait_for_text(rep, "Pending L1", timeout=20)
        n.beat(
            "18% blows past the 10% Services ceiling — so the engine re-ran and the quote "
            "RE-ENTERED approval on its own. The rep did not route it.",
            6.5,
        )

        # ---- Manager approves (reuse LEFT window) -------------------------
        n.beat("The manager signs in and sees it waiting in the L1 queue.", 4.0)
        ui.logout(rep)
        ui.login(rep, C.MANAGER)
        ui.open_first_approval(rep, reference=ref)
        n.beat("Same decision trace the rep saw. Approve.", 4.0)
        ui.approve_current(rep)

        # ---- RIGHT: customer sees the truthful status -------------------
        n.beat("Back on the customer's side — refresh. The status is truthful: approved, ready to confirm. Never a false 'Confirmed'.", 6.0)
        ui.open_app(cust, "/portal/quotations")
        time.sleep(1.5)
        ui.click_locator(cust, "xpath", f"//a[.//*[contains(normalize-space(.), {ui._xpath_literal(ref)})]]")
        ui.wait_for_text(cust, "Your quotation", timeout=15)
        n.hold(4.0)
        n.clear()


if __name__ == "__main__":
    main()
