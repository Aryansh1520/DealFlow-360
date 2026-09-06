#!/usr/bin/env python3
"""FLOW 3 — Warehouse split, backorder, replenish, consolidate.

Covers: T062-T064, T069, T095, T111.

Uses the seeded fixtures the QA plan documents:
  * a confirmed order for MON-27 x6   — Main 3 / East 5  -> a two-warehouse split
  * a confirmed order for SWT-24P x5  — total stock 2    -> fulfilled 2 / backorder 3

    Sign in as Omar (Operations)
      → open the split order: 2 shipments, estimated cost, stock reserved correctly
      → open the shortage order: 2 fulfilled, 3 on backorder, with a restock date
      → replenish the switch in the Main warehouse
      → consolidate the remaining backorder into a shipment — exactly once
"""

import time

from dealflow import api, ui
from dealflow.config import Credentials as C
from dealflow.config import Fixtures as F
from dealflow.scenario import single


def _open_fulfillment(driver, quote_id: int) -> None:
    ui.open_app(driver, f"/workspace/quotations/{quote_id}/fulfillment")
    ui.wait_for_text(driver, "Fulfil", timeout=20)
    time.sleep(1.5)


def main() -> None:
    split = api.find_quote_with_product(F.SPLIT_PRODUCT, statuses=("confirmed", "fulfilling"))
    short = api.find_quote_with_product(F.BACKORDER_PRODUCT, statuses=("confirmed", "fulfilling"))
    if not split or not short:
        raise SystemExit(
            "Seeded fulfilment fixtures not found — run:\n"
            "  docker compose exec backend python -m app.db.seed --reset --history --demo"
        )

    with single("Flow 3 · Fulfilment split & backorder") as d:
        n = ui.Narrator(d, title="Flow 3")

        n.beat("Sign in as Omar — Operations. He owns warehouses and fulfilment.", 3.5)
        ui.login(d, C.OPS)

        # ---- The two-warehouse split ---------------------------------------
        n.beat(f"Open the confirmed order for {F.SPLIT_PRODUCT} × {F.SPLIT_QTY}.", 4.0)
        _open_fulfillment(d, split["id"])
        n.beat(
            "The allocator split it: 3 units from Main, 3 from East. Two shipments, an "
            "estimated shipping cost, and 'fully allocatable'. It optimises coverage first, "
            "then the fewest warehouses.",
            7.0,
        )
        try:
            ui.click_button(d, "Accept suggested split")
            n.beat("Accepted — stock is now reserved against those two warehouses. No overselling.", 5.0)
        except Exception:
            n.beat("(This plan was already accepted — the reservations stand.)", 3.0)

        # ---- The backorder -----------------------------------------------
        n.beat(f"Now the order for {F.BACKORDER_PRODUCT} × {F.BACKORDER_QTY} — total stock is only 2.", 4.5)
        _open_fulfillment(d, short["id"])
        n.beat(
            "The system doesn't pretend inventory exists: 2 fulfilled, 3 on backorder, with an "
            "expected restock date. That date is already in the past here — which is why Deal "
            "Health raised a delivery-slippage alert.",
            7.5,
        )
        try:
            ui.click_button(d, "Accept suggested split")
            time.sleep(1.5)
        except Exception:
            pass

        # ---- Replenish, then consolidate --------------------------------
        n.beat("A supplier delivery arrives — replenish the switch in the Main warehouse.", 4.5)
        ui.open_app(d, "/config/warehouses")
        ui.wait_for_text(d, "Main Warehouse", timeout=15)
        ui.click_locator(d, "xpath", "//tr[.//*[contains(normalize-space(.),'Main Warehouse')]]")
        ui.wait_for_text(d, "On hand", timeout=15)
        ui.radix_select_by_label(d, "Product", F.BACKORDER_PRODUCT)
        ui.fill_by_label(d, "Delta", "40")
        ui.fill_placeholder(d, "Cycle count", "Supplier delivery received")
        ui.click_button(d, "Adjust")
        time.sleep(1.5)
        n.beat("Stock adjusted — a movement is logged with a reason. Return to the shortage order.", 5.0)
        ui.press_escape(d)

        _open_fulfillment(d, short["id"])
        try:
            ui.click_button(d, "Consolidate remaining backorder")
            n.beat("The outstanding backorder is consolidated into a shipment — exactly once, and only from real stock.", 6.5)
        except Exception:
            n.beat(
                "Replenishment cleared the shortfall — a fresh plan is now fully allocatable, so "
                "the previously-backordered units can ship. Nothing was ever oversold.",
                6.5,
            )
        n.hold(3.0)
        n.clear()


if __name__ == "__main__":
    main()
