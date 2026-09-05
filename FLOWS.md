# FLOWS.md — Manual test workflow for Frontend Phase 1

Everything below exercises the work in `FRONTEND_PHASE_1.md`: codegen pipeline, money/bps
primitives, enums boot sequence, hardened API client, shell/nav, design pass, and the six
config screens. Backend Phase 1 is already live — nothing here needs mocks.

---

## 0. Start the stack

```bash
cd DealFlow-360
docker compose up -d
```

Frontend: http://localhost:3001 · Backend: http://localhost:8001/api/v1

If containers are already running, your edits are picked up live (both `frontend` and
`backend` mount the source directory and hot-reload).

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

## 1. Codegen pipeline (Task 0)

```bash
cd frontend
yarn gen:api          # hits the live backend at :8001
# or
yarn gen:api:file     # reads the committed ../backend/openapi.json
```

Both should regenerate `src/lib/api/schema.d.ts` with **no diff** if the backend hasn't
changed — that's `yarn check:api` (run it; it should exit 0 right after a fresh generate).
If it fails, someone changed a backend schema without bumping `API_CONTRACT.md`.

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
   Pipeline, both tagged "Phase 2" and disabled), Approvals ("Phase 2", disabled),
   Fulfilment / Billing / Deal Health / Reports ("Phase 3", disabled), Configuration
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

## Explicitly not covered here

Mocks (Task 4) were skipped: every Phase 1 endpoint is already live on the backend, so
there was nothing to mock. Quotation builder, pipeline, approvals, trace panel,
fulfilment, billing, portal, dashboard and SSE are Phase 2/3 — see
`FRONTEND_PHASE_2.md` / `FRONTEND_PHASE_3.md` for their own flows once those phases land.
