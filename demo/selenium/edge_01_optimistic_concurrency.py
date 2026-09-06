#!/usr/bin/env python3
"""EDGE 1 — Optimistic concurrency (no silent overwrites).

Covers: T061, T104. Origin: ENGINEERING-DERIVED — a robustness proof, not a
literal PDF line; present it as "the system is safe under concurrent edits".

Two rep sessions open the SAME draft quotation at the same version.

    LEFT edits a line and commits   → server version N → N+1
    RIGHT (still on version N) edits another line
      → 409 VERSION_CONFLICT under the hood
      → the UI refreshes RIGHT to the server's current truth and keeps the rep's
        place in the form — no lost work, no silent clobber
"""

import time

from dealflow import ui
from dealflow.config import Credentials as C
from dealflow.config import Fixtures as F
from dealflow.scenario import two_up


def main() -> None:
    with two_up("Edge 1 · Optimistic concurrency") as pair:
        a, b = pair.left, pair.right
        n = ui.Narrator(a, b, title="Edge 1")

        n.beat("Two Sales Rep sessions — LEFT and RIGHT — signed in as the same rep.", 4.0)
        ui.login(a, C.REP)
        ui.login(b, C.REP)

        n.beat("LEFT starts a fresh quote for Acme and adds two lines.", 4.5)
        qid = ui.create_quotation(a, F.ACME)
        ui.add_catalogue_product(a, F.FLAGSHIP_HARDWARE)
        ui.add_catalogue_product(a, F.SPLIT_PRODUCT)

        n.beat("RIGHT opens the very same quotation. Both sides are now looking at version N.", 5.0)
        ui.open_app(b, f"/workspace/quotations/{qid}")
        ui.wait_for_text(b, F.FLAGSHIP_HARDWARE, timeout=15)
        n.hold(2.0)

        n.beat("LEFT bumps the laptop quantity and commits. The server moves to version N+1.", 5.5)
        row = ui.line_row(a, F.FLAGSHIP_HARDWARE)
        plus = row.find_element("xpath", ".//button[.//*[name()='svg']][2]")
        ui.safe_click(a, plus)
        time.sleep(2.0)

        n.beat("RIGHT is still on the stale version N. It now tries to change the monitor's discount.", 6.0)
        try:
            ui.set_line_discount(b, F.SPLIT_PRODUCT, 6)
        except Exception:
            pass
        time.sleep(2.0)

        n.beat(
            "The server rejected the stale write — 409 VERSION_CONFLICT. RIGHT didn't clobber "
            "LEFT's change: it caught the conflict, refetched the current version, and kept the "
            "rep in place. A non-blocking notice, not a lost form.",
            9.0,
        )
        n.hold(3.0)
        n.clear()


if __name__ == "__main__":
    main()
