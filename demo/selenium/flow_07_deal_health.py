#!/usr/bin/env python3
"""FLOW 7 — Deal health & anomaly detection.

Covers: T092 (stalled deal), T093 (discount anomaly — explained, not generic),
T094 (no anomaly below min sample size), T095 (delivery slippage),
T096 (nudge / acknowledge), T097 (live dashboard).

The seed lays down exactly these:
  * Beta Industries — approved & sent, then untouched 9 days   -> stalled_deal
  * Helios Energy   — rep2 (loose discounter) confirmed a ~22% order -> discount_anomaly
  * Acme (SWT-24P)  — backorder past its restock date          -> delivery_slippage
  * rep3 has only 3 historical quotes                           -> NO anomaly (too little data)
"""

import time

from dealflow import ui
from dealflow.config import Credentials as C
from dealflow.scenario import single


def main() -> None:
    with single("Flow 7 · Deal health") as d:
        n = ui.Narrator(d, title="Flow 7")

        n.beat("Sign in as Manav — a Sales Manager watching the whole book of deals.", 3.5)
        ui.login(d, C.MANAGER)

        n.beat("Deal Health. A KPI strip — open deals, value in approval, stalled count, open alerts — then every deal in one table.", 6.0)
        ui.open_app(d, "/dashboard/deal-health")
        ui.wait_for_text(d, "Open deals", timeout=20)
        time.sleep(2.5)

        n.beat("Open the alerts. Each one is grouped by type and EXPLAINS itself.", 4.5)
        ui.click_button(d, "Alerts")
        ui.wait_for_text(d, "vs", timeout=15)
        time.sleep(1.5)

        n.beat("A stalled deal: Beta Industries has gone quiet — sent, then no activity for over a week.", 5.5)
        n.beat(
            "A discount anomaly — and it reads the actual number, not a vague '⚠ anomaly': "
            "'X% discount vs this rep's Y% average across N quotes, Z sigma out.' "
            "The explanation IS the feature.",
            8.0,
        )
        n.beat(
            "Delivery slippage: a backorder past its expected restock date. And note what's "
            "NOT here — the rep with only 3 quotes raises no anomaly. Too small a sample to be "
            "statistically valid.",
            8.0,
        )
        n.hold(2.0)

        n.beat("Every alert links straight to its quotation — click the reference.", 5.0)
        try:
            ui.click_locator(d, "xpath", f"({ui.DIALOG}//a[starts-with(normalize-space(.),'QT-')])[1]")
            ui.wait_url_contains(d, "/workspace/quotations/", timeout=10)
            n.beat("Opened the exact deal behind the alert.", 4.0)
            n.hold(2.0)
            d.back()
            time.sleep(2.0)
            ui.click_button(d, "Alerts")
            time.sleep(1.5)
        except Exception:
            n.caption("(Alert → quote navigation — continuing.)")

        n.beat("Nudge the owning rep on one alert; acknowledge another. Both persist as events — the dashboard updates live, no reload.", 7.0)
        try:
            ui.click_by_title(d, "Nudge the owning rep")
            time.sleep(1.5)
            ui.click_by_title(d, "Acknowledge")
            time.sleep(1.5)
            n.beat("Acknowledged alerts dim and drop out of the open count. The nudge is recorded against the rep.", 6.0)
        except Exception:
            n.caption("(Nudge / acknowledge are the two icon buttons on the right of each alert row.)")
        n.hold(3.0)
        n.clear()


if __name__ == "__main__":
    main()
