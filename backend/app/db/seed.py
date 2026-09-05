"""Idempotent database seeding: roles, demo users/customers, and Phase 1's catalogue,
pricing, warehouse and policy configuration.

Re-runnable from empty without error — every block checks for existing rows first.
Reset with: `docker compose exec backend python -m app.db.seed --reset`
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import Category, Product, ProductVariant
from app.config.settings import settings
from app.core.security import hash_password
from app.customers.models import Customer
from app.policies.models import DiscountPolicy
from app.policies.service import create_policy
from app.pricing.models import PriceList, PriceListEntry
from app.roles.models import Role
from app.subscriptions.models import SubscriptionPlan
from app.users.models import User
from app.warehouses.models import Stock, Warehouse

logger = logging.getLogger(__name__)

ADMIN_ROLE = "admin"
DEFAULT_USER_ROLE = "user"

# Permission strings from API_CONTRACT.md §5.
DEFAULT_ROLES = [
    {"name": ADMIN_ROLE, "description": "Full access", "permissions": ["*"]},
    {"name": DEFAULT_USER_ROLE, "description": "Standard user", "permissions": []},
    {
        "name": "sales_rep",
        "description": "Builds and owns quotations",
        "permissions": ["catalog:read", "quotations:read", "quotations:write", "dashboard:read"],
    },
    {
        "name": "sales_manager",
        "description": "L1 approver; manages catalogue pricing",
        "permissions": [
            "catalog:read",
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
    },
    {
        "name": "finance",
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
    },
    {
        "name": "ops",
        "description": "Owns warehouses and fulfilment",
        "permissions": ["warehouses:read", "warehouses:write", "fulfillment:read", "fulfillment:write"],
    },
]

# Demo-only credentials, one per seeded role.
DEMO_PASSWORD = "demo12345"
DEMO_USERS = [
    {"email": "rep@example.com", "full_name": "Riya Rep", "role": "sales_rep"},
    {"email": "manager@example.com", "full_name": "Manav Manager", "role": "sales_manager"},
    {"email": "finance@example.com", "full_name": "Farah Finance", "role": "finance"},
    {"email": "ops@example.com", "full_name": "Om Ops", "role": "ops"},
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
        if db.scalar(select(Role).where(Role.name == spec["name"])) is None:
            db.add(Role(**spec))
            logger.info("Seeded role: %s", spec["name"])
    db.commit()


def _seed_users(db: Session) -> None:
    if db.scalar(select(User).where(User.email == settings.admin_email)) is None:
        admin_role = db.scalar(select(Role).where(Role.name == ADMIN_ROLE))
        db.add(
            User(
                email=settings.admin_email,
                full_name="Admin",
                hashed_password=hash_password(settings.admin_password),
                role=admin_role,
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


def seed_db(db: Session) -> None:
    _seed_roles(db)
    _seed_users(db)
    _seed_customers(db)
    categories = _seed_catalog(db)
    _seed_pricing(db)
    _seed_warehouses(db)
    _seed_subscription_plans(db)
    _seed_policy(db, categories)


if __name__ == "__main__":
    import argparse

    from app.config.logging import setup_logging
    from app.db.base import Base
    from app.db.session import SessionLocal, engine

    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables first")
    args = parser.parse_args()

    if args.reset:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    with SessionLocal() as session:
        seed_db(session)
    logger.info("Seed complete.")
