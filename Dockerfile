# ============================================================================
# ExhaustionLab v3.0 - Production Docker Image
# ============================================================================
# Multi-stage build with security best practices:
# - Non-root user
# - Minimal attack surface
# - Security updates
# - Health check
# - Layer caching optimization
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Builder - Build Python dependencies and wheel
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Build arguments
ARG POETRY_VERSION=1.8.3

# Environment variables for build
ENV POETRY_VERSION=${POETRY_VERSION} \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        git \
        ca-certificates && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Copy dependency files for better layer caching
COPY pyproject.toml poetry.lock ./

# Install dependencies (without dev dependencies)
RUN poetry install --without dev --no-root || poetry install --no-root

# Copy application code
COPY . .

# Build wheel distribution
RUN poetry build -f wheel

# ----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Labels for metadata
LABEL maintainer="ExhaustionLab Team" \
      version="3.0.0" \
      description="AI-powered cryptocurrency trading strategy evolution platform" \
      org.opencontainers.image.title="ExhaustionLab" \
      org.opencontainers.image.version="3.0.0" \
      org.opencontainers.image.description="Production-ready trading strategy evolution with AI" \
      org.opencontainers.image.vendor="ExhaustionLab" \
      org.opencontainers.image.licenses="MIT"

# Runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Application settings
    APP_ENV=production \
    WEBUI_PORT=8080 \
    # Qt settings for headless rendering
    QT_QPA_PLATFORM=offscreen \
    # Paths
    PATH="/home/exhaustionlab/.local/bin:${PATH}"

WORKDIR /app

# Install runtime dependencies and security updates
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        # Qt/GUI dependencies (for chart generation)
        libgl1 \
        libglib2.0-0 \
        libxkbcommon0 \
        libxcb-xinerama0 \
        libxcb1 \
        # Utility
        curl \
        ca-certificates && \
    # Security updates
    apt-get upgrade -y && \
    # Cleanup
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create non-root user
RUN groupadd --gid 1000 exhaustionlab && \
    useradd --uid 1000 --gid exhaustionlab --shell /bin/bash --create-home exhaustionlab && \
    # Create application directories
    mkdir -p /app /workspace /workspace/data /workspace/logs && \
    chown -R exhaustionlab:exhaustionlab /app /workspace

# Copy wheel from builder
COPY --from=builder --chown=exhaustionlab:exhaustionlab /build/dist/*.whl /tmp/

# Install application wheel
RUN pip install --no-cache-dir /tmp/exhaustionlab*.whl && \
    rm -f /tmp/exhaustionlab*.whl

# Copy entrypoint script
COPY --chown=exhaustionlab:exhaustionlab docker/entrypoint.sh /usr/local/bin/exhaustionlab-entrypoint.sh
RUN chmod +x /usr/local/bin/exhaustionlab-entrypoint.sh

# Copy application files
COPY --chown=exhaustionlab:exhaustionlab data ./data
COPY --chown=exhaustionlab:exhaustionlab .env.example ./.env.example

# Switch to non-root user
USER exhaustionlab

# Expose ports
EXPOSE 8080 9090

# Volumes for persistent data
VOLUME ["/workspace/data", "/workspace/logs"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail http://localhost:8080/health || exit 1

# Entrypoint
ENTRYPOINT ["exhaustionlab-entrypoint.sh"]

# Default command (can be overridden)
CMD ["webui"]
