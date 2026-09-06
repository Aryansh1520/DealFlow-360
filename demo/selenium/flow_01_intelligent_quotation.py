#!/usr/bin/env python3
"""FLOW 1 — Intelligent quotation (the flagship judge demo).

Covers: T017-T022, T032 (Acme exact scenario), T046-T049 (upsell), T040 (L1
routing), T053-T055 (approval queue + trace + approve), T060 (audit timeline).

    Login as Riya (Sales Rep)
      → New quote for Acme Corp (Gold)
      → Add ProBook 14 Laptop  @ 12%   (within the 15% Hardware/Gold ceiling)
      → Add On-Site Setup Service @ 18% (8 pts over the 10% Services ceiling)
      → Live warning + risk score + "needs L1"
      → Open the decision trace — every number explained
      → Accept an upsell — margin moves immediately
      → Submit — routed to L1 automatically, no approver picked by hand
      → Switch to Manav (Sales Manager) → same trace → Approve
      → Audit timeline shows the whole story
"""

from dealflow import ui
from dealflow.config import Credentials as C
from dealflow.config import Fixtures as F
from dealflow.scenario import single


def main() -> None:
    with single("Flow 1 · Intelligent quotation") as d:
        n = ui.Narrator(d, title="Flow 1")

        n.beat("Sign in as Riya — a Sales Rep. She builds deals; the system governs them.", 3.5)
        ui.login(d, C.REP)

        n.beat("New quotation for Acme Corp — a Gold-tier customer.", 3.0)
        qid = ui.create_quotation(d, F.ACME)
        ref = ui.current_quote_reference(d)

        n.beat(f"Add the {F.FLAGSHIP_HARDWARE} from the catalogue — Hardware.", 3.5)
        ui.add_catalogue_product(d, F.FLAGSHIP_HARDWARE)

        n.beat(f"Add the {F.FLAGSHIP_SERVICE} — a Services line.", 3.5)
        ui.add_catalogue_product(d, F.FLAGSHIP_SERVICE)

        n.beat("Give the laptop a 12% discount. Gold + Hardware both cap at 15% — this is fine.", 4.0)
        ui.set_line_discount(d, F.FLAGSHIP_HARDWARE, F.FLAGSHIP_HW_DISCOUNT_PCT)

        n.beat(
            "Now 18% on the Setup Service. The Services ceiling is 10% — watch the row turn amber.",
            4.5,
        )
        ui.set_line_discount(d, F.FLAGSHIP_SERVICE, F.FLAGSHIP_SVC_DISCOUNT_PCT)

        n.beat(
            "The totals block already knows: risk score climbs and it reads 'Needs L1'. "
            "The rep is told before submitting, not after.",
            5.0,
        )
        n.hold(2.0)

        n.beat("Click 'Why?' — the decision trace. This is the intellectual centrepiece.", 4.0)
        ui.open_decision_trace(d)
        n.beat(
            "Setup Service is 8.0 points over its 10% category ceiling. "
            "Blended overage, worst line, order value and margin — each contributes to the score.",
            6.0,
        )
        n.beat("Per-line table: the winning ceiling is min(tier, category). Rules fired are listed explicitly.", 6.0)
        ui.press_escape(d)
        n.hold(1.0)

        n.beat("Cross-sell: suggestions come from real co-purchase history — lift, order count, margin delta.", 4.5)
        try:
            ui.click_button(d, "Add to Quote")
            n.beat("Added. The margin bar pulses and moves — the backend recomputed, nothing faked client-side.", 5.0)
        except Exception:
            n.beat("(No suggestion surfaced for this mix — the panel stays honestly empty.)", 3.0)

        n.beat("Submit for approval. No approver is chosen by hand — routing is automatic.", 4.5)
        ui.submit_for_approval(d)
        n.beat("Status is now 'Pending L1'. Riya's job is done; the quote is the manager's to move.", 4.5)

        n.beat("Switch users — sign in as Manav, the Sales Manager.", 4.0)
        ui.logout(d)
        ui.login(d, C.MANAGER)

        n.beat("Approvals queue: reference, customer, total, risk, level, and how long it's waited.", 4.5)
        ui.open_first_approval(d, reference=ref)
        n.beat("The manager sees the *same* decision trace, byte-for-byte. That's the point.", 5.0)
        n.hold(2.0)

        n.beat("Approve.", 3.0)
        ui.approve_current(d)
        n.beat("Approved — the chain stepper shows the L1 step signed with Manav's name.", 4.0)

        n.beat(
            "Open the quotation's Activity panel — created, two lines added, two discounts "
            "changed, an upsell, submitted, approved. Every step has an actor and a timestamp.",
            6.5,
        )
        ui.open_app(d, f"/workspace/quotations/{qid}")
        ui.wait_for_text(d, "Activity", timeout=15)
        d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        n.hold(4.0)
        n.clear()


if __name__ == "__main__":
    main()
