"""FastAPI application factory for the ExhaustionLab dashboard."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..app.backtest.strategy_registry import StrategyRegistry
from .api import build_api_router
from .services import (
    EvolutionAnalytics,
    LLMDebugLogStore,
    StrategyDashboardService,
)


def create_app() -> FastAPI:
    """Create configured FastAPI application."""
    base_path = Path(__file__).parent
    templates = Jinja2Templates(directory=str(base_path / "templates"))
    static_dir = base_path / "static"

    registry = StrategyRegistry()
    log_store = LLMDebugLogStore()
    strategy_service = StrategyDashboardService(registry=registry)
    evolution_service = EvolutionAnalytics(registry=registry)

    app = FastAPI(
        title="ExhaustionLab Web UI",
        description="Realtime evolution view + debugging console",
    )

    # Mount API routes and static assets
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

    return app


app = create_app()


def main():
    """Convenience entrypoint: python -m exhaustionlab.webui.server."""
    import uvicorn

    port = int(os.environ.get("WEBUI_PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
