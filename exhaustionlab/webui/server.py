"""
FastAPI application factory for the ExhaustionLab dashboard.

ExhaustionLab v3.0 - Production-ready Web UI with:
- Unified Pydantic settings
- Structured JSON logging with request IDs
- Prometheus metrics
- Health check endpoint
- Standardized API responses
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..app.backtest.strategy_registry import StrategyRegistry
from ..app.config.settings import get_settings
from .api import build_api_router
from .middleware import MetricsMiddleware, RequestLoggingMiddleware
from .observability import get_health_status, get_logger, setup_logging
from .services import EvolutionAnalytics, LLMDebugLogStore, StrategyDashboardService

# Setup logging on module load
setup_logging()
logger = get_logger(__name__)

# Track startup time
_startup_time = time.time()


def create_app() -> FastAPI:
    """
    Create configured FastAPI application with v3.0 features.

    Includes:
    - Pydantic settings management
    - Structured logging middleware
    - Prometheus metrics middleware
    - CORS configuration
    - Health check and metrics endpoints
    """
    settings = get_settings()
    logger.info(f"Creating ExhaustionLab v{settings.version} application")
    logger.info(f"Environment: {settings.environment}")

    base_path = Path(__file__).parent
    templates = Jinja2Templates(directory=str(base_path / "templates"))
    static_dir = base_path / "static"

    # Initialize services
    logger.info("Initializing services...")
    registry = StrategyRegistry()
    log_store = LLMDebugLogStore()
    strategy_service = StrategyDashboardService(registry=registry)
    evolution_service = EvolutionAnalytics(registry=registry)

    # Create FastAPI app
    app = FastAPI(
        title="ExhaustionLab Web UI",
        description="AI-powered cryptocurrency trading strategy evolution platform",
        version=settings.version,
        docs_url="/api/docs" if settings.debug else None,
        redoc_url="/api/redoc" if settings.debug else None,
    )

    # Add middleware (order matters: last added = first executed)
    logger.info("Configuring middleware...")

    # CORS middleware
    if settings.ui.enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.ui.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        logger.info(f"CORS enabled for origins: {settings.ui.cors_origins}")

    # Metrics middleware
    if settings.observability.metrics_enabled:
        app.add_middleware(MetricsMiddleware)
        logger.info("Metrics middleware enabled")

    # Logging middleware
    app.add_middleware(RequestLoggingMiddleware)
    logger.info("Request logging middleware enabled")

    # Mount API routes and static assets
    logger.info("Mounting API routes...")
    app.include_router(build_api_router(log_store, strategy_service, evolution_service))
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def render_index(request: Request):
        """Server-rendered shell; dynamic data hydrates via JS."""
        overview = evolution_service.build_overview()
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "seed_overview": overview.model_dump(mode="json"),
            },
        )

    @app.get("/health")
    async def health_check():
        """
        Health check endpoint.

        Returns service status and uptime.
        """
        health = get_health_status()
        health["uptime_seconds"] = time.time() - _startup_time
        return health

    @app.get("/metrics")
    async def metrics():
        """
        Prometheus metrics endpoint.

        Returns metrics in Prometheus text format.
        """
        if not settings.observability.metrics_enabled:
            return Response(content="Metrics disabled", status_code=503)

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    @app.on_event("startup")
    async def startup_event():
        """Application startup event."""
        logger.info("=" * 80)
        logger.info(f"ExhaustionLab v{settings.version} starting...")
        logger.info(f"Environment: {settings.environment}")
        logger.info(f"Debug mode: {settings.debug}")
        logger.info(f"Web UI: http://{settings.ui.host}:{settings.ui.port}")
        logger.info(f"Health check: http://{settings.ui.host}:{settings.ui.port}/health")
        if settings.observability.metrics_enabled:
            logger.info(f"Metrics: http://{settings.ui.host}:{settings.ui.port}/metrics")
        logger.info("=" * 80)

    @app.on_event("shutdown")
    async def shutdown_event():
        """Application shutdown event."""
        logger.info("ExhaustionLab shutting down...")
        logger.info("Cleanup complete. Goodbye!")

    return app


app = create_app()


def main():
    """
    Convenience entrypoint.

    Usage:
        poetry run exhaustionlab-webui
        python -m exhaustionlab.webui.server
    """
    import uvicorn

    settings = get_settings()

    uvicorn.run(
        app,
        host=settings.ui.host,
        port=settings.ui.port,
        reload=settings.ui.reload,
        workers=settings.ui.workers,
        log_level=settings.ui.log_level,
    )


if __name__ == "__main__":
    main()
