"""Idempotent database seeding: RBAC roles, internal users, portal customers, the
Phase 1 configuration surface (catalogue, pricing, warehouses, subscription plans,
discount policy) and — behind flags — a year of backdated history plus the exact
fixtures the QA plan / 5-minute demo lean on.

Re-runnable from empty without error — every block checks for existing rows first.

Full demo reset (what the QA plan documents):

    docker compose exec backend python -m app.db.seed --reset --history --demo

`--history` and `--demo` are designed to be run together; `--demo` degrades
gracefully (logs a warning, skips that one fixture) if a `--history` precondition
such as a rep's discount baseline is missing.
"""

import logging
import random
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
from app.policies.service import activate_policy, create_policy
from app.pricing.models import PriceList, PriceListEntry
from app.quotations.models import Quotation, QuoteLine
from app.roles.models import Role
from app.subscriptions.models import SubscriptionPlan
from app.users.models import User
from app.warehouses.models import Stock, Warehouse

DEMO_ORG_NAME = "Demo Org"
DEMO_ORG_SLUG = "demo"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Affinity source bundles
# ---------------------------------------------------------------------------
# Plausible co-purchase bundles, used only to give Phase 2's product-affinity
# computation (an association-rule count over real `quote_lines`) real orders to
# learn from rather than starting the upsell panel empty. Every SKU here exists in
# PRODUCTS below.
AFFINITY_BUNDLES: list[tuple[str, ...]] = [
    ("LAP-PRO-14", "SVC-SETUP", "ACC-MOUSE", "ACC-HUB"),
    ("LAP-PRO-14", "SUB-SUPPORT-STD", "SW-AV-ENDPOINT"),
    ("LAP-PRO-16", "ACC-DOCK-PRO", "ACC-HEADSET", "SUB-SUPPORT-PREM"),
    ("DSK-X1", "ACC-KEYBOARD", "ACC-MOUSE", "MON-27"),
    ("DSK-PRO-GPU", "MON-32-4K", "ACC-MONITOR-ARM"),
    ("SVR-RACK-42U", "SVC-INSTALL", "UPS-3000", "SUB-SUPPORT-ENT"),
    ("SVR-STORAGE-24", "SUB-BACKUP", "SW-BACKUP-SRV", "SVC-MIGRATE"),
    ("SWT-24P", "SVC-INSTALL", "CAB-RACK-40"),
    ("SWT-48P", "AP-WIFI6", "FW-UTM", "SVC-NETWORK-AUDIT"),
    ("RTR-ENT", "FW-UTM", "SVC-NETWORK-AUDIT", "SUB-SECURITY"),
    ("MON-32-4K", "ACC-MONITOR-ARM", "ACC-DOCK-PRO"),
    ("TAB-10", "ACC-BACKPACK", "SW-MDM-SEAT", "SUB-PATCH"),
    ("LAP-ESS-15", "ACC-MOUSE", "ACC-KEYBOARD", "SW-OFFICE-PERP"),
    ("AP-WIFI6E", "SWT-48P", "CAB-RACK-40", "SFP-10G-4"),
]

# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------
# Human-readable role names — what an admin sees on the Roles screen. RBAC checks
# are all against `role.permissions`, never `role.name`, so the strings read
# naturally; only the constants below need to stay in sync with `DEFAULT_ROLES`
# and `DEMO_USERS`.
ADMIN_ROLE = "Administrator"
DEFAULT_USER_ROLE = "Standard User"
SALES_REP_ROLE = "Sales Rep"
SALES_MANAGER_ROLE = "Sales Manager"
FINANCE_ROLE = "Finance"
OPS_ROLE = "Operations"

# Permission strings from API_CONTRACT.md §5 / app/core/permissions.py.
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
            "fulfillment:read",
            "dashboard:read",
            "reports:read",
            "reports:export",
        ],
        "dashboard_type": "finance_ops",
    },
    {
        "name": OPS_ROLE,
        "description": "Owns warehouses and fulfilment",
        "permissions": [
            "warehouses:read",
            "warehouses:write",
            "fulfillment:read",
            "fulfillment:write",
            "catalog:read",
            "customers:read",
            "quotations:read",
            "dashboard:read",
        ],
        "dashboard_type": "finance_ops",
    },
]

# ---------------------------------------------------------------------------
# Internal users — one clear owner per role, plus a second of each so the
# reports "filter by rep", approval-queue and deal-health screens have variety.
# ---------------------------------------------------------------------------
DEMO_PASSWORD = "demo12345"
DEMO_USERS = [
    # reps
    {"email": "rep@example.com", "full_name": "Riya Rao", "role": SALES_REP_ROLE},
    # A deliberately loose discounter, so per-rep z-scores (Phase 3 anomaly
    # detection) are visibly different — see `_seed_history_v2`.
    {"email": "rep2@example.com", "full_name": "Dev Kapoor", "role": SALES_REP_ROLE},
    # Third rep gets only a handful of historical quotes on purpose: below the
    # policy's `min_sample_size`, so anomaly detection correctly stays silent.
    {"email": "rep3@example.com", "full_name": "Sam Sequeira", "role": SALES_REP_ROLE},
    {"email": "rep4@example.com", "full_name": "Priya Nair", "role": SALES_REP_ROLE},
    # managers (L1)
    {"email": "manager@example.com", "full_name": "Manav Mehta", "role": SALES_MANAGER_ROLE},
    {"email": "manager2@example.com", "full_name": "Meera Iyer", "role": SALES_MANAGER_ROLE},
    # finance (L2)
    {"email": "finance@example.com", "full_name": "Farah Sheikh", "role": FINANCE_ROLE},
    {"email": "finance2@example.com", "full_name": "Rohan Das", "role": FINANCE_ROLE},
    # operations / fulfilment
    {"email": "ops@example.com", "full_name": "Omar Farooq", "role": OPS_ROLE},
    {"email": "ops2@example.com", "full_name": "Nisha Pillai", "role": OPS_ROLE},
]

# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
DEMO_CUSTOMER_EMAIL = "customer@example.com"
DEMO_CUSTOMER_PASSWORD = "customer12345"

# The three the QA plan and the walkthrough name explicitly. Everything else is
# generated below to give the lists real volume.
NAMED_CUSTOMERS = [
    {
        "name": "Acme Corp",
        "email": DEMO_CUSTOMER_EMAIL,
        "company": "Acme Corp",
        "phone": "+91 22 4001 2200",
        "tier": "gold",
        "password": DEMO_CUSTOMER_PASSWORD,
        "portal_enabled": True,
    },
    {
        "name": "Beta Industries",
        "email": "beta@example.com",
        "company": "Beta Industries",
        "phone": "+91 80 4110 8890",
        "tier": "silver",
        "password": "customer12345",
        "portal_enabled": True,
    },
    {
        "name": "Corex Ltd",
        "email": "corex@example.com",
        "company": "Corex Ltd",
        "phone": "+91 44 2851 7345",
        "tier": "bronze",
        "password": "customer12345",
        "portal_enabled": True,
    },
    # Portal access explicitly revoked — for the "disabled portal user / old token"
    # security checks. Still a real customer an internal user can quote for.
    {
        "name": "Nimbus Data Systems",
        "email": "nimbus@example.com",
        "company": "Nimbus Data Systems",
        "phone": "+91 20 6720 4455",
        "tier": "gold",
        "password": "customer12345",
        "portal_enabled": False,
    },
]

# Realistic B2B buyers. (company, city) — tier + portal flag are assigned on a
# rotation below so all three tiers and both portal states are well represented.
GENERATED_CUSTOMER_COMPANIES = [
    ("Vertex Manufacturing", "Pune"), ("Helios Energy", "Ahmedabad"),
    ("Quill Publishing House", "Kolkata"), ("Ironclad Logistics", "Nagpur"),
    ("BlueOrbit Analytics", "Bengaluru"), ("Meridian Health Group", "Hyderabad"),
    ("Cascade Retail Partners", "Surat"), ("Northwind Traders", "Chandigarh"),
    ("Sterling Financial Services", "Mumbai"), ("Cobalt Robotics", "Chennai"),
    ("Greenfield Agritech", "Indore"), ("Apex Construction", "Jaipur"),
    ("Lumen Media Networks", "Noida"), ("Riverstone Hospitality", "Goa"),
    ("Pinnacle Education Trust", "Lucknow"), ("Onyx Mining Corporation", "Ranchi"),
    ("Sable Automotive", "Gurugram"), ("Fairwind Shipping", "Kochi"),
    ("Latitude Travel Group", "Thiruvananthapuram"), ("Quantum Semiconductors", "Mohali"),
    ("Everest Pharmaceuticals", "Baddi"), ("Copperline Electricals", "Coimbatore"),
    ("Driftwood Furniture", "Jodhpur"), ("Solaris Textiles", "Tiruppur"),
    ("Falcon Aerospace Components", "Bengaluru"), ("Harbor Foods", "Visakhapatnam"),
    ("Zephyr Cloud Solutions", "Hyderabad"), ("Granite Legal LLP", "New Delhi"),
    ("Marigold FMCG", "Kanpur"), ("Tidal Water Utilities", "Nashik"),
    ("Beacon Insurance Brokers", "Mumbai"), ("Cedarworks Packaging", "Vadodara"),
    ("Polaris Defence Systems", "Pune"), ("Amber Ceramics", "Morbi"),
    ("Northgate Warehousing", "Bhiwandi"), ("Silverline Diagnostics", "Chennai"),
    ("Windmill Renewables", "Rajkot"), ("Kingfisher Breweries Supply", "Bengaluru"),
    ("Stonebridge Realty", "Gurugram"), ("Cyan Print & Signage", "Faridabad"),
    ("Terra Firma Surveyors", "Dehradun"), ("Brightline Rail Contractors", "Bhopal"),
    ("Pacific Seafood Exports", "Mangaluru"), ("Vanguard Security Services", "Hyderabad"),
    ("Auric Jewellers Group", "Jaipur"), ("Meadowlark Dairy Co-op", "Anand"),
    ("Ridgeway Cement", "Chandrapur"), ("Halcyon Event Management", "Mumbai"),
    ("Torchbearer NGO Network", "New Delhi"), ("Deepwell Drilling", "Ahmedabad"),
    ("Frostpoint Cold Chain", "Ludhiana"), ("Crestview Hotels", "Udaipur"),
    ("Ecliptic Studios", "Bengaluru"), ("Oakmont Consulting", "Mumbai"),
    ("Willowbrook Schools Network", "Pune"), ("Sunbelt Solar Farms", "Jaisalmer"),
    ("Axiom Testing Labs", "Hyderabad"), ("Bramble Organic Farms", "Nashik"),
    ("Continental Tyres Depot", "Chennai"), ("Delta Precision Tools", "Rajkot"),
]

# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------
CATEGORIES = [
    {"name": "Hardware", "code": "HARDWARE", "description": "Laptops, desktops, servers, power"},
    {"name": "Networking", "code": "NETWORKING", "description": "Switches, routers, firewalls, Wi-Fi"},
    {"name": "Accessories", "code": "ACCESSORIES", "description": "Peripherals, docks, cabling"},
    {"name": "Services", "code": "SERVICES", "description": "One-time professional services"},
    {"name": "Software", "code": "SOFTWARE", "description": "Perpetual and per-seat licences"},
    {"name": "Subscriptions", "code": "SUBSCRIPTIONS", "description": "Recurring support and managed plans"},
]

# (sku, name, category_code, unit, list_minor, cost_minor, tax_bps, is_promoted, line_type)
# All money in paise. tax_bps 1800 == 18% GST throughout.
PRODUCTS = [
    # ---- Hardware ---------------------------------------------------------
    ("LAP-PRO-14", "ProBook 14 Ultralight Laptop", "HARDWARE", "unit", 8_000_000, 6_000_000, 1800, True, "one_time"),
    ("LAP-PRO-16", "ProBook 16 Performance Laptop", "HARDWARE", "unit", 11_000_000, 8_200_000, 1800, False, "one_time"),
    ("LAP-FLEX-13", "FlexBook 13 Convertible", "HARDWARE", "unit", 9_500_000, 7_100_000, 1800, False, "one_time"),
    ("LAP-ESS-15", "EssentialBook 15", "HARDWARE", "unit", 4_800_000, 3_600_000, 1800, False, "one_time"),
    # Deliberately thin margin (cost is 94% of list) — a discount past ~6% prices
    # it below cost, which is the negative-margin engine rejection fixture.
    ("LAP-CLEAR-13", "EssentialBook 13 (Clearance)", "HARDWARE", "unit", 4_000_000, 3_760_000, 1800, False, "one_time"),
    ("DSK-X1", "Workstation Tower X1", "HARDWARE", "unit", 6_500_000, 4_800_000, 1800, False, "one_time"),
    ("DSK-MINI", "Mini Desktop M2", "HARDWARE", "unit", 3_200_000, 2_350_000, 1800, False, "one_time"),
    ("DSK-PRO-GPU", "Workstation Tower X1 Pro (GPU)", "HARDWARE", "unit", 14_500_000, 11_200_000, 1800, False, "one_time"),
    ("SVR-RACK-42U", "42U Server Rack Cabinet", "HARDWARE", "unit", 16_600_000, 12_500_000, 1800, False, "one_time"),
    ("SVR-1U-NODE", "1U Compute Node R210", "HARDWARE", "unit", 22_000_000, 17_500_000, 1800, False, "one_time"),
    # High ticket — a few of these clear the finance value floor on their own.
    ("SVR-BLADE-CHASSIS", "Blade Chassis Enclosure 10-bay", "HARDWARE", "unit", 45_000_000, 35_000_000, 1800, False, "one_time"),
    ("SVR-STORAGE-24", "24-Bay Storage Array", "HARDWARE", "unit", 38_000_000, 29_500_000, 1800, False, "one_time"),
    ("MON-27", '27-inch QHD Monitor', "HARDWARE", "unit", 1_800_000, 1_250_000, 1800, False, "one_time"),
    ("MON-32-4K", '32-inch 4K Monitor', "HARDWARE", "unit", 3_400_000, 2_450_000, 1800, False, "one_time"),
    ("MON-24", '24-inch FHD Monitor', "HARDWARE", "unit", 1_100_000, 780_000, 1800, False, "one_time"),
    ("UPS-1500", "1500VA Rack UPS", "HARDWARE", "unit", 2_600_000, 1_850_000, 1800, False, "one_time"),
    ("UPS-3000", "3000VA Online UPS", "HARDWARE", "unit", 5_200_000, 3_900_000, 1800, False, "one_time"),
    ("TAB-10", "FieldTab 10 Rugged Tablet", "HARDWARE", "unit", 3_800_000, 2_800_000, 1800, True, "one_time"),
    # ---- Networking -----------------------------------------------------
    ("SWT-24P", "24-Port Gigabit Switch", "NETWORKING", "unit", 2_200_000, 1_500_000, 1800, False, "one_time"),
    ("SWT-48P", "48-Port Gigabit PoE Switch", "NETWORKING", "unit", 4_600_000, 3_200_000, 1800, False, "one_time"),
    ("SWT-8P", "8-Port Desktop Switch", "NETWORKING", "unit", 550_000, 360_000, 1800, False, "one_time"),
    ("RTR-ENT", "Enterprise Edge Router", "NETWORKING", "unit", 3_900_000, 2_700_000, 1800, False, "one_time"),
    ("RTR-SMB", "SMB VPN Router", "NETWORKING", "unit", 1_400_000, 920_000, 1800, False, "one_time"),
    ("AP-WIFI6", "Wi-Fi 6 Access Point", "NETWORKING", "unit", 850_000, 520_000, 1800, True, "one_time"),
    ("AP-WIFI6E", "Wi-Fi 6E Access Point Pro", "NETWORKING", "unit", 1_300_000, 820_000, 1800, False, "one_time"),
    ("FW-UTM", "UTM Firewall Appliance", "NETWORKING", "unit", 6_800_000, 4_900_000, 1800, False, "one_time"),
    ("CAB-RACK-40", "Cat6A Patch Cable (40-pack)", "NETWORKING", "pack", 320_000, 150_000, 1800, False, "one_time"),
    ("SFP-10G-4", "10G SFP+ Module (4-pack)", "NETWORKING", "pack", 680_000, 380_000, 1800, False, "one_time"),
    # ---- Accessories --------------------------------------------------
    ("ACC-MOUSE", "Wireless Mouse", "ACCESSORIES", "unit", 120_000, 60_000, 1800, False, "one_time"),
    ("ACC-KEYBOARD", "Mechanical Keyboard", "ACCESSORIES", "unit", 350_000, 180_000, 1800, False, "one_time"),
    ("ACC-HUB", "USB-C Docking Hub", "ACCESSORIES", "unit", 450_000, 220_000, 1800, True, "one_time"),
    ("ACC-DOCK-PRO", "Thunderbolt 4 Docking Station", "ACCESSORIES", "unit", 1_600_000, 980_000, 1800, False, "one_time"),
    ("ACC-WEBCAM", "1080p Business Webcam", "ACCESSORIES", "unit", 280_000, 150_000, 1800, False, "one_time"),
    ("ACC-HEADSET", "Noise-Cancelling Headset", "ACCESSORIES", "unit", 620_000, 350_000, 1800, False, "one_time"),
    ("ACC-MONITOR-ARM", "Dual Monitor Arm", "ACCESSORIES", "unit", 480_000, 240_000, 1800, False, "one_time"),
    ("ACC-KVM", "4-Port KVM Switch", "ACCESSORIES", "unit", 540_000, 300_000, 1800, False, "one_time"),
    ("ACC-SSD-1TB", "1TB Portable SSD", "ACCESSORIES", "unit", 720_000, 430_000, 1800, False, "one_time"),
    ("ACC-BACKPACK", "Business Laptop Backpack", "ACCESSORIES", "unit", 260_000, 120_000, 1800, False, "one_time"),
    ("ACC-PRESENTER", "Wireless Presenter Remote", "ACCESSORIES", "unit", 150_000, 70_000, 1800, False, "one_time"),
    ("ACC-CABLE-KIT", "Universal Cable Kit", "ACCESSORIES", "unit", 190_000, 80_000, 1800, True, "one_time"),
    # ---- Services (one-time) ----------------------------------------------
    ("SVC-SETUP", "On-Site Setup Service", "SERVICES", "service", 2_000_000, 650_000, 1800, False, "one_time"),
    ("SVC-INSTALL", "Rack & Stack Installation", "SERVICES", "service", 1_200_000, 400_000, 1800, False, "one_time"),
    ("SVC-ONBOARD", "Onboarding & Training (per day)", "SERVICES", "day", 1_500_000, 500_000, 1800, False, "one_time"),
    ("SVC-MIGRATE", "Data Migration Service", "SERVICES", "service", 3_500_000, 1_400_000, 1800, False, "one_time"),
    ("SVC-NETWORK-AUDIT", "Network Security Audit", "SERVICES", "service", 4_200_000, 1_600_000, 1800, False, "one_time"),
    ("SVC-HEALTH-CHECK", "Infrastructure Health Check", "SERVICES", "service", 1_800_000, 700_000, 1800, False, "one_time"),
    ("SVC-DEPLOY-MGMT", "Managed Deployment (project)", "SERVICES", "project", 6_000_000, 2_600_000, 1800, False, "one_time"),
    ("SVC-CUSTOM-INT", "Custom Integration (per day)", "SERVICES", "day", 2_400_000, 900_000, 1800, False, "one_time"),
    ("SVC-DR-PLAN", "Disaster Recovery Planning", "SERVICES", "project", 3_000_000, 1_100_000, 1800, False, "one_time"),
    ("SVC-PREMIUM-ENABLE", "Premium Support Enablement", "SERVICES", "service", 1_000_000, 300_000, 1800, False, "one_time"),
    # ---- Software (one-time licences) -----------------------------------
    ("SW-OFFICE-PERP", "Office Suite (perpetual licence)", "SOFTWARE", "licence", 2_500_000, 900_000, 1800, False, "one_time"),
    ("SW-AV-ENDPOINT", "Endpoint Antivirus (per seat)", "SOFTWARE", "seat", 180_000, 60_000, 1800, False, "one_time"),
    ("SW-BACKUP-SRV", "Backup Server Licence", "SOFTWARE", "licence", 1_900_000, 700_000, 1800, False, "one_time"),
    ("SW-VIRT-HOST", "Virtualization Host Licence", "SOFTWARE", "licence", 4_800_000, 2_100_000, 1800, False, "one_time"),
    ("SW-MDM-SEAT", "Device Management (per seat)", "SOFTWARE", "seat", 240_000, 90_000, 1800, False, "one_time"),
    ("SW-ANALYTICS", "BI Analytics Suite Licence", "SOFTWARE", "licence", 5_500_000, 2_400_000, 1800, True, "one_time"),
    # ---- Subscriptions (recurring) -------------------------------------
    ("SUB-SUPPORT-STD", "Standard Support Plan", "SUBSCRIPTIONS", "licence", 500_000, 150_000, 1800, True, "subscription"),
    ("SUB-SUPPORT-PREM", "Premium Support Plan", "SUBSCRIPTIONS", "licence", 1_200_000, 350_000, 1800, False, "subscription"),
    ("SUB-SUPPORT-ENT", "Enterprise Support Plan", "SUBSCRIPTIONS", "licence", 2_800_000, 800_000, 1800, False, "subscription"),
    ("SUB-BACKUP", "Cloud Backup Plan", "SUBSCRIPTIONS", "licence", 300_000, 80_000, 1800, False, "subscription"),
    ("SUB-MONITOR", "Infrastructure Monitoring Plan", "SUBSCRIPTIONS", "licence", 650_000, 190_000, 1800, False, "subscription"),
    ("SUB-SECURITY", "Managed Security Plan", "SUBSCRIPTIONS", "licence", 1_500_000, 450_000, 1800, False, "subscription"),
    ("SUB-PATCH", "Patch Management Plan", "SUBSCRIPTIONS", "licence", 400_000, 120_000, 1800, False, "subscription"),
    ("SUB-SLA-247", "24/7 SLA Add-on", "SUBSCRIPTIONS", "licence", 900_000, 260_000, 1800, True, "subscription"),
]

# Product variants: attribute/value/extra price (paise). LAP-PRO-14's RAM options
# are what the "variant resolves to the right price in a quote" check uses.
PRODUCT_VARIANTS = {
    "LAP-PRO-14": [
        ("RAM", "16GB", 0),
        ("RAM", "32GB", 800_000),
        ("RAM", "64GB", 1_800_000),
    ],
    "LAP-PRO-16": [
        ("Storage", "512GB SSD", 0),
        ("Storage", "1TB SSD", 600_000),
        ("Storage", "2TB SSD", 1_500_000),
    ],
    "DSK-X1": [
        ("CPU", "6-core", 0),
        ("CPU", "8-core", 900_000),
    ],
    "MON-27": [
        ("Stand", "Fixed", 0),
        ("Stand", "Height-adjustable", 250_000),
    ],
}

# ---------------------------------------------------------------------------
# Subscription plans
# ---------------------------------------------------------------------------
SUBSCRIPTION_PLANS = [
    {
        "name": "Monthly Standard",
        "interval": "monthly",
        "billing_cycles": None,  # open-ended
        "proration_enabled": True,
        "cancellation_notice_days": 15,
        "refund_policy": "prorated",
    },
    {
        "name": "Monthly Flex",
        "interval": "monthly",
        "billing_cycles": None,
        "proration_enabled": True,
        "cancellation_notice_days": 0,
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

# sku -> plan name. Subscriptions the demo leans on go on "Monthly Standard" so
# their schedule is simple to read; the rest are spread across the others.
SUBSCRIPTION_PRODUCT_PLAN = {
    "SUB-SUPPORT-STD": "Monthly Standard",
    "SUB-SUPPORT-PREM": "Monthly Standard",
    "SUB-SUPPORT-ENT": "Quarterly Plus",
    "SUB-BACKUP": "Monthly Standard",
    "SUB-MONITOR": "Monthly Flex",
    "SUB-SECURITY": "Quarterly Plus",
    "SUB-PATCH": "Monthly Flex",
    "SUB-SLA-247": "Annual Commitment",
}

# ---------------------------------------------------------------------------
# Warehouses
# ---------------------------------------------------------------------------
WAREHOUSES = [
    {"name": "Main Warehouse", "code": "MAIN", "address": "Plot 12, MIDC Industrial Area, Pune 411018",
     "shipping_cost_weight": 20, "replenishment_threshold": 15},
    {"name": "East Depot", "code": "EAST", "address": "Warehouse 4, Salt Lake Sector V, Kolkata 700091",
     "shipping_cost_weight": 65, "replenishment_threshold": 8},
    {"name": "West Hub", "code": "WEST", "address": "Unit 7, Andheri East Logistics Park, Mumbai 400069",
     "shipping_cost_weight": 45, "replenishment_threshold": 10},
    {"name": "South Depot", "code": "SOUTH", "address": "No. 88, Peenya Industrial Estate, Bengaluru 560058",
     "shipping_cost_weight": 80, "replenishment_threshold": 5},
]

# ---------------------------------------------------------------------------
# Discount policy (DECISION_ENGINE.md §2 defaults)
# ---------------------------------------------------------------------------
POLICY_V1 = {
    "tier_ceilings": [
        {"tier": "bronze", "ceiling_bps": 500},
        {"tier": "silver", "ceiling_bps": 1000},
        {"tier": "gold", "ceiling_bps": 1500},
    ],
    "category_defaults": {
        "HARDWARE": {"ceiling_bps": 1500, "margin_floor_bps": 1800},
        "NETWORKING": {"ceiling_bps": 1500, "margin_floor_bps": 2000},
        "ACCESSORIES": {"ceiling_bps": 1500, "margin_floor_bps": 1800},
        "SERVICES": {"ceiling_bps": 1000, "margin_floor_bps": 3500},
        "SOFTWARE": {"ceiling_bps": 1200, "margin_floor_bps": 5000},
        "SUBSCRIPTIONS": {"ceiling_bps": 800, "margin_floor_bps": 4000},
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


# ===========================================================================
# Org / RBAC / users / customers
# ===========================================================================
def _seed_roles(db: Session) -> None:
    for spec in DEFAULT_ROLES:
        existing = db.scalar(select(Role).where(Role.name == spec["name"]))
        if existing is None:
            db.add(Role(**spec))
            logger.info("Seeded role: %s", spec["name"])
        else:
            # Keep the default roles' permissions + dashboard assignment current on
            # re-seed; an admin's own custom roles are untouched.
            existing.permissions = spec["permissions"]
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
    the tenant context to `org` first."""
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
                full_name="Aditi Verma",
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
    for spec in NAMED_CUSTOMERS:
        if db.scalar(select(Customer).where(Customer.email == spec["email"])) is not None:
            continue
        db.add(
            Customer(
                name=spec["name"],
                email=spec["email"],
                company=spec["company"],
                phone=spec.get("phone"),
                tier=spec["tier"],
                hashed_password=hash_password(spec["password"]),
                portal_enabled=spec["portal_enabled"],
            )
        )
        logger.info("Seeded named customer: %s", spec["email"])

    tiers = ["gold", "silver", "silver", "bronze", "bronze", "bronze"]
    for i, (company, city) in enumerate(GENERATED_CUSTOMER_COMPANIES):
        slug = _slugify(company)
        email = f"{slug}@example.com"
        if db.scalar(select(Customer).where(Customer.email == email)) is not None:
            continue
        db.add(
            Customer(
                name=company,
                email=email,
                company=company,
                phone=f"+91 {90000 + i:05d} {10000 + (i * 37) % 89999:05d}",
                tier=tiers[i % len(tiers)],
                hashed_password=hash_password("customer12345"),
                # Roughly 1 in 9 has portal access switched off — enough disabled
                # accounts for the "disabled portal user" checks, without making
                # the portal feel empty.
                portal_enabled=(i % 9 != 4),
            )
        )
    db.commit()
    total = db.scalar(select(func.count()).select_from(Customer)) or 0
    logger.info("Customers now total %d", total)


# ===========================================================================
# Catalogue / pricing / warehouses / plans / policy
# ===========================================================================
def _seed_subscription_plans(db: Session) -> dict[str, SubscriptionPlan]:
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
    return plans


def _seed_catalog(db: Session, plans: dict[str, SubscriptionPlan]) -> dict[str, Category]:
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
        plan_id = None
        if line_type == "subscription":
            plan_name = SUBSCRIPTION_PRODUCT_PLAN.get(sku, "Monthly Standard")
            plan_id = plans[plan_name].id
        db.add(
            Product(
                sku=sku,
                name=name,
                category_id=categories[cat_code].id,
                description=f"{name} — {categories[cat_code].name.rstrip('s')} line item.",
                unit=unit,
                list_price_minor=list_minor,
                cost_price_minor=cost_minor,
                tax_bps=tax_bps,
                is_promoted=is_promoted,
                line_type=line_type,
                subscription_plan_id=plan_id,
                currency="INR",
                is_active=True,
            )
        )
    db.commit()

    for sku, variants in PRODUCT_VARIANTS.items():
        product = db.scalar(select(Product).where(Product.sku == sku))
        if product is None or product.variants:
            continue
        db.add_all(
            ProductVariant(product_id=product.id, attribute=attr, value=val, extra_price_minor=extra)
            for attr, val, extra in variants
        )
    db.commit()

    total = db.scalar(select(func.count()).select_from(Product)) or 0
    logger.info("Products now total %d", total)
    return categories


def _seed_pricing(db: Session) -> None:
    lists: dict[str, PriceList] = {}
    specs = [
        {"name": "Default", "tier": None, "is_default": True},
        {"name": "Gold Tier", "tier": "gold", "is_default": False},
        {"name": "Silver Tier", "tier": "silver", "is_default": False},
        {"name": "Bronze Value", "tier": "bronze", "is_default": False},
    ]
    for spec in specs:
        existing = db.scalar(select(PriceList).where(PriceList.name == spec["name"]))
        if existing is None:
            existing = PriceList(name=spec["name"], tier=spec["tier"], currency="INR", is_default=spec["is_default"])
            db.add(existing)
            db.flush()
            logger.info("Seeded price list: %s", spec["name"])
        lists[spec["name"]] = existing
    db.commit()

    # Tiered overrides on a spread of popular SKUs. (list_name, sku, override_minor, extra_discount_bps).
    # `None` override == list price kept, only the extra standing discount applies.
    entries = [
        ("Gold Tier", "LAP-PRO-14", 7_600_000, 0),
        ("Gold Tier", "LAP-PRO-16", 10_400_000, 0),
        ("Gold Tier", "SVC-SETUP", 1_800_000, 0),
        ("Gold Tier", "MON-27", 1_650_000, 0),
        ("Gold Tier", "SUB-SUPPORT-STD", None, 500),
        ("Gold Tier", "ACC-HUB", 400_000, 0),
        ("Gold Tier", "DSK-X1", 6_100_000, 0),
        ("Gold Tier", "SW-ANALYTICS", 5_100_000, 0),
        ("Silver Tier", "LAP-PRO-14", 7_800_000, 0),
        ("Silver Tier", "SVC-SETUP", 1_900_000, 0),
        ("Silver Tier", "MON-27", 1_720_000, 0),
        ("Silver Tier", "SUB-SUPPORT-STD", None, 250),
        ("Silver Tier", "SWT-24P", 2_100_000, 0),
        ("Silver Tier", "ACC-KEYBOARD", 320_000, 0),
        ("Bronze Value", "LAP-ESS-15", 4_650_000, 0),
        ("Bronze Value", "MON-24", 1_050_000, 0),
        ("Bronze Value", "ACC-MOUSE", 110_000, 0),
        ("Bronze Value", "SUB-BACKUP", None, 200),
    ]
    created = 0
    for list_name, sku, override, extra_bps in entries:
        price_list = lists[list_name]
        product = db.scalar(select(Product).where(Product.sku == sku))
        if product is None:
            continue
        if db.scalar(
            select(PriceListEntry).where(
                PriceListEntry.price_list_id == price_list.id,
                PriceListEntry.product_id == product.id,
            )
        ):
            continue
        db.add(
            PriceListEntry(
                price_list_id=price_list.id,
                product_id=product.id,
                variant_id=None,
                override_price_minor=override,
                extra_discount_bps=extra_bps,
            )
        )
        created += 1
    if created:
        db.commit()
        logger.info("Seeded %d price list entries", created)


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

    rng = random.Random(1234)
    created = 0
    for product in products:
        # Subscriptions and services aren't stocked — a token 0-row keeps the
        # stock grid rectangular without pretending there's inventory.
        stocked = product.line_type == "one_time" and product.category.code in (
            "HARDWARE",
            "NETWORKING",
            "ACCESSORIES",
        )
        for code, warehouse in warehouses.items():
            if db.scalar(
                select(Stock).where(Stock.product_id == product.id, Stock.warehouse_id == warehouse.id)
            ):
                continue
            if not stocked:
                on_hand = 0
            elif code == "MAIN":
                on_hand = rng.randint(45, 140)
            elif code == "WEST":
                on_hand = rng.randint(15, 60)
            elif code == "EAST":
                on_hand = rng.choice([0, 0, 4, 8, 12, 20, 30])
            else:  # SOUTH — deliberately thin
                on_hand = rng.choice([0, 0, 0, 3, 5, 10])
            db.add(Stock(product_id=product.id, warehouse_id=warehouse.id, on_hand=on_hand, reserved=0))
            created += 1
    if created:
        db.commit()
        logger.info("Seeded %d stock rows across %d warehouses", created, len(warehouses))


def _link_subscription_products(db: Session, plans: dict[str, SubscriptionPlan]) -> None:
    changed = False
    for sku, plan_name in SUBSCRIPTION_PRODUCT_PLAN.items():
        product = db.scalar(select(Product).where(Product.sku == sku))
        plan = plans.get(plan_name)
        if product is not None and plan is not None and product.subscription_plan_id != plan.id:
            product.subscription_plan_id = plan.id
            changed = True
    if changed:
        db.commit()
        logger.info("Linked subscription products to their plans")


def _seed_policy(db: Session, categories: dict[str, Category]) -> None:
    """Policy v1 (active) with DECISION_ENGINE.md defaults, plus an inactive draft
    v2 that only loosens the Services category ceiling (10% -> 20%) — a ready-made
    target for the "policy is data, not code" walkthrough and the policy-snapshot
    isolation check. Idempotent: does nothing once a policy exists."""
    if db.scalar(select(DiscountPolicy)) is not None:
        return

    def category_ceilings() -> list[dict]:
        return [
            {
                "category_id": categories[code].id,
                "ceiling_bps": defaults["ceiling_bps"],
                "margin_floor_bps": defaults["margin_floor_bps"],
            }
            for code, defaults in POLICY_V1["category_defaults"].items()
            if code in categories
        ]

    v1 = create_policy(
        db,
        tier_ceilings=POLICY_V1["tier_ceilings"],
        category_ceilings=category_ceilings(),
        weights=POLICY_V1["weights"],
        thresholds=POLICY_V1["thresholds"],
        upsell=POLICY_V1["upsell"],
        anomaly=POLICY_V1["anomaly"],
        stalled_after_days=POLICY_V1["stalled_after_days"],
    )
    activate_policy(db, v1)
    logger.info("Seeded and activated discount policy v%d", v1.version)

    loosened = category_ceilings()
    for row in loosened:
        if row["category_id"] == categories["SERVICES"].id:
            row["ceiling_bps"] = 2000
    v2 = create_policy(
        db,
        tier_ceilings=POLICY_V1["tier_ceilings"],
        category_ceilings=loosened,
        weights=POLICY_V1["weights"],
        thresholds=POLICY_V1["thresholds"],
        upsell=POLICY_V1["upsell"],
        anomaly=POLICY_V1["anomaly"],
        stalled_after_days=POLICY_V1["stalled_after_days"],
    )
    logger.info("Seeded inactive draft discount policy v%d (Services ceiling 20%%)", v2.version)


# ===========================================================================
# History (affinity + rep stats signal)
# ===========================================================================
def _new_paid_quote(
    db: Session,
    *,
    customer: Customer,
    rep: User,
    products_by_sku: dict[str, Product],
    skus: tuple[str, ...],
    policy_version: int,
    order_discount_bps: int = 0,
    when: datetime | None = None,
    qty_fn=lambda: 1,
) -> Quotation:
    """A terminal ('paid') historical order — real `quote_lines` for the affinity
    and rep-stats rebuilds to compute from. Written directly (no transitions): these
    never need a state machine, they just need to exist."""
    quotation = Quotation(
        reference="PENDING",
        customer_id=customer.id,
        owner_rep_id=rep.id,
        status="paid",
        version=1,
        policy_version=policy_version,
        order_discount_bps=order_discount_bps,
        currency="INR",
    )
    db.add(quotation)
    db.flush()
    year = (when or datetime.now(timezone.utc)).year
    quotation.reference = f"QT-{year}-{quotation.id:06d}"
    quotation.order_number = f"SO-{year}-{quotation.id:06d}"
    if when is not None:
        quotation.created_at = when
        quotation.updated_at = when
        quotation.last_activity_at = when

    for position, sku in enumerate(skus):
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
                quantity=qty_fn(),
                unit_price_minor=product.list_price_minor,
                cost_price_minor=product.cost_price_minor,
                discount_bps=0,
                added_from_suggestion=False,
                position=position,
            )
        )
    return quotation


def _seed_baseline_history_and_affinity(db: Session) -> None:
    """Runs on every seed: ~48 paid orders so the upsell panel has real
    co-purchase statistics from the first boot, with or without `--history`.
    Skipped the moment any quotation exists."""
    if db.scalar(select(Quotation)) is not None:
        return

    rep = db.scalar(select(User).where(User.email == "rep@example.com"))
    customers = db.scalars(select(Customer).where(Customer.portal_enabled.is_(True))).all()
    products_by_sku = {p.sku: p for p in db.scalars(select(Product)).all()}
    policy = db.scalar(select(DiscountPolicy).where(DiscountPolicy.is_active.is_(True)))
    if rep is None or not customers or policy is None:
        return

    rng = random.Random(7)
    created = 0
    for i in range(48):
        bundle = AFFINITY_BUNDLES[i % len(AFFINITY_BUNDLES)]
        customer = customers[i % len(customers)]
        _new_paid_quote(
            db,
            customer=customer,
            rep=rep,
            products_by_sku=products_by_sku,
            skus=bundle,
            policy_version=policy.version,
            when=datetime.now(timezone.utc) - timedelta(days=rng.randint(20, 400)),
            qty_fn=lambda: rng.randint(1, 3),
        )
        created += 1
    db.commit()
    logger.info("Seeded %d baseline historical quotations", created)
    logger.info("Rebuilt product affinity: %d rows", rebuild_affinity(db))


def _seed_history_v2(db: Session) -> None:
    """`--history`: ~160 more backdated paid quotations over ~12 months with
    distinct per-rep discount profiles, so anomaly detection has real signal:

    * Riya (rep)    — conservative, mean ~6%
    * Dev  (rep2)   — loose, mean ~14%   (this is the rep the anomaly demo uses)
    * Priya (rep4)  — middling, mean ~9%
    * Sam  (rep3)   — only 3 quotes total, below `min_sample_size` on purpose

    Idempotent: skipped once >120 quotations exist.
    """
    from app.dashboard.service import rebuild_rep_stats

    if (db.scalar(select(func.count()).select_from(Quotation)) or 0) > 120:
        logger.info("history already seeded — skipping --history")
        return

    rng = random.Random(42)
    reps = {
        u.email: u
        for u in db.scalars(
            select(User).where(
                User.email.in_(["rep@example.com", "rep2@example.com", "rep3@example.com", "rep4@example.com"])
            )
        )
    }
    profiles = {  # email -> (mean_bps, sd_bps, count)
        "rep@example.com": (600, 180, 70),
        "rep2@example.com": (1400, 300, 60),
        "rep4@example.com": (900, 220, 30),
        "rep3@example.com": (700, 150, 3),
    }
    customers = db.scalars(select(Customer)).all()
    products_by_sku = {p.sku: p for p in db.scalars(select(Product)).all()}
    policy = db.scalar(select(DiscountPolicy).where(DiscountPolicy.is_active.is_(True)))
    if len(reps) < 4 or not customers or policy is None:
        logger.warning("--history preconditions missing — skipping")
        return

    now = datetime.now(timezone.utc)
    created = 0
    for email, (mean_bps, sd_bps, count) in profiles.items():
        rep = reps[email]
        for i in range(count):
            disc = max(0, min(2400, int(rng.gauss(mean_bps, sd_bps))))
            bundle = AFFINITY_BUNDLES[(created + i) % len(AFFINITY_BUNDLES)]
            customer = customers[(created + i) % len(customers)]
            _new_paid_quote(
                db,
                customer=customer,
                rep=rep,
                products_by_sku=products_by_sku,
                skus=bundle,
                policy_version=policy.version,
                order_discount_bps=disc,
                when=now - timedelta(days=rng.randint(5, 360)),
                qty_fn=lambda: rng.randint(1, 4),
            )
            created += 1
    db.commit()
    logger.info("Seeded %d backdated historical quotations (--history)", created)
    logger.info("Rebuilt product affinity: %d rows", rebuild_affinity(db))
    logger.info("Rebuilt rep discount stats for %d reps", rebuild_rep_stats(db))


# ===========================================================================
# Demo fixtures — the exact scenarios the QA plan / 5-minute walkthrough use
# ===========================================================================
def _seed_demo_fixtures(db: Session) -> None:  # noqa: C901 — a script of independent fixtures
    from app.core.enums import QuoteStatus
    from app.events.service import record_event
    from app.quotations.transitions import transition

    rep = db.scalar(select(User).where(User.email == "rep@example.com"))
    rep2 = db.scalar(select(User).where(User.email == "rep2@example.com"))
    finance = db.scalar(select(User).where(User.email == "finance@example.com"))
    ops = db.scalar(select(User).where(User.email == "ops@example.com"))
    products = {p.sku: p for p in db.scalars(select(Product)).all()}
    active_version = db.scalar(select(DiscountPolicy.version).where(DiscountPolicy.is_active.is_(True)))
    if rep is None or active_version is None:
        logger.warning("--demo preconditions missing — skipping")
        return

    # Coarse idempotency: once a `sent` quote exists the fixtures are already down.
    if db.scalar(select(func.count()).select_from(Quotation).where(Quotation.status == QuoteStatus.SENT.value)):
        logger.info("demo fixtures already present — skipping --demo")
        return

    year = datetime.now(timezone.utc).year

    def customer(company: str) -> Customer | None:
        return db.scalar(select(Customer).where(Customer.company == company))

    def build(
        company: str,
        lines: list[tuple[str, int, int]],
        *,
        owner: User | None = None,
        order_discount_bps: int = 0,
    ) -> Quotation | None:
        """Draft quote with the given (sku, qty, line_discount_bps) lines."""
        cust = customer(company)
        if cust is None:
            return None
        owner = owner or rep
        quotation = Quotation(
            reference="PENDING",
            customer_id=cust.id,
            owner_rep_id=owner.id,
            status=QuoteStatus.DRAFT.value,
            version=1,
            policy_version=active_version,
            order_discount_bps=order_discount_bps,
            currency="INR",
        )
        db.add(quotation)
        db.flush()
        quotation.reference = f"QT-{year}-{quotation.id:06d}"
        for pos, (sku, qty, disc) in enumerate(lines):
            product = products.get(sku)
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
                    quantity=qty,
                    unit_price_minor=product.list_price_minor,
                    cost_price_minor=product.cost_price_minor,
                    discount_bps=disc,
                    added_from_suggestion=False,
                    position=pos,
                )
            )
        record_event(db, quotation, "quote.created", owner, summary="Demo fixture created.", payload={})
        db.flush()
        db.refresh(quotation)
        return quotation

    def walk(quotation: Quotation, statuses: list[str], *, actor: User | None = None) -> None:
        actor = actor or rep
        version = quotation.version
        for to in statuses:
            transition(db, quotation, to, actor, expected_version=version)
            version = quotation.version

    def age(quotation: Quotation, days: int) -> None:
        stale = datetime.now(timezone.utc) - timedelta(days=days)
        quotation.last_activity_at = stale
        quotation.updated_at = stale

    def set_stock(sku: str, per_code: dict[str, int]) -> None:
        product = products.get(sku)
        if product is None:
            return
        for st in db.scalars(select(Stock).where(Stock.product_id == product.id)):
            st.on_hand = per_code.get(st.warehouse.code, 0)
            st.reserved = 0

    # -- 1. Acme Corp — the flagship decision-engine example, routed to L1 --------
    #    Laptop 12% (within the 15% Hardware/Gold ceiling), Setup Service 18%
    #    (8 points over the 10% Services ceiling) -> whole quote flagged, pending L1.
    try:
        from app.approvals.service import route_quotation

        flagship = build("Acme Corp", [("LAP-PRO-14", 1, 1200), ("SVC-SETUP", 1, 1800)])
        if flagship is not None:
            route_quotation(db, flagship, rep, expected_version=flagship.version)
            db.commit()
            logger.info("Fixture: Acme flagship %s -> %s", flagship.reference, flagship.status)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'Acme flagship' failed")

    # -- 2. Beta Industries — approved & sent, then untouched 9 days -> stalled ---
    try:
        beta = build("Beta Industries", [("LAP-PRO-14", 2, 0), ("SVC-ONBOARD", 1, 0)])
        if beta is not None:
            walk(beta, [QuoteStatus.APPROVED.value, QuoteStatus.SENT.value])
            age(beta, 9)
            db.commit()
            logger.info("Fixture: Beta stalled %s", beta.reference)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'Beta stalled' failed")

    # -- 3. Corex Ltd — sent, with a live single-use magic link (portal demo) ----
    try:
        corex = build("Corex Ltd", [("DSK-X1", 1, 0), ("ACC-KEYBOARD", 1, 0), ("ACC-MOUSE", 1, 0)])
        if corex is not None:
            walk(corex, [QuoteStatus.APPROVED.value, QuoteStatus.SENT.value])
            db.commit()
            logger.info("Fixture: Corex sent + magic link %s", corex.reference)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'Corex sent' failed")

    # -- 4. Acme — two-warehouse split: Main 3 / East 5, demand 6 ---------------
    try:
        split = build("Acme Corp", [("MON-27", 6, 0)])
        if split is not None:
            walk(split, [QuoteStatus.APPROVED.value, QuoteStatus.SENT.value, QuoteStatus.CONFIRMED.value])
            set_stock("MON-27", {"MAIN": 3, "EAST": 5, "WEST": 0, "SOUTH": 0})
            db.commit()
            logger.info("Fixture: Acme split %s", split.reference)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'Acme split' failed")

    # -- 5. Acme — backorder: total stock 2, demand 5 --------------------------
    backorder_quote = None
    try:
        backorder_quote = build("Acme Corp", [("SWT-24P", 5, 0)])
        if backorder_quote is not None:
            walk(
                backorder_quote,
                [QuoteStatus.APPROVED.value, QuoteStatus.SENT.value, QuoteStatus.CONFIRMED.value],
            )
            set_stock("SWT-24P", {"MAIN": 2, "EAST": 0, "WEST": 0, "SOUTH": 0})
            db.commit()
            logger.info("Fixture: Acme backorder %s", backorder_quote.reference)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'Acme backorder' failed")

    # -- 6. Acme — single-warehouse fulfilment (fully in Main) -----------------
    try:
        single = build("Vertex Manufacturing", [("ACC-HUB", 4, 0), ("ACC-MOUSE", 4, 0)])
        if single is not None:
            walk(single, [QuoteStatus.APPROVED.value, QuoteStatus.SENT.value, QuoteStatus.CONFIRMED.value])
            set_stock("ACC-HUB", {"MAIN": 60, "EAST": 0, "WEST": 20, "SOUTH": 0})
            db.commit()
            logger.info("Fixture: single-warehouse %s", single.reference)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'single warehouse' failed")

    # -- 7. Hybrid billing — hardware (one-time) + subscription (recurring) -----
    #    Left at `confirmed` so the walkthrough can generate the invoice live.
    try:
        hybrid = build("Acme Corp", [("LAP-PRO-16", 3, 0), ("SUB-SUPPORT-STD", 3, 0)])
        if hybrid is not None:
            walk(hybrid, [QuoteStatus.APPROVED.value, QuoteStatus.SENT.value, QuoteStatus.CONFIRMED.value])
            db.commit()
            logger.info("Fixture: hybrid billing (confirmed) %s", hybrid.reference)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'hybrid billing' failed")

    # -- 8. Hybrid order taken to invoiced + a partial payment ----------------
    #    Ready-made for the invoice / partial-payment / full-payment checks.
    try:
        from app.billing.service import generate_invoice, record_payment

        billed = build("Meridian Health Group", [("SVR-1U-NODE", 1, 0), ("SUB-MONITOR", 10, 0)])
        if billed is not None and finance is not None:
            walk(billed, [QuoteStatus.APPROVED.value, QuoteStatus.SENT.value, QuoteStatus.CONFIRMED.value])
            db.commit()
            invoice = generate_invoice(db, billed, finance)
            record_payment(
                db, invoice, invoice.total_minor // 3, "bank_transfer", "SEED-PARTIAL-001", finance
            )
            logger.info("Fixture: invoiced + partial payment %s (invoice %s)", billed.reference, invoice.number)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'invoiced + partial payment' failed")

    # -- 9. Discount anomaly — rep2 (loose discounter) confirms a ~22% order ----
    try:
        if rep2 is not None:
            anomaly = build(
                "Helios Energy",
                [("DSK-X1", 3, 0), ("MON-27", 3, 0)],
                owner=rep2,
                order_discount_bps=2200,
            )
            if anomaly is not None:
                # draft -> approved is a legal edge; the confirmed side-effect runs
                # anomaly evaluation + folds this quote into rep2's Welford stats.
                walk(
                    anomaly,
                    [QuoteStatus.APPROVED.value, QuoteStatus.SENT.value, QuoteStatus.CONFIRMED.value],
                    actor=rep2,
                )
                db.commit()
                logger.info("Fixture: discount anomaly %s (rep2)", anomaly.reference)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'discount anomaly' failed")

    # -- 10. Delivery slippage — accept the backorder plan, then let the restock
    #        date fall into the past so the slippage alert fires. -------------
    try:
        from app.fulfillment.models import Backorder
        from app.fulfillment.service import accept_plan, get_plan

        if backorder_quote is not None and ops is not None:
            db.refresh(backorder_quote)
            plan = get_plan(db, backorder_quote)
            accept_plan(db, backorder_quote, backorder_quote.version, plan.plan_hash, ops)
            past = datetime.now(timezone.utc) - timedelta(days=6)
            for bo in db.scalars(select(Backorder).where(Backorder.quotation_id == backorder_quote.id)):
                bo.expected_restock_at = past
            db.commit()
            logger.info("Fixture: delivery slippage on %s", backorder_quote.reference)
    except Exception:
        db.rollback()
        logger.exception("Fixture 'delivery slippage' failed")

    # -- Materialise dashboard alerts (stalled / anomaly / slippage) ----------
    try:
        from app.dashboard.service import recompute_days_inactive, run_alert_sweep

        recompute_days_inactive(db)
        fired = run_alert_sweep(db)
        db.commit()
        logger.info("Alert sweep raised %d alert(s)", fired)
    except Exception:
        db.rollback()
        logger.exception("Alert sweep after --demo failed")

    logger.info("Seeded demo fixtures (--demo)")


# ===========================================================================
# Entry points
# ===========================================================================
def seed_db(db: Session, *, history: bool = False, demo: bool = False) -> None:
    demo_org = _get_or_create_demo_org(db)
    set_current_org(db, demo_org.id)

    _seed_roles(db)
    _seed_users(db)
    _seed_customers(db)
    plans = _seed_subscription_plans(db)
    categories = _seed_catalog(db, plans)
    _link_subscription_products(db, plans)
    _seed_pricing(db)
    _seed_warehouses(db)
    _seed_policy(db, categories)
    _seed_baseline_history_and_affinity(db)
    if history:
        _seed_history_v2(db)
    if demo:
        _seed_demo_fixtures(db)

    # Final consistency pass — after every quote (history + demo) exists.
    try:
        from app.dashboard.service import rebuild_rep_stats

        rebuild_affinity(db)
        rebuild_rep_stats(db)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("final affinity/rep-stats rebuild failed")


if __name__ == "__main__":
    import argparse

    from app.config.logging import setup_logging
    from app.db.base import Base
    from app.db.session import SessionLocal, engine

    setup_logging()

    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Drop and recreate all tables first")
    parser.add_argument("--history", action="store_true", help="Seed ~12 months of backdated history + rebuild affinity/rep stats")
    parser.add_argument("--demo", action="store_true", help="Seed the 5-minute-walkthrough demo fixtures")
    args = parser.parse_args()

    if args.reset:
        # `Base.metadata` only knows about tables whose model module has been
        # imported in this process — import them all so `drop_all` sees every FK.
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
