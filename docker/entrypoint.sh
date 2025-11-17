#!/usr/bin/env bash
# ============================================================================
# ExhaustionLab v3.0 - Docker Entrypoint Script
# ============================================================================
# Production-ready entrypoint with proper error handling and logging
# ============================================================================

set -euo pipefail

# Logging functions
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $*" >&2
}

log_warn() {
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') - $*"
}

# Banner
log_info "============================================================================"
log_info "ExhaustionLab v3.0 - AI-Powered Trading Strategy Evolution"
log_info "============================================================================"

# Determine runtime mode
MODE="${1:-webui}"  # Default to webui mode
log_info "Runtime mode: ${MODE}"

# Environment variables
log_info "Environment: ${APP_ENV:-development}"
log_info "Python version: $(python --version 2>&1 | cut -d' ' -f2)"

# Health check function
check_health() {
    local max_retries=30
    local retry=0
    local url="http://localhost:${WEBUI_PORT:-8080}/health"

    log_info "Waiting for application to be healthy..."

    while [ $retry -lt $max_retries ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            log_info "Application is healthy!"
            return 0
        fi
        retry=$((retry + 1))
        sleep 1
    done

    log_error "Application failed to become healthy after ${max_retries}s"
    return 1
}

# Execute based on mode
case "${MODE,,}" in
    gui)
        log_info "Starting GUI mode..."
        export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
        log_info "Qt platform: ${QT_QPA_PLATFORM}"

        exec python -m exhaustionlab.app.main
        ;;

    api|webui)
        log_info "Starting Web UI mode..."
        PORT="${WEBUI_PORT:-8080}"
        WORKERS="${WEBUI_WORKERS:-1}"
        LOG_LEVEL="${WEBUI_LOG_LEVEL:-info}"

        log_info "Port: ${PORT}"
        log_info "Workers: ${WORKERS}"
        log_info "Log level: ${LOG_LEVEL}"

        # Use poetry script entry point
        exec poetry run exhaustionlab-webui
        ;;

    test)
        log_info "Running test suite..."
        exec pytest tests/ -v
        ;;

    bash|shell)
        log_info "Starting interactive shell..."
        exec /bin/bash
        ;;

    *)
        # If argument looks like a command, execute it
        if command -v "$MODE" > /dev/null 2>&1; then
            log_info "Executing custom command: $*"
            exec "$@"
        else
            log_error "Unknown mode: ${MODE}"
            log_error "Available modes: gui, webui, api, test, bash, shell"
            log_error "Or provide a custom command"
            exit 1
        fi
        ;;
esac
