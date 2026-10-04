import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from ctxd.app.api.auth import build_verifier
from ctxd.app.api.middleware import RequestContextMiddleware
from ctxd.app.api.routes import router
from ctxd.app.config.settings import Settings, get_settings
from ctxd.app.observability.logging import configure_logging
from ctxd.app.observability.tracing import configure_tracing
from ctxd.app.runtime import CorpusBackend, RuntimeServices, create_runtime

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    configure_logging(settings.log_level)
    logger.info("effective_configuration", extra={"fields": settings.effective_configuration()})
    services: RuntimeServices = app.state.services
    services.start()
    try:
        yield
    finally:
        services.close()


def create_app(store: CorpusBackend | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name, version=settings.service_version, lifespan=lifespan)
    app.state.services = create_runtime(store, settings)
    app.state.settings = settings
    app.state.verifier = build_verifier(settings)
    app.add_middleware(RequestContextMiddleware)
    if settings.cors_allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allow_origins,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.include_router(router)
    configure_tracing(app, settings)
    return app


app = create_app()
