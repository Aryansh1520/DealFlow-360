"""Central configuration for the demo scripts.

Everything is overridable from the environment so the same scripts run against a
local `docker compose` stack or a deployed one:

    DF_BASE_URL   frontend origin           (default http://localhost:3001)
    DF_API_URL    backend API base          (default http://localhost:8001/api/v1)
    DF_SLOW       pacing multiplier, float  (default 1.6 — tuned for a live
                                             voiceover. Raise to 2.0+ for an even
                                             calmer take, drop to 0.4 for a quick
                                             dry run / selector check)
    DF_HEADLESS   1 to run without a visible window (default 0 — you want to see
                                             it for a recording)
    DF_KEEP_OPEN  1 to leave the browser open when a script finishes
"""

from __future__ import annotations

import os


def _flag(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "1" if default else "0").strip().lower() in {"1", "true", "yes", "on"}


BASE_URL = os.environ.get("DF_BASE_URL", "http://localhost:3001").rstrip("/")
API_URL = os.environ.get("DF_API_URL", "http://localhost:8001/api/v1").rstrip("/")
SLOW = float(os.environ.get("DF_SLOW", "1.6"))
HEADLESS = _flag("DF_HEADLESS")
KEEP_OPEN = _flag("DF_KEEP_OPEN")

# 1280x720 is the resolution the QA plan asks the demo to be legible at.
WINDOW_WIDTH = int(os.environ.get("DF_WIN_W", "1280"))
WINDOW_HEIGHT = int(os.environ.get("DF_WIN_H", "800"))


class Credentials:
    """Seeded logins — see backend/app/db/seed.py.

    Internal users share the password `demo12345`; the org admin uses `admin12345`;
    portal customers use `customer12345`.
    """

    ADMIN = ("admin@example.com", "admin12345")
    REP = ("rep@example.com", "demo12345")            # Riya Rao — conservative discounter
    REP2 = ("rep2@example.com", "demo12345")          # Dev Kapoor — loose discounter (anomaly demo)
    REP3 = ("rep3@example.com", "demo12345")          # Sam Sequeira — too few quotes for anomaly stats
    MANAGER = ("manager@example.com", "demo12345")    # Manav Mehta — L1 approver
    FINANCE = ("finance@example.com", "demo12345")    # Farah Sheikh — L2 approver + billing
    OPS = ("ops@example.com", "demo12345")            # Omar Farooq — warehouses + fulfilment

    CUSTOMER_ACME = ("customer@example.com", "customer12345")   # Acme Corp — Gold
    CUSTOMER_BETA = ("beta@example.com", "customer12345")       # Beta Industries — Silver
    CUSTOMER_COREX = ("corex@example.com", "customer12345")     # Corex Ltd — Bronze
    CUSTOMER_NIMBUS = ("nimbus@example.com", "customer12345")   # portal access disabled


class Fixtures:
    """Names / SKUs the seeded fixtures use, referenced by the scripts."""

    ACME = "Acme Corp"
    BETA = "Beta Industries"
    COREX = "Corex Ltd"

    # The canonical decision-engine example.
    FLAGSHIP_HARDWARE = "ProBook 14 Ultralight Laptop"   # LAP-PRO-14, Hardware, Gold/Hardware ceiling 15%
    FLAGSHIP_SERVICE = "On-Site Setup Service"            # SVC-SETUP, Services ceiling 10%
    FLAGSHIP_HW_DISCOUNT_PCT = 12                         # within ceiling
    FLAGSHIP_SVC_DISCOUNT_PCT = 18                        # 8 points over -> routes to L1

    SPLIT_PRODUCT = "27-inch QHD Monitor"                 # MON-27: Main 3 / East 5, order qty 6
    SPLIT_QTY = 6
    BACKORDER_PRODUCT = "24-Port Gigabit Switch"          # SWT-24P: total stock 2, order qty 5
    BACKORDER_QTY = 5

    SUBSCRIPTION_PRODUCT = "Standard Support Plan"        # SUB-SUPPORT-STD, recurring
    HYBRID_HARDWARE = "ProBook 16 Performance Laptop"     # LAP-PRO-16, one-time
