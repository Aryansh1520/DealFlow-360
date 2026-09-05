"""Generic CRUD base with pagination, filtering, sorting and search.

Instantiate directly for any model:

    user_crud = CRUDBase(User, search_fields=["email", "full_name"])
    items, total = user_crud.list(db, params=params, filters={"is_active": True})
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import asc, desc, func, inspect, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.pagination import PageParams
from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class CRUDBase(Generic[ModelT]):
    def __init__(self, model: type[ModelT], search_fields: list[str] | None = None):
        self.model = model
        self.search_fields = search_fields or []
        self._pk = inspect(model).primary_key[0]

    def _column(self, name: str):
        """Resolve a column by name, rejecting anything that isn't a real column."""
        if name not in self.model.__mapper__.columns:
            raise BadRequestException(f"Unknown field: {name}")
        return getattr(self.model, name)

    def get(self, db: Session, id: Any) -> ModelT | None:
        return db.get(self.model, id)

    def get_or_404(self, db: Session, id: Any) -> ModelT:
        obj = self.get(db, id)
        if obj is None:
            raise NotFoundException(f"{self.model.__name__} not found")
        return obj

    def list(
        self,
        db: Session,
        *,
        params: PageParams,
        filters: dict[str, Any] | None = None,
    ) -> tuple[list[ModelT], int]:
        """Return (items, total) applying equality filters, search, sorting and pagination."""
        stmt = select(self.model)

        if filters:
            for field, value in filters.items():
                if value is not None:
                    stmt = stmt.where(self._column(field) == value)

        if params.search and self.search_fields:
            pattern = f"%{params.search}%"
            stmt = stmt.where(
                or_(*[self._column(field).ilike(pattern) for field in self.search_fields])
            )

        total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

        if params.sort_by:
            column = self._column(params.sort_by)
            stmt = stmt.order_by(desc(column) if params.sort_order == "desc" else asc(column))
        else:
            stmt = stmt.order_by(self._pk)

        stmt = stmt.offset((params.page - 1) * params.page_size).limit(params.page_size)
        return list(db.scalars(stmt).all()), total

    def create(self, db: Session, data: dict[str, Any]) -> ModelT:
        obj = self.model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, obj: ModelT, data: dict[str, Any]) -> ModelT:
        for field, value in data.items():
            setattr(obj, field, value)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, obj: ModelT) -> None:
        db.delete(obj)
        db.commit()
