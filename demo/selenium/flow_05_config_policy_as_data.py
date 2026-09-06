#!/usr/bin/env python3
"""FLOW 5 — Backend configuration & "policy is data, not code".

Covers: T008-T015 (config CRUD, tier + category ceilings), T012/T016 (policy
versioning + snapshot), part of the PDF 8-step quick-test setup.

    Sign in as the org admin (full config access)
      → Products: a real catalogue, variants, cost price visible to staff
      → Price Lists: per-tier overrides
      → Discount Policy: the live version — Bronze 5 / Silver 10 / Gold 15,
        Services capped at 10
      → Edit as a NEW draft: raise the Services category ceiling 10% → 20%
      → the old version is untouched; activate the new one
      → future quotes evaluate against v-new; in-flight quotes keep their snapshot
"""

import time

from dealflow import ui
from dealflow.config import Credentials as C
from dealflow.scenario import single


def main() -> None:
    with single("Flow 5 · Config & policy-as-data") as d:
        n = ui.Narrator(d, title="Flow 5")

        n.beat("Sign in as the org admin — full access to every configuration surface.", 3.5)
        ui.login(d, C.ADMIN)

        n.beat("The product catalogue — dozens of real SKUs across Hardware, Networking, Services, Software, Subscriptions.", 5.0)
        ui.open_app(d, "/config/products")
        ui.wait_for_text(d, "List price", timeout=15)
        time.sleep(2.5)
        n.beat("Search and category filters, cost price shown to staff, variants collapsed into a hint. Full CRUD sits behind catalog:write.", 6.0)
        try:
            ui.fill(ui.visible(d, "css selector", "input[placeholder^='Search products']"), "ProBook")
            time.sleep(2.0)
        except Exception:
            pass

        n.beat("Price Lists — a default list plus per-tier overrides. The right price resolves for the customer's context.", 5.5)
        ui.open_app(d, "/config/price-lists")
        time.sleep(2.5)

        n.beat("Now the Discount Policy screen — the demo centrepiece for governance.", 4.0)
        ui.open_app(d, "/config/policy")
        ui.wait_for_text(d, "Tier ceilings", timeout=15)
        time.sleep(2.0)
        n.beat(
            "Version selector defaults to the ACTIVE version. Tier ceilings: Bronze 5%, "
            "Silver 10%, Gold 15%. Category ceilings: Services capped at 10%. The stricter "
            "of the two always wins.",
            8.0,
        )

        n.beat("Edit as a new draft — the form pre-fills from the version you're viewing.", 4.5)
        ui.click_button(d, "Edit as new draft")
        ui.wait_for_text(d, "Category ceilings", timeout=15)
        time.sleep(1.5)

        n.beat("Raise the Services category ceiling from 10% to 20%.", 4.5)
        row = ui.visible(d, "xpath", "//tr[.//td[contains(normalize-space(.),'Services')]]")
        ceiling_input = row.find_element("xpath", ".//input[@inputmode='decimal'][1]")
        ui.set_bps(d, ceiling_input, 20)

        n.beat("Save as a new draft version. Editing never mutates a version in place.", 5.0)
        ui.click_button(d, "Save as new draft version")
        time.sleep(2.0)
        n.beat("A new version appears in the selector — and the old one is still there, unchanged. Historical reproducibility.", 6.5)

        n.beat("Activate the new version. The dialog names the version number explicitly — this changes what every future quote is scored against.", 6.0)
        ui.click_button(d, "Activate this version")
        ui.click_dialog_button(d, "Activate v")  # "Activate v3"
        ui.wait_for_text(d, "Active", timeout=15)
        time.sleep(2.0)
        n.beat(
            "Done — no code change, no redeploy. Policy is data. Quotations already scored "
            "keep the policy version they were evaluated under; only new evaluations use the "
            "new ceilings.",
            8.0,
        )
        n.hold(2.0)

        # Leave the environment as seeded so run order doesn't matter — and it
        # doubles as proof the switch is reversible in one click.
        n.beat("And because it's just data, rolling back is one click — reselect the original version and activate it.", 6.0)
        try:
            trigger = ui.clickable(d, "xpath", "//button[@role='combobox']")
            ui.radix_select(d, trigger, "Version 1")
            ui.click_button(d, "Activate this version")
            ui.click_dialog_button(d, "Activate v")
            time.sleep(2.0)
            n.beat("Back on version 1. Nothing was migrated or lost — every version is still there, immutable.", 6.0)
        except Exception:
            n.caption("(Roll back manually: select Version 1 → Activate this version.)")
        n.hold(3.0)
        n.clear()


if __name__ == "__main__":
    main()
