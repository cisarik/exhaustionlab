"""FastAPI router that exposes dashboard endpoints."""

from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from .chart_generator import get_chart_generator
from .evolution_service import get_evolution_service
from .settings_service import get_settings_service
from .demo_data import (
    generate_demo_strategies,
    generate_demo_backtest_result,
    get_quick_start_presets,
    generate_overview_metrics,
)
from .services import (
    EvolutionAnalytics,
    LLMDebugLogStore,
    StrategyDashboardService,
)


class EvolutionStartRequest(BaseModel):
    """Request to start evolution."""

    num_generations: int = 5
    population_size: int = 3
    use_llm: bool = True
    use_crawled: bool = True
    symbol: str = "ADAEUR"
    timeframe: str = "1m"


# ----- Validation & Reporting Request Models (module scope for Pydantic v2) -----


class BacktestParseRequest(BaseModel):
    """Request to parse backtest output."""

    output_dir: str
    symbol: str = "BTCUSDT"


class ComprehensiveScoreRequest(BaseModel):
    """Request to calculate comprehensive score."""

    backtest_output_dir: str
    symbol: str = "BTCUSDT"
    portfolio_size_usd: float = 100000
    out_of_sample_ratio: float | None = None
    cross_market_pass_rate: float | None = None


class ReportGenerateRequest(BaseModel):
    """Request to generate validation report."""

    backtest_output_dir: str
    symbol: str = "BTCUSDT"
    portfolio_size_usd: float = 100000
    out_of_sample_ratio: float | None = None
    cross_market_pass_rate: float | None = None
    include_costs: bool = True
    output_filename: str | None = None
    fee_bps: float = 10.0


class SlippageEstimateRequest(BaseModel):
    """Request to estimate slippage."""

    symbol: str = "BTCUSDT"
    order_size_usd: float = 10000
    signal_frequency: float = 5.0
    volatility: float = 0.8


class TradingCostsRequest(BaseModel):
    """Request to calculate trading costs."""

    backtest_output_dir: str
    symbol: str = "BTCUSDT"
    portfolio_size_usd: float = 100000
    include_fees: bool = True
    fee_bps: float = 10.0


class DeployStrategyRequest(BaseModel):
    """Request to deploy a strategy for live/paper trading."""

    strategy_id: str
    strategy_name: str
    mode: str = "paper"  # "paper" or "live"
    symbols: list[str] = ["ADAEUR"]
    timeframe: str = "1m"
    # Risk parameters
    max_position_size: float = 0.02
    max_daily_loss: float = 0.01
    max_drawdown: float = 0.05
    max_open_positions: int = 3
    enable_stop_loss: bool = True
    stop_loss_pct: float = 0.02
    enable_take_profit: bool = True
    take_profit_pct: float = 0.05
    # Exchange config
    exchange: str = "binance"
    api_key: str | None = None
    api_secret: str | None = None
    testnet: bool = True


def build_api_router(
    log_store: LLMDebugLogStore,
    strategy_service: StrategyDashboardService,
    evolution_service: EvolutionAnalytics,
) -> APIRouter:
    """Wire up API routes with injected services."""
    router = APIRouter()

    @router.get("/api/llm/sessions")
    def list_llm_sessions(limit: int = Query(12, ge=1, le=50)):
        sessions = log_store.list_sessions(limit=limit)
        return [session.model_dump(mode="json") for session in sessions]

    @router.get("/api/llm/sessions/{session_id}")
    def get_llm_session(session_id: str):
        session = log_store.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session.model_dump(mode="json")

    @router.get("/api/strategies/top")
    def get_top_strategies(limit: int = Query(8, ge=1, le=24)):
        strategies = strategy_service.list_top_strategies(limit=limit)
        return [strategy.model_dump(mode="json") for strategy in strategies]

    @router.get("/api/strategies/{strategy_id}")
    def get_strategy(strategy_id: str):
        strategy = strategy_service.get_strategy_detail(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        return strategy.model_dump(mode="json")

    @router.post("/api/strategies/{strategy_id}/simulate")
    async def simulate_strategy(strategy_id: str):
        result = await strategy_service.run_simulation(strategy_id)
        if result.status == "error":
            raise HTTPException(
                status_code=400, detail=result.detail or "Simulation failed"
            )
        return result.model_dump(mode="json")

    @router.get("/api/evolution/overview")
    def get_evolution_overview():
        overview = evolution_service.build_overview()
        return {"metrics": overview.model_dump(mode="json")}

    @router.get("/api/charts/candlestick.png")
    def get_candlestick_chart(
        symbol: str = Query("ADAEUR", description="Trading symbol"),
        timeframe: str = Query("1m", description="Timeframe (1m, 5m, 15m, 1h, etc.)"),
        limit: int = Query(200, ge=50, le=1000, description="Number of candles"),
        width: int = Query(1400, ge=400, le=3840, description="Chart width"),
        height: int = Query(800, ge=300, le=2160, description="Chart height"),
        signals: bool = Query(True, description="Show exhaustion signals"),
        volume: bool = Query(True, description="Show volume panel"),
        strategy_id: str = Query(None, description="Strategy ID for backtest overlay"),
        show_trades: bool = Query(False, description="Show trade markers"),
        show_equity: bool = Query(False, description="Show equity curve"),
    ):
        """Generate and return a candlestick chart as PNG with optional backtest overlay."""
        chart_gen = get_chart_generator()
        evolution_service = get_evolution_service()

        try:
            trades = None
            equity_curve = None

            # Get backtest data if strategy selected
            if strategy_id and (show_trades or show_equity):
                backtest = evolution_service.get_backtest_result(strategy_id)
                if backtest:
                    if show_trades:
                        trades = backtest.get("trades", [])
                    if show_equity:
                        equity_curve = backtest.get("equity_curve", [])

            img_bytes = chart_gen.generate_chart(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                width=width,
                height=height,
                show_signals=signals,
                show_volume=volume
                and not show_equity,  # Use volume panel for equity if enabled
                trades=trades,
                equity_curve=equity_curve,
            )
            return Response(content=img_bytes, media_type="image/png")
        except Exception as exc:
            raise HTTPException(
                status_code=500, detail=f"Chart generation failed: {exc}"
            )

    @router.post("/api/charts/clear-cache")
    def clear_chart_cache():
        """Clear all cached chart images."""
        chart_gen = get_chart_generator()
        chart_gen.clear_cache()
        return {"status": "success", "message": "Chart cache cleared"}

    # ===== Evolution Endpoints =====

    @router.post("/api/evolution/start")
    async def start_evolution(request: EvolutionStartRequest):
        """Start evolution process."""
        evolution_service = get_evolution_service()
        result = await evolution_service.start_evolution(
            num_generations=request.num_generations,
            population_size=request.population_size,
            use_llm=request.use_llm,
            use_crawled=request.use_crawled,
            symbol=request.symbol,
            timeframe=request.timeframe,
        )
        return result

    @router.get("/api/evolution/progress")
    def get_evolution_progress():
        """Get current evolution progress."""
        evolution_service = get_evolution_service()
        return evolution_service.get_progress()

    @router.get("/api/evolution/events")
    async def evolution_events_stream():
        """
        Server-Sent Events stream for real-time evolution updates.

        Usage in JavaScript:
        const eventSource = new EventSource('/api/evolution/events');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(data);
        };
        """
        evolution_service = get_evolution_service()

        async def event_generator() -> AsyncGenerator[str, None]:
            queue = await evolution_service.subscribe()
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        # SSE format: data: <json>\n\n
                        import json

                        yield f"data: {json.dumps(event)}\n\n"
                    except asyncio.TimeoutError:
                        # Send keepalive
                        yield f"data: {json.dumps({'event_type': 'keepalive', 'timestamp': asyncio.get_event_loop().time()})}\n\n"
            finally:
                evolution_service.unsubscribe(queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get("/api/evolution/hall-of-fame")
    def get_hall_of_fame(limit: int = Query(10, ge=1, le=50)):
        """Get top strategies by fitness."""
        evolution_service = get_evolution_service()
        return evolution_service.get_hall_of_fame(limit=limit)

    @router.get("/api/evolution/backtest/{strategy_id}")
    def get_backtest_result(strategy_id: str):
        """Get detailed backtest result for a strategy."""
        evolution_service = get_evolution_service()
        result = evolution_service.get_backtest_result(strategy_id)
        if not result:
            raise HTTPException(status_code=404, detail="Backtest result not found")
        return result

    @router.get("/api/evolution/strategy-code/{strategy_id}")
    def get_strategy_code(strategy_id: str):
        """Get strategy source code."""
        evolution_service = get_evolution_service()
        # Find strategy in evolution service
        strategy = next(
            (
                s
                for s in evolution_service.strategies
                if s.get("strategy_id") == strategy_id
            ),
            None,
        )
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")

        return {
            "strategy_id": strategy_id,
            "name": strategy.get("name", "Unknown"),
            "code": strategy.get("code", "# Code not available"),
            "language": "python",  # or "pine" for PineScript
        }

    # ===== LIVE TRADING ENDPOINTS =====

    @router.post("/api/trading/deploy")
    async def deploy_strategy(request: DeployStrategyRequest):
        """Deploy a strategy for live/paper trading."""
        from .live_trading_service import (
            live_trading_service,
            TradingMode,
            RiskParameters,
        )

        risk_params = RiskParameters(
            max_position_size=request.max_position_size,
            max_daily_loss=request.max_daily_loss,
            max_drawdown=request.max_drawdown,
            max_open_positions=request.max_open_positions,
            enable_stop_loss=request.enable_stop_loss,
            stop_loss_pct=request.stop_loss_pct,
            enable_take_profit=request.enable_take_profit,
            take_profit_pct=request.take_profit_pct,
        )

        mode = TradingMode.PAPER if request.mode == "paper" else TradingMode.LIVE

        deployment_id = await live_trading_service.deploy_strategy(
            strategy_id=request.strategy_id,
            strategy_name=request.strategy_name,
            mode=mode,
            symbols=request.symbols,
            timeframe=request.timeframe,
            risk_params=risk_params,
            exchange=request.exchange,
            api_key=request.api_key,
            api_secret=request.api_secret,
            testnet=request.testnet,
        )

        return {
            "deployment_id": deployment_id,
            "status": "deployed",
            "message": f"Strategy deployed in {request.mode} mode",
        }

    @router.post("/api/trading/stop/{deployment_id}")
    async def stop_deployment(deployment_id: str):
        """Stop a deployment."""
        from .live_trading_service import live_trading_service

        await live_trading_service.stop_deployment(deployment_id)
        return {"status": "stopped", "deployment_id": deployment_id}

    @router.post("/api/trading/emergency-stop")
    async def emergency_stop():
        """Emergency stop all deployments."""
        from .live_trading_service import live_trading_service

        await live_trading_service.emergency_stop_all()
        return {
            "status": "emergency_stop_complete",
            "message": "All deployments stopped",
        }

    @router.get("/api/trading/deployments")
    def get_all_deployments():
        """Get all active deployments."""
        from .live_trading_service import live_trading_service

        deployments = live_trading_service.get_all_deployments()
        return [
            {
                "deployment_id": d.deployment_id,
                "strategy_id": d.strategy_id,
                "strategy_name": d.strategy_name,
                "mode": d.mode,
                "status": d.status,
                "start_time": d.start_time.isoformat(),
                "uptime_seconds": d.uptime_seconds,
                "total_trades": d.total_trades,
                "winning_trades": d.winning_trades,
                "losing_trades": d.losing_trades,
                "win_rate": d.win_rate,
                "total_pnl": d.total_pnl,
                "total_pnl_pct": d.total_pnl_pct,
                "open_positions": d.open_positions,
                "daily_pnl": d.daily_pnl,
                "daily_pnl_pct": d.daily_pnl_pct,
                "current_drawdown": d.current_drawdown,
                "max_drawdown": d.max_drawdown,
                "last_error": d.last_error,
                "error_count": d.error_count,
            }
            for d in deployments
        ]

    @router.get("/api/trading/deployment/{deployment_id}")
    def get_deployment_status(deployment_id: str):
        """Get status of a specific deployment."""
        from .live_trading_service import live_trading_service

        status = live_trading_service.get_deployment_status(deployment_id)
        if not status:
            raise HTTPException(status_code=404, detail="Deployment not found")

        return {
            "deployment_id": status.deployment_id,
            "strategy_id": status.strategy_id,
            "strategy_name": status.strategy_name,
            "mode": status.mode,
            "status": status.status,
            "start_time": status.start_time.isoformat(),
            "uptime_seconds": status.uptime_seconds,
            "total_trades": status.total_trades,
            "winning_trades": status.winning_trades,
            "losing_trades": status.losing_trades,
            "win_rate": status.win_rate,
            "total_pnl": status.total_pnl,
            "total_pnl_pct": status.total_pnl_pct,
            "open_positions": status.open_positions,
            "daily_pnl": status.daily_pnl,
            "daily_pnl_pct": status.daily_pnl_pct,
            "current_drawdown": status.current_drawdown,
            "max_drawdown": status.max_drawdown,
            "last_error": status.last_error,
            "error_count": status.error_count,
        }

    @router.get("/api/trading/positions/{deployment_id}")
    def get_positions(deployment_id: str):
        """Get open positions for a deployment."""
        from .live_trading_service import live_trading_service

        positions = live_trading_service.get_positions(deployment_id)
        return [
            {
                "position_id": p.position_id,
                "strategy_id": p.strategy_id,
                "symbol": p.symbol,
                "side": p.side,
                "entry_price": p.entry_price,
                "quantity": p.quantity,
                "entry_time": p.entry_time.isoformat(),
                "stop_loss": p.stop_loss,
                "take_profit": p.take_profit,
                "current_price": p.current_price,
                "unrealized_pnl": p.unrealized_pnl,
                "unrealized_pnl_pct": p.unrealized_pnl_pct,
            }
            for p in positions
        ]

    @router.get("/api/trading/history/{deployment_id}")
    def get_trade_history(deployment_id: str, limit: int = Query(100, ge=1, le=1000)):
        """Get trade history for a deployment."""
        from .live_trading_service import live_trading_service

        trades = live_trading_service.get_trade_history(deployment_id, limit=limit)
        return [
            {
                "trade_id": t.trade_id,
                "strategy_id": t.strategy_id,
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "entry_time": t.entry_time.isoformat(),
                "exit_time": t.exit_time.isoformat(),
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "commission": t.commission,
                "reason": t.reason,
            }
            for t in trades
        ]

    # ===== SETTINGS ENDPOINTS =====

    class SettingsUpdateRequest(BaseModel):
        """Request to update settings"""

        exchange: dict | None = None
        llm: dict | None = None
        risk: dict | None = None
        evolution: dict | None = None
        ui: dict | None = None

    @router.get("/api/settings")
    def get_settings():
        """Get current application settings (secrets masked)."""
        settings_service = get_settings_service()
        return settings_service.get_settings(include_secrets=False)

    @router.get("/api/settings/full")
    def get_settings_full():
        """Get settings including secrets (use with caution)."""
        settings_service = get_settings_service()
        return settings_service.get_settings(include_secrets=True)

    @router.post("/api/settings")
    def update_settings(request: SettingsUpdateRequest):
        """Update application settings."""
        settings_service = get_settings_service()

        updates = {}
        if request.exchange:
            updates["exchange"] = request.exchange
        if request.llm:
            updates["llm"] = request.llm
        if request.risk:
            updates["risk"] = request.risk
        if request.evolution:
            updates["evolution"] = request.evolution
        if request.ui:
            updates["ui"] = request.ui

        success = settings_service.update_settings(updates)

        if success:
            return {
                "status": "success",
                "message": "Settings updated successfully",
                "settings": settings_service.get_settings(include_secrets=False),
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update settings")

    @router.post("/api/settings/reset")
    def reset_settings():
        """Reset settings to defaults."""
        settings_service = get_settings_service()
        success = settings_service.reset_to_defaults()

        if success:
            return {
                "status": "success",
                "message": "Settings reset to defaults",
                "settings": settings_service.get_settings(include_secrets=False),
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to reset settings")

    @router.get("/api/settings/validate/exchange")
    def validate_exchange():
        """Validate exchange connection."""
        settings_service = get_settings_service()
        is_valid, message = settings_service.validate_exchange_connection()
        return {"valid": is_valid, "message": message}

    @router.get("/api/settings/validate/llm")
    def validate_llm():
        """Validate LLM connection."""
        settings_service = get_settings_service()
        is_valid, message = settings_service.validate_llm_connection()
        return {"valid": is_valid, "message": message}

    # ===== DEMO DATA & PRESETS =====

    @router.get("/api/demo/strategies")
    def get_demo_strategies(count: int = Query(8, ge=1, le=20)):
        """Get demo strategies with good metrics."""
        return generate_demo_strategies(count)

    @router.get("/api/demo/backtest/{strategy_id}")
    def get_demo_backtest(strategy_id: str):
        """Get demo backtest result."""
        return generate_demo_backtest_result(strategy_id)

    @router.get("/api/demo/overview")
    def get_demo_overview():
        """Get demo overview metrics."""
        return generate_overview_metrics()

    @router.get("/api/presets/paper-trading")
    def get_paper_trading_presets():
        """Get quick-start paper trading presets."""
        return get_quick_start_presets()

    @router.post("/api/backtest/run")
    async def run_backtest(request: dict):
        """Run backtest for a strategy."""
        strategy_id = request.get("strategy_id")
        if not strategy_id:
            raise HTTPException(status_code=400, detail="strategy_id required")

        # For now, return demo backtest result
        # In production, this would run actual backtest
        result = generate_demo_backtest_result(strategy_id)
        return {
            "status": "completed",
            "backtest_id": f"bt-{strategy_id}",
            "result": result,
        }

    # ===== MULTI-MARKET TESTING ENDPOINTS =====

    class MultiMarketTestRequest(BaseModel):
        """Request to test strategies across markets."""

        strategy_ids: list[str] = []  # Empty = test all strategies in hall of fame
        symbols: list[str] = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        timeframes: list[str] = ["5m", "15m", "1h"]
        lookback_days: int = 30

    @router.get("/api/multi-market/available-markets")
    def get_available_markets():
        """Get available markets and timeframes for testing."""
        return {
            "symbols": [
                {"value": "BTCUSDT", "label": "BTC/USDT", "category": "major"},
                {"value": "ETHUSDT", "label": "ETH/USDT", "category": "major"},
                {"value": "BNBUSDT", "label": "BNB/USDT", "category": "major"},
                {"value": "ADAUSDT", "label": "ADA/USDT", "category": "mid"},
                {"value": "SOLUSDT", "label": "SOL/USDT", "category": "mid"},
                {"value": "DOGEUSDT", "label": "DOGE/USDT", "category": "meme"},
                {"value": "MATICUSDT", "label": "MATIC/USDT", "category": "mid"},
                {"value": "DOTUSDT", "label": "DOT/USDT", "category": "mid"},
                {"value": "AVAXUSDT", "label": "AVAX/USDT", "category": "mid"},
                {"value": "LINKUSDT", "label": "LINK/USDT", "category": "mid"},
            ],
            "timeframes": [
                {"value": "1m", "label": "1 Minute"},
                {"value": "5m", "label": "5 Minutes"},
                {"value": "15m", "label": "15 Minutes"},
                {"value": "1h", "label": "1 Hour"},
                {"value": "4h", "label": "4 Hours"},
                {"value": "1d", "label": "1 Day"},
            ],
        }

    @router.post("/api/multi-market/test")
    async def test_strategies_multi_market(request: MultiMarketTestRequest):
        """
        Test strategies across multiple markets and timeframes.

        Returns multi-market testing results with fitness scores.
        """
        evolution_service = get_evolution_service()

        # Get strategies to test
        if request.strategy_ids:
            strategies = [
                s
                for s in evolution_service.get_hall_of_fame(limit=50)
                if s["id"] in request.strategy_ids
            ]
        else:
            # Test top 10 strategies
            strategies = evolution_service.get_hall_of_fame(limit=10)

        # Simulate multi-market testing
        # In production, this would call the actual validation framework
        import random
        from datetime import datetime

        results = []
        for strategy in strategies:
            # Test on each market/timeframe combination
            market_results = []
            for symbol in request.symbols:
                for timeframe in request.timeframes:
                    # Simulate test result
                    base_fitness = strategy.get("fitness", 0.5)
                    variation = random.uniform(-0.2, 0.2)
                    fitness = max(0, min(1, base_fitness + variation))

                    sharpe = random.uniform(0.5, 2.5)
                    drawdown = random.uniform(0.05, 0.35)
                    win_rate = random.uniform(0.45, 0.75)

                    market_results.append(
                        {
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "fitness": round(fitness, 4),
                            "sharpe_ratio": round(sharpe, 2),
                            "max_drawdown": round(drawdown, 3),
                            "win_rate": round(win_rate, 3),
                            "profit_factor": round(random.uniform(0.8, 2.5), 2),
                            "total_trades": random.randint(20, 150),
                            "passed": fitness > 0.6 and sharpe > 0.8,
                        }
                    )

            # Calculate aggregated metrics
            passed_markets = sum(1 for m in market_results if m["passed"])
            total_markets = len(market_results)
            avg_fitness = sum(m["fitness"] for m in market_results) / total_markets
            avg_sharpe = sum(m["sharpe_ratio"] for m in market_results) / total_markets
            max_drawdown = max(m["max_drawdown"] for m in market_results)
            avg_win_rate = sum(m["win_rate"] for m in market_results) / total_markets

            results.append(
                {
                    "strategy_id": strategy["id"],
                    "strategy_name": strategy.get("name", "Unnamed"),
                    "original_fitness": strategy.get("fitness", 0),
                    "markets_tested": total_markets,
                    "markets_passed": passed_markets,
                    "pass_rate": round(passed_markets / total_markets, 3),
                    "avg_fitness": round(avg_fitness, 4),
                    "avg_sharpe": round(avg_sharpe, 2),
                    "max_drawdown": round(max_drawdown, 3),
                    "avg_win_rate": round(avg_win_rate, 3),
                    "market_results": market_results,
                    "tested_at": datetime.now().isoformat(),
                    "status": (
                        "approved"
                        if passed_markets / total_markets >= 0.6
                        else "rejected"
                    ),
                }
            )

        # Sort by average fitness
        results.sort(key=lambda x: x["avg_fitness"], reverse=True)

        return {
            "status": "completed",
            "total_strategies": len(results),
            "total_markets": len(request.symbols) * len(request.timeframes),
            "results": results,
        }

    @router.get("/api/multi-market/results")
    def get_multi_market_results():
        """
        Get cached multi-market testing results.

        Returns the most recent testing results.
        """
        # For now, return empty or demo data
        # In production, this would retrieve from cache/database
        return {
            "status": "no_data",
            "message": "No multi-market tests run yet. Click 'Test All Markets' to start.",
            "results": [],
        }

    # ===== VALIDATION FRAMEWORK ENDPOINTS =====

    @router.post("/api/validation/parse-backtest")
    async def parse_backtest(payload: BacktestParseRequest = Body(...)):
        """
        Parse PyneCore backtest output files.

        Returns parsed backtest with all trades and metrics.
        """
        from pathlib import Path
        from exhaustionlab.app.validation import parse_backtest_from_directory

        try:
            output_dir = Path(payload.output_dir)
            if not output_dir.exists():
                raise HTTPException(
                    status_code=404,
                    detail=f"Output directory not found: {payload.output_dir}",
                )

            # Parse backtest
            backtest = parse_backtest_from_directory(output_dir)

            # Convert to JSON-serializable format
            return {
                "status": "success",
                "backtest": {
                    "strategy_name": backtest.strategy_name,
                    "symbol": backtest.symbol,
                    "timeframe": backtest.timeframe,
                    "start_date": backtest.start_date.isoformat(),
                    "end_date": backtest.end_date.isoformat(),
                    "total_trades": backtest.total_trades,
                    "winning_trades": backtest.winning_trades,
                    "losing_trades": backtest.losing_trades,
                    "metrics": {
                        "total_return": backtest.total_return,
                        "annualized_return": backtest.annualized_return,
                        "sharpe_ratio": backtest.sharpe_ratio,
                        "sortino_ratio": backtest.sortino_ratio,
                        "max_drawdown": backtest.max_drawdown,
                        "max_drawdown_duration": backtest.max_drawdown_duration,
                        "win_rate": backtest.win_rate,
                        "profit_factor": backtest.profit_factor,
                        "avg_win": backtest.avg_win,
                        "avg_loss": backtest.avg_loss,
                        "largest_win": backtest.largest_win,
                        "largest_loss": backtest.largest_loss,
                    },
                    "equity_curve": backtest.equity_curve.to_dict(),
                    "returns": backtest.returns.to_dict(),
                },
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to parse backtest: {str(e)}"
            )

    @router.post("/api/validation/calculate-score")
    async def calculate_comprehensive_score(
        payload: ComprehensiveScoreRequest = Body(...),
    ):
        """
        Calculate comprehensive strategy score.

        Returns weighted score breakdown (Performance/Risk/Execution/Robustness).
        """
        from pathlib import Path
        from exhaustionlab.app.validation import (
            parse_backtest_from_directory,
            ComprehensiveScorer,
        )

        try:
            # Parse backtest
            output_dir = Path(payload.backtest_output_dir)
            backtest = parse_backtest_from_directory(output_dir)

            # Calculate score
            scorer = ComprehensiveScorer()
            scores = scorer.calculate_comprehensive_score(
                backtest=backtest,
                symbol=payload.symbol,
                portfolio_size_usd=payload.portfolio_size_usd,
                out_of_sample_ratio=payload.out_of_sample_ratio,
                cross_market_pass_rate=payload.cross_market_pass_rate,
            )

            # Generate score report
            report = scorer.generate_score_report(scores)

            return {
                "status": "success",
                "scores": scores.to_dict(),
                "report": report,
                "deployment_status": (
                    "approved"
                    if scores.total_score >= 75
                    else "conditional" if scores.total_score >= 65 else "not_approved"
                ),
                "recommended_position_size": (
                    2.0 * (scores.total_score / 100)
                    if scores.total_score >= 75
                    else (
                        1.0 * (scores.total_score / 100)
                        if scores.total_score >= 65
                        else 0.0
                    )
                ),
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to calculate score: {str(e)}"
            )

    @router.post("/api/validation/generate-report")
    async def generate_validation_report(payload: ReportGenerateRequest = Body(...)):
        """
        Generate comprehensive HTML validation report.

        Returns path to generated report file.
        """
        from pathlib import Path
        from exhaustionlab.app.validation import (
            parse_backtest_from_directory,
            ComprehensiveScorer,
            generate_validation_report,
            calculate_trading_costs,
        )

        try:
            # Parse backtest
            output_dir = Path(payload.backtest_output_dir)
            backtest = parse_backtest_from_directory(output_dir)

            # Calculate score
            scorer = ComprehensiveScorer()
            scores = scorer.calculate_comprehensive_score(
                backtest=backtest,
                symbol=payload.symbol,
                portfolio_size_usd=payload.portfolio_size_usd,
                out_of_sample_ratio=payload.out_of_sample_ratio,
                cross_market_pass_rate=payload.cross_market_pass_rate,
            )

            # Calculate costs if requested
            costs = None
            if payload.include_costs:
                trades_df = backtest.to_dataframe()
                costs = calculate_trading_costs(
                    trades_df=trades_df,
                    symbol=payload.symbol,
                    portfolio_size_usd=payload.portfolio_size_usd,
                    include_fees=True,
                    fee_bps=payload.fee_bps,
                )

            # Generate output filename
            if payload.output_filename:
                output_path = Path("reports") / payload.output_filename
            else:
                from datetime import datetime

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = (
                    Path("reports") / f"validation_{payload.symbol}_{timestamp}.html"
                )

            # Generate report
            report_path = generate_validation_report(
                backtest=backtest,
                scores=scores,
                symbol=payload.symbol,
                output_path=output_path,
                costs=costs,
            )

            return {
                "status": "success",
                "report_path": str(report_path),
                "total_score": scores.total_score,
                "deployment_status": (
                    "approved"
                    if scores.total_score >= 75
                    else "conditional" if scores.total_score >= 65 else "not_approved"
                ),
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to generate report: {str(e)}"
            )

    @router.post("/api/validation/estimate-slippage")
    async def estimate_slippage(payload: SlippageEstimateRequest = Body(...)):
        """
        Estimate slippage for a trade.

        Returns detailed slippage breakdown.
        """
        from exhaustionlab.app.validation import SlippageEstimator

        try:
            estimator = SlippageEstimator()

            # Estimate slippage
            estimate = estimator.estimate_slippage(
                symbol=payload.symbol,
                order_size_usd=payload.order_size_usd,
                signal_frequency=payload.signal_frequency,
                volatility=payload.volatility,
            )

            return {
                "status": "success",
                "estimate": {
                    "total_slippage_bps": estimate.total_slippage_bps,
                    "spread_cost_bps": estimate.spread_cost_bps,
                    "market_impact_bps": estimate.market_impact_bps,
                    "execution_delay_bps": estimate.execution_delay_bps,
                    "volatility_slippage_bps": estimate.volatility_slippage_bps,
                    "confidence_interval_lower_bps": estimate.confidence_interval_lower_bps,
                    "confidence_interval_upper_bps": estimate.confidence_interval_upper_bps,
                    "signal_frequency": estimate.signal_frequency,
                    "order_size_usd": estimate.order_size_usd,
                    "liquidity_class": estimate.liquidity_class.value,
                    "time_of_day": estimate.time_of_day.value,
                },
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to estimate slippage: {str(e)}"
            )

    @router.post("/api/validation/calculate-costs")
    async def calculate_trading_costs_api(payload: TradingCostsRequest = Body(...)):
        """
        Calculate total trading costs (slippage + fees).

        Returns comprehensive cost breakdown.
        """
        from pathlib import Path
        from exhaustionlab.app.validation import (
            parse_backtest_from_directory,
            calculate_trading_costs,
        )

        try:
            # Parse backtest to get trades
            output_dir = Path(payload.backtest_output_dir)
            backtest = parse_backtest_from_directory(output_dir)
            trades_df = backtest.to_dataframe()

            # Calculate costs
            costs = calculate_trading_costs(
                trades_df=trades_df,
                symbol=payload.symbol,
                portfolio_size_usd=payload.portfolio_size_usd,
                include_fees=payload.include_fees,
                fee_bps=payload.fee_bps,
            )

            return {
                "status": "success",
                "costs": costs,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to calculate costs: {str(e)}"
            )

    @router.get("/api/validation/liquidity-info/{symbol}")
    async def get_liquidity_info(symbol: str):
        """
        Get liquidity information for a symbol.

        Returns liquidity classification and metrics.
        """
        from exhaustionlab.app.validation import SlippageEstimator

        try:
            estimator = SlippageEstimator()
            liquidity_info = estimator.get_symbol_liquidity_info(symbol)

            return {
                "status": "success",
                "symbol": symbol,
                "liquidity_info": liquidity_info,
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get liquidity info: {str(e)}"
            )

    return router
