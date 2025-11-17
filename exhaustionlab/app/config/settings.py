"""
Unified application settings using Pydantic BaseSettings.

This module provides type-safe configuration management with:
- Environment variable loading from .env
- Default values for all settings
- Validation on startup
- Separation of concerns (exchange, LLM, risk, evolution, UI)
- Secret masking for security

Usage:
    from exhaustionlab.app.config.settings import get_settings

    settings = get_settings()
    print(settings.exchange.api_key)  # Loaded from BINANCE_API_KEY
    print(settings.llm.base_url)      # Loaded from LLM_BASE_URL
    print(settings.risk.max_drawdown) # Default: 0.25
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExchangeSettings(BaseSettings):
    """Exchange connection settings."""

    model_config = SettingsConfigDict(env_prefix="BINANCE_", case_sensitive=False)

    api_key: str = Field(default="", description="Binance API key")
    api_secret: str = Field(default="", description="Binance API secret")
    testnet: bool = Field(default=True, description="Use testnet")
    base_url: str = Field(
        default="https://testnet.binance.vision/api",
        description="API base URL",
    )
    ws_url: str = Field(
        default="wss://testnet.binance.vision/ws",
        description="WebSocket URL",
    )
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    rate_limit_requests: int = Field(default=1200, description="Requests per minute")

    def mask_secrets(self) -> dict:
        """Return settings with masked secrets."""
        data = self.model_dump()
        if self.api_key:
            data["api_key"] = f"{self.api_key[:4]}...{self.api_key[-4:]}"
        if self.api_secret:
            data["api_secret"] = "***MASKED***"
        return data


class LLMSettings(BaseSettings):
    """LLM client settings."""

    model_config = SettingsConfigDict(env_prefix="LLM_", case_sensitive=False)

    base_url: str = Field(
        default="http://127.0.0.1:1234/v1",
        description="LLM API base URL (OpenAI-compatible)",
    )
    api_key: str = Field(
        default="not-needed-for-local",
        description="API key (not needed for local LLM)",
    )
    model: str = Field(
        default="deepseek-r1-0528-qwen3-8b",
        description="Model identifier",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling",
    )
    max_tokens: int = Field(
        default=2000,
        ge=100,
        le=8000,
        description="Maximum response tokens",
    )
    timeout: int = Field(default=120, description="Request timeout in seconds")
    max_retries: int = Field(default=2, description="Maximum retry attempts")
    fallback_enabled: bool = Field(
        default=True,
        description="Enable fallback to GA if LLM unavailable",
    )

    def mask_secrets(self) -> dict:
        """Return settings with masked secrets."""
        data = self.model_dump()
        if self.api_key and self.api_key != "not-needed-for-local":
            data["api_key"] = f"{self.api_key[:4]}...{self.api_key[-4:]}"
        return data


class RiskSettings(BaseSettings):
    """Risk management settings."""

    model_config = SettingsConfigDict(env_prefix="RISK_", case_sensitive=False)

    max_position_size: float = Field(
        default=0.02,
        ge=0.001,
        le=1.0,
        description="Maximum position size (% of portfolio)",
    )
    max_daily_loss: float = Field(
        default=0.01,
        ge=0.001,
        le=0.5,
        description="Maximum daily loss (% of portfolio)",
    )
    max_drawdown: float = Field(
        default=0.25,
        ge=0.01,
        le=0.9,
        description="Maximum drawdown threshold",
    )
    max_open_positions: int = Field(
        default=3,
        ge=1,
        le=50,
        description="Maximum concurrent open positions",
    )
    enable_stop_loss: bool = Field(default=True, description="Enable stop loss")
    stop_loss_pct: float = Field(
        default=0.02,
        ge=0.001,
        le=0.5,
        description="Stop loss percentage",
    )
    enable_take_profit: bool = Field(default=True, description="Enable take profit")
    take_profit_pct: float = Field(
        default=0.05,
        ge=0.001,
        le=1.0,
        description="Take profit percentage",
    )
    min_sharpe_ratio: float = Field(
        default=1.2,
        ge=0.0,
        le=10.0,
        description="Minimum Sharpe ratio for deployment",
    )
    min_win_rate: float = Field(
        default=0.45,
        ge=0.0,
        le=1.0,
        description="Minimum win rate for deployment",
    )


class EvolutionSettings(BaseSettings):
    """Evolution engine settings."""

    model_config = SettingsConfigDict(env_prefix="EVOLUTION_", case_sensitive=False)

    num_generations: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Number of evolution generations",
    )
    population_size: int = Field(
        default=10,
        ge=2,
        le=100,
        description="Population size per generation",
    )
    mutation_rate: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Mutation probability",
    )
    crossover_rate: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Crossover probability",
    )
    selection_pressure: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Selection pressure (0=random, 1=elitist)",
    )
    use_llm: bool = Field(default=True, description="Use LLM for evolution")
    use_adaptive: bool = Field(
        default=True,
        description="Use adaptive parameter optimization",
    )
    use_crawled: bool = Field(
        default=False,
        description="Use web-crawled examples",
    )
    max_indicators: int = Field(
        default=6,
        ge=1,
        le=20,
        description="Maximum indicators per strategy",
    )
    max_loc: int = Field(
        default=500,
        ge=50,
        le=2000,
        description="Maximum lines of code",
    )
    complexity_preference: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Complexity preference (0=simple, 1=complex)",
    )


class UISettings(BaseSettings):
    """Web UI settings."""

    model_config = SettingsConfigDict(env_prefix="UI_", case_sensitive=False)

    port: int = Field(default=8080, ge=1024, le=65535, description="Web UI port")
    host: str = Field(default="0.0.0.0", description="Web UI host")
    reload: bool = Field(default=False, description="Enable hot reload (dev only)")
    workers: int = Field(default=1, ge=1, le=32, description="Number of workers")
    log_level: Literal["debug", "info", "warning", "error"] = Field(
        default="info",
        description="Logging level",
    )
    enable_cors: bool = Field(default=True, description="Enable CORS")
    cors_origins: list[str] = Field(
        default=["*"],
        description="Allowed CORS origins",
    )


class DatabaseSettings(BaseSettings):
    """Database settings."""

    model_config = SettingsConfigDict(env_prefix="DB_", case_sensitive=False)

    path: str = Field(
        default="~/.cache/exhaustionlab/strategies.db",
        description="SQLite database path",
    )
    echo: bool = Field(default=False, description="Echo SQL queries (debug)")
    pool_size: int = Field(default=5, ge=1, le=50, description="Connection pool size")
    pool_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Pool timeout in seconds",
    )

    @field_validator("path")
    @classmethod
    def expand_path(cls, v: str) -> str:
        """Expand ~ and environment variables in path."""
        return os.path.expanduser(os.path.expandvars(v))


class CacheSettings(BaseSettings):
    """Cache settings."""

    model_config = SettingsConfigDict(env_prefix="CACHE_", case_sensitive=False)

    enabled: bool = Field(default=True, description="Enable caching")
    ttl: int = Field(default=300, ge=0, le=86400, description="Cache TTL in seconds")
    max_size: int = Field(
        default=1000,
        ge=10,
        le=100000,
        description="Maximum cache entries",
    )
    dir: str = Field(
        default="~/.cache/exhaustionlab/",
        description="Cache directory",
    )

    @field_validator("dir")
    @classmethod
    def expand_dir(cls, v: str) -> str:
        """Expand ~ and environment variables in directory."""
        path = Path(os.path.expanduser(os.path.expandvars(v)))
        path.mkdir(parents=True, exist_ok=True)
        return str(path)


class ObservabilitySettings(BaseSettings):
    """Observability settings (logging, metrics, tracing)."""

    model_config = SettingsConfigDict(env_prefix="OBSERVABILITY_", case_sensitive=False)

    # Logging
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log format",
    )
    log_file: str = Field(
        default="~/.cache/exhaustionlab/logs/app.log",
        description="Log file path",
    )
    log_rotation: str = Field(default="500 MB", description="Log rotation size")
    log_retention: str = Field(default="30 days", description="Log retention period")

    # Metrics
    metrics_enabled: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Metrics port",
    )

    # Tracing
    tracing_enabled: bool = Field(default=False, description="Enable distributed tracing")
    tracing_endpoint: str = Field(
        default="",
        description="Tracing collector endpoint",
    )

    @field_validator("log_file")
    @classmethod
    def expand_log_path(cls, v: str) -> str:
        """Expand ~ and create log directory."""
        path = Path(os.path.expanduser(os.path.expandvars(v)))
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)


class AppSettings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application metadata
    app_name: str = Field(default="ExhaustionLab", description="Application name")
    version: str = Field(default="3.0.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Environment",
    )
    debug: bool = Field(default=False, description="Debug mode")

    # Nested settings
    exchange: ExchangeSettings = Field(default_factory=ExchangeSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    risk: RiskSettings = Field(default_factory=RiskSettings)
    evolution: EvolutionSettings = Field(default_factory=EvolutionSettings)
    ui: UISettings = Field(default_factory=UISettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    def mask_secrets(self) -> dict:
        """Return full config with all secrets masked."""
        data = self.model_dump()
        data["exchange"] = self.exchange.mask_secrets()
        data["llm"] = self.llm.mask_secrets()
        return data

    def to_dict(self, include_secrets: bool = False) -> dict:
        """Convert to dictionary, optionally masking secrets."""
        if include_secrets:
            return self.model_dump()
        return self.mask_secrets()


@lru_cache
def get_settings() -> AppSettings:
    """
    Get application settings (cached singleton).

    This function is cached to ensure settings are loaded only once.
    Use dependency injection in FastAPI:

        from fastapi import Depends
        from exhaustionlab.app.config.settings import get_settings, AppSettings

        @app.get("/api/info")
        def get_info(settings: AppSettings = Depends(get_settings)):
            return {"version": settings.version}
    """
    return AppSettings()


def reload_settings() -> AppSettings:
    """
    Reload settings from environment (clears cache).

    Use this sparingly, typically only in development or after
    updating .env file.
    """
    get_settings.cache_clear()
    return get_settings()


# Export for convenience
__all__ = [
    "AppSettings",
    "ExchangeSettings",
    "LLMSettings",
    "RiskSettings",
    "EvolutionSettings",
    "UISettings",
    "DatabaseSettings",
    "CacheSettings",
    "ObservabilitySettings",
    "get_settings",
    "reload_settings",
]
