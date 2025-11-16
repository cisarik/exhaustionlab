SHELL := /bin/bash

.PHONY: install test webui fmt lint clean

install:
	poetry install --with dev

test:
	poetry run pytest

webui:
	poetry run exhaustionlab-webui

fmt:
	poetry run black .

lint:
	poetry run ruff check .

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage reports || true

