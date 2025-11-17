# ExhaustionLab v3.0 - Deployment Guide

Production deployment guide with security best practices, environment configuration, and operational procedures.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Deployment Methods](#deployment-methods)
- [Security Checklist](#security-checklist)
- [Monitoring & Observability](#monitoring--observability)
- [Operational Procedures](#operational-procedures)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

### System Requirements

- **CPU**: 2+ cores (4+ recommended)
- **Memory**: 2GB minimum (4GB+ recommended)
- **Disk**: 10GB minimum (SSD recommended)
- **OS**: Linux (Ubuntu 22.04 LTS recommended), macOS, Windows + WSL2

### Software Requirements

- **Python**: 3.11, 3.12, or 3.13
- **Poetry**: 1.7.1+ (dependency management)
- **Docker**: 24.0+ (optional, for containerized deployment)
- **Docker Compose**: 2.20+ (optional)

---

## ⚙️ Environment Configuration

### Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
nano .env
```

### Core Settings

```bash
# Application
APP_ENV=production            # production, staging, development
APP_VERSION=3.0.0
DEBUG=false

# Web UI
WEBUI_PORT=8080
WEBUI_HOST=0.0.0.0
WEBUI_WORKERS=1               # Increase for production
WEBUI_LOG_LEVEL=info         # debug, info, warning, error
```

### Exchange Configuration

```bash
# Binance API (REQUIRED for live trading)
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_TESTNET=true         # Use testnet for safety!
BINANCE_TIMEOUT=30
BINANCE_MAX_RETRIES=3
```

### LLM Configuration

```bash
# LLM Settings (for AI strategy generation)
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_MODEL=deepseek-r1-0528-qwen3-8b
LLM_TEMPERATURE=0.7
LLM_TOP_P=0.9
LLM_MAX_TOKENS=2000
LLM_TIMEOUT=120
LLM_FALLBACK_ENABLED=true    # Fallback to GA if LLM unavailable
```

### Risk Management

```bash
# Risk Limits (CRITICAL for live trading!)
RISK_MAX_POSITION_SIZE=0.02   # 2% of portfolio per position
RISK_MAX_DAILY_LOSS=0.01      # 1% daily loss limit
RISK_MAX_DRAWDOWN=0.25        # 25% maximum drawdown
RISK_MAX_OPEN_POSITIONS=3     # Maximum concurrent positions
RISK_STOP_LOSS_PCT=0.02       # 2% stop loss
RISK_TAKE_PROFIT_PCT=0.05     # 5% take profit
```

### Evolution Settings

```bash
# Strategy Evolution
EVOLUTION_NUM_GENERATIONS=10
EVOLUTION_POPULATION_SIZE=10
EVOLUTION_MUTATION_RATE=0.2
EVOLUTION_USE_LLM=true
EVOLUTION_USE_ADAPTIVE=true
EVOLUTION_MAX_INDICATORS=6
EVOLUTION_MAX_LOC=500
```

### Database Configuration

```bash
# SQLite (default)
DB_PATH=~/.cache/exhaustionlab/strategies.db

# PostgreSQL (advanced, optional)
DB_USER=exhaustionlab
DB_PASSWORD=your_secure_password_here
DB_NAME=exhaustionlab
DB_HOST=localhost
DB_PORT=5432
```

### Logging & Observability

```bash
# Logging
OBSERVABILITY_LOG_FORMAT=json              # json or text
OBSERVABILITY_LOG_FILE=~/.cache/exhaustionlab/logs/app.log
OBSERVABILITY_LOG_ROTATION=500 MB
OBSERVABILITY_LOG_RETENTION=30 days

# Metrics
OBSERVABILITY_METRICS_ENABLED=true
OBSERVABILITY_METRICS_PORT=9090
```

### CORS Configuration

```bash
# CORS (if exposing API publicly)
UI_ENABLE_CORS=true
UI_CORS_ORIGINS=["*"]         # Change to specific domains in production!
```

---

## 🚀 Deployment Methods

### Method 1: Docker Compose (Recommended)

**Best for**: Production deployments, easy management

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Configure all settings

# 2. Build image
make docker-build
# OR
docker-compose build

# 3. Start services
make docker-run
# OR
docker-compose up -d

# 4. Check status
docker-compose ps
docker-compose logs -f webui

# 5. Access application
# Web UI: http://localhost:8080
# Health: http://localhost:8080/health
# Metrics: http://localhost:9090/metrics
```

**With monitoring stack:**

```bash
# Start with Prometheus + Grafana
docker-compose --profile monitoring up -d

# Access:
# - Web UI: http://localhost:8080
# - Prometheus: http://localhost:9091
# - Grafana: http://localhost:3000 (admin/admin)
```

### Method 2: Poetry (Development)

**Best for**: Development, testing, local debugging

```bash
# 1. Install dependencies
make install
# OR
poetry install

# 2. Configure environment
cp .env.example .env
nano .env

# 3. Start web UI
make webui
# OR
poetry run exhaustionlab-webui

# Access: http://localhost:8080
```

### Method 3: Systemd Service (Production Linux)

**Best for**: Production Linux servers, automatic startup

```bash
# 1. Create service file
sudo nano /etc/systemd/system/exhaustionlab.service
```

```ini
[Unit]
Description=ExhaustionLab Web UI v3.0
After=network.target

[Service]
Type=simple
User=exhaustionlab
WorkingDirectory=/opt/exhaustionlab
Environment="PATH=/opt/exhaustionlab/.venv/bin:/usr/bin"
EnvironmentFile=/opt/exhaustionlab/.env
ExecStart=/opt/exhaustionlab/.venv/bin/exhaustionlab-webui
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/opt/exhaustionlab/data /opt/exhaustionlab/logs

[Install]
WantedBy=multi-user.target
```

```bash
# 2. Enable and start
sudo systemctl enable exhaustionlab
sudo systemctl start exhaustionlab

# 3. Check status
sudo systemctl status exhaustionlab
sudo journalctl -u exhaustionlab -f
```

---

## 🔒 Security Checklist

### Pre-Deployment

- [ ] Change default passwords in `.env`
- [ ] Use testnet API keys initially
- [ ] Configure risk limits appropriately
- [ ] Enable HTTPS (reverse proxy)
- [ ] Restrict CORS origins
- [ ] Review and minimize exposed ports
- [ ] Enable firewall rules
- [ ] Set up log rotation

### API Key Security

```bash
# NEVER commit .env to git!
echo ".env" >> .gitignore

# Use environment-specific secrets
# Production keys should NEVER be in development environments

# Rotate keys regularly
# Monitor API key usage in Binance account
```

### Network Security

```bash
# Use reverse proxy (Nginx/Caddy) with HTTPS
# Example Nginx configuration:

server {
    listen 443 ssl http2;
    server_name trading.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}
```

### Docker Security

```bash
# Run as non-root user (already configured)
# Scan images for vulnerabilities
docker scan exhaustionlab:3.0.0

# Use Docker secrets for sensitive data
docker secret create binance_api_key ./api_key.txt
docker secret create binance_api_secret ./api_secret.txt
```

---

## 📊 Monitoring & Observability

### Health Checks

```bash
# Application health
curl http://localhost:8080/health

# Expected response:
{
  "status": "healthy",
  "version": "3.0.0",
  "environment": "production",
  "uptime_seconds": 3600.5,
  "services": {
    "api": "up",
    "database": "up",
    "llm": "up",
    "exchange": "up"
  }
}
```

### Prometheus Metrics

```bash
# View metrics
curl http://localhost:8080/metrics

# Key metrics:
# - http_requests_total
# - http_request_duration_seconds
# - evolution_strategies_generated_total
# - llm_requests_total
# - trading_trades_executed_total
```

### Structured Logging

```bash
# View JSON logs
tail -f ~/.cache/exhaustionlab/logs/app.log | jq .

# Filter by level
jq 'select(.level == "ERROR")' ~/.cache/exhaustionlab/logs/app.log

# Filter by request ID
jq 'select(.request_id == "abc123")' ~/.cache/exhaustionlab/logs/app.log
```

### Alerting

Configure alerts in Prometheus `prometheus.yml`:

```yaml
rule_files:
  - '/etc/prometheus/alerts.yml'

alerting:
  alertmanagers:
    - static_configs:
      - targets: ['alertmanager:9093']
```

Example alerts (`alerts.yml`):

```yaml
groups:
  - name: exhaustionlab
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: LowSuccessRate
        expr: rate(evolution_strategies_generated_total{status="success"}[1h]) < 0.5
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Low strategy generation success rate"
```

---

## 🔧 Operational Procedures

### Backup & Restore

```bash
# Backup database
./scripts/backup.sh

# Restore from backup
./scripts/restore.sh backup_2025-11-17.tar.gz
```

### Rolling Updates

```bash
# Zero-downtime update with Docker
docker-compose pull
docker-compose up -d --no-deps --build webui
```

### Scaling

```bash
# Increase workers
# In .env:
WEBUI_WORKERS=4

# Restart
docker-compose restart webui
```

### Log Rotation

Logs are automatically rotated based on settings:

```bash
OBSERVABILITY_LOG_ROTATION=500 MB
OBSERVABILITY_LOG_RETENTION=30 days
```

---

## 🔍 Troubleshooting

### Application won't start

```bash
# Check logs
docker-compose logs webui

# Common issues:
# 1. Port already in use
lsof -i :8080
kill -9 <PID>

# 2. Permission denied
sudo chown -R $USER:$USER ./data ./logs

# 3. Missing dependencies
poetry install
```

### Database connection errors

```bash
# Check database
docker-compose ps db

# Reset database
docker-compose down -v
docker-compose up -d
```

### LLM connection failures

```bash
# Test LLM endpoint
curl http://127.0.0.1:1234/v1/models

# Fallback enabled?
OBSERVABILITY_LLM_FALLBACK_ENABLED=true
```

### High memory usage

```bash
# Check resource usage
docker stats

# Reduce workers
WEBUI_WORKERS=1

# Set memory limits in docker-compose.yml
```

---

## 📚 Additional Resources

- [README.md](README.md) - Project overview
- [AGENTS.md](AGENTS.md) - Architecture guide
- [CI_CD_SETUP.md](CI_CD_SETUP.md) - CI/CD configuration
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines

---

**Status**: ✅ Production-ready deployment guide for ExhaustionLab v3.0

Last Updated: 2025-11-17
