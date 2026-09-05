"""Aggregates all feature routers under one API router.

Phase 1 (catalogue, pricing, warehouses, subscriptions, policies) is fully implemented.
Phase 2/3 routers (quotations, approvals, fulfillment, billing, portal, dashboard,
events) exist only as the Task 0 stub pass — every path from `API_CONTRACT.md` §4
responds `501 Not Implemented` until its own phase lands.
"""

from fastapi import APIRouter

from app.approvals.router import router as approvals_router
from app.auth.router import router as auth_router
from app.billing.router import quotation_billing_router, router as billing_router
from app.catalog.router import router as catalog_router
from app.customers.router import router as customers_router
from app.dashboard.router import router as dashboard_router
from app.events.router import router as events_router
from app.fulfillment.router import router as fulfillment_router
from app.meta.router import health_router, router as meta_router
from app.policies.router import router as policies_router
from app.portal.router import public_router as portal_public_router, router as portal_router
from app.pricing.router import router as pricing_router
from app.quotations.router import router as quotations_router
from app.roles.router import router as roles_router
from app.subscriptions.router import router as subscriptions_router
from app.users.router import router as users_router
from app.warehouses.router import router as warehouses_router, stock_router

api_router = APIRouter()

# ---- Phase 1: live -----------------------------------------------------------------
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(meta_router, prefix="/meta", tags=["meta"])
api_router.include_router(health_router, tags=["health"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(roles_router, prefix="/roles", tags=["roles"])
api_router.include_router(customers_router, prefix="/customers", tags=["customers"])
api_router.include_router(catalog_router, tags=["catalog"])
api_router.include_router(pricing_router, prefix="/price-lists", tags=["pricing"])
api_router.include_router(warehouses_router, prefix="/warehouses", tags=["warehouses"])
api_router.include_router(stock_router, prefix="/stock", tags=["warehouses"])
api_router.include_router(subscriptions_router, prefix="/subscription-plans", tags=["subscriptions"])
api_router.include_router(policies_router, prefix="/policies", tags=["policies"])

# ---- Phase 2/3: stub pass (Task 0) --------------------------------------------------
api_router.include_router(quotations_router, prefix="/quotations", tags=["quotations"])
api_router.include_router(fulfillment_router, prefix="/quotations", tags=["fulfillment"])
api_router.include_router(quotation_billing_router, prefix="/quotations", tags=["billing"])
api_router.include_router(approvals_router, prefix="/approvals", tags=["approvals"])
api_router.include_router(billing_router, prefix="/invoices", tags=["billing"])
api_router.include_router(portal_public_router, prefix="/portal", tags=["portal"])
api_router.include_router(portal_router, prefix="/portal", tags=["portal"])
api_router.include_router(dashboard_router, tags=["dashboard"])
api_router.include_router(events_router, prefix="/events", tags=["events"])
