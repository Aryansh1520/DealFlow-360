"""Idempotent database seeding: default roles and the initial admin user."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.security import hash_password
from app.customers.models import Customer
from app.roles.models import Role
from app.users.models import User

logger = logging.getLogger(__name__)

ADMIN_ROLE = "admin"
DEFAULT_USER_ROLE = "user"

DEFAULT_ROLES = [
    {"name": ADMIN_ROLE, "description": "Full access", "permissions": ["*"]},
    {"name": DEFAULT_USER_ROLE, "description": "Standard user", "permissions": []},
]

# Demo-only credentials, mirroring the seeded admin account below.
DEMO_CUSTOMER_EMAIL = "customer@example.com"
DEMO_CUSTOMER_PASSWORD = "customer12345"


def seed_db(db: Session) -> None:
    for spec in DEFAULT_ROLES:
        if db.scalar(select(Role).where(Role.name == spec["name"])) is None:
            db.add(Role(**spec))
            logger.info("Seeded role: %s", spec["name"])
    db.commit()

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

    if db.scalar(select(Customer).where(Customer.email == DEMO_CUSTOMER_EMAIL)) is None:
        db.add(
            Customer(
                name="Acme Corp",
                email=DEMO_CUSTOMER_EMAIL,
                company="Acme Corp",
                tier="gold",
                hashed_password=hash_password(DEMO_CUSTOMER_PASSWORD),
                portal_enabled=True,
            )
        )
        db.commit()
        logger.info("Seeded demo customer: %s", DEMO_CUSTOMER_EMAIL)
