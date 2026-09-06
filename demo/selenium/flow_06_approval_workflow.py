#!/usr/bin/env python3
"""FLOW 6 — Approval workflow in depth.

Covers: T053-T057 (queue, trace, approve, reject, return-for-revision),
T059 (approved-quote edit re-routes), T060 (audit).

    Riya builds an over-ceiling quote for Beta Industries → submits → Pending L1
    Manav opens it → reviews the trace and the chain stepper
      → Returns it for revision with a reason  (a reason is mandatory)
    Riya sees it editable again → dials the discount back → resubmits
    Manav approves → chain complete
"""

import time

from dealflow import ui
from dealflow.config import Credentials as C
from dealflow.config import Fixtures as F
from dealflow.scenario import single


def main() -> None:
    with single("Flow 6 · Approval workflow") as d:
        n = ui.Narrator(d, title="Flow 6")

        n.beat("Riya (Sales Rep) builds a quote for Beta Industries — Silver tier.", 3.5)
        ui.login(d, C.REP)
        qid = ui.create_quotation(d, F.BETA)
        ref = ui.current_quote_reference(d)
        ui.add_catalogue_product(d, F.FLAGSHIP_SERVICE)
        ui.add_catalogue_product(d, "Premium Support Plan")

        n.beat("She puts 18% on the Setup Service — Silver caps at 10%, Services caps at 10%. Well over.", 5.0)
        ui.set_line_discount(d, F.FLAGSHIP_SERVICE, 18)
        n.beat("Submit — routed straight to L1. No approver picked by hand.", 4.5)
        ui.submit_for_approval(d)

        n.beat("Manav (Sales Manager) signs in. The queue shows quote, customer, total, risk, level and wait time.", 5.5)
        ui.logout(d)
        ui.login(d, C.MANAGER)
        ui.open_first_approval(d, reference=ref)
        n.beat("He opens it: the approval chain stepper, the read-only quotation, and the same decision trace inline.", 6.0)
        n.hold(2.0)

        n.beat("He returns it for revision. The dialog refuses to submit without a reason.", 5.0)
        ui.return_for_revision(d, "Services discount is 8 points over ceiling — bring it to 10% or add justification.")
        n.beat("Status is now 'Returned for revision' — and the reason is on the audit trail with his name and the timestamp.", 6.0)

        n.beat("Riya reopens it — the builder is editable again. She dials the Setup Service discount down to 9%.", 6.0)
        ui.logout(d)
        ui.login(d, C.REP)
        ui.open_app(d, f"/workspace/quotations/{qid}")
        ui.wait_for_text(d, "Returned for revision", timeout=15)
        ui.set_line_discount(d, F.FLAGSHIP_SERVICE, 9)
        n.beat("Now it's inside every ceiling. Resubmit.", 4.0)
        ui.submit_for_approval(d)
        time.sleep(1.5)
        n.beat(
            "It's compliant now — so the engine auto-approves it. It doesn't even reach the "
            "manager's queue. The system routes work only when the risk is real.",
            7.0,
        )
        ui.open_app(d, f"/workspace/quotations/{qid}")
        ui.wait_for_text(d, "Approved", timeout=15)
        n.hold(2.0)

        n.beat(
            "One clean audit trail across the whole episode: submitted, returned WITH a reason, "
            "revised, resubmitted, approved — every step carries an actor and a timestamp.",
            7.5,
        )
        d.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        n.hold(3.0)
        n.clear()


if __name__ == "__main__":
    main()
