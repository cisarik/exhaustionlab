# CI/CD Configuration Guide

This document describes the continuous integration and deployment setup for ExhaustionLab's BDD test suite.

## 📋 Table of Contents

- [Overview](#overview)
- [GitHub Actions](#github-actions)
- [GitLab CI](#gitlab-ci)
- [Pre-commit Hooks](#pre-commit-hooks)
- [Coverage Reporting](#coverage-reporting)
- [Local Testing](#local-testing)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

Our CI/CD pipeline ensures code quality through:

- **Automated Testing**: BDD tests run on every push/PR
- **Multi-Python Support**: Tests on Python 3.11, 3.12, 3.13
- **Code Quality**: Black, Ruff, isort, Bandit checks
- **Coverage Tracking**: 80% minimum coverage enforcement
- **Pre-commit Hooks**: Catch issues before commit

---

## 🐙 GitHub Actions

### Workflows

#### 1. **BDD Tests** (`.github/workflows/bdd-tests.yml`)

Runs on: `push`, `pull_request`, manual trigger

**Jobs:**
- `bdd-tests`: Runs on Python 3.11, 3.12, 3.13 matrix
- `integration-tests`: Pipeline and concurrent tests
- `code-quality`: Black, Ruff linting

**Features:**
- Poetry dependency caching
- Coverage reporting to Codecov
- JUnit test reports
- HTML coverage artifacts
- GitHub Step Summaries

**Badge:**
```markdown
![BDD Tests](https://github.com/<org>/<repo>/workflows/BDD%20Tests%20-%20Strategy%20Extraction/badge.svg)
```

#### 2. **Coverage Report** (`.github/workflows/coverage-report.yml`)

Runs on: `push` to main/develop, `pull_request`, weekly schedule

**Features:**
- Full test suite coverage
- Coverage badge generation
- PR coverage comments
- HTML report artifacts
- 80% minimum enforcement

**Usage:**

```bash
# View in GitHub Actions UI
# Artifacts are available for 30 days
# HTML coverage report in htmlcov/
```

---

## 🦊 GitLab CI

Configuration: `.gitlab-ci.yml`

### Stages

1. **test**: BDD tests on Python 3.11, 3.12, 3.13
2. **quality**: Black, Ruff checks
3. **report**: Coverage analysis

### Jobs

```yaml
bdd-tests:python3.13     # Main test job with coverage
integration-tests        # Pipeline tests
code-quality:black       # Formatting check
code-quality:ruff        # Linting check
coverage-report          # 80% minimum
nightly-full-suite      # Scheduled full run
```

### Artifacts

- JUnit test reports (integrated with GitLab UI)
- HTML coverage reports (30 days retention)
- Cobertura coverage XML

**Badge:**
```markdown
[![pipeline status](https://gitlab.com/<org>/<repo>/badges/main/pipeline.svg)](https://gitlab.com/<org>/<repo>/-/commits/main)
[![coverage report](https://gitlab.com/<org>/<repo>/badges/main/coverage.svg)](https://gitlab.com/<org>/<repo>/-/commits/main)
```

---

## 🪝 Pre-commit Hooks

### Installation

```bash
# Install pre-commit
poetry add pre-commit --group dev
poetry run pre-commit install

# Install hooks
poetry run pre-commit install --hook-type pre-commit
poetry run pre-commit install --hook-type pre-push
```

### Hooks Configured

#### Code Quality
- **black**: Code formatting (100 line length)
- **ruff**: Linting with auto-fix
- **isort**: Import sorting (black profile)

#### File Checks
- Trailing whitespace removal
- End-of-file fixer
- YAML/JSON/TOML validation
- Large file detection (1MB limit)
- Merge conflict detection
- Private key detection

#### Python Checks
- Debug statement detection
- AST validation
- Docstring first check

#### Security
- **bandit**: Security issue scanning

#### BDD-Specific
- Gherkin feature file validation
- Quick BDD smoke test (pre-push)
- Test naming convention check

### Manual Usage

```bash
# Run on all files
poetry run pre-commit run --all-files

# Run specific hook
poetry run pre-commit run black --all-files
poetry run pre-commit run bdd-quick-test

# Update hook versions
poetry run pre-commit autoupdate

# Skip hooks for a commit (use sparingly!)
git commit --no-verify
```

### Pre-push BDD Test

Automatically runs before `git push`:
```bash
poetry run pytest tests/bdd/test_strategy_extraction.py -x -q --tb=no
```

To skip:
```bash
git push --no-verify
```

---

## 📊 Coverage Reporting

### Configuration

Located in `pyproject.toml`:

```toml
[tool.coverage.run]
source = ["exhaustionlab"]
branch = true
parallel = true
omit = ["*/tests/*", "*/test_*.py"]

[tool.coverage.report]
precision = 2
show_missing = true
exclude_lines = ["pragma: no cover", "def __repr__", ...]
```

### Local Coverage

```bash
# Run with coverage
poetry run pytest tests/bdd/ --cov=exhaustionlab/app/meta_evolution --cov-report=html

# View HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# Terminal report with missing lines
poetry run pytest tests/bdd/ --cov=exhaustionlab --cov-report=term-missing

# Enforce minimum coverage
poetry run pytest tests/bdd/ --cov=exhaustionlab --cov-fail-under=80
```

### Coverage Targets

| Module | Target | Current |
|--------|--------|---------|
| `meta_evolution/` | 80% | ✅ >80% |
| `crawlers/` | 70% | 🟡 Improving |
| Overall | 80% | ✅ Target |

---

## 🧪 Local Testing

### Quick Commands

```bash
# Run all BDD tests
poetry run pytest tests/bdd/test_strategy_extraction.py -v

# Run specific scenario
poetry run pytest tests/bdd/test_strategy_extraction.py::test_end_to_end_extraction_pipeline -v

# Run integration tests only
poetry run pytest tests/bdd/ -k "pipeline or concurrent or incremental" -v

# Run with coverage
poetry run pytest tests/bdd/ --cov=exhaustionlab --cov-report=html

# Parallel execution (faster)
poetry run pytest tests/bdd/ -n auto

# Stop on first failure
poetry run pytest tests/bdd/ -x

# Show output
poetry run pytest tests/bdd/ -v -s
```

### Makefile Targets

Add to `Makefile`:

```makefile
.PHONY: test-bdd test-coverage lint format pre-commit

test-bdd:
	poetry run pytest tests/bdd/test_strategy_extraction.py -v

test-integration:
	poetry run pytest tests/bdd/ -k "pipeline or concurrent" -v

test-coverage:
	poetry run pytest tests/bdd/ --cov=exhaustionlab --cov-report=html --cov-report=term-missing

lint:
	poetry run black --check .
	poetry run ruff check .
	poetry run isort --check .

format:
	poetry run black .
	poetry run ruff check --fix .
	poetry run isort .

pre-commit:
	poetry run pre-commit run --all-files

ci-local:
	poetry run pytest tests/bdd/ --cov=exhaustionlab --cov-fail-under=80 -v
```

Usage:
```bash
make test-bdd
make test-coverage
make lint
make format
make ci-local
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. **Poetry not found in CI**

**Solution:** Ensure Poetry installation step is present:
```yaml
- name: Install Poetry
  uses: snok/install-poetry@v1
  with:
    version: 1.7.1
```

#### 2. **Cache not working**

**Solution:** Clear cache and rebuild:
```bash
# GitHub Actions
# Settings → Actions → Caches → Delete

# GitLab CI
# CI/CD → Pipelines → Clear runner caches

# Local
rm -rf .cache/
poetry cache clear --all pypi
```

#### 3. **Coverage not uploading**

**Solution:** Check token configuration:
```yaml
# GitHub: CODECOV_TOKEN secret
# GitLab: Environment variables
```

#### 4. **Pre-commit hooks too slow**

**Solution:** Skip slow hooks locally:
```bash
SKIP=bdd-quick-test git commit -m "Quick fix"
```

Or disable for development:
```bash
poetry run pre-commit uninstall
```

#### 5. **BDD tests timeout**

**Solution:** Increase timeout in CI:
```yaml
# GitHub Actions
timeout-minutes: 30

# GitLab CI
timeout: 30m
```

#### 6. **Dependency conflicts**

**Solution:** Lock dependencies:
```bash
poetry lock --no-update
poetry install
```

---

## 🚀 Best Practices

### Commit Messages

Use conventional commits for automated changelogs:
```
feat: add concurrent extraction tests
fix: resolve race condition in database
test: improve BDD coverage to 85%
ci: optimize pipeline caching
docs: update CI/CD setup guide
```

### Branch Protection

Recommended GitHub/GitLab settings:
- ✅ Require status checks (BDD tests)
- ✅ Require up-to-date branches
- ✅ Require code review
- ✅ Enforce coverage threshold
- ❌ Allow force push

### Performance Tips

1. **Cache Poetry venv**:
   - Speeds up CI by 60-80%
   - Invalidates on `poetry.lock` change

2. **Parallel testing**:
   ```bash
   poetry run pytest tests/bdd/ -n auto
   ```

3. **Fail fast**:
   ```yaml
   strategy:
     fail-fast: true  # Stop on first failure
   ```

4. **Test selection**:
   ```bash
   # Only run changed test files
   poetry run pytest --lf  # last failed
   poetry run pytest --ff  # failed first
   ```

---

## 📈 Monitoring

### GitHub Actions

View in: `Actions` tab → Select workflow

**Metrics:**
- Success rate
- Average duration
- Cache hit rate
- Coverage trends

### GitLab CI

View in: `CI/CD` → `Pipelines`

**Dashboards:**
- Pipeline analytics
- Coverage trends
- Test reports
- Merge request reports

---

## 🔄 Maintenance

### Weekly Tasks

```bash
# Update pre-commit hooks
poetry run pre-commit autoupdate

# Update dependencies
poetry update

# Run full test suite
poetry run pytest tests/ --cov=exhaustionlab
```

### Monthly Tasks

- Review coverage trends
- Update Python versions in CI
- Review and archive old artifacts
- Update CI/CD documentation

---

## 📚 Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [GitLab CI Docs](https://docs.gitlab.com/ee/ci/)
- [Pre-commit](https://pre-commit.com/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [Codecov](https://about.codecov.io/)

---

**Status**: ✅ All CI/CD pipelines operational and tested

Last Updated: 2025-11-17
