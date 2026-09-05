"""Idempotent database seeding: roles, demo users/customers, and Phase 1's catalogue,
pricing, warehouse and policy configuration.

Re-runnable from empty without error — every block checks for existing rows first.
Reset with: `docker compose exec backend python -m app.db.seed --reset`
"""

import logging
import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.affinity.service import rebuild_affinity
from app.catalog.models import Category, Product, ProductVariant
from app.config.settings import settings
from app.core.security import hash_password
from app.core.tenant_context import set_current_org
from app.customers.models import Customer
from app.organizations.models import Organization
from app.policies.models import DiscountPolicy
from app.policies.service import create_policy
from app.pricing.models import PriceList, PriceListEntry
from app.quotations.models import Quotation, QuoteLine
from app.roles.models import Role
from app.subscriptions.models import SubscriptionPlan
from app.users.models import User
from app.warehouses.models import Stock, Warehouse

DEMO_ORG_NAME = "Demo Org"
DEMO_ORG_SLUG = "demo"

# Plausible co-purchase bundles, purely to give Phase 2's product-affinity computation
# (an association-rule count over real `quote_lines`) something real to compute from.
# Phase 2 scope is "compute once at seed time" — see BACKEND_PHASE_2.md Task 7.
AFFINITY_BUNDLES: list[tuple[str, ...]] = [
    ("LAP-PRO-14", "SVC-SETUP", "ACC-MOUSE", "ACC-HUB"),
    ("DSK-X1", "ACC-KEYBOARD", "ACC-MOUSE"),
    ("SVR-RACK-42U", "SVC-INSTALL", "SUB-SUPPORT-STD"),
    ("SWT-24P", "SVC-INSTALL"),
    ("LAP-PRO-14", "SUB-SUPPORT-PREM"),
    ("MON-27", "ACC-MOUSE", "ACC-KEYBOARD"),
    ("LAP-PRO-14", "ACC-MOUSE", "ACC-HUB"),
    ("DSK-X1", "SVC-SETUP", "ACC-KEYBOARD"),
]

logger = logging.getLogger(__name__)

# Human-readable role names — these are what an admin sees on the Roles screen,
# not an internal code. Nothing outside this module matches on the string value
# (RBAC checks are all against `role.permissions`, never `role.name`), so these
# are free to read naturally; only the constants below need to stay in sync with
# `DEFAULT_ROLES` / `DEMO_USERS`.
ADMIN_ROLE = "Administrator"
DEFAULT_USER_ROLE = "Standard User"
SALES_REP_ROLE = "Sales Rep"
SALES_MANAGER_ROLE = "Sales Manager"
FINANCE_ROLE = "Finance"
OPS_ROLE = "Operations"

# Permission strings from API_CONTRACT.md §5 / app/core/permissions.py.
# `dashboard_type` (Phase 3) picks which of the four dashboard layouts the frontend
# renders for the role — an admin can re-point it on the Roles screen.
DEFAULT_ROLES = [
    {"name": ADMIN_ROLE, "description": "Full access", "permissions": ["*"], "dashboard_type": "super_admin"},
    {"name": DEFAULT_USER_ROLE, "description": "Standard user", "permissions": [], "dashboard_type": "generic"},
    {
        "name": SALES_REP_ROLE,
        "description": "Builds and owns quotations",
        "permissions": [
            "catalog:read",
            "customers:read",
            "quotations:read",
            "quotations:write",
            "dashboard:read",
        ],
        "dashboard_type": "generic",
    },
    {
        "name": SALES_MANAGER_ROLE,
        "description": "L1 approver; manages catalogue pricing",
        "permissions": [
            "catalog:read",
            "customers:read",
            "pricing:read",
            "pricing:write",
            "quotations:read",
            "quotations:write",
            "approvals:l1",
            "fulfillment:read",
            "fulfillment:write",
            "dashboard:read",
            "reports:read",
            "reports:export",
        ],
        "dashboard_type": "sales_manager",
    },
    {
        "name": FINANCE_ROLE,
        "description": "L2 approver; owns policy, subscriptions and billing",
        "permissions": [
            "policies:read",
            "policies:write",
            "subscriptions:read",
            "subscriptions:write",
            "approvals:l2",
            "billing:read",
            "billing:write",
            "dashboard:read",
            "reports:read",
            "reports:export",
        ],
        "dashboard_type": "finance_ops",
    },
    {
        "name": OPS_ROLE,
        "description": "Owns warehouses and fulfilment",
        "permissions": ["warehouses:read", "warehouses:write", "fulfillment:read", "fulfillment:write"],
        "dashboard_type": "finance_ops",
    },
]

# Demo-only credentials, one per seeded role.
DEMO_PASSWORD = "demo12345"
DEMO_USERS = [
    {"email": "rep@example.com", "full_name": "Riya Rep", "role": SALES_REP_ROLE},
    # A second rep with a deliberately looser discount habit, so per-rep z-scores
    # (Phase 3 anomaly detection) are visibly different. See `_seed_history_v2`.
    {"email": "rep2@example.com", "full_name": "Dev Discount", "role": SALES_REP_ROLE},
    {"email": "manager@example.com", "full_name": "Manav Manager", "role": SALES_MANAGER_ROLE},
    {"email": "finance@example.com", "full_name": "Farah Finance", "role": FINANCE_ROLE},
    {"email": "ops@example.com", "full_name": "Om Ops", "role": OPS_ROLE},
]

DEMO_CUSTOMER_EMAIL = "customer@example.com"
DEMO_CUSTOMER_PASSWORD = "customer12345"
DEMO_CUSTOMERS = [
    {
        "name": "Acme Corp",
        "email": DEMO_CUSTOMER_EMAIL,
        "company": "Acme Corp",
        "tier": "gold",
        "password": DEMO_CUSTOMER_PASSWORD,
    },
    {
        "name": "Beta Industries",
        "email": "beta@example.com",
        "company": "Beta Industries",
        "tier": "silver",
        "password": "customer12345",
    },
    {
        "name": "Corex Ltd",
        "email": "corex@example.com",
        "company": "Corex Ltd",
        "tier": "bronze",
        "password": "customer12345",
    },
]

CATEGORIES = [
    {"name": "Hardware", "code": "HARDWARE", "description": "Physical equipment"},
    {"name": "Services", "code": "SERVICES", "description": "One-time professional services"},
    {"name": "Subscriptions", "code": "SUBSCRIPTIONS", "description": "Recurring plans"},
    {"name": "Accessories", "code": "ACCESSORIES", "description": "Small peripherals and add-ons"},
]

# (sku, name, category_code, unit, list_minor, cost_minor, tax_bps, is_promoted, line_type)
PRODUCTS = [
    ("LAP-PRO-14", "Laptop Pro 14", "HARDWARE", "unit", 8_000_000, 6_000_000, 1800, True, "one_time"),
    ("DSK-X1", "Desktop Workstation X1", "HARDWARE", "unit", 6_500_000, 4_800_000, 1800, False, "one_time"),
    ("SVR-RACK-42U", "Server Rack 42U", "HARDWARE", "unit", 16_600_000, 12_500_000, 1800, False, "one_time"),
    ("SWT-24P", "Network Switch 24-Port", "HARDWARE", "unit", 2_200_000, 1_500_000, 1800, False, "one_time"),
    ("MON-27", '27" Monitor', "HARDWARE", "unit", 1_800_000, 1_250_000, 1800, False, "one_time"),
    ("SVC-SETUP", "Setup Service", "SERVICES", "service", 2_000_000, 650_000, 1800, False, "one_time"),
    ("SVC-INSTALL", "Installation Service", "SERVICES", "service", 1_200_000, 400_000, 1800, False, "one_time"),
    ("SVC-ONBOARD", "Onboarding & Training", "SERVICES", "service", 1_500_000, 500_000, 1800, False, "one_time"),
    ("SUB-SUPPORT-STD", "Standard Support Plan", "SUBSCRIPTIONS", "licence", 500_000, 150_000, 1800, True, "subscription"),
    ("SUB-SUPPORT-PREM", "Premium Support Plan", "SUBSCRIPTIONS", "licence", 1_200_000, 350_000, 1800, False, "subscription"),
    ("SUB-BACKUP", "Cloud Backup Plan", "SUBSCRIPTIONS", "licence", 300_000, 80_000, 1800, False, "subscription"),
    ("ACC-MOUSE", "Wireless Mouse", "ACCESSORIES", "unit", 120_000, 60_000, 1800, False, "one_time"),
    ("ACC-KEYBOARD", "Mechanical Keyboard", "ACCESSORIES", "unit", 350_000, 180_000, 1800, False, "one_time"),
    ("ACC-HUB", "USB-C Docking Hub", "ACCESSORIES", "unit", 450_000, 220_000, 1800, False, "one_time"),
]

SUBSCRIPTION_PLANS = [
    {
        "name": "Monthly Standard",
        "interval": "monthly",
        "billing_cycles": None,
        "proration_enabled": True,
        "cancellation_notice_days": 15,
        "refund_policy": "prorated",
    },
    {
        "name": "Quarterly Plus",
        "interval": "quarterly",
        "billing_cycles": 4,
        "proration_enabled": True,
        "cancellation_notice_days": 30,
        "refund_policy": "credit_note",
    },
    {
        "name": "Annual Commitment",
        "interval": "yearly",
        "billing_cycles": 1,
        "proration_enabled": False,
        "cancellation_notice_days": 30,
        "refund_policy": "none",
    },
]

WAREHOUSES = [
    {"name": "Main Warehouse", "code": "MAIN", "shipping_cost_weight": 30, "replenishment_threshold": 10},
    {"name": "East Depot", "code": "EAST", "shipping_cost_weight": 70, "replenishment_threshold": 5},
]

# DECISION_ENGINE.md §2 defaults.
POLICY_V1 = {
    "tier_ceilings": [
        {"tier": "bronze", "ceiling_bps": 500},
        {"tier": "silver", "ceiling_bps": 1000},
        {"tier": "gold", "ceiling_bps": 1500},
    ],
    # category_ceilings filled in at seed time once category IDs are known.
    "category_defaults": {
        "HARDWARE": {"ceiling_bps": 1500, "margin_floor_bps": 1800},
        "SERVICES": {"ceiling_bps": 1000, "margin_floor_bps": 3500},
        "SUBSCRIPTIONS": {"ceiling_bps": 800, "margin_floor_bps": 4000},
        "ACCESSORIES": {"ceiling_bps": 1500, "margin_floor_bps": 1800},
    },
    "weights": {
        "w_blended_bps": 4500,
        "w_worst_bps": 3500,
        "w_value_bps": 1000,
        "w_margin_bps": 1000,
        "scale_overage_bps": 1000,
        "value_reference_minor": 50_000_000,
        "margin_scale_bps": 500,
    },
    "thresholds": {
        "t1_l1_required": 20,
        "t2_l2_required": 55,
        "hard_breach_bps": 500,
        "finance_value_floor_minor": 100_000_000,
    },
    "upsell": {
        "min_margin_bps": 1000,
        "w_lift_bps": 5000,
        "w_margin_bps": 3000,
        "w_promo_bps": 2000,
    },
    "anomaly": {"sigma_multiplier_bps": 20000, "min_sample_size": 5},
    "stalled_after_days": 7,
}


def _seed_roles(db: Session) -> None:
    for spec in DEFAULT_ROLES:
        existing = db.scalar(select(Role).where(Role.name == spec["name"]))
        if existing is None:
            db.add(Role(**spec))
            logger.info("Seeded role: %s", spec["name"])
        elif existing.dashboard_type != spec["dashboard_type"]:
            # Keep the default roles' dashboard assignment current on re-seed; an
            # admin's own custom roles / overrides are untouched.
            existing.dashboard_type = spec["dashboard_type"]
    db.commit()


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


def unique_slug(db: Session, name: str) -> str:
    """A URL-safe slug for `name`, suffixed `-2`, `-3`, … until it's unused."""
    base = _slugify(name)
    candidate = base
    n = 2
    while db.scalar(select(Organization).where(Organization.slug == candidate)) is not None:
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def seed_organization(db: Session, org: Organization) -> None:
    """Minimal bootstrap for a newly registered organization: its RBAC roles, a
    default price list, and one active discount policy. The caller must have pinned
    the tenant context to `org` first (so writes are stamped with its `org_id`).
    Catalogue, warehouses, customers and additional members are left for the org's
    admin to create."""
    _seed_roles(db)

    if db.scalar(select(PriceList).where(PriceList.is_default.is_(True))) is None:
        db.add(PriceList(name="Default", tier=None, currency="INR", is_default=True))
        db.commit()
        logger.info("Seeded default price list for org %d", org.id)

    if db.scalar(select(DiscountPolicy)) is None:
        policy = create_policy(
            db,
            tier_ceilings=POLICY_V1["tier_ceilings"],
            category_ceilings=[],  # no categories yet — admin adds them, then edits the policy
            weights=POLICY_V1["weights"],
            thresholds=POLICY_V1["thresholds"],
            upsell=POLICY_V1["upsell"],
            anomaly=POLICY_V1["anomaly"],
            stalled_after_days=POLICY_V1["stalled_after_days"],
        )
        policy.is_active = True
        policy.activated_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Seeded active discount policy v%d for org %d", policy.version, org.id)


def _get_or_create_demo_org(db: Session) -> Organization:
    org = db.scalar(select(Organization).where(Organization.slug == DEMO_ORG_SLUG))
    if org is None:
        org = Organization(name=DEMO_ORG_NAME, slug=DEMO_ORG_SLUG)
        db.add(org)
        db.commit()
        db.refresh(org)
        logger.info("Seeded organization: %s", DEMO_ORG_NAME)
    return org


def _seed_users(db: Session) -> None:
    if db.scalar(select(User).where(User.email == settings.admin_email)) is None:
        admin_role = db.scalar(select(Role).where(Role.name == ADMIN_ROLE))
        db.add(
            User(
                email=settings.admin_email,
                full_name="Admin",
                hashed_password=hash_password(settings.admin_password),
                role=admin_role,
                is_org_owner=True,
            )
        )
        db.commit()
        logger.info("Seeded admin user: %s", settings.admin_email)

    for spec in DEMO_USERS:
        if db.scalar(select(User).where(User.email == spec["email"])) is not None:
            continue
        role = db.scalar(select(Role).where(Role.name == spec["role"]))
        db.add(
            User(
                email=spec["email"],
                full_name=spec["full_name"],
                hashed_password=hash_password(DEMO_PASSWORD),
                role=role,
            )
        )
        logger.info("Seeded demo user: %s", spec["email"])
    db.commit()


def _seed_customers(db: Session) -> None:
    for spec in DEMO_CUSTOMERS:
        if db.scalar(select(Customer).where(Customer.email == spec["email"])) is not None:
            continue
        db.add(
            Customer(
                name=spec["name"],
                email=spec["email"],
                company=spec["company"],
                tier=spec["tier"],
                hashed_password=hash_password(spec["password"]),
                portal_enabled=True,
            )
        )
        logger.info("Seeded demo customer: %s", spec["email"])
    db.commit()


def _seed_catalog(db: Session) -> dict[str, Category]:
    categories: dict[str, Category] = {}
    for spec in CATEGORIES:
        category = db.scalar(select(Category).where(Category.code == spec["code"]))
        if category is None:
            category = Category(**spec)
            db.add(category)
            db.flush()
            logger.info("Seeded category: %s", spec["code"])
        categories[spec["code"]] = category
    db.commit()

    for sku, name, cat_code, unit, list_minor, cost_minor, tax_bps, is_promoted, line_type in PRODUCTS:
        if db.scalar(select(Product).where(Product.sku == sku)) is not None:
            continue
        db.add(
            Product(
                sku=sku,
                name=name,
                category_id=categories[cat_code].id,
                unit=unit,
                list_price_minor=list_minor,
                cost_price_minor=cost_minor,
                tax_bps=tax_bps,
                is_promoted=is_promoted,
                line_type=line_type,
                currency="INR",
                is_active=True,
            )
        )
        logger.info("Seeded product: %s", sku)
    db.commit()

    laptop = db.scalar(select(Product).where(Product.sku == "LAP-PRO-14"))
    if laptop is not None and not laptop.variants:
        db.add_all(
            [
                ProductVariant(product_id=laptop.id, attribute="RAM", value="16GB", extra_price_minor=0),
                ProductVariant(
                    product_id=laptop.id, attribute="RAM", value="32GB", extra_price_minor=800_000
                ),
            ]
        )
        db.commit()
        logger.info("Seeded variants for LAP-PRO-14")

    return categories


def _seed_pricing(db: Session) -> None:
    default_list = db.scalar(select(PriceList).where(PriceList.is_default.is_(True)))
    if default_list is None:
        default_list = PriceList(name="Default", tier=None, currency="INR", is_default=True)
        db.add(default_list)
        db.commit()
        logger.info("Seeded price list: Default")

    gold_list = db.scalar(select(PriceList).where(PriceList.tier == "gold"))
    if gold_list is None:
        gold_list = PriceList(name="Gold Tier", tier="gold", currency="INR", is_default=False)
        db.add(gold_list)
        db.commit()
        logger.info("Seeded price list: Gold Tier")

    setup_service = db.scalar(select(Product).where(Product.sku == "SVC-SETUP"))
    if setup_service is not None and not db.scalar(
        select(PriceListEntry).where(
            PriceListEntry.price_list_id == gold_list.id,
            PriceListEntry.product_id == setup_service.id,
        )
    ):
        db.add(
            PriceListEntry(
                price_list_id=gold_list.id,
                product_id=setup_service.id,
                variant_id=None,
                override_price_minor=1_800_000,  # ₹18,000 instead of ₹20,000 list
                extra_discount_bps=0,
            )
        )
        db.commit()
        logger.info("Seeded Gold price list entry for SVC-SETUP")


def _seed_warehouses(db: Session) -> None:
    warehouses: dict[str, Warehouse] = {}
    for spec in WAREHOUSES:
        warehouse = db.scalar(select(Warehouse).where(Warehouse.code == spec["code"]))
        if warehouse is None:
            warehouse = Warehouse(**spec)
            db.add(warehouse)
            db.flush()
            logger.info("Seeded warehouse: %s", spec["code"])
        warehouses[spec["code"]] = warehouse
    db.commit()

    products = db.scalars(select(Product)).all()
    if not products:
        return

    created = 0
    for index, product in enumerate(products):
        for code, warehouse in warehouses.items():
            if db.scalar(
                select(Stock).where(Stock.product_id == product.id, Stock.warehouse_id == warehouse.id)
            ):
                continue
            # Deliberately uneven: Main is well-stocked, East is thin/patchy so
            # Phase 3's split-shipment and backorder paths have real fixtures.
            on_hand = 60 if code == "MAIN" else (index % 4) * 2  # 0, 2, 4, 6 cycling
            db.add(Stock(product_id=product.id, warehouse_id=warehouse.id, on_hand=on_hand, reserved=0))
            created += 1
    if created:
        db.commit()
        logger.info("Seeded %d stock rows across %d warehouses", created, len(warehouses))


def _seed_subscription_plans(db: Session) -> None:
    plans: dict[str, SubscriptionPlan] = {}
    for spec in SUBSCRIPTION_PLANS:
        plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.name == spec["name"]))
        if plan is None:
            plan = SubscriptionPlan(**spec)
            db.add(plan)
            db.flush()
            logger.info("Seeded subscription plan: %s", spec["name"])
        plans[spec["name"]] = plan
    db.commit()

    monthly = plans.get("Monthly Standard")
    if monthly is not None:
        subscription_skus = ["SUB-SUPPORT-STD", "SUB-SUPPORT-PREM", "SUB-BACKUP"]
        products = db.scalars(select(Product).where(Product.sku.in_(subscription_skus))).all()
        changed = False
        for product in products:
            if product.subscription_plan_id is None:
                product.subscription_plan_id = monthly.id
                changed = True
        if changed:
            db.commit()
            logger.info("Linked subscription products to Monthly Standard plan")


def _seed_policy(db: Session, categories: dict[str, Category]) -> None:
    if db.scalar(select(DiscountPolicy)) is not None:
        return

    category_ceilings = [
        {
            "category_id": categories[code].id,
            "ceiling_bps": defaults["ceiling_bps"],
            "margin_floor_bps": defaults["margin_floor_bps"],
        }
        for code, defaults in POLICY_V1["category_defaults"].items()
        if code in categories
    ]

    policy = create_policy(
        db,
        tier_ceilings=POLICY_V1["tier_ceilings"],
        category_ceilings=category_ceilings,
        weights=POLICY_V1["weights"],
        thresholds=POLICY_V1["thresholds"],
        upsell=POLICY_V1["upsell"],
        anomaly=POLICY_V1["anomaly"],
        stalled_after_days=POLICY_V1["stalled_after_days"],
    )
    policy.is_active = True
    policy.activated_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Seeded and activated discount policy version %d", policy.version)


def _seed_historical_quotations_and_affinity(db: Session) -> None:
    """Synthetic, terminal ("paid") historical orders — real `quote_lines` rows for
    `rebuild_affinity` to compute real co-purchase statistics from, rather than
    starting the upsell panel empty. Runs once: skipped the moment any quotation
    (synthetic or a real user's) already exists."""
    if db.scalar(select(Quotation)) is not None:
        return

    rep = db.scalar(select(User).where(User.email == "rep@example.com"))
    customers = db.scalars(select(Customer)).all()
    products_by_sku = {p.sku: p for p in db.scalars(select(Product)).all()}
    policy = db.scalar(select(DiscountPolicy).where(DiscountPolicy.is_active.is_(True)))
    if rep is None or not customers or policy is None:
        return

    created = 0
    for i in range(24):
        bundle = AFFINITY_BUNDLES[i % len(AFFINITY_BUNDLES)]
        customer = customers[i % len(customers)]
        quotation = Quotation(
            reference="PENDING",
            customer_id=customer.id,
            owner_rep_id=rep.id,
            status="paid",
            version=1,
            policy_version=policy.version,
            order_discount_bps=0,
            currency="INR",
        )
        db.add(quotation)
        db.flush()
        quotation.reference = f"QT-2025-{quotation.id:06d}"

        for position, sku in enumerate(bundle):
            product = products_by_sku.get(sku)
            if product is None:
                continue
            db.add(
                QuoteLine(
                    quotation_id=quotation.id,
                    product_id=product.id,
                    variant_id=None,
                    category_id=product.category_id,
                    line_type=product.line_type,
                    subscription_plan_id=product.subscription_plan_id,
                    quantity=1,
                    unit_price_minor=product.list_price_minor,
                    cost_price_minor=product.cost_price_minor,
                    discount_bps=0,
                    added_from_suggestion=False,
                    position=position,
                )
            )
        created += 1
    db.commit()
    logger.info("Seeded %d historical quotations for affinity computation", created)

    affinity_rows = rebuild_affinity(db)
    logger.info("Rebuilt product affinity: %d rows", affinity_rows)


def _backdate(quotation: Quotation, when: datetime) -> None:
    quotation.created_at = when
    quotation.updated_at = when
    quotation.last_activity_at = when


def _seed_history_v2(db: Session) -> None:
    """`--history`: ~180 confirmed/paid quotations spread over 12 backdated months
    with two distinct per-rep discount profiles (Riya conservative ~6%, Dev loose
    ~14%), so Phase 3's affinity + anomaly detection have real signal. Then
    `rebuild_affinity` and `rebuild_rep_stats`. Idempotent: skipped once >100
    quotations exist."""
    import random

    from app.dashboard.service import rebuild_rep_stats

    if (db.scalar(select(func.count()).select_from(Quotation)) or 0) > 100:
        logger.info("history already seeded — skipping --history")
        return

    rng = random.Random(42)
    reps = {
        u.email: u
        for u in db.scalars(
            select(User).where(User.email.in_(["rep@example.com", "rep2@example.com"]))
        )
    }
    profiles = {
        "rep@example.com": (600, 180),   # mean 6.0%, sd ~1.8%
        "rep2@example.com": (1400, 300),  # mean 14.0%, sd ~3.0%
    }
    customers = db.scalars(select(Customer)).all()
    products_by_sku = {p.sku: p for p in db.scalars(select(Product)).all()}
    policy = db.scalar(select(DiscountPolicy).where(DiscountPolicy.is_active.is_(True)))
    if len(reps) < 2 or not customers or policy is None:
        logger.warning("--history preconditions missing — skipping")
        return

    now = datetime.now(timezone.utc)
    created = 0
    for i in range(180):
        email = "rep@example.com" if i % 2 == 0 else "rep2@example.com"
        rep = reps[email]
        mean_bps, sd_bps = profiles[email]
        disc = max(0, min(2500, int(rng.gauss(mean_bps, sd_bps))))
        bundle = AFFINITY_BUNDLES[i % len(AFFINITY_BUNDLES)]
        customer = customers[i % len(customers)]
        when = now - timedelta(days=rng.randint(5, 360))

        quotation = Quotation(
            reference="PENDING",
            customer_id=customer.id,
            owner_rep_id=rep.id,
            status="paid",
            version=1,
            policy_version=policy.version,
            order_discount_bps=disc,
            currency="INR",
        )
        db.add(quotation)
        db.flush()
        quotation.reference = f"QT-{when.year}-{quotation.id:06d}"
        quotation.order_number = f"SO-{when.year}-{quotation.id:06d}"
        _backdate(quotation, when)

        for position, sku in enumerate(bundle):
            product = products_by_sku.get(sku)
            if product is None:
                continue
            db.add(
                QuoteLine(
                    quotation_id=quotation.id,
                    product_id=product.id,
                    variant_id=None,
                    category_id=product.category_id,
                    line_type=product.line_type,
                    subscription_plan_id=product.subscription_plan_id,
                    quantity=rng.randint(1, 4),
                    unit_price_minor=product.list_price_minor,
                    cost_price_minor=product.cost_price_minor,
                    discount_bps=0,
                    added_from_suggestion=False,
                    position=position,
                )
            )
        created += 1
    db.commit()
    logger.info("Seeded %d backdated historical quotations (--history)", created)

    logger.info("Rebuilt product affinity: %d rows", rebuild_affinity(db))
    logger.info("Rebuilt rep discount stats for %d reps", rebuild_rep_stats(db))


def _seed_demo_fixtures(db: Session) -> None:
    """`--demo`: the specific fixtures the 5-minute walkthrough leans on."""
    from app.core.enums import QuoteStatus
    from app.events.service import record_event
    from app.quotations.transitions import transition

    rep = db.scalar(select(User).where(User.email == "rep@example.com"))
    products = {p.sku: p for p in db.scalars(select(Product)).all()}
    if rep is None:
        return

    # `--demo` is idempotent at the coarse grain: once a `sent` quote exists the
    # fixtures have already been laid down.
    if db.scalar(select(func.count()).select_from(Quotation).where(Quotation.status == QuoteStatus.SENT.value)):
        logger.info("demo fixtures already present — skipping --demo")
        return

    def _quote_for(company: str, sku: str, qty: int, *, status_flow: list[str], age_days: int = 0) -> Quotation | None:
        customer = db.scalar(select(Customer).where(Customer.company == company))
        product = products.get(sku)
        if customer is None or product is None:
            return None
        quotation = Quotation(
            reference="PENDING",
            customer_id=customer.id,
            owner_rep_id=rep.id,
            status=QuoteStatus.DRAFT.value,
            version=1,
            policy_version=db.scalar(select(DiscountPolicy.version).where(DiscountPolicy.is_active.is_(True))),
            order_discount_bps=0,
            currency="INR",
        )
        db.add(quotation)
        db.flush()
        quotation.reference = f"QT-{datetime.now(timezone.utc).year}-{quotation.id:06d}"
        db.add(
            QuoteLine(
                quotation_id=quotation.id,
                product_id=product.id,
                variant_id=None,
                category_id=product.category_id,
                line_type=product.line_type,
                subscription_plan_id=product.subscription_plan_id,
                quantity=qty,
                unit_price_minor=product.list_price_minor,
                cost_price_minor=product.cost_price_minor,
                discount_bps=0,
                position=0,
            )
        )
        record_event(db, quotation, "quote.created", rep, summary="Demo fixture created.", payload={})
        db.flush()
        db.refresh(quotation)  # so quotation.lines is populated for the engine on transition
        version = quotation.version
        for to in status_flow:
            transition(db, quotation, to, rep, expected_version=version)
            version = quotation.version
        if age_days:
            stale = datetime.now(timezone.utc) - timedelta(days=age_days)
            quotation.last_activity_at = stale
            quotation.updated_at = stale
        db.commit()
        return quotation

    # Beta Industries: sat untouched for 9 days -> stalled_deal alert fires.
    _quote_for("Beta Industries", "LAP-PRO-14", 2, status_flow=[QuoteStatus.APPROVED.value, QuoteStatus.SENT.value], age_days=9)
    # Corex Ltd: `sent` with a live magic link, for the two-window portal demo.
    _quote_for("Corex Ltd", "DSK-X1", 1, status_flow=[QuoteStatus.APPROVED.value, QuoteStatus.SENT.value])
    # A visible split: stock 3 in Main / 5 in East, ordered qty 6.
    split = _quote_for("Acme Corp", "MON-27", 6, status_flow=[QuoteStatus.APPROVED.value, QuoteStatus.SENT.value, QuoteStatus.CONFIRMED.value])
    if split is not None:
        mon = products["MON-27"]
        for st in db.scalars(select(Stock).where(Stock.product_id == mon.id)):
            st.on_hand = 3 if st.warehouse.code == "MAIN" else 5
            st.reserved = 0
    # A visible backorder: total stock 2, ordered qty 5.
    bo = _quote_for("Acme Corp", "SWT-24P", 5, status_flow=[QuoteStatus.APPROVED.value, QuoteStatus.SENT.value, QuoteStatus.CONFIRMED.value])
    if bo is not None:
        swt = products["SWT-24P"]
        first = True
        for st in db.scalars(select(Stock).where(Stock.product_id == swt.id)):
            st.on_hand = 2 if first else 0
            st.reserved = 0
            first = False
    db.commit()
    logger.info("Seeded demo fixtures (--demo)")


def seed_db(db: Session, *, history: bool = False, demo: bool = False) -> None:
    demo_org = _get_or_create_demo_org(db)
    set_current_org(db, demo_org.id)

    _seed_roles(db)
    _seed_users(db)
    _seed_customers(db)
    categories = _seed_catalog(db)
    _seed_pricing(db)
    _seed_warehouses(db)
    _seed_subscription_plans(db)
    _seed_policy(db, categories)
    _seed_historical_quotations_and_affinity(db)
    if history:
        _seed_history_v2(db)
    if demo:
        _seed_demo_fixtures(db)


if __name__ == "__main__":
    import argparse

    from app.config.logging import setup_logging
    from app.db.base import Base
    from app.db.session import SessionLocal, engine

    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables first")
    parser.add_argument("--history", action="store_true", help="Seed 12 months of backdated history + rebuild affinity/rep stats")
    parser.add_argument("--demo", action="store_true", help="Seed the 5-minute-walkthrough demo fixtures")
    args = parser.parse_args()

    if args.reset:
        # `Base.metadata` only knows about tables whose model module has actually been
        # imported somewhere in this process — without these, `drop_all` can't see
        # (e.g.) `quote_approvals`'s FK to `quotations` and tries to drop out of order.
        from app.affinity import models as _affinity_models  # noqa: F401
        from app.approvals import models as _approvals_models  # noqa: F401
        from app.billing import models as _billing_models  # noqa: F401
        from app.core import idempotency as _idempotency_models  # noqa: F401
        from app.dashboard import models as _dashboard_models  # noqa: F401
        from app.events import models as _events_models  # noqa: F401
        from app.fulfillment import models as _fulfillment_models  # noqa: F401
        from app.portal import models as _portal_models  # noqa: F401

        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        seed_db(session, history=args.history, demo=args.demo)
    logger.info("Seed complete.")
