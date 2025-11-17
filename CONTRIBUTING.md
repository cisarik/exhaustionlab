# Contributing to ExhaustionLab

Thanks for helping! This guide keeps the repo human‑friendly and consistent.

## Quick Start
- Install: `poetry install --with dev`
- Run tests: `poetry run pytest`
- Start Web UI: `poetry run exhaustionlab-webui` (or `make webui`)

## Make Targets
If you have `make` available:
- `make install` — install deps (incl. dev)
- `make test` — run all tests
- `make webui` — start FastAPI server on :8080
- `make fmt` — format with Black
- `make lint` — Ruff lint

## Conventions
- Code style: Black (PEP8+), Ruff for lint
- Typing: prefer precise type hints; keep modules Pydantic v2‑compatible
- Tests: place new tests in `tests/`; keep demos in `examples/`
- Docs: update README/PRD/AGENTS when changing external APIs or UX

## PR Checklist
- [ ] Tests pass (`poetry run pytest`)
- [ ] Lint/format clean (`make lint fmt`)
- [ ] Docs updated where relevant
- [ ] No secrets committed (`.env` ignored, `.env.example` updated if needed)

## Security
- Never hard‑code credentials. Use env vars and `.env` (see `.env.example`).
- Be mindful of rate limits and scraping policies when working on crawlers.

Happy hacking! 🚀
