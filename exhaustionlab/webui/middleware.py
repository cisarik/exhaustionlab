"""
Middleware for request logging, metrics, and tracing.

Provides:
- Structured JSON logging with request IDs
- Request/response duration tracking
- Prometheus metrics collection
- Error tracking and alerting
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..app.config.settings import get_settings
from .observability import get_logger, get_metrics

# Context variable for request ID (available throughout request lifecycle)
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging.

    Logs all requests with:
    - Request ID (UUID)
    - Method, path, query params
    - Client IP, user agent
    - Response status code
    - Duration in milliseconds
    - Error details (if any)
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = get_logger(__name__)
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)

        # Start timer
        start_time = time.time()

        # Extract request metadata
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")

        # Log request
        self.logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": client_ip,
                "user_agent": user_agent,
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            self.logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                },
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            self.logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )

            # Re-raise to let FastAPI handle it
            raise


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for Prometheus metrics collection.

    Tracks:
    - Request count by method, path, status code
    - Request duration histogram
    - In-flight requests gauge
    - Error count by type
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.metrics = get_metrics()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Track in-flight requests
        self.metrics.in_flight_requests.inc()

        # Start timer
        start_time = time.time()

        # Extract path (remove query params for cleaner metrics)
        path = request.url.path
        method = request.method

        try:
            # Process request
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            status_code = response.status_code

            self.metrics.request_count.labels(
                method=method,
                path=path,
                status=status_code,
            ).inc()

            self.metrics.request_duration.labels(
                method=method,
                path=path,
            ).observe(duration)

            return response

        except Exception as exc:
            # Record error
            duration = time.time() - start_time

            self.metrics.request_count.labels(
                method=method,
                path=path,
                status=500,
            ).inc()

            self.metrics.request_duration.labels(
                method=method,
                path=path,
            ).observe(duration)

            self.metrics.error_count.labels(
                error_type=type(exc).__name__,
            ).inc()

            # Re-raise
            raise

        finally:
            # Decrement in-flight requests
            self.metrics.in_flight_requests.dec()


def get_request_id() -> str:
    """Get current request ID from context."""
    return request_id_var.get()


__all__ = [
    "RequestLoggingMiddleware",
    "MetricsMiddleware",
    "get_request_id",
]
