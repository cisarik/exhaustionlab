# Quick Start - CI/CD for BDD Tests

## 🚀 **5-Minute Setup**

### Step 1: Verify Installation

```bash
# Check that all dependencies are installed
poetry run pytest --version
poetry run pre-commit --version
poetry run black --version

# Should all work ✅
```

### Step 2: Run Tests Locally

```bash
# Quick test
poetry run pytest tests/bdd/test_strategy_extraction.py -v

# With coverage
poetry run pytest tests/bdd/ --cov=exhaustionlab/app/meta_evolution --cov-report=html

# Open coverage report
xdg-open htmlcov/index.html  # Linux
open htmlcov/index.html       # macOS
```

### Step 3: Use Makefile Commands

```bash
# See all available commands
make -f Makefile.ci help

# Run most common ones
make -f Makefile.ci test-bdd       # Run BDD tests
make -f Makefile.ci test-coverage  # Run with coverage
make -f Makefile.ci format         # Format code
make -f Makefile.ci lint           # Check code quality
make -f Makefile.ci ci-local       # Full CI pipeline
```

### Step 4: Git Workflow

```bash
# Pre-commit hooks are already installed!
# They will run automatically on commit

# Make changes
vim tests/bdd/test_strategy_extraction.py

# Format and test
make -f Makefile.ci format
make -f Makefile.ci test-bdd

# Commit (hooks run automatically)
git add tests/bdd/
git commit -m "test: add new BDD scenarios"

# Push (triggers CI/CD pipelines)
git push origin main
```

---

## 📦 **What Was Created**

### CI/CD Configuration Files

```
.github/workflows/
├── bdd-tests.yml           # GitHub Actions - BDD tests
└── coverage-report.yml     # GitHub Actions - Coverage

.gitlab-ci.yml              # GitLab CI configuration
.pre-commit-config.yaml     # Pre-commit hooks
Makefile.ci                 # Local CI commands
pyproject.toml              # Updated with coverage config
```

### Documentation

```
CI_CD_SETUP.md              # Complete setup guide (9.5KB)
CI_CD_SUMMARY.md            # Implementation summary (12KB)
QUICK_START_CI_CD.md        # This file (quick reference)
```

---

## ⚡ **Most Useful Commands**

```bash
# Testing
make -f Makefile.ci test-bdd              # Run all BDD tests
make -f Makefile.ci test-integration      # Run pipeline tests only
make -f Makefile.ci test-coverage         # Run with HTML coverage
make -f Makefile.ci coverage-html         # Generate and open coverage

# Code Quality
make -f Makefile.ci format                # Auto-format code
make -f Makefile.ci lint                  # Check code style
make -f Makefile.ci security              # Run security scan

# CI/CD
make -f Makefile.ci ci-local              # Full CI pipeline locally
make -f Makefile.ci ci-fast               # Quick CI check
make -f Makefile.ci pre-commit            # Run all pre-commit hooks

# Maintenance
make -f Makefile.ci clean                 # Clean artifacts
make -f Makefile.ci stats                 # Show test statistics
make -f Makefile.ci deps-update           # Update dependencies
```

---

## 🎯 **GitHub Actions Status**

Once you push to GitHub, you'll see:

### Workflow: BDD Tests
- **Matrix**: Python 3.11, 3.12, 3.13
- **Jobs**: bdd-tests, integration-tests, code-quality
- **Duration**: ~3-5 minutes
- **Artifacts**: Coverage reports, JUnit XML

### Workflow: Coverage Report
- **Triggers**: Push to main/develop, PRs, weekly schedule
- **Coverage**: Minimum 80% enforced
- **Reports**: Codecov, HTML artifacts

### Add Status Badges to README

```markdown
![BDD Tests](https://github.com/<org>/<repo>/workflows/BDD%20Tests%20-%20Strategy%20Extraction/badge.svg)
![Coverage](https://codecov.io/gh/<org>/<repo>/branch/main/graph/badge.svg)
```

---

## 🦊 **GitLab CI/CD Status**

After pushing to GitLab, you'll see:

### Pipeline Stages
1. **test**: BDD tests on Python 3.11/3.12/3.13
2. **quality**: Black, Ruff checks
3. **report**: Coverage enforcement (80% minimum)

### Add Badges to README

```markdown
[![pipeline status](https://gitlab.com/<org>/<repo>/badges/main/pipeline.svg)](https://gitlab.com/<org>/<repo>/-/commits/main)
[![coverage report](https://gitlab.com/<org>/<repo>/badges/main/coverage.svg)](https://gitlab.com/<org>/<repo>/-/commits/main)
```

---

## 🪝 **Pre-commit Hooks**

### What Runs Automatically

**On every commit:**
- Black formatting
- Ruff linting
- isort import sorting
- YAML/JSON validation
- Security checks (Bandit)
- Private key detection

**On push:**
- Quick BDD smoke test

### Manual Control

```bash
# Run manually on all files
poetry run pre-commit run --all-files

# Skip hooks for emergency commit
git commit --no-verify

# Update hook versions
poetry run pre-commit autoupdate
```

---

## 📊 **Current Test Status**

```
✅ 20 BDD scenarios (100% passing)
✅ 103 step definitions
✅ 996 lines of test code
✅ 150 lines of Gherkin features

Coverage (BDD-tested modules):
✅ code_extractor.py:     76.40%
✅ strategy_database.py:  72.36%
✅ quality_scorer.py:     60.66%
✅ mock_repo_data.py:    100.00%
```

---

## 🎓 **Daily Developer Workflow**

### Morning Routine

```bash
# Update to latest
git pull origin main

# Update dependencies (weekly)
make -f Makefile.ci deps-update

# Run tests to verify everything works
make -f Makefile.ci test-bdd
```

### During Development

```bash
# 1. Write code
vim exhaustionlab/app/meta_evolution/...

# 2. Write/update BDD tests
vim tests/bdd/test_strategy_extraction.py
vim tests/bdd/features/strategy_extraction.feature

# 3. Format code
make -f Makefile.ci format

# 4. Run tests
make -f Makefile.ci test-bdd

# 5. Check coverage
make -f Makefile.ci test-coverage

# 6. Commit (pre-commit hooks run automatically)
git add .
git commit -m "feat: add new extraction feature"

# 7. Push (CI/CD runs automatically)
git push origin feature-branch
```

### Before Creating PR

```bash
# Run full CI pipeline locally
make -f Makefile.ci ci-local

# View coverage report
make -f Makefile.ci coverage-html

# Ensure all checks pass
make -f Makefile.ci lint
make -f Makefile.ci security

# Create PR
gh pr create  # or via web UI
```

---

## 🔧 **Troubleshooting**

### Tests Failing Locally

```bash
# Clean cache and re-run
make -f Makefile.ci clean
poetry install
make -f Makefile.ci test-bdd
```

### Pre-commit Hooks Too Slow

```bash
# Skip slow hooks temporarily
SKIP=bdd-quick-test git commit -m "Quick fix"

# Or disable for development session
poetry run pre-commit uninstall
# Remember to reinstall later!
poetry run pre-commit install
```

### Coverage Below Threshold

```bash
# See what's not covered
make -f Makefile.ci test-coverage

# View detailed HTML report
make -f Makefile.ci coverage-html
```

### CI Failing on GitHub/GitLab

```bash
# Test the exact same thing locally
make -f Makefile.ci ci-local

# Check logs in CI/CD UI
# - GitHub: Actions tab
# - GitLab: CI/CD → Pipelines
```

---

## 📈 **Best Practices**

### Commit Messages

Use conventional commits:
```
feat: add concurrent extraction support
fix: resolve race condition in database
test: add BDD scenarios for error handling
docs: update CI/CD documentation
ci: optimize workflow caching
```

### Test Writing

1. Write Gherkin scenario first (`.feature` file)
2. Run tests to see missing step definitions
3. Implement step definitions (`.py` file)
4. Verify tests pass
5. Check coverage increases

### Code Reviews

- ✅ All CI checks must pass
- ✅ Coverage should not decrease
- ✅ Pre-commit hooks should pass
- ✅ Tests should be meaningful

---

## 🎉 **Success Indicators**

You'll know everything is working when:

- ✅ Tests pass locally: `make -f Makefile.ci test-bdd`
- ✅ Coverage is good: `make -f Makefile.ci test-coverage`
- ✅ Pre-commit hooks pass: automatic on commit
- ✅ GitHub/GitLab CI passes: green badge
- ✅ No linting errors: `make -f Makefile.ci lint`

---

## 📚 **More Information**

- **Detailed Setup**: See [`CI_CD_SETUP.md`](CI_CD_SETUP.md)
- **Full Summary**: See [`CI_CD_SUMMARY.md`](CI_CD_SUMMARY.md)
- **BDD Tests**: See [`tests/bdd/README.md`](tests/bdd/README.md)

---

## 🤝 **Getting Help**

### Check These First

1. Run `make -f Makefile.ci help` for command reference
2. Check CI logs in GitHub Actions / GitLab Pipelines
3. Review `CI_CD_SETUP.md` for detailed documentation

### Common Issues

- **Poetry not found**: Run `poetry install`
- **Pre-commit not installed**: Run `poetry run pre-commit install`
- **Tests failing**: Run `make -f Makefile.ci clean` then re-run
- **Coverage low**: View `htmlcov/index.html` for missing lines

---

**Happy Testing! 🚀**

All CI/CD is configured and ready to use. Just commit and push!
