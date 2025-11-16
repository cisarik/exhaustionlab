# Validation Framework API Endpoints

## 🎯 Overview

REST API endpoints for the validation framework, exposing all validation functionality via HTTP.

**Total:** 6 new endpoints added to `/exhaustionlab/webui/api.py`

---

## 📡 Endpoints

### 1. **Parse Backtest**
```
POST /api/validation/parse-backtest
```

**Description:** Parse PyneCore backtest output files and extract all metrics.

**Request Body:**
```json
{
  "output_dir": "/path/to/pynecore/output",
  "symbol": "BTCUSDT"
}
```

**Response:**
```json
{
  "status": "success",
  "backtest": {
    "strategy_name": "Momentum Exhaustion v2",
    "symbol": "BTCUSDT",
    "timeframe": "5m",
    "start_date": "2024-01-01T00:00:00",
    "end_date": "2024-11-16T00:00:00",
    "total_trades": 150,
    "winning_trades": 95,
    "losing_trades": 55,
    "metrics": {
      "total_return": 0.425,
      "annualized_return": 0.425,
      "sharpe_ratio": 1.82,
      "sortino_ratio": 2.15,
      "max_drawdown": 0.183,
      "max_drawdown_duration": 12,
      "win_rate": 0.633,
      "profit_factor": 2.45,
      "avg_win": 125.50,
      "avg_loss": -82.30,
      "largest_win": 450.00,
      "largest_loss": -220.00
    },
    "equity_curve": {...},
    "returns": {...}
  }
}
```

**Errors:**
- `404`: Output directory not found
- `500`: Failed to parse backtest files

---

### 2. **Calculate Comprehensive Score**
```
POST /api/validation/calculate-score
```

**Description:** Calculate comprehensive strategy score with weighted components.

**Request Body:**
```json
{
  "backtest_output_dir": "/path/to/pynecore/output",
  "symbol": "BTCUSDT",
  "portfolio_size_usd": 100000,
  "out_of_sample_ratio": 0.75,
  "cross_market_pass_rate": 0.80
}
```

**Response:**
```json
{
  "status": "success",
  "scores": {
    "performance": {
      "sharpe": 12.0,
      "return": 8.5,
      "win_rate": 8.0,
      "total": 28.5
    },
    "risk": {
      "drawdown": 11.0,
      "consistency": 8.5,
      "recovery": 4.5,
      "total": 24.0
    },
    "execution": {
      "frequency": 9.0,
      "latency": 4.0,
      "slippage": 3.0,
      "total": 16.0
    },
    "robustness": {
      "out_of_sample": 5.0,
      "cross_market": 5.0,
      "total": 10.0
    },
    "total": 78.5
  },
  "report": "=== COMPREHENSIVE STRATEGY SCORE === ...",
  "deployment_status": "approved",
  "recommended_position_size": 0.0157
}
```

**Errors:**
- `404`: Backtest directory not found
- `500`: Failed to calculate score

---

### 3. **Generate Validation Report**
```
POST /api/validation/generate-report
```

**Description:** Generate comprehensive HTML validation report with charts.

**Request Body:**
```json
{
  "backtest_output_dir": "/path/to/pynecore/output",
  "symbol": "BTCUSDT",
  "portfolio_size_usd": 100000,
  "out_of_sample_ratio": 0.75,
  "cross_market_pass_rate": 0.80,
  "include_costs": true,
  "output_filename": "my_strategy_report.html"
}
```

**Response:**
```json
{
  "status": "success",
  "report_path": "reports/my_strategy_report.html",
  "total_score": 78.5,
  "deployment_status": "approved"
}
```

**Features:**
- Executive summary with deployment status
- Performance metrics table
- 4 embedded charts (equity, drawdown, returns, monthly)
- Trade journal
- Score breakdown
- Actionable recommendations

**Errors:**
- `404`: Backtest directory not found
- `500`: Failed to generate report

---

### 4. **Estimate Slippage**
```
POST /api/validation/estimate-slippage
```

**Description:** Estimate slippage for a single trade.

**Request Body:**
```json
{
  "symbol": "BTCUSDT",
  "order_size_usd": 10000,
  "signal_frequency": 5.0,
  "volatility": 0.8
}
```

**Response:**
```json
{
  "status": "success",
  "estimate": {
    "total_slippage_bps": 5.45,
    "spread_cost_bps": 1.20,
    "market_impact_bps": 1.65,
    "execution_delay_bps": 1.35,
    "volatility_slippage_bps": 1.25,
    "confidence_interval_lower_bps": 4.36,
    "confidence_interval_upper_bps": 6.54,
    "signal_frequency": 5.0,
    "order_size_usd": 10000,
    "liquidity_class": "very_high",
    "time_of_day": "us"
  }
}
```

**Errors:**
- `500`: Failed to estimate slippage

---

### 5. **Calculate Trading Costs**
```
POST /api/validation/calculate-costs
```

**Description:** Calculate total trading costs (slippage + fees) for entire backtest.

**Request Body:**
```json
{
  "backtest_output_dir": "/path/to/pynecore/output",
  "symbol": "BTCUSDT",
  "portfolio_size_usd": 100000,
  "include_fees": true,
  "fee_bps": 10.0
}
```

**Response:**
```json
{
  "status": "success",
  "costs": {
    "slippage": {
      "total_slippage_cost_usd": 285.40,
      "slippage_drag_annual_pct": 0.72,
      "avg_slippage_per_trade_bps": 5.45,
      "slippage_breakdown": {
        "spread": 1.20,
        "market_impact": 1.65,
        "execution_delay": 1.35,
        "volatility": 1.25
      }
    },
    "fees": {
      "total_fees_usd": 450.00,
      "annual_fee_drag_pct": 1.12,
      "trades_per_year": 1825
    },
    "total_costs": {
      "total_costs_usd": 735.40,
      "total_annual_drag_pct": 1.84
    },
    "cost_breakdown_pct": {
      "slippage": 38.8,
      "fees": 61.2
    }
  }
}
```

**Errors:**
- `404`: Backtest directory not found
- `500`: Failed to calculate costs

---

### 6. **Get Liquidity Info**
```
GET /api/validation/liquidity-info/{symbol}
```

**Description:** Get liquidity information and classification for a symbol.

**URL Parameters:**
- `symbol` (required): Trading symbol (e.g., "BTCUSDT")

**Response:**
```json
{
  "status": "success",
  "symbol": "BTCUSDT",
  "liquidity_info": {
    "liquidity_class": "very_high",
    "avg_24h_volume_usd": 5000000000,
    "avg_1h_volume_usd": 208333333,
    "bid_ask_spread_bps": 1.0,
    "order_book_depth_1pct_usd": 50000000,
    "order_book_depth_5pct_usd": 200000000,
    "liquidity_score": 95.0,
    "market_impact_coefficient": 0.5
  }
}
```

**Errors:**
- `500`: Failed to get liquidity info

---

## 🔧 Usage Examples

### cURL Examples

**1. Parse Backtest:**
```bash
curl -X POST http://localhost:8000/api/validation/parse-backtest \
  -H "Content-Type: application/json" \
  -d '{
    "output_dir": "/home/user/backtests/output_20241116",
    "symbol": "BTCUSDT"
  }'
```

**2. Calculate Score:**
```bash
curl -X POST http://localhost:8000/api/validation/calculate-score \
  -H "Content-Type: application/json" \
  -d '{
    "backtest_output_dir": "/home/user/backtests/output_20241116",
    "symbol": "BTCUSDT",
    "portfolio_size_usd": 100000,
    "out_of_sample_ratio": 0.75,
    "cross_market_pass_rate": 0.80
  }'
```

**3. Generate Report:**
```bash
curl -X POST http://localhost:8000/api/validation/generate-report \
  -H "Content-Type: application/json" \
  -d '{
    "backtest_output_dir": "/home/user/backtests/output_20241116",
    "symbol": "BTCUSDT",
    "portfolio_size_usd": 100000,
    "include_costs": true,
    "output_filename": "btc_validation.html"
  }'
```

**4. Estimate Slippage:**
```bash
curl -X POST http://localhost:8000/api/validation/estimate-slippage \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "ETHUSDT",
    "order_size_usd": 5000,
    "signal_frequency": 10.0,
    "volatility": 1.2
  }'
```

**5. Calculate Costs:**
```bash
curl -X POST http://localhost:8000/api/validation/calculate-costs \
  -H "Content-Type: application/json" \
  -d '{
    "backtest_output_dir": "/home/user/backtests/output_20241116",
    "symbol": "BTCUSDT",
    "portfolio_size_usd": 100000,
    "include_fees": true,
    "fee_bps": 10.0
  }'
```

**6. Get Liquidity Info:**
```bash
curl http://localhost:8000/api/validation/liquidity-info/BTCUSDT
```

---

### Python Examples

```python
import requests

BASE_URL = "http://localhost:8000"

# 1. Parse backtest
response = requests.post(
    f"{BASE_URL}/api/validation/parse-backtest",
    json={
        "output_dir": "/path/to/output",
        "symbol": "BTCUSDT"
    }
)
backtest = response.json()["backtest"]
print(f"Total return: {backtest['metrics']['total_return']:.2%}")

# 2. Calculate score
response = requests.post(
    f"{BASE_URL}/api/validation/calculate-score",
    json={
        "backtest_output_dir": "/path/to/output",
        "symbol": "BTCUSDT",
        "portfolio_size_usd": 100000,
        "out_of_sample_ratio": 0.75,
        "cross_market_pass_rate": 0.80
    }
)
result = response.json()
print(f"Total score: {result['scores']['total']}/100")
print(f"Status: {result['deployment_status']}")

# 3. Generate report
response = requests.post(
    f"{BASE_URL}/api/validation/generate-report",
    json={
        "backtest_output_dir": "/path/to/output",
        "symbol": "BTCUSDT",
        "portfolio_size_usd": 100000,
        "include_costs": True
    }
)
report_path = response.json()["report_path"]
print(f"Report saved: {report_path}")

# 4. Estimate slippage
response = requests.post(
    f"{BASE_URL}/api/validation/estimate-slippage",
    json={
        "symbol": "ETHUSDT",
        "order_size_usd": 5000,
        "signal_frequency": 10.0,
        "volatility": 1.2
    }
)
estimate = response.json()["estimate"]
print(f"Estimated slippage: {estimate['total_slippage_bps']:.2f} bps")

# 5. Calculate costs
response = requests.post(
    f"{BASE_URL}/api/validation/calculate-costs",
    json={
        "backtest_output_dir": "/path/to/output",
        "symbol": "BTCUSDT",
        "portfolio_size_usd": 100000,
        "include_fees": True,
        "fee_bps": 10.0
    }
)
costs = response.json()["costs"]
print(f"Annual cost drag: {costs['total_costs']['total_annual_drag_pct']:.2f}%")

# 6. Get liquidity info
response = requests.get(f"{BASE_URL}/api/validation/liquidity-info/BTCUSDT")
info = response.json()["liquidity_info"]
print(f"Liquidity class: {info['liquidity_class']}")
print(f"24h volume: ${info['avg_24h_volume_usd']:,.0f}")
```

---

### JavaScript Examples

```javascript
const BASE_URL = 'http://localhost:8000';

// 1. Parse backtest
async function parseBacktest(outputDir, symbol) {
  const response = await fetch(`${BASE_URL}/api/validation/parse-backtest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      output_dir: outputDir,
      symbol: symbol
    })
  });
  const data = await response.json();
  return data.backtest;
}

// 2. Calculate score
async function calculateScore(outputDir, symbol, portfolioSize) {
  const response = await fetch(`${BASE_URL}/api/validation/calculate-score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      backtest_output_dir: outputDir,
      symbol: symbol,
      portfolio_size_usd: portfolioSize,
      out_of_sample_ratio: 0.75,
      cross_market_pass_rate: 0.80
    })
  });
  const data = await response.json();
  return data;
}

// 3. Generate report
async function generateReport(outputDir, symbol) {
  const response = await fetch(`${BASE_URL}/api/validation/generate-report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      backtest_output_dir: outputDir,
      symbol: symbol,
      portfolio_size_usd: 100000,
      include_costs: true
    })
  });
  const data = await response.json();
  console.log(`Report generated: ${data.report_path}`);
  return data.report_path;
}

// 4. Estimate slippage
async function estimateSlippage(symbol, orderSize, frequency) {
  const response = await fetch(`${BASE_URL}/api/validation/estimate-slippage`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      symbol: symbol,
      order_size_usd: orderSize,
      signal_frequency: frequency,
      volatility: 0.8
    })
  });
  const data = await response.json();
  return data.estimate;
}

// 5. Get liquidity info
async function getLiquidityInfo(symbol) {
  const response = await fetch(`${BASE_URL}/api/validation/liquidity-info/${symbol}`);
  const data = await response.json();
  return data.liquidity_info;
}

// Usage
const backtest = await parseBacktest('/path/to/output', 'BTCUSDT');
console.log(`Total return: ${(backtest.metrics.total_return * 100).toFixed(2)}%`);

const score = await calculateScore('/path/to/output', 'BTCUSDT', 100000);
console.log(`Score: ${score.scores.total}/100`);
console.log(`Status: ${score.deployment_status}`);

const reportPath = await generateReport('/path/to/output', 'BTCUSDT');

const slippage = await estimateSlippage('ETHUSDT', 5000, 10.0);
console.log(`Slippage: ${slippage.total_slippage_bps.toFixed(2)} bps`);

const liquidity = await getLiquidityInfo('BTCUSDT');
console.log(`Liquidity: ${liquidity.liquidity_class}`);
```

---

## 🔒 Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP status codes:**
- `200`: Success
- `400`: Bad request (invalid parameters)
- `404`: Resource not found (directory, file, etc.)
- `500`: Internal server error (parsing, calculation, etc.)

**Best practices:**
```python
try:
    response = requests.post(url, json=data)
    response.raise_for_status()  # Raise exception for 4xx/5xx
    result = response.json()
except requests.exceptions.HTTPError as e:
    print(f"HTTP error: {e}")
    print(f"Details: {e.response.json()['detail']}")
except Exception as e:
    print(f"Error: {e}")
```

---

## 📊 Integration with WebUI

The validation dashboard can now call these endpoints to:

1. **Parse uploaded backtest files**
2. **Calculate and display scores in real-time**
3. **Generate downloadable reports**
4. **Show slippage estimates for different scenarios**
5. **Display trading costs breakdown**
6. **Provide liquidity information for symbols**

---

## ✅ Status

**🟢 ALL ENDPOINTS OPERATIONAL**

- ✅ 6 REST API endpoints added
- ✅ All imports tested and working
- ✅ Consistent error handling
- ✅ Comprehensive documentation
- ✅ Ready for frontend integration

---

## 🚀 Next Steps

1. **UI Integration** (low priority)
   - Add validation tab to dashboard
   - File upload for backtest outputs
   - Real-time score visualization
   - Report download button

2. **WebSocket Support** (future)
   - Real-time progress updates during report generation
   - Streaming slippage calculations
   - Live cost monitoring

3. **Caching** (future)
   - Cache parsed backtests
   - Cache generated reports
   - Redis integration

---

**The validation framework is now fully accessible via REST API!** 🎯✨
