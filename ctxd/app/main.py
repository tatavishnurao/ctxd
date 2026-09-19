from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ctxd.app.api.middleware import RequestContextMiddleware
from ctxd.app.api.routes import router
from ctxd.app.config.settings import get_settings
from ctxd.app.observability.logging import configure_logging
from ctxd.app.observability.tracing import configure_tracing


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.service_version, lifespan=lifespan)
    app.add_middleware(RequestContextMiddleware)
    app.include_router(router)
    configure_tracing(app, settings)
    return app


app = create_app()
