"""Pydantic models for standardized API responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Standardized API response wrapper.

    All endpoints should return responses in this format:
    {
        "status": "success" | "error",
        "data": {...},
        "message": "Optional human-readable message",
        "timestamp": "2025-11-17T12:34:56.789Z",
        "request_id": "req_abc123"
    }
    """

    status: Literal["success", "error"]
    data: T | None = None
    message: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "data": {"result": "example"},
                "message": "Operation completed successfully",
                "timestamp": "2025-11-17T12:34:56.789Z",
                "request_id": "req_abc123",
            }
        }


class ErrorResponse(BaseModel):
    """Error response model."""

    status: Literal["error"] = "error"
    error: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "error",
                "error": "ValidationError",
                "detail": "Strategy ID not found",
                "timestamp": "2025-11-17T12:34:56.789Z",
                "request_id": "req_abc123",
            }
        }


class StrategyMetrics(BaseModel):
    """Strategy performance metrics."""

    sharpe_ratio: float
    sortino_ratio: float | None = None
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_return: float | None = None
    annualized_return: float | None = None


class StrategyResponse(BaseModel):
    """Single strategy response."""

    strategy_id: str
    name: str
    fitness: float
    generation: int
    metrics: StrategyMetrics
    code: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class EvolutionMetrics(BaseModel):
    """Evolution overview metrics."""

    total_strategies: int
    total_generations: int
    best_fitness: float
    avg_fitness: float
    best_sharpe: float
    avg_sharpe: float
    success_rate: float
    llm_success_rate: float | None = None
    ga_success_rate: float | None = None


class EvolutionOverviewResponse(BaseModel):
    """Evolution overview response."""

    metrics: EvolutionMetrics
    top_strategies: list[StrategyResponse] = Field(default=[])
    hall_of_fame: list[StrategyResponse] = Field(default=[])


class BacktestTrade(BaseModel):
    """Single backtest trade."""

    trade_id: str
    entry_time: datetime
    exit_time: datetime
    side: Literal["long", "short"]
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    pnl_pct: float
    commission: float | None = None


class BacktestResultResponse(BaseModel):
    """Backtest result response."""

    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    metrics: StrategyMetrics
    trades: list[BacktestTrade] = Field(default=[])
    equity_curve: dict[str, Any] | None = None
    returns: dict[str, Any] | None = None


class ChartResponse(BaseModel):
    """Chart generation response (metadata)."""

    chart_type: str
    symbol: str
    timeframe: str
    width: int
    height: int
    generated_at: datetime = Field(default_factory=datetime.now)
    url: str | None = None


class DeploymentStatus(BaseModel):
    """Deployment status."""

    deployment_id: str
    strategy_id: str
    strategy_name: str
    mode: Literal["paper", "live"]
    status: Literal["running", "stopped", "error"]
    start_time: datetime
    uptime_seconds: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    open_positions: int
    daily_pnl: float
    daily_pnl_pct: float
    current_drawdown: float
    max_drawdown: float
    last_error: str | None = None
    error_count: int


class DeploymentResponse(BaseModel):
    """Deployment response."""

    deployment_id: str
    status: Literal["deployed", "stopped", "error"]
    message: str
    deployment: DeploymentStatus | None = None


class SettingsResponse(BaseModel):
    """Settings response."""

    app_name: str
    version: str
    environment: str
    exchange: dict[str, Any]
    llm: dict[str, Any]
    risk: dict[str, Any]
    evolution: dict[str, Any]
    ui: dict[str, Any]
    database: dict[str, Any] | None = None
    cache: dict[str, Any] | None = None


class ValidationScores(BaseModel):
    """Validation score breakdown."""

    performance_score: float
    risk_score: float
    execution_score: float
    robustness_score: float
    total_score: float
    deployment_status: Literal["approved", "conditional", "not_approved"]


class ValidationReportResponse(BaseModel):
    """Validation report response."""

    report_path: str
    scores: ValidationScores
    backtest: BacktestResultResponse
    costs: dict[str, Any] | None = None
    generated_at: datetime = Field(default_factory=datetime.now)


class SlippageEstimate(BaseModel):
    """Slippage estimate breakdown."""

    total_slippage_bps: float
    spread_cost_bps: float
    market_impact_bps: float
    execution_delay_bps: float
    volatility_slippage_bps: float
    confidence_interval_lower_bps: float
    confidence_interval_upper_bps: float
    signal_frequency: float
    order_size_usd: float
    liquidity_class: str
    time_of_day: str


class MultiMarketResult(BaseModel):
    """Multi-market test result for a single strategy."""

    strategy_id: str
    strategy_name: str
    original_fitness: float
    markets_tested: int
    markets_passed: int
    pass_rate: float
    avg_fitness: float
    avg_sharpe: float
    max_drawdown: float
    avg_win_rate: float
    market_results: list[dict[str, Any]]
    tested_at: datetime
    status: Literal["approved", "rejected"]


class MultiMarketTestResponse(BaseModel):
    """Multi-market testing response."""

    status: Literal["completed", "running", "error"]
    total_strategies: int
    total_markets: int
    results: list[MultiMarketResult]


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    uptime_seconds: float
    timestamp: datetime = Field(default_factory=datetime.now)
    services: dict[str, Literal["up", "down"]]


class MetricsResponse(BaseModel):
    """Prometheus metrics response."""

    metrics: str  # Prometheus text format


__all__ = [
    "ApiResponse",
    "ErrorResponse",
    "StrategyResponse",
    "StrategyMetrics",
    "EvolutionOverviewResponse",
    "EvolutionMetrics",
    "BacktestResultResponse",
    "BacktestTrade",
    "ChartResponse",
    "DeploymentResponse",
    "DeploymentStatus",
    "SettingsResponse",
    "ValidationReportResponse",
    "ValidationScores",
    "SlippageEstimate",
    "MultiMarketTestResponse",
    "MultiMarketResult",
    "HealthCheckResponse",
    "MetricsResponse",
]
