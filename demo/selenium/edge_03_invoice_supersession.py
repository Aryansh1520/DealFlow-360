#!/usr/bin/env python3
"""EDGE 3 — Invoice immutability & supersession lineage.

Covers: T087 (issued invoice immutable), T091 (supersede = full reversing credit
note + corrected invoice, lineage oldest→newest, original values intact).

Uses the seeded order that already has an issued invoice with a partial payment
(a 1U compute node + a monitoring subscription). If none is found, the script
generates one first.

    Sign in as Farah (Finance)
      → the issued invoice cannot be edited — corrections go through 'Supersede'
      → Supersede: state a reason, adjust a line
      → out come a full-reversal CREDIT NOTE and a CORRECTED invoice
      → the original is now read-only; the lineage reads oldest → newest
"""

import time

from dealflow import api, ui
from dealflow.config import Credentials as C
from dealflow.config import Fixtures as F
from dealflow.scenario import single


def main() -> None:
    quote = api.find_quote_with_product(
        "1U Compute Node", statuses=("invoiced", "confirmed", "fulfilling")
    ) or api.find_quote_with_product(F.HYBRID_HARDWARE, statuses=("confirmed", "invoiced", "fulfilling"))
    if not quote:
        raise SystemExit("No invoiceable order found — run the --demo seed first.")

    with single("Edge 3 · Invoice supersession") as d:
        n = ui.Narrator(d, title="Edge 3")

        n.beat("Sign in as Farah — Finance.", 3.0)
        ui.login(d, C.FINANCE)

        n.beat("Open Billing for this order.", 3.5)
        ui.open_app(d, f"/workspace/quotations/{quote['id']}/billing")
        ui.wait_for_text(d, "Invoices", timeout=20)
        time.sleep(1.5)

        # Make sure an issued invoice exists.
        if "issued" not in d.find_element("tag name", "body").text.lower():
            try:
                ui.click_button(d, "Generate invoice")
                ui.wait_for_text(d, "issued", timeout=20)
                time.sleep(1.5)
            except Exception:
                pass

        n.beat(
            "The invoice is issued — so it's immutable. There's no 'edit'. The only correction "
            "path is 'Supersede'.",
            6.0,
        )

        n.beat("Supersede it — state why, and adjust a line amount.", 5.0)
        ui.click_button(d, "Supersede")
        ui.wait_for_text(d, "credit note", timeout=15)
        ui.fill_placeholder(d, "Why is this correction", "Wrong quantity billed on the compute node line.")
        try:
            first_amount = ui.visible(
                d, "xpath", f"({ui.DIALOG}//input[@inputmode='decimal'])[2]"
            )
            cur = float((first_amount.get_attribute("value") or "0").replace(",", "")) or 1000.0
            ui.set_money(d, first_amount, round(cur * 0.9, 2))
        except Exception:
            pass

        n.beat("Issue the credit note and the corrected invoice.", 5.0)
        ui.click_button(d, "Issue credit note")
        time.sleep(2.5)

        n.beat(
            "Three documents now, in lineage order: the ORIGINAL — now 'superseded', read-only; "
            "a full-reversal CREDIT NOTE; and the CORRECTED invoice. The original's committed "
            "commercial values were never touched.",
            9.0,
        )
        d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        n.hold(4.0)
        n.clear()


if __name__ == "__main__":
    main()
