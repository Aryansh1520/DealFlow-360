"""Database engine, session factory and request-scoped session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.db.tenancy import register_tenancy

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Wire automatic tenant scoping (implicit org_id filter on reads, org_id stamp on
# writes) onto every session opened from this factory.
register_tenancy(SessionLocal)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
