from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import Category, Product, ProductVariant
from app.catalog.schemas import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductVariantCreate,
    ProductVariantRead,
    ProductVariantUpdate,
)
from app.core.crud import CRUDBase
from app.core.deps import require_permissions
from app.core.exceptions import ConflictException, NotFoundException
from app.core.pagination import Page, PageParams
from app.core.responses import SuccessResponse, ok
from app.db.session import get_db

router = APIRouter()

DbSession = Annotated[Session, Depends(get_db)]

category_crud = CRUDBase(Category, search_fields=["name", "code"])
product_crud = CRUDBase(Product, search_fields=["name", "sku"])
variant_crud = CRUDBase(ProductVariant)

CatalogRead = Depends(require_permissions("catalog:read"))
CatalogWrite = Depends(require_permissions("catalog:write"))


# ---- Categories ---------------------------------------------------------------

@router.get("/categories", response_model=SuccessResponse[Page[CategoryRead]], dependencies=[CatalogRead])
def list_categories(db: DbSession, params: Annotated[PageParams, Depends()]):
    items, total = category_crud.list(db, params=params)
    return ok(Page[CategoryRead].create(items, total, params), "Categories retrieved successfully.")


@router.post(
    "/categories",
    response_model=SuccessResponse[CategoryRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[CatalogWrite],
)
def create_category(payload: CategoryCreate, db: DbSession):
    if db.scalar(select(Category).where(Category.code == payload.code)):
        raise ConflictException("A category with this code already exists")
    category = category_crud.create(db, payload.model_dump())
    return ok(category, "Category created successfully.")


@router.get("/categories/{category_id}", response_model=SuccessResponse[CategoryRead], dependencies=[CatalogRead])
def get_category(category_id: int, db: DbSession):
    return ok(category_crud.get_or_404(db, category_id), "Category retrieved successfully.")


@router.patch("/categories/{category_id}", response_model=SuccessResponse[CategoryRead], dependencies=[CatalogWrite])
def update_category(category_id: int, payload: CategoryUpdate, db: DbSession):
    category = category_crud.get_or_404(db, category_id)
    updated = category_crud.update(db, category, payload.model_dump(exclude_unset=True))
    return ok(updated, "Category updated successfully.")


@router.delete("/categories/{category_id}", response_model=SuccessResponse[None], dependencies=[CatalogWrite])
def delete_category(category_id: int, db: DbSession):
    category = category_crud.get_or_404(db, category_id)
    category_crud.delete(db, category)
    return ok(None, "Category deleted successfully.")


# ---- Products -------------------------------------------------------------------

@router.get("/products", response_model=SuccessResponse[Page[ProductRead]], dependencies=[CatalogRead])
def list_products(
    db: DbSession,
    params: Annotated[PageParams, Depends()],
    category_id: Annotated[int | None, Query()] = None,
    is_promoted: Annotated[bool | None, Query()] = None,
    line_type: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
):
    items, total = product_crud.list(
        db,
        params=params,
        filters={
            "category_id": category_id,
            "is_promoted": is_promoted,
            "line_type": line_type,
            "is_active": is_active,
        },
    )
    page = Page[ProductRead].create([ProductRead.from_model(p) for p in items], total, params)
    return ok(page, "Products retrieved successfully.")


@router.post(
    "/products",
    response_model=SuccessResponse[ProductRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[CatalogWrite],
)
def create_product(payload: ProductCreate, db: DbSession):
    if db.scalar(select(Product).where(Product.sku == payload.sku)):
        raise ConflictException("A product with this SKU already exists")
    product = product_crud.create(db, payload.model_dump())
    db.refresh(product)
    return ok(ProductRead.from_model(product), "Product created successfully.")


@router.get("/products/{product_id}", response_model=SuccessResponse[ProductRead], dependencies=[CatalogRead])
def get_product(product_id: int, db: DbSession):
    product = product_crud.get_or_404(db, product_id)
    return ok(ProductRead.from_model(product), "Product retrieved successfully.")


@router.patch("/products/{product_id}", response_model=SuccessResponse[ProductRead], dependencies=[CatalogWrite])
def update_product(product_id: int, payload: ProductUpdate, db: DbSession):
    product = product_crud.get_or_404(db, product_id)
    updated = product_crud.update(db, product, payload.model_dump(exclude_unset=True))
    return ok(ProductRead.from_model(updated), "Product updated successfully.")


@router.delete("/products/{product_id}", response_model=SuccessResponse[None], dependencies=[CatalogWrite])
def delete_product(product_id: int, db: DbSession):
    product = product_crud.get_or_404(db, product_id)
    product_crud.delete(db, product)
    return ok(None, "Product deleted successfully.")


# ---- Variants (nested under product) ---------------------------------------------

@router.post(
    "/products/{product_id}/variants",
    response_model=SuccessResponse[ProductVariantRead],
    status_code=status.HTTP_201_CREATED,
    dependencies=[CatalogWrite],
)
def create_variant(product_id: int, payload: ProductVariantCreate, db: DbSession):
    product_crud.get_or_404(db, product_id)
    existing = db.scalar(
        select(ProductVariant).where(
            ProductVariant.product_id == product_id,
            ProductVariant.attribute == payload.attribute,
            ProductVariant.value == payload.value,
        )
    )
    if existing:
        raise ConflictException("This variant already exists for the product")
    variant = variant_crud.create(db, {**payload.model_dump(), "product_id": product_id})
    return ok(variant, "Variant created successfully.")


@router.patch(
    "/products/{product_id}/variants/{variant_id}",
    response_model=SuccessResponse[ProductVariantRead],
    dependencies=[CatalogWrite],
)
def update_variant(product_id: int, variant_id: int, payload: ProductVariantUpdate, db: DbSession):
    variant = variant_crud.get_or_404(db, variant_id)
    if variant.product_id != product_id:
        raise NotFoundException("Variant not found for this product")
    updated = variant_crud.update(db, variant, payload.model_dump(exclude_unset=True))
    return ok(updated, "Variant updated successfully.")


@router.delete(
    "/products/{product_id}/variants/{variant_id}",
    response_model=SuccessResponse[None],
    dependencies=[CatalogWrite],
)
def delete_variant(product_id: int, variant_id: int, db: DbSession):
    variant = variant_crud.get_or_404(db, variant_id)
    if variant.product_id != product_id:
        raise NotFoundException("Variant not found for this product")
    variant_crud.delete(db, variant)
    return ok(None, "Variant deleted successfully.")
