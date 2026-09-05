"""Database engine, session factory and request-scoped session dependency."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import settings
from app.db.tenancy import register_tenancy

engine = create_engine(settings.database_url, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

# Wire automatic tenant scoping (implicit org_id filter on reads, org_id stamp on
# writes) onto every session opened from this factory.
register_tenancy(SessionLocal)


# SSE frames recorded during a transaction are buffered on `session.info` and only
# flushed to Redis once the transaction actually commits — a rolled-back mutation
# must never emit a live frame. Import locally so a stream/redis import problem
# can't break the session factory itself.
@event.listens_for(SessionLocal, "after_commit")
def _flush_sse_frames(session: Session) -> None:
    from app.events.stream import flush_session_frames

    flush_session_frames(session)


@event.listens_for(SessionLocal, "after_rollback")
def _discard_sse_frames(session: Session) -> None:
    from app.events.stream import discard_session_frames

    discard_session_frames(session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
