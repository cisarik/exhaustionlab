"""Pydantic models for API requests."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvolutionStartRequest(BaseModel):
    """Request to start evolution."""

    num_generations: int = Field(default=5, ge=1, le=100)
    population_size: int = Field(default=3, ge=2, le=50)
    use_llm: bool = Field(default=True)
    use_crawled: bool = Field(default=True)
    symbol: str = Field(default="ADAEUR")
    timeframe: str = Field(default="1m")


class BacktestParseRequest(BaseModel):
    """Request to parse backtest output."""

    output_dir: str
    symbol: str = Field(default="BTCUSDT")


class ComprehensiveScoreRequest(BaseModel):
    """Request to calculate comprehensive score."""

    backtest_output_dir: str
    symbol: str = Field(default="BTCUSDT")
    portfolio_size_usd: float = Field(default=100000, gt=0)
    out_of_sample_ratio: float | None = Field(default=None, ge=0, le=1)
    cross_market_pass_rate: float | None = Field(default=None, ge=0, le=1)


class ReportGenerateRequest(BaseModel):
    """Request to generate validation report."""

    backtest_output_dir: str
    symbol: str = Field(default="BTCUSDT")
    portfolio_size_usd: float = Field(default=100000, gt=0)
    out_of_sample_ratio: float | None = Field(default=None, ge=0, le=1)
    cross_market_pass_rate: float | None = Field(default=None, ge=0, le=1)
    include_costs: bool = Field(default=True)
    output_filename: str | None = None
    fee_bps: float = Field(default=10.0, ge=0)


class SlippageEstimateRequest(BaseModel):
    """Request to estimate slippage."""

    symbol: str = Field(default="BTCUSDT")
    order_size_usd: float = Field(default=10000, gt=0)
    signal_frequency: float = Field(default=5.0, gt=0)
    volatility: float = Field(default=0.8, ge=0)


class TradingCostsRequest(BaseModel):
    """Request to calculate trading costs."""

    backtest_output_dir: str
    symbol: str = Field(default="BTCUSDT")
    portfolio_size_usd: float = Field(default=100000, gt=0)
    include_fees: bool = Field(default=True)
    fee_bps: float = Field(default=10.0, ge=0)


class DeployStrategyRequest(BaseModel):
    """Request to deploy a strategy for live/paper trading."""

    strategy_id: str
    strategy_name: str
    mode: str = Field(default="paper", pattern="^(paper|live)$")
    symbols: list[str] = Field(default=["ADAEUR"])
    timeframe: str = Field(default="1m")

    # Risk parameters
    max_position_size: float = Field(default=0.02, gt=0, le=1)
    max_daily_loss: float = Field(default=0.01, gt=0, le=1)
    max_drawdown: float = Field(default=0.05, gt=0, le=1)
    max_open_positions: int = Field(default=3, ge=1)
    enable_stop_loss: bool = True
    stop_loss_pct: float = Field(default=0.02, gt=0, le=1)
    enable_take_profit: bool = True
    take_profit_pct: float = Field(default=0.05, gt=0, le=1)

    # Exchange config
    exchange: str = Field(default="binance")
    api_key: str | None = None
    api_secret: str | None = None
    testnet: bool = True


class SettingsUpdateRequest(BaseModel):
    """Request to update settings."""

    exchange: dict | None = None
    llm: dict | None = None
    risk: dict | None = None
    evolution: dict | None = None
    ui: dict | None = None


class MultiMarketTestRequest(BaseModel):
    """Request to test strategies across markets."""

    strategy_ids: list[str] = Field(default=[])
    symbols: list[str] = Field(default=["BTCUSDT", "ETHUSDT", "BNBUSDT"])
    timeframes: list[str] = Field(default=["5m", "15m", "1h"])
    lookback_days: int = Field(default=30, ge=1, le=365)


__all__ = [
    "EvolutionStartRequest",
    "BacktestParseRequest",
    "ComprehensiveScoreRequest",
    "ReportGenerateRequest",
    "SlippageEstimateRequest",
    "TradingCostsRequest",
    "DeployStrategyRequest",
    "SettingsUpdateRequest",
    "MultiMarketTestRequest",
]
