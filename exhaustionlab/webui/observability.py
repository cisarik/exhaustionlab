"""
Observability utilities: logging, metrics, and tracing.

Provides:
- Structured JSON logging with Loguru
- Prometheus metrics collection
- Health check endpoint
- Distributed tracing (future)
"""

from __future__ import annotations

import json
import logging
import sys
from functools import lru_cache
from typing import Any

from loguru import logger
from prometheus_client import Counter, Gauge, Histogram

from ..app.config.settings import get_settings


class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect to Loguru.

    This ensures all logging (including from libraries) goes through
    our structured logging system.
    """

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where the logged message originated
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging() -> None:
    """
    Setup structured logging with Loguru.

    Configures:
    - JSON formatting for production
    - Pretty formatting for development
    - Log rotation and retention
    - Intercepts standard logging
    """
    settings = get_settings()

    # Remove default handler
    logger.remove()

    # Console handler (pretty format for dev, JSON for prod)
    if settings.observability.log_format == "json":
        # JSON format for production
        def json_formatter(record: dict) -> str:
            log_entry = {
                "timestamp": record["time"].isoformat(),
                "level": record["level"].name,
                "message": record["message"],
                "module": record["name"],
                "function": record["function"],
                "line": record["line"],
            }

            # Add extra fields
            if record.get("extra"):
                log_entry.update(record["extra"])

            # Add exception if present
            if record["exception"]:
                log_entry["exception"] = {
                    "type": record["exception"].type.__name__,
                    "value": str(record["exception"].value),
                    "traceback": record["exception"].traceback,
                }

            return json.dumps(log_entry)

        logger.add(
            sys.stdout,
            format=json_formatter,
            level=settings.ui.log_level.upper(),
            serialize=False,
        )
    else:
        # Pretty format for development
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=settings.ui.log_level.upper(),
            colorize=True,
        )

    # File handler (always JSON)
    logger.add(
        settings.observability.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="INFO",
        rotation=settings.observability.log_rotation,
        retention=settings.observability.log_retention,
        compression="gz",
        serialize=True,  # JSON format
    )

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Intercept uvicorn, fastapi logs
    for logger_name in ["uvicorn", "uvicorn.access", "fastapi"]:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]


@lru_cache
def get_logger(name: str | None = None):
    """
    Get logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Loguru logger instance
    """
    return logger.bind(module=name or "app")


class PrometheusMetrics:
    """
    Prometheus metrics collection.

    Tracks:
    - HTTP requests: count, duration, in-flight
    - Evolution: strategies generated, fitness scores
    - Backtest: runs, successes, failures
    - LLM: requests, successes, failures, latency
    - System: CPU, memory, disk usage
    """

    def __init__(self):
        # HTTP metrics
        self.request_count = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "path", "status"],
        )

        self.request_duration = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            ["method", "path"],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
        )

        self.in_flight_requests = Gauge(
            "http_requests_in_flight",
            "In-flight HTTP requests",
        )

        self.error_count = Counter(
            "http_errors_total",
            "Total HTTP errors",
            ["error_type"],
        )

        # Evolution metrics
        self.strategies_generated = Counter(
            "evolution_strategies_generated_total",
            "Total strategies generated",
            ["method"],  # llm, ga, hybrid
        )

        self.strategy_fitness = Histogram(
            "evolution_strategy_fitness",
            "Strategy fitness scores",
            buckets=[0.0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0],
        )

        self.evolution_duration = Histogram(
            "evolution_generation_duration_seconds",
            "Evolution generation duration",
            buckets=[1, 5, 10, 30, 60, 120, 300],
        )

        # Backtest metrics
        self.backtest_runs = Counter(
            "backtest_runs_total",
            "Total backtest runs",
            ["status"],  # success, failure
        )

        self.backtest_duration = Histogram(
            "backtest_duration_seconds",
            "Backtest run duration",
            buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
        )

        # LLM metrics
        self.llm_requests = Counter(
            "llm_requests_total",
            "Total LLM requests",
            ["status"],  # success, failure, timeout
        )

        self.llm_latency = Histogram(
            "llm_request_duration_seconds",
            "LLM request duration",
            buckets=[0.5, 1, 2, 5, 10, 30, 60, 120],
        )

        self.llm_tokens = Histogram(
            "llm_tokens_total",
            "LLM tokens used",
            ["type"],  # prompt, completion
            buckets=[100, 500, 1000, 2000, 4000, 8000],
        )

        # Trading metrics
        self.trades_executed = Counter(
            "trading_trades_executed_total",
            "Total trades executed",
            ["mode", "symbol", "side"],  # paper/live, BTCUSDT, long/short
        )

        self.trade_pnl = Histogram(
            "trading_trade_pnl",
            "Trade PnL distribution",
            buckets=[-100, -50, -10, -5, 0, 5, 10, 50, 100],
        )

        self.active_deployments = Gauge(
            "trading_active_deployments",
            "Number of active deployments",
            ["mode"],
        )

        # System metrics
        self.system_cpu_usage = Gauge(
            "system_cpu_usage_percent",
            "CPU usage percentage",
        )

        self.system_memory_usage = Gauge(
            "system_memory_usage_bytes",
            "Memory usage in bytes",
        )

    def record_strategy_generated(self, method: str, fitness: float, duration: float):
        """Record strategy generation metrics."""
        self.strategies_generated.labels(method=method).inc()
        self.strategy_fitness.observe(fitness)
        self.evolution_duration.observe(duration)

    def record_backtest(self, status: str, duration: float):
        """Record backtest metrics."""
        self.backtest_runs.labels(status=status).inc()
        self.backtest_duration.observe(duration)

    def record_llm_request(
        self,
        status: str,
        duration: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ):
        """Record LLM request metrics."""
        self.llm_requests.labels(status=status).inc()
        self.llm_latency.observe(duration)
        if prompt_tokens > 0:
            self.llm_tokens.labels(type="prompt").observe(prompt_tokens)
        if completion_tokens > 0:
            self.llm_tokens.labels(type="completion").observe(completion_tokens)

    def record_trade(self, mode: str, symbol: str, side: str, pnl: float):
        """Record trade execution metrics."""
        self.trades_executed.labels(mode=mode, symbol=symbol, side=side).inc()
        self.trade_pnl.observe(pnl)


@lru_cache
def get_metrics() -> PrometheusMetrics:
    """Get Prometheus metrics instance (singleton)."""
    return PrometheusMetrics()


def get_health_status() -> dict[str, Any]:
    """
    Get application health status.

    Returns:
        Health status with service availability
    """
    settings = get_settings()

    # Check service health
    services = {
        "api": "up",
        "database": "up",  # TODO: Check actual DB connection
        "llm": "up",  # TODO: Check LLM availability
        "exchange": "up",  # TODO: Check exchange API
    }

    # Determine overall status
    if all(status == "up" for status in services.values()):
        overall_status = "healthy"
    elif any(status == "up" for status in services.values()):
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "version": settings.version,
        "environment": settings.environment,
        "services": services,
    }


__all__ = [
    "setup_logging",
    "get_logger",
    "get_metrics",
    "get_health_status",
    "PrometheusMetrics",
]
