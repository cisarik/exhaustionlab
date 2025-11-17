# ExhaustionLab v3.0 - Installation Instructions

## 🚀 Quick Install

### For First-Time Users

```bash
# 1. Clone repository
git clone <repository-url>
cd exhaustionlab

# 2. Install all dependencies (one command!)
make install

# 3. Configure environment
cp .env.example .env
nano .env  # Add your API keys and settings

# 4. Start the application
make webui

# 5. Access
# Web UI:    http://localhost:8080
# Health:    http://localhost:8080/health
# Metrics:   http://localhost:8080/metrics
# API Docs:  http://localhost:8080/api/docs
```

---

## 📦 Upgrading from v2.x to v3.0

### Step 1: Update Code

```bash
cd exhaustionlab
git pull origin main
```

### Step 2: Install New Dependencies

```bash
# Method 1: Using Make (recommended)
make install

# Method 2: Using Poetry directly
poetry install

# Verify installation
poetry show pydantic pydantic-settings prometheus-client loguru
```

**New dependencies added:**
- `pydantic ^2.5.0` - Data validation
- `pydantic-settings ^2.0.0` - Settings management
- `prometheus-client ^0.19.0` - Metrics collection
- `loguru ^0.7.0` - Structured logging

### Step 3: Update Environment Configuration

The v3.0 configuration system is more comprehensive. Update your `.env` file:

```bash
# Backup old config
cp .env .env.v2.backup

# Copy new template
cp .env.example .env

# Migrate your settings from .env.v2.backup to .env
# See DEPLOYMENT.md for all available settings
```

**New environment variables (all optional with defaults):**

```bash
# Application
APP_ENV=production
DEBUG=false

# Web UI
WEBUI_PORT=8080
WEBUI_HOST=0.0.0.0
WEBUI_WORKERS=1
WEBUI_LOG_LEVEL=info

# Observability
OBSERVABILITY_LOG_FORMAT=json
OBSERVABILITY_LOG_FILE=~/.cache/exhaustionlab/logs/app.log
OBSERVABILITY_METRICS_ENABLED=true
OBSERVABILITY_METRICS_PORT=9090

# Database
DB_PATH=~/.cache/exhaustionlab/strategies.db

# Cache
CACHE_ENABLED=true
CACHE_TTL=300
```

### Step 4: Verify Installation

```bash
# Test import
python -c "from exhaustionlab.app.config.settings import get_settings; print('✅ Settings OK')"

# Test web UI startup (dry run)
make webui-dev  # Ctrl+C to stop

# Run tests
make test-fast
```

### Step 5: Review Breaking Changes

**No breaking changes!** v3.0 is **100% backward compatible** with v2.x.

All new features are opt-in:
- Old `os.environ.get()` calls still work
- New Pydantic settings are recommended but not required
- All existing APIs continue to work

---

## 🐳 Docker Installation

### Build Image

```bash
# Using Make
make docker-build

# Or using Docker Compose
docker-compose build
```

### Run Container

```bash
# Basic stack
make docker-run
# OR
docker-compose up -d

# With monitoring stack
docker-compose --profile monitoring up -d
```

### Verify

```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f webui

# Check health
curl http://localhost:8080/health
```

---

## 🧪 Testing Installation

### Run Test Suite

```bash
# All tests
make test

# Fast tests only (skip slow markers)
make test-fast

# With coverage report
make test-coverage
open htmlcov/index.html  # View coverage

# BDD tests
make test-bdd
```

### Check Code Quality

```bash
# Check formatting and linting
make lint

# Auto-fix issues
make fmt
```

### Run CI Pipeline Locally

```bash
# Full CI pipeline (install, lint, test, build)
make ci-local
```

---

## 🔧 Troubleshooting

### Problem: `ModuleNotFoundError: No module named 'pydantic_settings'`

**Solution:**
```bash
# Reinstall dependencies
poetry lock --no-update
poetry install

# OR
make install
```

### Problem: `poetry: command not found`

**Solution:**
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH
export PATH="$HOME/.local/bin:$PATH"

# Verify
poetry --version
```

### Problem: Port 8080 already in use

**Solution:**
```bash
# Find process using port
lsof -i :8080

# Kill process
kill -9 <PID>

# OR change port in .env
echo "WEBUI_PORT=8081" >> .env
```

### Problem: Permission denied on logs directory

**Solution:**
```bash
# Create logs directory with proper permissions
mkdir -p ~/.cache/exhaustionlab/logs
chmod 755 ~/.cache/exhaustionlab/logs
```

### Problem: Docker build fails

**Solution:**
```bash
# Clear Docker cache
docker-compose down -v
docker system prune -af

# Rebuild
make docker-build
```

---

## 📚 Next Steps

After successful installation:

1. **Read Documentation**
   - `README.md` - Project overview
   - `AGENTS.md` - Architecture guide (v3.0 section)
   - `DEPLOYMENT.md` - Production deployment
   - `examples/README.md` - Example scripts

2. **Configure Application**
   - Set up API keys in `.env`
   - Configure risk limits
   - Set LLM endpoint (if using)

3. **Explore Features**
   - Start web UI: `make webui`
   - View metrics: http://localhost:8080/metrics
   - Check health: http://localhost:8080/health
   - API docs: http://localhost:8080/api/docs

4. **Run Examples**
   - See `examples/README.md`
   - Start with `examples/test_basic_integration.py`

---

## 🆘 Getting Help

- **Documentation**: See `docs/` directory
- **Examples**: See `examples/` directory
- **Issues**: GitHub Issues (if applicable)
- **Logs**: `~/.cache/exhaustionlab/logs/app.log`

---

**Status**: ✅ Installation guide for ExhaustionLab v3.0

Last Updated: 2025-11-17
