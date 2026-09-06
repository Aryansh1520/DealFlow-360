# DealFlow360 — screen-recording automation

Ten Selenium scripts that drive the real app end-to-end at a narratable pace, with
an on-screen caption bar you can read as your voiceover. They cover every
**[PDF-DIRECT]** scenario the QA plan says must be shown, the two judge demo
flows, and three robustness ("edge") proofs where DealFlow360 has an advantage.

| # | Script | What it proves | QA-plan tests |
|---|--------|----------------|---------------|
| 1 | `flow_01_intelligent_quotation.py` | Build → live risk → decision trace → upsell → auto L1 routing → manager approve → audit trail | T017-T022, T032, T040, T046-T049, T053-T055, T060 |
| 2 | `flow_02_live_negotiation.py` | **Two windows.** Customer counter-offer → rep updates with no refresh (SSE) → rep applies → engine re-runs → quote **re-enters approval on its own** → manager approves → customer sees the truthful status | T070-T081, T110 |
| 3 | `flow_03_fulfillment_split_backorder.py` | Two-warehouse split (Main 3 / East 5, demand 6), backorder (stock 2, demand 5), replenish, consolidate; delivery-slippage | T062-T064, T069, T095, T111 |
| 4 | `flow_04_hybrid_billing_payment.py` | One-time + recurring on one order, generate invoice, partial then full payment, order flips to Paid | T082-T084, T088-T089, T112 |
| 5 | `flow_05_config_policy_as_data.py` | Catalogue / price lists / discount policy; edit a category ceiling as a **new version**, activate it, roll back — no redeploy | T008-T015, T016 |
| 6 | `flow_06_approval_workflow.py` | Queue, trace, chain stepper, **return-for-revision with a mandatory reason**, resubmit, approve | T053-T057, T059, T060 |
| 7 | `flow_07_deal_health.py` | Stalled deal, discount anomaly **that explains itself**, delivery slippage, no anomaly below min sample size, nudge / acknowledge | T092-T097 |
| e1 | `edge_01_optimistic_concurrency.py` | **Two windows.** Stale write → `409 VERSION_CONFLICT`, UI refreshes to server truth, no lost work | T061, T104 |
| e2 | `edge_02_portal_isolation.py` | **Two windows.** Same quote, staff vs customer: cost/margin/risk/trace absent from the customer response; `/dashboard` bounces to `/portal`; another customer's quote is denied | T007, T071-T073, T080, Security Matrix |
| e3 | `edge_03_invoice_supersession.py` | Issued invoice is immutable; supersede → full-reversal credit note + corrected invoice; lineage oldest → newest | T087, T091 |

Two-window flows open two **independent** Chrome sessions tiled to fill exactly
half the screen each. Single-actor flows run one maximised window.

---

## Prerequisites

1. **The stack is up** and reachable on the default ports:

   ```bash
   cd DealFlow-360
   docker compose up -d
   # frontend http://localhost:3001 · backend http://localhost:8001
   ```

2. **Fresh demo data.** Every script assumes the documented fixtures exist. Re-seed
   before a recording session (and again before re-running flows 3/4/e3, which
   consume single-use fixtures):

   ```bash
   docker compose exec backend python -m app.db.seed --reset --history --demo
   ```

3. **Google Chrome** installed (any recent version). Selenium 4 downloads a
   matching `chromedriver` itself — nothing else to install.

4. **A Python with a working stdlib.** The Homebrew `python@3.13/3.14` on this
   machine has a broken `pyexpat`, so the venv here is built from the system
   Python:

   ```bash
   cd DealFlow-360/demo/selenium
   /usr/bin/python3 -m venv .venv
   ./.venv/bin/pip install -r requirements.txt
   ```

---

## Running

```bash
cd DealFlow-360/demo/selenium

# one flow
./.venv/bin/python flow_01_intelligent_quotation.py

# guided run of all ten, pausing before each so you can arm the recorder
./.venv/bin/python run_all.py

# a subset, back to back
./.venv/bin/python run_all.py 1 2 7 --no-pause
```

### Knobs (environment variables)

| var | default | meaning |
|-----|---------|---------|
| `DF_SLOW` | `1.6` | pacing multiplier. `1.6` suits a live voiceover; `2.2` for a calmer take; `0.35` for a fast selector check |
| `DF_BASE_URL` | `http://localhost:3001` | frontend origin |
| `DF_API_URL` | `http://localhost:8001/api/v1` | backend API base |
| `DF_HEADLESS` | `0` | `1` runs with no visible window (don't use for a recording) |
| `DF_KEEP_OPEN` | `0` | `1` leaves the browser open at the end until you press Enter |
| `DF_WIN_W` | auto | force a per-window width for two-up flows |

Example — a relaxed take of the flagship flow, browser left open at the end:

```bash
DF_SLOW=2.2 DF_KEEP_OPEN=1 ./.venv/bin/python flow_01_intelligent_quotation.py
```

---

## Recording tips

- **Order for a single continuous take:** 5 → 1 → 6 → 2 → 3 → 4 → 7, then the edge
  flows. Flow 5 activates a new policy version and then rolls back to v1, so the
  environment is left as seeded either way — but re-seeding between flows is always
  safe.
- The **caption bar** (bottom-centre, dark pill) is the narration script. Each line
  is timed by `DF_SLOW`; raise it if you talk slowly.
- The rate limiter is set to 15000 req/min in `.env` so a slow narrated run never
  trips it. Chrome's "save password" bubble is disabled in the driver options.
- Two-window flows: record the whole screen, not one window. The left window is
  always the internal user; the right window is the customer (or a second rep in
  `edge_01`).
- Screenshots of any failure land in `demo/selenium/screenshots/`.

---

## Layout

```
demo/selenium/
├── requirements.txt
├── run_all.py                 # sequential runner
├── flow_0*.py / edge_0*.py    # one self-contained script per flow
└── dealflow/
    ├── config.py              # URLs, seeded credentials, fixture names
    ├── driver.py              # Chrome factory + screen tiling
    ├── ui.py                  # waits, clicks, Radix <Select>, BpsInput, captions, login, builder helpers
    ├── api.py                 # tiny read-only client — locates seeded fixtures by product/status
    └── scenario.py            # banner + browser lifecycle + failure screenshots
```

No `data-testid`s exist in the app, so `ui.py` selects on visible text and ARIA
roles — the same cues a person reads. If the frontend copy changes, the small set
of literal strings to update all live in `ui.py` and the flow scripts' `n.beat(...)`
captions.
