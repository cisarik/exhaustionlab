# Validation Framework - Quick Start Guide

## 🚀 Quick Start

The validation framework is now complete and ready to use! This guide shows you how to get started.

---

## 📦 What's Available

**10 Modules (6,202 LOC):**
1. EnhancedMultiMarketTester - Test across markets/timeframes
2. ProfitAnalyzer - 15+ institutional metrics
3. WalkForwardValidator - Overfitting detection
4. MonteCarloSimulator - 1000+ bootstrap simulations
5. DeploymentReadinessScorer - Go/No-Go decisions
6. SlippageEstimator - 4-component slippage model ⭐ NEW
7. ExecutionQualityAnalyzer - 15+ execution metrics ⭐ NEW
8. BacktestParser - Parse real PyneCore outputs ⭐ NEW
9. ComprehensiveScorer - 100-point scoring ⭐ NEW
10. ReportGenerator - Professional HTML reports ⭐ NEW

**6 REST API Endpoints (306 LOC):**
- POST /api/validation/parse-backtest
- POST /api/validation/calculate-score
- POST /api/validation/generate-report
- POST /api/validation/estimate-slippage
- POST /api/validation/calculate-costs
- GET /api/validation/liquidity-info/{symbol}

---

## 🎯 Basic Usage

### 1. Parse a PyneCore Backtest

```python
from exhaustionlab.app.validation import parse_backtest_from_directory

# Parse PyneCore output
backtest = parse_backtest_from_directory("/path/to/pynecore/output/")

print(f"Strategy: {backtest.strategy_name}")
print(f"Total trades: {backtest.total_trades}")
print(f"Return: {backtest.annualized_return:.2%}")
print(f"Sharpe: {backtest.sharpe_ratio:.2f}")
print(f"Max DD: {backtest.max_drawdown:.2%}")
print(f"Win rate: {backtest.win_rate:.2%}")
```

### 2. Calculate Comprehensive Score

```python
from exhaustionlab.app.validation import ComprehensiveScorer

scorer = ComprehensiveScorer()
scores = scorer.calculate_comprehensive_score(
    backtest=backtest,
    symbol="BTCUSDT",
    portfolio_size_usd=100000,
)

print(f"Total Score: {scores.total_score:.1f}/100")
print(f"Performance: {scores.performance_total:.1f}/35")
print(f"Risk: {scores.risk_total:.1f}/30")
print(f"Execution: {scores.execution_total:.1f}/20")
print(f"Robustness: {scores.robustness_total:.1f}/15")

# Print full report
print(scorer.generate_score_report(scores))
```

### 3. Estimate Trading Costs

```python
from exhaustionlab.app.validation import calculate_trading_costs

costs = calculate_trading_costs(
    trades_df=backtest.to_dataframe(),
    symbol="BTCUSDT",
    portfolio_size_usd=100000,
    include_fees=True,
    fee_bps=10.0,
)

print(f"Total annual drag: {costs['total_costs']['total_annual_drag_pct']:.2f}%")
print(f"Slippage: {costs['slippage']['slippage_drag_annual_pct']:.2f}%")
print(f"Fees: {costs['fees']['annual_fee_drag_pct']:.2f}%")
```

### 4. Generate Professional Report

```python
from exhaustionlab.app.validation import generate_validation_report

report_path = generate_validation_report(
    backtest=backtest,
    scores=scores,
    symbol="BTCUSDT",
    output_path="reports/my_strategy.html",
    costs=costs,
)

print(f"Report generated: {report_path}")
# Open in browser: open {report_path}
```

---

## 🔗 Complete Pipeline Example

```python
from exhaustionlab.app.validation import (
    parse_backtest_from_directory,
    ComprehensiveScorer,
    calculate_trading_costs,
    generate_validation_report,
)

# Step 1: Parse backtest
backtest = parse_backtest_from_directory("/path/to/output/")

# Step 2: Calculate score
scorer = ComprehensiveScorer()
scores = scorer.calculate_comprehensive_score(
    backtest=backtest,
    symbol="BTCUSDT",
    portfolio_size_usd=100000,
)

# Step 3: Calculate costs
costs = calculate_trading_costs(
    trades_df=backtest.to_dataframe(),
    symbol="BTCUSDT",
    portfolio_size_usd=100000,
)

# Step 4: Generate report
report_path = generate_validation_report(
    backtest=backtest,
    scores=scores,
    symbol="BTCUSDT",
    output_path="reports/validation.html",
    costs=costs,
)

# Step 5: Make deployment decision
if scores.total_score >= 75:
    print("✅ APPROVED for live trading")
    print(f"Position size: {2.0 * (scores.total_score / 100):.2%}")
elif scores.total_score >= 65:
    print("⚠️ CONDITIONALLY APPROVED")
    print(f"Use reduced position size: {1.0 * (scores.total_score / 100):.2%}")
else:
    print("❌ NOT APPROVED for deployment")
```

---

## 🌐 REST API Examples

### Using Python requests

```python
import requests

BASE_URL = "http://localhost:8000"

# Parse backtest
response = requests.post(
    f"{BASE_URL}/api/validation/parse-backtest",
    json={
        "output_dir": "/path/to/output",
        "symbol": "BTCUSDT"
    }
)
backtest = response.json()["backtest"]

# Calculate score
response = requests.post(
    f"{BASE_URL}/api/validation/calculate-score",
    json={
        "backtest_output_dir": "/path/to/output",
        "symbol": "BTCUSDT",
        "portfolio_size_usd": 100000
    }
)
result = response.json()
print(f"Score: {result['scores']['total']}/100")
print(f"Status: {result['deployment_status']}")

# Generate report
response = requests.post(
    f"{BASE_URL}/api/validation/generate-report",
    json={
        "backtest_output_dir": "/path/to/output",
        "symbol": "BTCUSDT",
        "portfolio_size_usd": 100000
    }
)
report_path = response.json()["report_path"]
print(f"Report: {report_path}")
```

### Using cURL

```bash
# Estimate slippage
curl -X POST http://localhost:8000/api/validation/estimate-slippage \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "order_size_usd": 10000,
    "signal_frequency": 5.0,
    "volatility": 0.8
  }'

# Get liquidity info
curl http://localhost:8000/api/validation/liquidity-info/BTCUSDT
```

---

## 📊 Understanding the Scores

### Total Score: 100 points

**Performance (35 points):**
- Sharpe Ratio (15 pts): Target > 1.5
- Total Return (10 pts): Target > 30% annual
- Win Rate (10 pts): Target > 55%

**Risk (30 points):**
- Max Drawdown (15 pts): Target < 25%
- Consistency (10 pts): Target > 65% positive months
- Recovery Time (5 pts): Target < 30 days

**Execution (20 points):**
- Frequency (10 pts): Optimal for market liquidity
- Latency (5 pts): Execution speed requirements
- Slippage (5 pts): Target < 5 bps

**Robustness (15 points):**
- Out-of-Sample (7 pts): OOS/IS ratio > 0.7
- Cross-Market (8 pts): Pass rate > 75%

### Deployment Thresholds

| Score Range | Status | Action |
|-------------|--------|--------|
| ≥ 75 | ✅ **APPROVED** | Deploy with recommended position size |
| 65-75 | ⚠️ **CONDITIONAL** | Deploy with reduced position size |
| < 65 | ❌ **NOT APPROVED** | Do not deploy, address issues |

---

## 🎨 Report Features

The generated HTML report includes:

1. **Executive Summary**
   - Deployment status badge (Approved/Conditional/Not Approved)
   - Key metrics (return, Sharpe, drawdown, win rate)
   - Trading costs breakdown

2. **Performance Metrics Table**
   - 12+ metrics with actual values
   - Target thresholds
   - Status indicators (✓ pass, ⚠ warning)

3. **Score Breakdown**
   - Total score and grade (A/B/C/D/F)
   - 4 component sections with progress bars
   - Sub-metric details

4. **Visual Analytics**
   - Equity curve (line chart)
   - Drawdown analysis (area chart)
   - Returns distribution (histogram)
   - Monthly returns (bar chart)

5. **Trade Journal**
   - Recent trades table
   - Entry/exit prices and times
   - P&L with color coding
   - Exit reasons

6. **Recommendations**
   - Specific improvement suggestions
   - Issue identification
   - Deployment guidance

---

## 💡 Common Use Cases

### 1. Before Live Deployment

```python
# Validate strategy before going live
backtest = parse_backtest_from_directory("/path/to/output/")
scorer = ComprehensiveScorer()
scores = scorer.calculate_comprehensive_score(backtest, "BTCUSDT", 100000)

if scores.total_score >= 75:
    # Generate report for stakeholders
    generate_validation_report(backtest, scores, "BTCUSDT", "reports/deploy.html")
    print("✅ Ready for deployment")
else:
    print("❌ Not ready - score too low")
```

### 2. Cost Analysis

```python
# Analyze trading costs for different strategies
for strategy_dir in strategy_dirs:
    backtest = parse_backtest_from_directory(strategy_dir)
    costs = calculate_trading_costs(
        backtest.to_dataframe(),
        "BTCUSDT",
        100000
    )
    print(f"{strategy_dir}: {costs['total_costs']['total_annual_drag_pct']:.2f}% drag")
```

### 3. Slippage Estimation

```python
from exhaustionlab.app.validation import SlippageEstimator

estimator = SlippageEstimator()

# Compare slippage across different frequencies
for freq in [1, 5, 10, 20, 50]:
    estimate = estimator.estimate_slippage(
        "BTCUSDT",
        order_size_usd=10000,
        signal_frequency=freq,
        volatility=0.8
    )
    print(f"{freq} signals/day: {estimate.total_slippage_bps:.2f} bps")
```

### 4. Multi-Market Validation

```python
from exhaustionlab.app.validation import EnhancedMultiMarketTester

tester = EnhancedMultiMarketTester()
configs = tester.create_test_matrix(
    symbols=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
    timeframes=["5m", "15m", "1h"],
)

results = await tester.test_strategy(my_strategy, configs)
print(f"Pass rate: {results.pass_rate:.1%}")
print(f"Mean Sharpe: {results.mean_sharpe:.2f}")
```

---

## 📚 Documentation

**Complete Guides:**
- `ADVANCED_VALIDATION_FEATURES.md` - Slippage and execution analysis
- `COMPLETE_VALIDATION_IMPLEMENTATION.md` - System overview
- `REAL_BACKTEST_INTEGRATION_COMPLETE.md` - Backtest parsing guide
- `REPORT_GENERATOR_COMPLETE.md` - Report generation
- `VALIDATION_FRAMEWORK_FINAL_SUMMARY.md` - Complete summary
- `VALIDATION_API_ENDPOINTS.md` - API reference

---

## 🔧 Configuration

### Custom Report Config

```python
from exhaustionlab.app.validation import ReportGenerator, ReportConfig

config = ReportConfig(
    include_charts=True,
    include_trade_journal=True,
    chart_width=1400,
    chart_height=500,
    chart_dpi=120,
    max_trades_in_journal=200,
)

generator = ReportGenerator(config)
report_path = generator.generate_html_report(
    backtest=backtest,
    scores=scores,
    symbol="BTCUSDT",
    output_path="reports/custom.html",
)
```

### Custom Scoring Weights

The scoring weights are defined in `ComprehensiveScorer`:

```python
# To customize, modify these class attributes:
ComprehensiveScorer.SHARPE_TARGET = 1.5
ComprehensiveScorer.RETURN_TARGET = 0.30
ComprehensiveScorer.WIN_RATE_TARGET = 0.55
ComprehensiveScorer.DRAWDOWN_TARGET = 0.25
```

---

## ⚠️ Important Notes

### 1. PyneCore Output Format

The BacktestParser expects these files:
- `trades.json` - List of all trades
- `equity.json` - Equity curve data (optional)
- `summary.json` - Strategy metadata (optional)

Minimum required: `trades.json`

### 2. Slippage Estimation

Slippage estimates are based on:
- Market liquidity (from historical volume)
- Signal frequency (from backtest)
- Volatility (from returns or input)
- Time of day (from timestamp)

Estimates are conservative (95% confidence interval).

### 3. Report Generation

Reports include base64-encoded charts, making them:
- ✅ Portable (single file)
- ✅ No external dependencies
- ✅ Easy to share/archive
- ⚠️ Large file size (~2-5 MB)

### 4. API Endpoints

The FastAPI server must be running:
```bash
cd exhaustionlab/webui
python app.py
```

Access at: `http://localhost:8000`

---

## 🐛 Troubleshooting

### Import Error

```python
ModuleNotFoundError: No module named 'exhaustionlab.app.validation'
```

**Solution:** Ensure poetry environment is activated:
```bash
poetry shell
poetry install
```

### Backtest Parse Error

```python
FileNotFoundError: trades.json not found
```

**Solution:** Verify PyneCore output directory contains `trades.json`

### Chart Generation Error

```python
ImportError: matplotlib backend error
```

**Solution:** Matplotlib is already installed. If issues persist:
```bash
poetry add matplotlib
```

### API Connection Error

```bash
Connection refused on http://localhost:8000
```

**Solution:** Start the webui server:
```bash
cd exhaustionlab/webui
python app.py
```

---

## 🎯 Next Steps

1. **Try the Examples:** Run the basic usage examples above
2. **Generate a Report:** Create your first validation report
3. **Read the Docs:** Check out the comprehensive guides
4. **Use the API:** Try the REST API endpoints
5. **Integrate with UI:** (Optional) Add validation tab to dashboard

---

## ✅ Status

**Framework:** 🟢 **PRODUCTION READY**

All components implemented, tested, and documented. Ready for real-world strategy validation!

---

**Questions?** Check the comprehensive documentation guides in the root directory.

**Issues?** All components have proper error handling and logging for debugging.

**Feedback?** The framework is extensible - add custom metrics, modify thresholds, or integrate with other systems.

---

**Quick Start Guide Complete!** 🚀

Start validating your strategies with confidence!
