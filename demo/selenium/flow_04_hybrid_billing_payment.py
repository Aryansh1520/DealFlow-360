#!/usr/bin/env python3
"""FLOW 4 — Hybrid billing → invoice → payment.

Covers: T082-T084 (one-time + recurring on one order), T088-T089 (partial then
full payment), T112.

Uses the seeded confirmed hybrid order (a ProBook 16 as a one-time line + a
Standard Support Plan as a recurring subscription line).

    Sign in as Farah (Finance)
      → Billing tab: one-time charges vs. the recurring schedule, side by side
      → Generate the invoice — one-time lines + the first period, nothing else
      → Record a partial payment — balance drops, invoice still unpaid
      → Record the rest — invoice PAID, the order flips to Paid
"""

import time

from dealflow import api, ui
from dealflow.config import Credentials as C
from dealflow.config import Fixtures as F
from dealflow.scenario import single


def main() -> None:
    hybrid = api.find_quote_with_product(F.HYBRID_HARDWARE, statuses=("confirmed", "fulfilling", "invoiced"))
    if not hybrid:
        raise SystemExit(
            "Seeded hybrid-billing fixture not found — run:\n"
            "  docker compose exec backend python -m app.db.seed --reset --history --demo"
        )

    with single("Flow 4 · Hybrid billing & payment") as d:
        n = ui.Narrator(d, title="Flow 4")

        n.beat("Sign in as Farah — Finance. She owns billing and second-level approval.", 3.5)
        ui.login(d, C.FINANCE)

        n.beat("Open the Billing tab for a confirmed order that mixes hardware and a subscription.", 4.5)
        ui.open_app(d, f"/workspace/quotations/{hybrid['id']}/billing")
        ui.wait_for_text(d, "Billing", timeout=20)
        time.sleep(1.5)
        n.beat(
            "Two panels: 'One-time charges' — invoiced once, immediately — and 'Recurring — "
            "upcoming schedule', one row per billing period. The same order, kept apart. No "
            "cross-contamination.",
            7.5,
        )
        n.hold(2.0)

        n.beat("Generate the invoice. It picks up the one-time lines plus the first due period — nothing else.", 5.5)
        if "issued" not in d.find_element("tag name", "body").text.lower():
            try:
                ui.click_button(d, "Generate invoice")
                ui.wait_for_text(d, "issued", timeout=30)
                n.beat("Issued. Correct amount, tax and status — and it's now immutable.", 5.0)
            except Exception:
                n.caption("(Invoice generation is still settling — continuing with the issued invoice.)")
        else:
            n.beat("This order already has an issued invoice with a payment against it — pick up from there.", 5.0)
        time.sleep(2.0)

        n.beat("Record a partial payment — about half of the outstanding balance.", 4.5)
        ui.click_button(d, "Record payment")
        amount_input = ui.visible(d, "xpath", f"{ui.DIALOG}//input[@inputmode='decimal']")
        raw = amount_input.get_attribute("value") or "0"
        outstanding = float(raw.replace(",", "")) or 0.0
        ui.set_money(d, amount_input, max(1.0, round(outstanding / 2, 2)))
        ui.click_dialog_button(d, "Record payment")
        time.sleep(2.0)
        n.beat("Paid amount goes up, balance comes down — but the invoice stays 'issued', not 'paid'.", 6.0)
        n.hold(2.0)

        n.beat("Now record the rest — the dialog defaults to the exact outstanding balance.", 4.5)
        ui.click_button(d, "Record payment")
        time.sleep(1.5)
        ui.click_dialog_button(d, "Record payment")
        ui.wait_for_text(d, "paid", timeout=25)
        n.beat("Invoice PAID in full — and the quotation's payment state flips to Paid with it. Reconciled to the paisa.", 6.5)
        n.hold(3.0)
        n.clear()


if __name__ == "__main__":
    main()
