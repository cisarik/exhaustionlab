# ExhaustionLab v3.0 - Production Makefile
# One-command workflow for development and deployment

.PHONY: help install test test-fast test-coverage test-bdd test-integration lint fmt format check webui webui-dev docker-build docker-run docker-stop clean install-hooks pre-commit ci-local all

# Default target: show help
help:
	@echo "🚀 ExhaustionLab v3.0 - Development Commands"
	@echo ""
	@echo "📦 Installation & Setup:"
	@echo "  make install          Install all dependencies (production + dev)"
	@echo "  make install-hooks    Install pre-commit hooks"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test             Run full test suite"
	@echo "  make test-fast        Run fast tests (exclude slow markers)"
	@echo "  make test-coverage    Run tests with HTML coverage report"
	@echo "  make test-bdd         Run BDD tests only"
	@echo "  make test-integration Run integration tests only"
	@echo ""
	@echo "🔍 Code Quality:"
	@echo "  make lint             Check code quality (black, ruff, isort)"
	@echo "  make fmt              Auto-format code (black, ruff --fix, isort)"
	@echo "  make format           Alias for fmt"
	@echo "  make check            Run all quality checks (lint + test)"
	@echo "  make pre-commit       Run pre-commit hooks on all files"
	@echo ""
	@echo "🌐 Web UI:"
	@echo "  make webui            Start production web UI on :8080"
	@echo "  make webui-dev        Start development web UI with reload"
	@echo ""
	@echo "🐳 Docker:"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-run       Run in Docker container"
	@echo "  make docker-stop      Stop Docker containers"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  make clean            Remove cache files and build artifacts"
	@echo ""
	@echo "🚀 CI/CD:"
	@echo "  make ci-local         Run full CI pipeline locally"
	@echo "  make all              Install + lint + test (full build)"

# Installation targets
install:
	@echo "📦 Installing dependencies..."
	poetry install --with dev
	@echo "✅ Installation complete!"

install-hooks:
	@echo "🪝 Installing pre-commit hooks..."
	poetry run pre-commit install
	poetry run pre-commit install --hook-type pre-push
	@echo "✅ Hooks installed!"

# Testing targets
test:
	@echo "🧪 Running full test suite..."
	poetry run pytest tests/ -v

test-fast:
	@echo "⚡ Running fast tests..."
	poetry run pytest tests/ -v -m "not slow"

test-coverage:
	@echo "📊 Running tests with coverage..."
	poetry run pytest tests/ \
		--cov=exhaustionlab \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml \
		-v
	@echo "✅ Coverage report generated in htmlcov/"
	@echo "📄 Open htmlcov/index.html to view"

test-bdd:
	@echo "🥒 Running BDD tests..."
	poetry run pytest tests/bdd/ -v

test-integration:
	@echo "🔗 Running integration tests..."
	poetry run pytest tests/ -v -m integration

# Code quality targets
lint:
	@echo "🔍 Checking code quality..."
	@echo "  → Running black check..."
	poetry run black --check .
	@echo "  → Running ruff check..."
	poetry run ruff check .
	@echo "  → Running isort check..."
	poetry run isort --check .
	@echo "✅ All checks passed!"

fmt:
	@echo "✨ Auto-formatting code..."
	@echo "  → Running black..."
	poetry run black .
	@echo "  → Running ruff fix..."
	poetry run ruff check --fix .
	@echo "  → Running isort..."
	poetry run isort .
	@echo "✅ Formatting complete!"

format: fmt

check: lint test-fast
	@echo "✅ All checks passed!"

pre-commit:
	@echo "🪝 Running pre-commit hooks..."
	poetry run pre-commit run --all-files

# Web UI targets
webui:
	@echo "🌐 Starting ExhaustionLab Web UI (production mode)..."
	@echo "📍 http://localhost:8080"
	poetry run exhaustionlab-webui

webui-dev:
	@echo "🌐 Starting ExhaustionLab Web UI (development mode)..."
	@echo "📍 http://localhost:8080"
	@echo "♻️  Hot reload enabled"
	poetry run uvicorn exhaustionlab.webui.server:app --host 0.0.0.0 --port 8080 --reload

# Docker targets
docker-build:
	@echo "🐳 Building Docker image..."
	docker-compose build
	@echo "✅ Image built!"

docker-run:
	@echo "🐳 Starting Docker containers..."
	docker-compose up -d
	@echo "✅ Containers started!"
	@echo "📍 Web UI: http://localhost:8080"

docker-stop:
	@echo "🛑 Stopping Docker containers..."
	docker-compose down
	@echo "✅ Containers stopped!"

# Cleanup targets
clean:
	@echo "🧹 Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name "*.coverage" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true
	@echo "✅ Cleanup complete!"

# CI/CD targets
ci-local:
	@echo "🚀 Running CI pipeline locally..."
	@echo "Step 1/3: Code quality checks..."
	$(MAKE) lint
	@echo "Step 2/3: Running tests with coverage..."
	poetry run pytest tests/ --cov=exhaustionlab --cov-fail-under=80 -v
	@echo "Step 3/3: Build validation..."
	poetry build
	@echo "✅ CI pipeline completed successfully!"

all: install lint test
	@echo "🎉 Full build completed successfully!"
