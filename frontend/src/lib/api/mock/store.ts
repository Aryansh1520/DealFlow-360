/**
 * In-memory quotation/event/approval store backing the mock layer. Resets on
 * page reload — that's fine, it's a stand-in for `BACKEND_PHASE_2.md`'s
 * `quotations`/`quote_events`/`quote_approvals` tables until those exist.
 *
 * Mirrors `DECISION_ENGINE.md` §8's routing/re-approval rules and
 * `API_CONTRACT.md` §7's optimistic-concurrency contract so the UI built
 * against this behaves identically once it's swapped for the real API.
 */
import { evaluate, type EngineLineInput } from "@/lib/api/mock/engine";
import {
  getActivePolicy,
  getAllCustomers,
  getAllProducts,
  getCustomer,
  getProduct,
} from "@/lib/api/mock/reference-data";
import type {
  ApprovalRead,
  DecisionTrace,
  ProductVariantRead,
  QuotationRead,
  QuoteComputation,
  QuoteEventRead,
  QuoteLineRead,
  SuggestionRead,
} from "@/lib/api/types";

// Local copy of the state machine, matching `API_CONTRACT.md` §2 exactly —
// this is the mock's *internal* routing logic (standing in for the backend's
// `transitions.py`), not something the UI reads for rendering. The UI itself
// still gets `transitions` from the real `/meta/enums` and never hardcodes it.
const MOCK_TRANSITIONS: Record<string, string[]> = {
  draft: ["pending_l1", "pending_l2", "approved", "cancelled"],
  pending_l1: ["pending_l2", "approved", "rejected", "returned_for_revision", "cancelled"],
  pending_l2: ["approved", "rejected", "returned_for_revision", "cancelled"],
  returned_for_revision: ["draft", "cancelled"],
  approved: ["sent", "cancelled"],
  sent: ["under_negotiation", "confirmed", "expired", "cancelled"],
  under_negotiation: ["pending_l1", "pending_l2", "sent", "confirmed", "cancelled"],
  confirmed: ["fulfilling", "cancelled"],
  fulfilling: ["invoiced"],
  invoiced: ["paid"],
  paid: [],
  rejected: [],
  cancelled: [],
  expired: [],
};

export class MockApiError extends Error {
  code: string;
  status: number;
  extra: Record<string, unknown>;

  constructor(code: string, status: number, message: string, extra: Record<string, unknown> = {}) {
    super(message);
    this.code = code;
    this.status = status;
    this.extra = extra;
  }
}

interface MockLine {
  id: number;
  productId: number;
  variantId: number | null;
  quantity: number;
  discountBps: number;
  addedFromSuggestion: boolean;
}

interface MockQuotation {
  id: number;
  reference: string;
  orderNumber: string | null;
  customerId: number;
  ownerRepName: string;
  ownerRepId: number;
  status: string;
  version: number;
  policyVersion: number;
  orderDiscountBps: number;
  validUntil: string | null;
  lines: MockLine[];
  fulfillmentStatus: string | null;
  createdAt: string;
  updatedAt: string;
  lastActivityAt: string;
  approvedLineHash: string | null;
  dismissedSuggestionIds: Set<number>;
}

interface MockEvent {
  id: number;
  quotationId: number;
  eventType: string;
  actorType: "internal" | "customer" | "system";
  actorId: number | null;
  actorName: string;
  summary: string;
  payload: Record<string, unknown>;
  createdAt: string;
}

interface MockApproval {
  id: number;
  quotationId: number;
  level: "l1_sales_manager" | "l2_finance";
  sequence: number;
  status: "pending" | "approved" | "rejected" | "returned" | "skipped";
  riskScore: number;
  actedById: number | null;
  actedByName: string | null;
  reason: string | null;
  actedAt: string | null;
  createdAt: string;
}

export interface Actor {
  id: number;
  name: string;
}

const quotations = new Map<number, MockQuotation>();
const events: MockEvent[] = [];
const approvals: MockApproval[] = [];

let nextQuotationId = 101;
let nextLineId = 1001;
let nextEventId = 5001;
let nextApprovalId = 9001;

let seeded = false;
let seedingPromise: Promise<void> | null = null;

function nowIso(): string {
  return new Date().toISOString();
}

function daysAgoIso(days: number): string {
  return new Date(Date.now() - days * 86_400_000).toISOString();
}

function lineHash(lines: MockLine[]): string {
  return lines
    .map((l) => `${l.productId}:${l.variantId ?? ""}:${l.quantity}:${l.discountBps}`)
    .sort()
    .join("|");
}

function recordEvent(
  quotationId: number,
  eventType: string,
  actor: Actor | null,
  summary: string,
  payload: Record<string, unknown> = {}
): void {
  events.push({
    id: nextEventId++,
    quotationId,
    eventType,
    actorType: actor ? "internal" : "system",
    actorId: actor?.id ?? null,
    actorName: actor?.name ?? "System",
    summary,
    payload,
    createdAt: nowIso(),
  });
  const q = quotations.get(quotationId);
  if (q) q.lastActivityAt = nowIso();
}

async function seedOne(
  customerId: number,
  status: string,
  lines: { productId: number; quantity: number; discountBps: number }[],
  daysAgo: number
): Promise<MockQuotation> {
  const id = nextQuotationId++;
  const mockLines: MockLine[] = lines.map((l) => ({
    id: nextLineId++,
    productId: l.productId,
    variantId: null,
    quantity: l.quantity,
    discountBps: l.discountBps,
    addedFromSuggestion: false,
  }));
  const createdAt = daysAgoIso(daysAgo);
  const q: MockQuotation = {
    id,
    reference: `QT-2026-${String(id).padStart(6, "0")}`,
    orderNumber: null,
    customerId,
    ownerRepName: "Riya Rep",
    ownerRepId: 1,
    status,
    version: 1,
    policyVersion: (await getActivePolicy()).version,
    orderDiscountBps: 0,
    validUntil: null,
    lines: mockLines,
    fulfillmentStatus: null,
    createdAt,
    updatedAt: createdAt,
    lastActivityAt: createdAt,
    approvedLineHash: null,
    dismissedSuggestionIds: new Set(),
  };
  quotations.set(id, q);
  recordEvent(id, "quote.created", null, `Quotation ${q.reference} created.`);
  for (const line of mockLines) {
    const product = await getProduct(line.productId);
    recordEvent(
      id,
      "quote.line_added",
      null,
      `${product.name} added — qty ${line.quantity}, ${(line.discountBps / 100).toFixed(1)}% discount.`
    );
  }
  return q;
}

async function ensureSeeded(): Promise<void> {
  if (seeded) return;
  if (!seedingPromise) {
    seedingPromise = (async () => {
      const products = await getAllProducts();
      const customers = await getAllCustomers();
      const laptop = products.find((p) => p.name === "Laptop Pro 14");
      const setup = products.find((p) => p.name === "Setup Service");
      const desktop = products.find((p) => p.name === "Desktop Workstation X1");
      const acme = customers.find((c) => c.tier === "gold") ?? customers[0];
      const beta = customers.find((c) => c.tier === "silver") ?? customers[0];
      const corex = customers.find((c) => c.tier === "bronze") ?? customers[0];

      if (laptop && setup && acme) {
        // DECISION_ENGINE.md §5, worked example A — the problem statement's own
        // case. Risk ≈38, routes to Sales Manager. This is the flagship demo
        // quotation: open it, show the trace, submit, approve.
        const q = await seedOne(
          acme.id,
          "pending_l1",
          [
            { productId: laptop.id, quantity: 1, discountBps: 1200 },
            { productId: setup.id, quantity: 1, discountBps: 1800 },
          ],
          1
        );
        const policy = await getActivePolicy();
        const result = await evaluateQuotationLines(q, policy);
        q.approvedLineHash = lineHash(q.lines);
        approvals.push({
          id: nextApprovalId++,
          quotationId: q.id,
          level: "l1_sales_manager",
          sequence: 1,
          status: "pending",
          riskScore: result.computation.risk_score,
          actedById: null,
          actedByName: null,
          reason: null,
          actedAt: null,
          createdAt: q.createdAt,
        });
        recordEvent(
          q.id,
          "quote.submitted",
          { id: q.ownerRepId, name: q.ownerRepName },
          `Quotation submitted for approval. Risk ${result.computation.risk_score}/100.`
        );
      }

      if (desktop && beta) {
        // A plain compliant draft — good for exercising the builder without
        // any approval noise.
        await seedOne(beta.id, "draft", [{ productId: desktop.id, quantity: 2, discountBps: 500 }], 0);
      }

      const switchProduct = products.find((p) => p.name === "Network Switch 24-Port");
      if (switchProduct && corex) {
        // A stalled deal for the pipeline view — untouched for over a week.
        await seedOne(
          corex.id,
          "sent",
          [{ productId: switchProduct.id, quantity: 3, discountBps: 300 }],
          9
        );
      }

      seeded = true;
    })();
  }
  await seedingPromise;
}

async function resolveVariant(
  productId: number,
  variantId: number | null
): Promise<ProductVariantRead | null> {
  if (variantId == null) return null;
  const product = await getProduct(productId);
  return product.variants.find((v) => v.id === variantId) ?? null;
}

async function toEngineInputs(lines: MockLine[]): Promise<EngineLineInput[]> {
  return Promise.all(
    lines.map(async (line) => ({
      lineId: line.id,
      product: await getProduct(line.productId),
      variant: await resolveVariant(line.productId, line.variantId),
      quantity: line.quantity,
      discountBps: line.discountBps,
    }))
  );
}

async function evaluateQuotationLines(q: MockQuotation, policy = null as Awaited<ReturnType<typeof getActivePolicy>> | null) {
  const activePolicy = policy ?? (await getActivePolicy());
  const customer = await getCustomer(q.customerId);
  const inputs = await toEngineInputs(q.lines);
  return evaluate(inputs, activePolicy, customer.tier, q.orderDiscountBps);
}

async function toQuotationRead(q: MockQuotation): Promise<QuotationRead> {
  const customer = await getCustomer(q.customerId);
  const result = await evaluateQuotationLines(q);

  const lines: QuoteLineRead[] = result.lines.map((l) => ({
    id: l.lineId!,
    quotation_id: q.id,
    product_id: l.productId,
    product_name: l.productName,
    variant_id: l.variantId,
    category_id: l.categoryId,
    line_type: "one_time",
    subscription_plan_id: null,
    quantity: l.quantity,
    unit_price_minor: l.unitPriceMinor,
    discount_bps: l.discountBps,
    net_minor: l.netMinor,
    tax_minor: l.taxMinor,
    cost_minor: l.costMinor,
    margin_minor: l.marginMinor,
    margin_bps: l.marginBps,
    ceiling_bps: l.ceilingBps,
    overage_bps: l.overageBps,
    added_from_suggestion:
      q.lines.find((raw) => raw.id === l.lineId)?.addedFromSuggestion ?? false,
  }));

  const computation: QuoteComputation = {
    ...result.computation,
    trace: result.trace as unknown as DecisionTrace,
  };

  return {
    id: q.id,
    reference: q.reference,
    order_number: q.orderNumber,
    customer_id: q.customerId,
    customer_name: customer.name,
    customer_tier: customer.tier,
    owner_rep_id: q.ownerRepId,
    owner_rep_name: q.ownerRepName,
    status: q.status,
    version: q.version,
    policy_version: q.policyVersion,
    currency: computation.currency,
    valid_until: q.validUntil,
    lines,
    computation,
    fulfillment_status: q.fulfillmentStatus,
    created_at: q.createdAt,
    updated_at: q.updatedAt,
    last_activity_at: q.lastActivityAt,
  };
}

function getOrThrow(id: number): MockQuotation {
  const q = quotations.get(id);
  if (!q) throw new MockApiError("NOT_FOUND", 404, "Quotation not found");
  return q;
}

async function checkVersion(q: MockQuotation, expectedVersion: number): Promise<void> {
  if (q.version !== expectedVersion) {
    const current = await toQuotationRead(q);
    throw new MockApiError(
      "VERSION_CONFLICT",
      409,
      "This quotation changed since you loaded it.",
      { current_version: q.version, current }
    );
  }
}

/** Re-routes a quotation whenever its lines change while approval is pending
 * — `DECISION_ENGINE.md` §8's "golden rule". Approved-at-10%-then-edited-to-25%
 * cannot silently keep its approval. */
function maybeResetApprovals(q: MockQuotation): void {
  if (q.approvedLineHash == null) return;
  if (lineHash(q.lines) === q.approvedLineHash) return;
  const pending = approvals.filter((a) => a.quotationId === q.id && a.status === "pending");
  for (const a of pending) a.status = "skipped";
  q.approvedLineHash = null;
  if (q.status === "pending_l1" || q.status === "pending_l2") {
    q.status = "draft";
    recordEvent(q.id, "quote.returned", null, "Lines changed after submission — approval chain reset.");
  }
}

// ---- Public store API ------------------------------------------------------

export interface ListQuotationsFilters {
  status?: string;
  owner_rep_id?: number;
  customer_id?: number;
  q?: string;
  page: number;
  page_size: number;
}

export async function listQuotations(filters: ListQuotationsFilters) {
  await ensureSeeded();
  let all = Array.from(quotations.values());
  if (filters.status) all = all.filter((q) => q.status === filters.status);
  if (filters.customer_id) all = all.filter((q) => q.customerId === filters.customer_id);
  if (filters.q) {
    const needle = filters.q.toLowerCase();
    const customers = await getAllCustomers();
    all = all.filter((q) => {
      const customer = customers.find((c) => c.id === q.customerId);
      return (
        q.reference.toLowerCase().includes(needle) ||
        customer?.name.toLowerCase().includes(needle)
      );
    });
  }
  all.sort((a, b) => b.lastActivityAt.localeCompare(a.lastActivityAt));

  const total = all.length;
  const start = (filters.page - 1) * filters.page_size;
  const pageItems = all.slice(start, start + filters.page_size);
  const items = await Promise.all(pageItems.map(toQuotationRead));
  return {
    items,
    total,
    page: filters.page,
    page_size: filters.page_size,
    pages: total ? Math.ceil(total / filters.page_size) : 0,
  };
}

export async function getQuotation(id: number): Promise<QuotationRead> {
  await ensureSeeded();
  return toQuotationRead(getOrThrow(id));
}

export async function createQuotation(
  customerId: number,
  validUntil: string | null,
  actor: Actor
): Promise<QuotationRead> {
  await ensureSeeded();
  const id = nextQuotationId++;
  const createdAt = nowIso();
  const q: MockQuotation = {
    id,
    reference: `QT-2026-${String(id).padStart(6, "0")}`,
    orderNumber: null,
    customerId,
    ownerRepName: actor.name,
    ownerRepId: actor.id,
    status: "draft",
    version: 1,
    policyVersion: (await getActivePolicy()).version,
    orderDiscountBps: 0,
    validUntil,
    lines: [],
    fulfillmentStatus: null,
    createdAt,
    updatedAt: createdAt,
    lastActivityAt: createdAt,
    approvedLineHash: null,
    dismissedSuggestionIds: new Set(),
  };
  quotations.set(id, q);
  recordEvent(id, "quote.created", actor, `Quotation ${q.reference} created.`);
  return toQuotationRead(q);
}

export async function updateQuotation(
  id: number,
  expectedVersion: number,
  patch: { order_discount_bps?: number; valid_until?: string | null },
  actor: Actor
): Promise<QuotationRead> {
  await ensureSeeded();
  const q = getOrThrow(id);
  await checkVersion(q, expectedVersion);
  if (patch.order_discount_bps != null) q.orderDiscountBps = patch.order_discount_bps;
  if (patch.valid_until !== undefined) q.validUntil = patch.valid_until;
  q.version += 1;
  q.updatedAt = nowIso();
  maybeResetApprovals(q);
  recordEvent(id, "quote.discount_changed", actor, "Order-level discount updated.");
  return toQuotationRead(q);
}

export async function addLine(
  id: number,
  expectedVersion: number,
  payload: { product_id: number; variant_id: number | null; quantity: number; discount_bps: number; from_suggestion?: boolean },
  actor: Actor
): Promise<QuotationRead> {
  await ensureSeeded();
  const q = getOrThrow(id);
  await checkVersion(q, expectedVersion);
  const product = await getProduct(payload.product_id);
  q.lines.push({
    id: nextLineId++,
    productId: payload.product_id,
    variantId: payload.variant_id,
    quantity: payload.quantity,
    discountBps: payload.discount_bps,
    addedFromSuggestion: payload.from_suggestion ?? false,
  });
  q.version += 1;
  q.updatedAt = nowIso();
  maybeResetApprovals(q);
  recordEvent(
    id,
    "quote.line_added",
    actor,
    `${product.name} added — qty ${payload.quantity}, ${(payload.discount_bps / 100).toFixed(1)}% discount.`
  );
  return toQuotationRead(q);
}

export async function updateLine(
  id: number,
  lineId: number,
  expectedVersion: number,
  patch: { quantity?: number; discount_bps?: number },
  actor: Actor
): Promise<QuotationRead> {
  await ensureSeeded();
  const q = getOrThrow(id);
  await checkVersion(q, expectedVersion);
  const line = q.lines.find((l) => l.id === lineId);
  if (!line) throw new MockApiError("NOT_FOUND", 404, "Line not found");
  const product = await getProduct(line.productId);
  const before = { ...line };
  if (patch.quantity != null) line.quantity = patch.quantity;
  if (patch.discount_bps != null) line.discountBps = patch.discount_bps;
  q.version += 1;
  q.updatedAt = nowIso();
  maybeResetApprovals(q);
  if (patch.discount_bps != null && patch.discount_bps !== before.discountBps) {
    recordEvent(
      id,
      "quote.discount_changed",
      actor,
      `${actor.name} changed ${product.name} discount from ${(before.discountBps / 100).toFixed(1)}% to ${(patch.discount_bps / 100).toFixed(1)}%.`
    );
  } else {
    recordEvent(id, "quote.line_updated", actor, `${product.name} quantity updated to ${line.quantity}.`);
  }
  return toQuotationRead(q);
}

export async function removeLine(
  id: number,
  lineId: number,
  expectedVersion: number,
  actor: Actor
): Promise<QuotationRead> {
  await ensureSeeded();
  const q = getOrThrow(id);
  await checkVersion(q, expectedVersion);
  const line = q.lines.find((l) => l.id === lineId);
  const product = line ? await getProduct(line.productId) : null;
  q.lines = q.lines.filter((l) => l.id !== lineId);
  q.version += 1;
  q.updatedAt = nowIso();
  maybeResetApprovals(q);
  recordEvent(id, "quote.line_removed", actor, `${product?.name ?? "Line"} removed.`);
  return toQuotationRead(q);
}

export async function preview(
  id: number,
  payload: {
    lines: { product_id: number; variant_id: number | null; quantity: number; discount_bps: number }[];
    order_discount_bps: number;
  }
): Promise<QuoteComputation> {
  await ensureSeeded();
  const q = getOrThrow(id);
  const customer = await getCustomer(q.customerId);
  const policy = await getActivePolicy();
  const inputs: EngineLineInput[] = await Promise.all(
    payload.lines.map(async (l) => ({
      lineId: null,
      product: await getProduct(l.product_id),
      variant: await resolveVariant(l.product_id, l.variant_id),
      quantity: l.quantity,
      discountBps: l.discount_bps,
    }))
  );
  const result = evaluate(inputs, policy, customer.tier, payload.order_discount_bps);
  return { ...result.computation, trace: result.trace as unknown as DecisionTrace };
}

export async function submitQuotation(
  id: number,
  expectedVersion: number,
  actor: Actor
): Promise<QuotationRead> {
  await ensureSeeded();
  const q = getOrThrow(id);
  await checkVersion(q, expectedVersion);
  const result = await evaluateQuotationLines(q);

  if (result.belowCost) {
    throw new MockApiError(
      "POLICY_VIOLATION",
      422,
      "One or more lines are priced below cost — fix before submitting.",
      { rule: "MARGIN_FLOOR_BREACH" }
    );
  }

  q.version += 1;
  q.updatedAt = nowIso();
  q.approvedLineHash = lineHash(q.lines);

  // Clear any stale approval rows from a previous submit cycle.
  for (const a of approvals) {
    if (a.quotationId === id && a.status === "pending") a.status = "skipped";
  }

  if (result.computation.required_approvals.length === 0) {
    q.status = "approved";
    recordEvent(id, "quote.approved", actor, "Auto-approved — no policy breach.");
  } else {
    const levels = result.computation.required_approvals;
    levels.forEach((level, index) => {
      approvals.push({
        id: nextApprovalId++,
        quotationId: id,
        level,
        sequence: index + 1,
        status: index === 0 ? "pending" : "pending",
        riskScore: result.computation.risk_score,
        actedById: null,
        actedByName: null,
        reason: null,
        actedAt: null,
        createdAt: nowIso(),
      });
    });
    // Only the first sequence is actionable until it clears.
    approvals
      .filter((a) => a.quotationId === id && a.sequence > 1)
      .forEach((a) => (a.status = "pending"));
    q.status = levels.includes("l1_sales_manager") ? "pending_l1" : "pending_l2";
    recordEvent(
      id,
      "quote.submitted",
      actor,
      `Quotation submitted for approval. Risk ${result.computation.risk_score}/100.`
    );
  }
  return toQuotationRead(q);
}

export async function transitionQuotation(
  id: number,
  expectedVersion: number,
  toStatus: string,
  reason: string | undefined,
  actor: Actor
): Promise<QuotationRead> {
  await ensureSeeded();
  const q = getOrThrow(id);
  await checkVersion(q, expectedVersion);
  const allowed = MOCK_TRANSITIONS[q.status] ?? [];
  if (!allowed.includes(toStatus)) {
    throw new MockApiError(
      "ILLEGAL_TRANSITION",
      409,
      `Cannot move from "${q.status}" to "${toStatus}".`
    );
  }
  const from = q.status;
  q.status = toStatus;
  q.version += 1;
  q.updatedAt = nowIso();
  recordEvent(
    id,
    toStatus === "cancelled" ? "quote.cancelled" : "quote.line_updated",
    actor,
    `Status changed from ${from} to ${toStatus}${reason ? ` — ${reason}` : ""}.`
  );
  return toQuotationRead(q);
}

export async function listEvents(id: number, page: number, pageSize: number) {
  await ensureSeeded();
  getOrThrow(id);
  const all = events
    .filter((e) => e.quotationId === id)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  const total = all.length;
  const start = (page - 1) * pageSize;
  const items: QuoteEventRead[] = all.slice(start, start + pageSize).map((e) => ({
    id: e.id,
    quotation_id: e.quotationId,
    event_type: e.eventType,
    actor_type: e.actorType,
    actor_id: e.actorId,
    actor_name: e.actorName,
    summary: e.summary,
    payload: e.payload,
    created_at: e.createdAt,
  }));
  return { items, total, page, page_size: pageSize, pages: total ? Math.ceil(total / pageSize) : 0 };
}

export async function getDecisionTrace(id: number): Promise<DecisionTrace> {
  await ensureSeeded();
  const q = getOrThrow(id);
  const result = await evaluateQuotationLines(q);
  return result.trace as unknown as DecisionTrace;
}

export async function getSuggestions(id: number, limit: number): Promise<SuggestionRead[]> {
  await ensureSeeded();
  const q = getOrThrow(id);
  const policy = await getActivePolicy();
  const products = await getAllProducts();
  const cartProductIds = new Set(q.lines.map((l) => l.productId));
  const cartCategoryIds = new Set(
    await Promise.all(q.lines.map(async (l) => (await getProduct(l.productId)).category_id))
  );

  const baseline = await evaluateQuotationLines(q, policy);

  const candidates = products.filter(
    (p) => !cartProductIds.has(p.id) && !q.dismissedSuggestionIds.has(p.id)
  );

  const scored = await Promise.all(
    candidates.map(async (candidate) => {
      const candidateInputs = await toEngineInputs(q.lines);
      candidateInputs.push({
        lineId: null,
        product: candidate,
        variant: null,
        quantity: 1,
        discountBps: 0,
      });
      const customer = await getCustomer(q.customerId);
      const withCandidate = evaluate(candidateInputs, policy, customer.tier, q.orderDiscountBps);
      const candidateLine = withCandidate.lines.find((l) => l.productId === candidate.id)!;
      if (candidateLine.marginBps < policy.upsell.min_margin_bps) return null;

      const marginDelta = withCandidate.computation.margin_minor - baseline.computation.margin_minor;
      const marginDeltaBps = candidateLine.marginBps;
      const sameCategory = cartCategoryIds.has(candidate.category_id);
      // No real affinity table in the mock — approximate `lift` with a
      // same-category / promoted heuristic (the documented cold-start
      // fallback in `FEATURES.md` §2), scaled into a plausible-looking ratio.
      const lift = sameCategory ? 2.1 : candidate.is_promoted ? 1.4 : 1.0;
      const supportCount = sameCategory ? 24 : 8;

      const normLift = Math.min(100, (lift / 4) * 100);
      const normMargin = Math.min(100, marginDeltaBps / 100);
      const score =
        (policy.upsell.w_lift_bps / 10000) * normLift +
        (policy.upsell.w_margin_bps / 10000) * normMargin +
        (policy.upsell.w_promo_bps / 10000) * (candidate.is_promoted ? 100 : 0);

      if (score <= 0 && !sameCategory && !candidate.is_promoted) return null;

      const reason = sameCategory
        ? `Frequently bought with items already in this quote · ${supportCount} past orders`
        : candidate.is_promoted
          ? "Currently promoted"
          : "Popular add-on";

      const suggestion: SuggestionRead = {
        product_id: candidate.id,
        product_name: candidate.name,
        sku: candidate.sku,
        list_price_minor: candidate.list_price_minor,
        suggested_quantity: 1,
        score: Math.round(Math.min(100, Math.max(0, score))),
        lift,
        support_count: supportCount,
        margin_delta_minor: marginDelta,
        margin_delta_bps: marginDeltaBps,
        is_promoted: candidate.is_promoted,
        reason,
        currency: candidate.currency,
      };
      return suggestion;
    })
  );

  return scored
    .filter((s): s is SuggestionRead => s !== null)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

export async function dismissSuggestion(id: number, productId: number, actor: Actor): Promise<void> {
  await ensureSeeded();
  const q = getOrThrow(id);
  q.dismissedSuggestionIds.add(productId);
  const product = await getProduct(productId);
  recordEvent(id, "quote.upsell_dismissed", actor, `Dismissed suggestion: ${product.name}.`);
}

// ---- Approvals --------------------------------------------------------------

export interface ListApprovalsFilters {
  level?: string;
  status?: string;
}

export async function listApprovals(filters: ListApprovalsFilters): Promise<ApprovalRead[]> {
  await ensureSeeded();
  const customers = await getAllCustomers();
  let rows = approvals.filter((a) => {
    // Only the current sequence's row is queue-visible until it clears.
    const q = quotations.get(a.quotationId);
    if (!q) return false;
    const rowsForQuote = approvals
      .filter((x) => x.quotationId === a.quotationId)
      .sort((x, y) => x.sequence - y.sequence);
    const firstPending = rowsForQuote.find((x) => x.status === "pending");
    return firstPending?.id === a.id || a.status !== "pending";
  });
  if (filters.level) rows = rows.filter((a) => a.level === filters.level);
  if (filters.status) rows = rows.filter((a) => a.status === filters.status);
  rows = rows.sort((a, b) => a.createdAt.localeCompare(b.createdAt));

  return Promise.all(
    rows.map(async (a) => {
      const q = quotations.get(a.quotationId)!;
      const customer = customers.find((c) => c.id === q.customerId);
      const result = await evaluateQuotationLines(q);
      const read: ApprovalRead = {
        id: a.id,
        quotation_id: a.quotationId,
        quotation_reference: q.reference,
        customer_name: customer?.name ?? "Unknown",
        total_minor: result.computation.total_minor,
        currency: result.computation.currency,
        level: a.level,
        sequence: a.sequence,
        status: a.status,
        risk_score: a.riskScore,
        acted_by_id: a.actedById,
        acted_by_name: a.actedByName,
        reason: a.reason,
        acted_at: a.actedAt,
        created_at: a.createdAt,
      };
      return read;
    })
  );
}

/**
 * **Contract gap, flagged rather than worked around silently**: the frozen
 * `API_CONTRACT.md` §4.6 has no "list approvals for a quotation" endpoint —
 * only the actionable `/approvals/queue` and a single `/approvals/{id}`. The
 * approvals detail screen needs every sequence (approved, pending, skipped)
 * to render the chain stepper, so this mock-only helper reconstructs it.
 * When Dev A adds a real endpoint for this, swap it in here and delete this
 * function; nothing else needs to change.
 */
export async function listApprovalsForQuotation(quotationId: number): Promise<ApprovalRead[]> {
  await ensureSeeded();
  const q = quotations.get(quotationId);
  if (!q) throw new MockApiError("NOT_FOUND", 404, "Quotation not found");
  const customer = await getCustomer(q.customerId);
  const rows = approvals
    .filter((a) => a.quotationId === quotationId)
    .sort((a, b) => a.sequence - b.sequence);
  const result = await evaluateQuotationLines(q);
  return rows.map((a) => ({
    id: a.id,
    quotation_id: a.quotationId,
    quotation_reference: q.reference,
    customer_name: customer.name,
    total_minor: result.computation.total_minor,
    currency: result.computation.currency,
    level: a.level,
    sequence: a.sequence,
    status: a.status,
    risk_score: a.riskScore,
    acted_by_id: a.actedById,
    acted_by_name: a.actedByName,
    reason: a.reason,
    acted_at: a.actedAt,
    created_at: a.createdAt,
  }));
}

export async function getApproval(id: number): Promise<ApprovalRead> {
  await ensureSeeded();
  const a = approvals.find((x) => x.id === id);
  if (!a) throw new MockApiError("NOT_FOUND", 404, "Approval not found");
  const q = quotations.get(a.quotationId)!;
  const customer = await getCustomer(q.customerId);
  const result = await evaluateQuotationLines(q);
  return {
    id: a.id,
    quotation_id: a.quotationId,
    quotation_reference: q.reference,
    customer_name: customer.name,
    total_minor: result.computation.total_minor,
    currency: result.computation.currency,
    level: a.level,
    sequence: a.sequence,
    status: a.status,
    risk_score: a.riskScore,
    acted_by_id: a.actedById,
    acted_by_name: a.actedByName,
    reason: a.reason,
    acted_at: a.actedAt,
    created_at: a.createdAt,
  };
}

export async function actOnApproval(
  id: number,
  action: "approve" | "reject" | "return_for_revision",
  reason: string | undefined,
  actor: Actor
): Promise<QuotationRead> {
  await ensureSeeded();
  const a = approvals.find((x) => x.id === id);
  if (!a) throw new MockApiError("NOT_FOUND", 404, "Approval not found");
  const q = quotations.get(a.quotationId)!;

  a.actedById = actor.id;
  a.actedByName = actor.name;
  a.reason = reason ?? null;
  a.actedAt = nowIso();

  if (action === "approve") {
    a.status = "approved";
    const next = approvals.find(
      (x) => x.quotationId === q.id && x.sequence === a.sequence + 1
    );
    if (next) {
      q.status = "pending_l2";
      recordEvent(
        q.id,
        "quote.approved",
        actor,
        `${actor.name} approved (${a.level === "l1_sales_manager" ? "Sales Manager" : "Finance"}) — now pending Finance review.`
      );
    } else {
      q.status = "approved";
      recordEvent(q.id, "quote.approved", actor, `${actor.name} approved. Approval chain complete.`);
    }
  } else if (action === "reject") {
    a.status = "rejected";
    q.status = "rejected";
    recordEvent(q.id, "quote.rejected", actor, `${actor.name} rejected: ${reason}`);
  } else {
    a.status = "returned";
    q.status = "returned_for_revision";
    recordEvent(q.id, "quote.returned", actor, `${actor.name} returned for revision: ${reason}`);
  }

  q.version += 1;
  q.updatedAt = nowIso();
  return toQuotationRead(q);
}
