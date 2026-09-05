from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.api import api_router
from app.config.logging import setup_logging
from app.config.settings import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import register_middleware
from app.db.seed import seed_db
from app.db.session import SessionLocal

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        seed_db(db)
    yield


# API docs are only exposed outside production, driven by ENVIRONMENT.
docs_enabled = not settings.is_production

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url=f"{settings.api_prefix}/docs" if docs_enabled else None,
    redoc_url=None,
    openapi_url=f"{settings.api_prefix}/openapi.json" if docs_enabled else None,
    # Hides the "Schemas" section at the bottom of Swagger UI.
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
)

register_middleware(app)
register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
