# FLOWS.md — Manual test workflow, Frontend Phases 1 & 2

Part A exercises `FRONTEND_PHASE_1.md`: codegen pipeline, money/bps primitives, enums boot
sequence, hardened API client, shell/nav, design pass, and the six config screens. Part B
(new) exercises `FRONTEND_PHASE_2.md`: the quotation builder, decision trace, approvals and
event timeline. **Backend Phases 1 and 2 are both fully live** — nothing in this file needs
mocks; a mock quotations/approvals layer was built and used briefly while backend Phase 2
was in flight, then deleted the moment the real endpoints landed (merged from
`feature/decision-workflow`), per the mock-layer cleanup rule in `FRONTEND_PHASE_1.md` Task
4. Every flow below has been verified against the real backend, both via the UI routes
(server-rendered 200s) and via direct API calls (curl) confirming response shapes, the
worked risk-score example, and the version-conflict error shape.

---

# Part A — Phase 1

---

## 0. Start the stack

```bash
cd DealFlow-360
docker compose up -d
```

Frontend: http://localhost:3001 · Backend: http://localhost:8001/api/v1

If containers are already running, your edits are picked up live (both `frontend` and
`backend` mount the source directory and hot-reload).

**One-time step if you already had this stack running before today**: the frontend
image gained a new dev dependency (`openapi-typescript`, used by the auto-sync below).
Docker Compose reuses the anonymous `node_modules` volume across recreates, so an
existing environment's volume won't have it and the schema auto-sync will silently no-op
(falls back to the existing `schema.d.ts` — it won't crash, but won't sync either). Fix it
once with:
```bash
docker compose up -d --force-recreate -V frontend
```
`-V` recreates anonymous volumes from the image instead of carrying over the old ones. Not
needed on a fresh clone.

### Seeded logins (password `demo12345` unless noted)

| Role | Email | What they should see |
|---|---|---|
| Admin | `admin@example.com` / `admin12345` | Everything, including cost price and all writes |
| Sales Rep | `rep@example.com` | Read-only catalogue; no Configuration write controls |
| Sales Manager | `manager@example.com` | Catalogue read, Price Lists read+write |
| Finance | `finance@example.com` | Discount Policy read+write, Subscription Plans read+write |
| Ops | `ops@example.com` | Warehouses read+write |
| Customer (portal) | `customer@example.com` / `customer12345` | Bounced out of `/dashboard` entirely |

---

## 1. Codegen pipeline (Task 0) — now automatic, no manual step needed

Type sync no longer relies on anyone remembering to run a script:

- **Every `docker compose up`**: the frontend container waits for the backend's
  `/health` to respond, then regenerates `schema.d.ts` from the backend's *live*
  `/api/v1/openapi.json` before starting `next dev` (`frontend/docker-entrypoint.sh`).
  This is also what fixed the `v1.0.0` vs `v1.1.0` contract-mismatch banner — the real
  bug was `contract_version` hardcoded to `v1.0.0` in `backend/app/config/settings.py`;
  it's now `v1.1.0`, matching `API_CONTRACT.md`.
- **Every image build** (`docker compose build` / `up --build`, dev or
  `APP_ENV=production`): the backend Dockerfile bakes a fresh `openapi.json` into its
  own image at build time (pure schema introspection — no DB, no running server). The
  frontend Dockerfile then pulls that *exact* file straight out of the backend build via
  Compose's `additional_contexts: backend-schema: service:backend` and regenerates
  `schema.d.ts` from it before `yarn build` runs. So a production image always ships
  types that match whatever backend it was built alongside — no dependency on a
  possibly-stale committed file, and no live backend needed at build time (matches the
  "never fetch the schema at runtime in production" rule).
- **Manual regeneration** (still available, e.g. for a plain non-Docker `yarn dev`):
  ```bash
  cd frontend
  yarn gen:api          # hits a live backend at :8001
  # or
  yarn gen:api:file     # reads the committed ../backend/openapi.json
  ```

Verify the sync is holding:
```bash
yarn check:api   # regenerates from ../backend/openapi.json and diffs — should exit 0
```
If it fails, someone changed a backend schema without bumping `API_CONTRACT.md`'s version.

```bash
yarn check:money   # should exit 0 — no `_minor` field divided outside money.ts / money-input.tsx
yarn typecheck     # should be clean
```

---

## 2. Boot sequence & contract banner (Task 2)

1. Log in as any user. Open devtools → Network → confirm exactly **one** call to
   `GET /meta/enums` for the whole session (TanStack Query caches it with
   `staleTime: Infinity`).
2. To see the dev-only mismatch banner: temporarily change
   `EXPECTED_CONTRACT_VERSION` in `src/lib/config.ts` to `"v9.9.9"`, reload — a red banner
   should appear at the top of the dashboard shell saying the contract versions disagree.
   Revert the change afterward.

---

## 3. Navigation & guards (Task 5)

1. Log in as `admin@example.com`. Sidebar should show: Dashboard, Workspace (Quotations /
   Pipeline — both live now), Approvals (live), Fulfilment / Billing / Deal Health / Reports
   (still tagged "Phase 3" and disabled — those screens don't exist yet), Configuration
   (Products, Price Lists, Discount Policy, Warehouses, Subscription Plans, Customers),
   User Management (Users, Roles).
2. Log in as `rep@example.com` — Configuration should only show items the rep has
   `:read` on (Products, since `sales_rep` only holds `catalog:read`); Price Lists,
   Discount Policy, Warehouses, Subscription Plans should be **absent** from the sidebar
   (permission-filtered, not just disabled).
3. Try navigating a customer session (`customer@example.com`) to `/dashboard` directly —
   should hard-redirect to `/portal`.

---

## 4. Products (`/config/products`)

Login: `admin@example.com`.

1. **List**: search by name/SKU, filter by category — both should reset to page 1.
2. **Create**: click "Add product". Fill name/SKU/category/unit/list price/cost
   price/tax — confirm the money fields show a currency prefix and format to 2dp on
   blur, and the tax field shows a trailing `%`.
3. **Variants**: in the same dialog, click "Add variant" twice (e.g. Size/Small,
   Size/Large with different extra prices), save. Reopen the product — variants should
   persist and show a "N variants" hint in the list.
4. **Edit**: remove one variant, edit another's extra price, save — confirm only the
   changed/removed variants trigger requests (check Network tab: an unmodified row should
   not fire a PATCH).
5. **Subscription line type**: set Line type to "Subscription" — a Subscription plan
   picker should appear; switch back to "One-time" and it should disappear.
6. **Permission check**: log in as `rep@example.com` — Products list should be visible
   (read) but **no** "Add product" button, no row actions, and no cost-price column.

---

## 5. Price Lists (`/config/price-lists`)

Login: `manager@example.com` (has `pricing:write`).

1. Master list on the left shows all price lists with tier badge + currency; the
   default list has a star icon.
2. Create a new price list (e.g. "Gold Promo", tier Gold). It should appear in the left
   list and auto-select.
3. In the right panel, "Add entry" → pick a product → "Override price" → set an amount →
   save. Confirm the entries table shows the product name (not a raw ID) and the override
   amount formatted as money.
4. Edit the entry's extra discount — confirm it renders as `%`, not a raw bps integer.
5. Delete the entry, then delete the price list — both should confirm before deleting.

---

## 6. Warehouses (`/config/warehouses`)

Login: `ops@example.com`.

1. Create a warehouse (code auto-uppercases visually only; the value you type is sent
   as-is). Shipping weight must reject values outside 1–100 (native input + zod).
2. From the row's "…" menu, click "View stock" — opens a dialog with an adjust form on
   top (product picker, delta, reason) and a stock table below.
3. Adjust stock by a positive delta for a product with no existing stock row — confirm a
   new row appears with the right on-hand/available numbers (`available = on_hand -
   reserved`, computed, never edited directly).
4. Try a negative delta larger than on-hand — the backend should reject it
   (`400`), and the toast should show the backend's message, not `[object Object]`.

---

## 7. Subscription Plans (`/config/subscription-plans`)

Login: `finance@example.com`.

1. Create a plan: Monthly, 12 billing cycles, proration enabled, 30-day cancellation
   notice, refund policy "Prorated".
2. Edit it to "Unlimited" cycles (clear the field) — confirm the table shows
   "Unlimited" rather than blank or `null`.
3. Delete it — confirm dialog names the plan.

---

## 8. Discount Policy (`/config/policy`) — the demo screen

Login: `finance@example.com`.

1. Version selector should default to the **active** version (green "Active" badge).
2. Read view shows tier ceilings, category ceilings, weights, thresholds, and the
   anomaly/stalled-deal summary sentence — all as formatted percentages/money, not raw
   integers.
3. Click "Edit as new draft" — the form pre-fills from the version you were viewing.
   Change the Services category ceiling from 10% to 20%, save.
4. Confirm: a **new version** appears in the selector (e.g. v2) and the **old version is
   still there unchanged** — editing never mutates the version in place.
5. Click "Activate this version" on the new draft — a dialog names the version number
   explicitly ("Activate policy v2?"). Confirm.
6. Reopen the version selector — the new version should now carry the "Active" badge and
   the old one should show "Draft".
7. **This is the live demo beat** (`FEATURES.md` §1): once Phase 2's quote builder exists,
   re-previewing a quote after this edit should change its routing with no redeploy.

---

## 9. Customers (`/customers`)

Login: `admin@example.com`.

1. Filter by tier (Gold/Silver/Bronze/All) — list should refetch and reset to page 1.
2. Combine the tier filter with the search box — both apply together.

---

## 10. Cross-cutting checks

- **Empty states**: on a fresh-ish list (e.g. filter Price Lists to a tier with none), you
  should see real English ("No entries yet — this list falls back to each product's list
  price."), never a bare "No data".
- **Loading states**: throttle the network (devtools → Slow 3G) and reload any config
  screen — skeleton rows should render, not a blank table.
- **Tabular numbers**: watch a money or bps value while editing a quantity/discount field —
  digits should not jitter or reflow (`tabular-nums` is applied in `<Money>`/`<Bps>`/the two
  input components).
- **Idempotency key stability**: this phase doesn't have a user-facing idempotent action yet
  (that's Phase 2's submit/approve), but `useIdempotencyKey` is unit-testable now — calling
  it twice with the same `intentId` across re-renders must return the same UUID.

---

## Known contract gap to flag to Dev A

`ProductRead` (both `API_CONTRACT.md` §3 and the live backend) does **not** include
`is_active`, even though `ProductCreate`/`ProductUpdate` accept it and `GET /products`
accepts an `is_active` filter. The Products screen therefore cannot render an
Active/Inactive column or badge — it's a write-only field from the frontend's point of
view. Not worked around silently: this needs a contract version bump (add `is_active` to
`ProductRead`) before an active/inactive badge can be shown.

---

# Part B — Phase 2: Quotation builder, decision engine, approvals

Real backend Phase 2 (from `feature/decision-workflow`, merged in). Every step below was
run against it directly.

## 11. The flagship demo scenario — problem statement's own example

This is the single most important flow to rehearse. Login: `rep@example.com`.

1. **Workspace → Quotations → New quotation.** Pick **Acme Corp** (Gold tier). You land on
   the builder.
2. From the catalogue panel (left), add **Laptop Pro 14** and **Setup Service**.
3. Set Laptop Pro 14's discount to **12%**. Watch the totals block update within ~250ms
   (debounced preview) — no full-page spinner, just a hairline progress bar while fetching.
   The line should stay in the neutral tone (within its 15% ceiling).
4. Set Setup Service's discount to **18%**. The row should flip to the `warning` tone with a
   tooltip: *"8.0 points over the 10.0% ceiling."* The totals block's risk chip should land
   around **38–41/100** (varies slightly from the doc's illustrative numbers because the
   real seeded cost prices differ — the *mechanism* is what matters) and show **"Will
   require: Sales Manager approval."**
5. Click **Why?** — the decision trace drawer opens: headline summary, the four-component
   contribution bar (blended/worst/value/margin) with the L1/L2 threshold ruler, the
   per-line table with the winning ceiling underlined and the breach row toned red/amber,
   and the rules-fired chips (`LINE_CEILING_BREACH`, `HARD_BREACH_OVERRIDE`,
   `BLENDED_THRESHOLD`).
6. Click **Submit for Approval** → confirm. Status badge flips to *Pending L1*. Scroll the
   Activity panel — `quote.created`, two `quote.line_added`, `quote.submitted` events, each
   with a real actor name and human sentence.
7. **Switch to `manager@example.com`** (a second browser profile or incognito).
   Approvals → the quotation appears in the queue with reference, customer, total, risk,
   level, waiting-since.
8. Open it. The same trace panel renders inline (byte-identical numbers to what the rep
   saw — that's the point). Click **Approve** → confirm. Status flips to *Approved*, chain
   stepper shows the L1 step as approved with your name.
9. Back on the rep's tab, refresh the builder (or just the events panel) — `quote.approved`
   event now shows "Manav Manager moved this quotation from pending_l1 to approved."

## 12. Live margin & upsell (Task 2, Task 3)

1. Create a new draft quotation for any customer, add one product.
2. Open devtools → Network, filter to `preview`. Edit the discount field by typing digits
   slowly for ~10 seconds, then stop. You should see **far fewer than 10** preview
   requests fire (debounced + aborted-superseded) — that's the measured claim from
   `FRONTEND_PHASE_2.md` Task 2b.
3. Open the upsell panel (right column) — suggestions should appear with a lift chip,
   support count, margin delta in the `positive` tone, and the backend-composed `reason`
   string rendered verbatim.
4. Click **Add to Quote** on a suggestion — the totals block should briefly flash (a ring
   pulse, ~400ms) as the margin bar moves. Confirm the new line appears tagged "Added from
   suggestion."
5. Dismiss a different suggestion — it should disappear immediately (optimistic update) and
   not reappear on next load.

## 13. Approvals — reject and return-for-revision (Task 5)

1. Submit a quote that requires approval (any Gold/Silver customer with a category-breaching
   discount works). As `manager@example.com`, open it from the queue.
2. Click **Reject** — the dialog should refuse to submit with an empty reason. Fill a
   reason, confirm. Status flips to *Rejected*; a terminal state — the chain stepper shows
   the rejected step and no further actions render.
3. Repeat with **Return for revision** on a fresh submission — status should flip to
   *Returned for revision*, and the quotation becomes editable again in the builder (the
   catalogue panel and line edits re-enable).
4. Optimistic concurrency: open the same quotation in two tabs as the rep. Edit a discount
   in tab A and let it commit. In tab B (stale `version`), try to edit a different line —
   you should get a non-blocking toast ("This quote changed — refreshed to the latest
   version") and tab B's data should refresh to the server's current truth, **not** lose
   your place in the form.
5. Idempotency: click **Approve** and, before the request resolves, click it again as fast
   as possible (or throttle the network to make the window wider) — the quotation must
   advance exactly one step, never double-approve.

## 14. Pipeline & event timeline (Task 1, Task 6)

1. Workspace → Pipeline. Columns should be generated from `/meta/enums`' `quote_status`
   list, with every terminal status (`paid`, `rejected`, `cancelled`, `expired`) collapsed
   into one "Closed" column — not a hardcoded column list.
2. Cards show customer, amount, a risk chip toned by the same L1/L2 thresholds as the
   builder, and "Nd inactive."
3. On the quotation detail, expand an event's "Details" — the raw `payload` JSON should
   render, collapsed by default, dev-visible only on click.
4. **Reload Data** button on the quotations list should show a spinner and actually
   refetch (check the Network tab), not just decorate.

---

## Known contract gap (Phase 2)

`API_CONTRACT.md` §4.6 documents `GET /approvals/queue` and `GET /approvals/{id}` but no
"list every approval sequence for one quotation" endpoint — needed for the chain stepper.
`features/approvals/api.ts::chainForQuotation` works around this by fetching the
unfiltered queue and filtering by `quotation_id` client-side (fine at hackathon scale;
flagged rather than silently invented). Ask Dev A for a `quotation_id` filter if the queue
grows large enough for this to matter.

---

# Demo-readiness vs. the problem statement (`DealFlow360.md`)

Cross-checking against the judge-facing tier list and the must-have/good-to-have split in
`context/DealFlow360.md`.

## Tier 1 — MUST SHOW: all five done

| # | Item | Status |
|---|---|---|
| 1 | Quotation builder | ✅ Real backend, three-column layout, live editing |
| 2 | Discount governance (tier × category ceiling) | ✅ Real engine, `MIN(tier, category)` |
| 3 | Live margin | ✅ Debounced `/preview`, margin bar, no client-side math |
| 4 | Decision trace | ✅ All four blocks, real trace data, shared component |
| 5 | Automatic approval routing | ✅ `/submit` routes per risk score + hard gates |

## Tier 2 — VERY STRONG: all three done

| # | Item | Status |
|---|---|---|
| 6 | Upsell recommendation | ✅ Real affinity-backed suggestions, margin delta, lift |
| 7 | Approval workflow | ✅ Queue, act, chain stepper, reject/return with reason |
| 8 | Audit timeline | ✅ Real event ledger, backend-composed summaries |

## Tier 3 — DIFFERENTIATION: not started (Phase 3)

| # | Item | Status |
|---|---|---|
| 9 | Customer portal (negotiation) | ❌ Only the Phase 1 placeholder "My Quotations" shell exists |
| 10 | Live negotiation over SSE | ❌ No SSE endpoint or hook yet |
| 11 | Warehouse split / backorders | ❌ `fulfillment` module not built (backend or frontend) |
| 12 | Hybrid billing (one-time + subscription) | ❌ `billing` module not built |

## Tier 4 — Polish: not started (Phase 3)

| # | Item | Status |
|---|---|---|
| 13 | Deal health dashboard | ❌ `deal_metrics` read model doesn't exist yet |
| 14 | Anomaly detection (discount vs. rep average) | ❌ `rep_discount_stats` / alerts not built |
| 15 | Reports | ❌ Not built |
| 16 | Exports (PDF/XLS) | ❌ Not built |
| 17 | Cache / perf metrics | ❌ Not built (graceful to skip per the doc) |

## Must-have checklist (`DealFlow360.md` §27)

**Business:** Authentication ✅ · Products ✅ · Price lists ✅ · Customer tiers ✅ ·
Discount ceilings ✅ · Approval routing ✅ · Quotation creation ✅ · Margin calculation ✅ ·
Upsell/cross-sell ✅ · Warehouse splitting ❌ · Backorders ❌ · Subscription + one-time
billing ❌ · Customer portal (negotiation) ❌ · Negotiation ❌ · Deal health ❌ ·
Reporting ❌.

**Technical correctness:** Business rules live in application logic, not hardcoded ✅ ·
Real separate portal principal (structural, from the auth slice) ✅ · RBAC ✅ · Audit trail
(event ledger) ✅ · Real seeded data (12 months of history + real affinity) ✅ · Working
end-to-end flow, quote → live margin → trace → submit → approve, verified via UI and curl
✅ · Two complete demo flows — the **internal** flow (rep → manager) is fully verified; the
**two-window portal/SSE** flow is not built yet (Phase 3).

## What this means for the next demo round

The safe, honest framing right now: *"We've completed the identity/principal foundation,
the full backend configuration surface, and the core self-governing quote lifecycle —
quotation → live risk scoring → explainable approval routing → audit trail. That's Tier 1
and Tier 2 in full, running against a real database and a real decision engine, not a
demo stub."* The customer portal negotiation, SSE, fulfilment and billing (Tier 3/4) are
the explicit next milestone — `FRONTEND_PHASE_3.md` / `BACKEND_PHASE_3.md` — and should be
described as "next," not implied to already work.

**Rehearse flow §11 above precisely as written** — it's the exact problem-statement
scenario and currently the strongest thing in the app to put in front of judges.
