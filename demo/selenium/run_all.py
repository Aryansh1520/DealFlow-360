#!/usr/bin/env python3
"""Run the demo flows one after another.

    ./.venv/bin/python run_all.py                 # every flow, pausing between each
    ./.venv/bin/python run_all.py 1 2 7           # only flows 1, 2, 7
    ./.venv/bin/python run_all.py --no-pause      # back to back (CI / rehearsal)

Between flows it waits for Enter so you can start / stop your screen recorder.
"""

import importlib
import sys

FLOWS = [
    ("1", "flow_01_intelligent_quotation", "Intelligent quotation (flagship)"),
    ("2", "flow_02_live_negotiation", "Live two-window negotiation"),
    ("3", "flow_03_fulfillment_split_backorder", "Fulfilment split & backorder"),
    ("4", "flow_04_hybrid_billing_payment", "Hybrid billing & payment"),
    ("5", "flow_05_config_policy_as_data", "Config & policy-as-data"),
    ("6", "flow_06_approval_workflow", "Approval workflow depth"),
    ("7", "flow_07_deal_health", "Deal health & anomalies"),
    ("e1", "edge_01_optimistic_concurrency", "Edge · optimistic concurrency"),
    ("e2", "edge_02_portal_isolation", "Edge · portal isolation"),
    ("e3", "edge_03_invoice_supersession", "Edge · invoice supersession"),
]


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--no-pause"]
    pause = "--no-pause" not in sys.argv
    selected = [f for f in FLOWS if not args or f[0] in args]

    if not selected:
        print("No matching flows. Keys:", ", ".join(k for k, _, _ in FLOWS))
        return

    for key, module_name, label in selected:
        if pause:
            try:
                input(f"\n▶  Ready for [{key}] {label} — press Enter (Ctrl-C to stop) ")
            except (EOFError, KeyboardInterrupt):
                print("\nstopped.")
                return
        print(f"\n=== [{key}] {label} ===")
        module = importlib.import_module(module_name)
        try:
            module.main()
        except SystemExit as exc:
            print(f"  skipped: {exc}")
        except Exception as exc:  # keep going through the rest of the run
            print(f"  FAILED: {exc!r}")


if __name__ == "__main__":
    main()
