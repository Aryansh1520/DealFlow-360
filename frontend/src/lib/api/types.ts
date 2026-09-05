/**
 * Thin, readable aliases over the generated `schema.d.ts` so components never
 * import `components["schemas"]["…"]` directly. This is the **only** file allowed
 * to reference `schema.d.ts` — see `FRONTEND_PHASE_1.md` Task 0.
 *
 * One line per shape in `API_CONTRACT.md` §3 (and the request payloads each
 * feature needs). Add to this file, never hand-write an API type elsewhere.
 */
import type { components } from "./schema";

type S = components["schemas"];

// ---- Meta / enums ---------------------------------------------------------------
export type MetaEnums = S["MetaEnums"];
export type PermissionResourceRead = S["PermissionResourceRead"];

// ---- Catalogue --------------------------------------------------------------------
export type CategoryRead = S["CategoryRead"];
export type CategoryCreate = S["CategoryCreate"];
export type CategoryUpdate = S["CategoryUpdate"];

export type ProductRead = S["ProductRead"];
export type ProductCreate = S["ProductCreate"];
export type ProductUpdate = S["ProductUpdate"];

export type ProductVariantRead = S["ProductVariantRead"];
export type ProductVariantCreate = S["ProductVariantCreate"];
export type ProductVariantUpdate = S["ProductVariantUpdate"];

// ---- Pricing ------------------------------------------------------------------------
export type PriceListRead = S["PriceListRead"];
export type PriceListCreate = S["PriceListCreate"];
export type PriceListUpdate = S["PriceListUpdate"];

export type PriceListEntryRead = S["PriceListEntryRead"];
export type PriceListEntryCreate = S["PriceListEntryCreate"];
export type PriceListEntryUpdate = S["PriceListEntryUpdate"];

// ---- Warehouses & stock -------------------------------------------------------------
export type WarehouseRead = S["WarehouseRead"];
export type WarehouseCreate = S["WarehouseCreate"];
export type WarehouseUpdate = S["WarehouseUpdate"];

export type StockRead = S["StockRead"];
export type StockAdjustRequest = S["StockAdjustRequest"];

// ---- Subscription plans -------------------------------------------------------------
export type SubscriptionPlanRead = S["SubscriptionPlanRead"];
export type SubscriptionPlanCreate = S["SubscriptionPlanCreate"];
export type SubscriptionPlanUpdate = S["SubscriptionPlanUpdate"];

// ---- Discount policy ------------------------------------------------------------------
export type PolicyRead = S["PolicyRead"];
export type PolicyCreate = S["PolicyCreate"];
export type PolicyWeights = S["PolicyWeights"];
export type PolicyThresholds = S["PolicyThresholds"];
export type PolicyUpsell = S["PolicyUpsell"];
export type PolicyAnomaly = S["PolicyAnomaly"];
export type TierCeilingRead = S["TierCeilingRead"];
export type TierCeilingInput = S["TierCeilingInput"];
export type CategoryCeilingRead = S["CategoryCeilingRead"];
export type CategoryCeilingInput = S["CategoryCeilingInput"];

// ---- Quotations (Phase 2) -------------------------------------------------------------
export type QuotationRead = S["QuotationRead"];
export type QuotationCreate = S["QuotationCreate"];
export type QuotationUpdate = S["QuotationUpdate"];
export type QuoteLineRead = S["QuoteLineRead"];
export type QuoteLineCreate = S["QuoteLineCreate"];
export type QuoteLineUpdate = S["QuoteLineUpdate"];
export type QuoteComputation = S["QuoteComputation"];
export type QuoteEventRead = S["QuoteEventRead"];
export type PreviewRequest = S["PreviewRequest"];
export type PreviewLine = S["PreviewLine"];
export type SubmitRequest = S["SubmitRequest"];
export type SuggestionRead = S["SuggestionRead"];

// ---- Decision trace (Phase 2) -----------------------------------------------------------
export type DecisionTrace = S["DecisionTrace"];
export type DecisionTraceComponent = S["DecisionTraceComponent"];
export type DecisionTraceLine = S["DecisionTraceLine"];
export type DecisionTraceRule = S["DecisionTraceRule"];

// ---- Approvals (Phase 2) ----------------------------------------------------------------
export type ApprovalRead = S["ApprovalRead"];
export type ApprovalActRequest = S["ApprovalActRequest"];

// ---- Fulfilment (Phase 3) --------------------------------------------------------------
export type FulfillmentPlan = S["FulfillmentPlan"];
export type ShipmentPlan = S["ShipmentPlan"];
export type ShipmentLine = S["ShipmentLine"];
export type BackorderLine = S["BackorderLine"];
export type AllocationInput = S["AllocationInput"];
export type FulfillmentAcceptRequest = S["FulfillmentAcceptRequest"];
export type FulfillmentOverrideRequest = S["FulfillmentOverrideRequest"];
export type FulfillmentConsolidateRequest = S["FulfillmentConsolidateRequest"];

// ---- Billing & invoices (Phase 3) -------------------------------------------------------
export type BillingScheduleEntry = S["BillingScheduleEntry"];
export type InvoiceRead = S["InvoiceRead"];
export type InvoiceLineRead = S["InvoiceLineRead"];
export type PaymentRequest = S["PaymentRequest"];

// ---- Customer portal (Phase 3) -----------------------------------------------------------
export type PortalQuotationRead = S["PortalQuotationRead"];
export type PortalQuoteLine = S["PortalQuoteLine"];
export type PortalTotals = S["PortalTotals"];
export type PortalTimelineEntry = S["PortalTimelineEntry"];
export type PortalCommentRequest = S["PortalCommentRequest"];
export type PortalCounterRequest = S["PortalCounterRequest"];
export type PortalConfirmRequest = S["PortalConfirmRequest"];
export type PortalConfirmResponse = S["PortalConfirmResponse"];
export type MagicLinkRedeemRequest = S["MagicLinkRedeemRequest"];
export type MagicLinkRedeemResponse = S["MagicLinkRedeemResponse"];

// ---- Dashboard, alerts & reports (Phase 3) ------------------------------------------------
export type DealHealthRow = S["DealHealthRow"];
export type AlertRead = S["AlertRead"];

// ---- Auth / users / roles / customers (existing starter slice) -----------------------------
export type TokenResponse = S["TokenResponse"];
export type LoginRequest = S["LoginRequest"];
export type RegisterRequest = S["RegisterRequest"];
export type RefreshRequest = S["RefreshRequest"];
export type MeResponse = S["MeResponse"];
export type MeUpdate = S["MeUpdate"];

export type UserRead = S["UserRead"];
export type UserCreate = S["UserCreate"];
export type UserUpdate = S["UserUpdate"];

export type RoleRead = S["RoleRead"];
export type RoleCreate = S["RoleCreate"];
export type RoleUpdate = S["RoleUpdate"];

export type CustomerRead = S["CustomerRead"];
export type CustomerCreate = S["CustomerCreate"];
export type CustomerUpdate = S["CustomerUpdate"];

// ---- Error envelope (API_CONTRACT.md §1) ---------------------------------------------------
export type ValidationErrorDetail = S["ValidationError"];
export type HTTPValidationError = S["HTTPValidationError"];

export type ErrorCode =
  | "VALIDATION_ERROR"
  | "VERSION_CONFLICT"
  | "IDEMPOTENCY_REPLAY"
  | "ILLEGAL_TRANSITION"
  | "INSUFFICIENT_STOCK"
  | "POLICY_VIOLATION"
  | "FORBIDDEN_PRINCIPAL"
  | "NOT_FOUND"
  | "PERMISSION_DENIED";

/** `data` on any non-2xx response — contract §1 "Error envelope". */
export interface ErrorData {
  code: ErrorCode | null;
  request_id: string;
  [extra: string]: unknown;
}

/** `data` on a `409 VERSION_CONFLICT` — contract §7. */
export interface VersionConflictData extends ErrorData {
  code: "VERSION_CONFLICT";
  current_version: number;
  current: QuotationRead;
}

/** `data` on a `422 VALIDATION_ERROR`. */
export interface FieldValidationData extends ErrorData {
  code: "VALIDATION_ERROR";
  errors: { field: string; message: string }[];
}
