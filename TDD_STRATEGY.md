# Test-Driven Development Strategy — ExhaustionLab

**Philosophy:** Write tests first, then implement. Tests are specifications, not afterthoughts.

---

## Why TDD for Trading Systems

**Critical Reasons:**

1. **Money is on the line** - Bugs cost real capital
2. **Complex interactions** - Strategies, risk, execution must work together perfectly
3. **Regression prevention** - Changes shouldn't break existing functionality
4. **Documentation** - Tests show how components should be used
5. **Confidence** - Deploy to live trading with certainty

**TDD Mantra:** Red → Green → Refactor

---

## Testing Pyramid

```
         /\
        /  \
       /E2E \      ← Few (10%): Full system tests
      /------\
     /        \
    / Integr. \    ← Some (30%): Component integration
   /----------\
  /            \
 /    Unit      \  ← Many (60%): Individual functions
/----------------\
```

**Our Target Coverage:**
- Unit Tests: 80%+ coverage
- Integration Tests: Critical paths covered
- E2E Tests: Happy path + major error scenarios

---

## Test Categories

### 1. Unit Tests (60% of tests)

**What:** Test individual functions/methods in isolation

**When to write:**
- Before implementing any function with logic
- For all calculation functions (indicators, metrics, scoring)
- For data transformations
- For validation logic

**Example:**

```python
# Test BEFORE implementation

def test_calculate_sharpe_ratio():
    """Test Sharpe ratio calculation."""
    returns = pd.Series([0.01, 0.02, -0.01, 0.03, 0.00])

    sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.0)

    assert sharpe > 0
    assert 0 < sharpe < 10  # Reasonable range

def test_calculate_sharpe_ratio_zero_std():
    """Test Sharpe with zero standard deviation."""
    returns = pd.Series([0.0, 0.0, 0.0, 0.0])

    sharpe = calculate_sharpe_ratio(returns)

    assert sharpe == 0.0  # Should handle gracefully

# NOW implement calculate_sharpe_ratio()
```

### 2. Integration Tests (30% of tests)

**What:** Test multiple components working together

**When to write:**
- Before implementing component integrations
- For API integrations (GitHub, Reddit, Binance)
- For LLM + Validator pipeline
- For Backtest → Metrics calculation

**Example:**

```python
# Test BEFORE integration

@pytest.mark.integration
def test_llm_to_validator_pipeline():
    """Test LLM generation → validation flow."""
    # Setup
    llm_client = LocalLLMClient()
    validator = PyneCoreValidator()

    # Generate strategy
    context = PromptContext(
        strategy_type="momentum",
        market_focus="spot_crypto"
    )

    result = llm_client.generate_strategy(context)

    # Validate
    validation = validator.validate(result.code)

    # Assertions
    assert result.success
    assert validation.is_valid
    assert validation.syntax_errors == []

# NOW implement integration
```

### 3. End-to-End Tests (10% of tests)

**What:** Test complete user workflows

**When to write:**
- Before implementing major features
- For critical business flows (strategy generation → validation → paper trading)

**Example:**

```python
@pytest.mark.e2e
def test_full_strategy_generation_pipeline():
    """Test complete pipeline from directive to live-ready strategy."""

    # 1. Create evolution directive
    directive = EvolutionDirective(
        strategy_type=MetaStrategyType.MOMENTUM,
        market_focus=MarketFocus.SPOT_CRYPTO,
        performance_targets={'min_sharpe': 2.0}
    )

    # 2. Load web examples
    knowledge_base = StrategyKnowledgeBase()
    examples = knowledge_base.find_similar(directive.strategy_type, limit=5)
    assert len(examples) > 0

    # 3. Generate strategy
    orchestrator = IntelligentOrchestrator(llm_client, meta_config)
    strategy = orchestrator.generate_intelligent_strategy(directive)
    assert strategy is not None

    # 4. Validate
    validator = LiveTradingValidator()
    result = validator.validate_strategy_for_live_trading(
        strategy.pyne_code,
        backtest_data,
        directive.strategy_type,
        directive.market_focus
    )

    # 5. Assert live readiness
    assert result['is_live_trading_ready']
    assert result['metrics'].live_trading_score >= 70

# NOW implement full pipeline
```

---

## TDD Workflow by Component

### Component 1: Web Crawler

**Test Order:**

```python
# tests/test_web_crawler.py

# 1. Test data models first
def test_strategy_knowledge_creation():
    """Can we create a StrategyKnowledge object?"""
    # Write test
    # Run test (RED)
    # Implement StrategyKnowledge dataclass
    # Run test (GREEN)
    pass

# 2. Test quality scoring
def test_quality_scorer_github_strategy():
    """Does quality scorer work for GitHub strategies?"""
    # Write test
    # Run test (RED)
    # Implement _score_source() method
    # Run test (GREEN)
    pass

# 3. Test GitHub API interaction (mock first)
@pytest.mark.unit
def test_github_crawler_search_mock():
    """Does GitHub search work with mocked API?"""
    # Write test with mocked requests
    # Run test (RED)
    # Implement search_strategies()
    # Run test (GREEN)
    pass

# 4. Test real GitHub API (integration)
@pytest.mark.integration
def test_github_crawler_search_real():
    """Does GitHub search work with real API?"""
    # Write test
    # Run test (RED)
    # Fix any issues
    # Run test (GREEN)
    pass

# 5. Test full extraction pipeline
@pytest.mark.integration
def test_extract_and_score_strategy():
    """Can we extract, parse, and score a real strategy?"""
    # Write test
    # Run test (RED)
    # Implement full pipeline
    # Run test (GREEN)
    pass
```

**Implementation Order:**
1. Write test_strategy_knowledge_creation → FAIL
2. Implement StrategyKnowledge → PASS
3. Write test_quality_scorer_github_strategy → FAIL
4. Implement StrategyQualityScorer._score_source → PASS
5. Continue...

### Component 2: Intelligent Prompts

**Test Order:**

```python
# tests/test_intelligent_prompts.py

# 1. Test prompt context creation
def test_prompt_context_creation():
    context = PromptContext(
        strategy_type=StrategyType.MOMENTUM,
        market_focus="spot_crypto",
        timeframe="1h"
    )
    assert context.strategy_type == StrategyType.MOMENTUM

# 2. Test system prompt generation
def test_build_system_prompt():
    builder = IntelligentPromptBuilder(knowledge_base=None)
    system = builder._build_system_prompt()

    assert "expert" in system.lower()
    assert "trading" in system.lower()
    assert len(system) > 100

# 3. Test requirements section
def test_build_requirements_section():
    context = PromptContext(
        strategy_type=StrategyType.MOMENTUM,
        market_focus="spot_crypto",
        timeframe="1h",
        target_sharpe=2.0
    )

    builder = IntelligentPromptBuilder(knowledge_base=None)
    requirements = builder._build_requirements_section(context)

    assert "momentum" in requirements.lower()
    assert "2.0" in requirements
    assert "sharpe" in requirements.lower()

# 4. Test pattern analysis
def test_analyze_patterns():
    examples = [create_mock_strategy() for _ in range(5)]

    builder = IntelligentPromptBuilder(knowledge_base=None)
    patterns = builder._analyze_patterns(examples)

    assert "Common Indicators" in patterns
    assert "Average Performance" in patterns

# 5. Test full prompt construction
def test_build_complete_prompt():
    context = PromptContext(
        strategy_type=StrategyType.MOMENTUM,
        market_focus="spot_crypto",
        timeframe="1h",
        example_strategies=[create_mock_strategy() for _ in range(3)]
    )

    builder = IntelligentPromptBuilder(knowledge_base=None)
    prompt = builder.build_generation_prompt(context)

    # Check all sections present
    assert "TASK:" in prompt
    assert "REQUIREMENTS" in prompt
    assert "EXAMPLES" in prompt
    assert "GUIDELINES" in prompt
    assert "@script.indicator" in prompt
```

### Component 3: Production Validator

**Test Order:**

```python
# tests/test_production_validator.py

# 1. Test metric calculations with synthetic data
def test_calculate_sharpe_ratio():
    trades = create_synthetic_trades(
        returns=[0.01, 0.02, -0.01, 0.03],
        win_rate=0.50
    )

    validator = LiveTradingValidator()
    sharpe = validator._calculate_sharpe_ratio(trades)

    assert sharpe > 0
    assert sharpe < 10  # Reasonable range

# 2. Test drawdown calculation
def test_calculate_max_drawdown():
    equity_curve = pd.Series([100, 110, 105, 95, 100, 115])

    validator = LiveTradingValidator()
    dd = validator._calculate_max_drawdown(equity_curve)

    assert dd > 0
    assert dd < 1.0  # Should be fraction
    expected = (110 - 95) / 110  # ~13.6%
    assert abs(dd - expected) < 0.01

# 3. Test scoring formula
def test_calculate_live_trading_score():
    metrics = LiveTradingMetrics(
        sharpe_ratio=2.5,
        max_drawdown=0.12,
        win_rate=0.55,
        total_return=0.30,
        monthly_volatility=0.08,
        signals_per_day=12,
        avg_slippage=0.003,
        fill_rate=0.96,
        avg_latency_ms=250
    )

    validator = LiveTradingValidator()
    score = validator.calculate_live_trading_score(metrics)

    assert 0 <= score <= 100
    assert score >= 80  # Should be high for these metrics

# 4. Test validation with real backtest data
@pytest.mark.integration
def test_validate_real_strategy():
    # Load real backtest results
    backtest_results = load_real_backtest()

    validator = LiveTradingValidator()
    result = validator.validate_strategy_for_live_trading(
        strategy_code="...",
        backtest_data=backtest_results,
        strategy_type=MetaStrategyType.MOMENTUM,
        market_focus=MarketFocus.SPOT_CRYPTO
    )

    assert 'metrics' in result
    assert 'is_live_trading_ready' in result
    assert isinstance(result['metrics'].live_trading_score, float)
```

---

## Test Utilities & Fixtures

### Shared Fixtures

```python
# tests/conftest.py

import pytest
import pandas as pd
from exhaustionlab.app.meta_evolution.knowledge_base import *


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    data = pd.DataFrame({
        'ts_open': dates,
        'open': 100 + np.random.randn(100).cumsum(),
        'high': 102 + np.random.randn(100).cumsum(),
        'low': 98 + np.random.randn(100).cumsum(),
        'close': 100 + np.random.randn(100).cumsum(),
        'volume': np.random.randint(1000, 10000, 100)
    })
    return data


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing without API calls."""
    class MockLLMClient:
        def generate(self, prompt, **kwargs):
            return {
                'choices': [{
                    'message': {
                        'content': MOCK_STRATEGY_CODE
                    }
                }]
            }

        def test_connection(self):
            return True

    return MockLLMClient()


@pytest.fixture
def sample_strategy_knowledge():
    """Create sample strategy knowledge for testing."""
    return StrategyKnowledge(
        id="test-123",
        name="Test Momentum Strategy",
        category=StrategyType.MOMENTUM,
        source=StrategySource(
            platform=SourcePlatform.GITHUB,
            url="https://github.com/test/strategy",
            author="testuser",
            title="Test Strategy",
            description="A test strategy",
            github_stars=100
        ),
        code=StrategyCode(
            pyne_core=MOCK_STRATEGY_CODE,
            lines_of_code=150,
            complexity_score=0.5,
            has_risk_management=True
        ),
        backtest_metrics=BacktestMetrics(
            sharpe_ratio=2.5,
            max_drawdown=0.12,
            win_rate=0.55,
            profit_factor=2.3
        ),
        quality_score=85.0
    )


# Mock strategy code
MOCK_STRATEGY_CODE = '''
"""@pyne"""
from pynecore import input, plot, color, script, Series

@script.indicator(title="Test Strategy", overlay=True)
def main():
    length = input.int("Length", 14)
    rsi = ta.rsi(close, length)

    buy_signal = rsi < 30
    sell_signal = rsi > 70

    plot(buy_signal ? close : na, "Buy", color=color.green)
    plot(sell_signal ? close : na, "Sell", color=color.red)
'''
```

---

## Coverage Requirements

### Minimum Coverage by Module

| Module | Target Coverage | Critical Functions Must Have |
|--------|----------------|------------------------------|
| knowledge_base.py | 90% | 100% |
| quality_scorer.py | 95% | 100% |
| intelligent_prompts.py | 85% | 100% |
| live_trading_validator.py | 90% | 100% |
| github_crawler.py | 70% | 90% |
| reddit_crawler.py | 70% | 90% |
| risk_manager.py | 95% | 100% |
| position_manager.py | 95% | 100% |

**Critical Functions:** Functions that handle money, calculate metrics, or make trading decisions.

### Running Coverage

```bash
# Run tests with coverage
poetry run pytest --cov=exhaustionlab --cov-report=html --cov-report=term

# View coverage report
open htmlcov/index.html

# Require minimum coverage
poetry run pytest --cov=exhaustionlab --cov-fail-under=80
```

---

## Test Execution Strategy

### Development Workflow

```bash
# 1. Watch mode during development (run tests on file change)
poetry run ptw -- tests/test_module.py -v

# 2. Fast feedback (skip slow integration tests)
poetry run pytest -m "not integration and not e2e"

# 3. Full suite before commit
poetry run pytest --cov=exhaustionlab --cov-fail-under=80

# 4. Integration tests before push
poetry run pytest -m integration

# 5. E2E tests before deployment
poetry run pytest -m e2e
```

### CI/CD Pipeline

```yaml
# .github/workflows/test.yml

name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Lint
        run: |
          poetry run black --check exhaustionlab/
          poetry run ruff check exhaustionlab/

      - name: Unit Tests
        run: |
          poetry run pytest tests/ -m "not integration and not e2e" --cov=exhaustionlab --cov-fail-under=80

      - name: Integration Tests
        run: |
          poetry run pytest tests/ -m integration

      - name: Upload Coverage
        uses: codecov/codecov-action@v2
        with:
          file: ./coverage.xml
```

---

## Property-Based Testing

For complex calculations, use hypothesis:

```python
from hypothesis import given, strategies as st

@given(
    returns=st.lists(
        st.floats(min_value=-0.1, max_value=0.1),
        min_size=10,
        max_size=1000
    )
)
def test_sharpe_ratio_properties(returns):
    """Test Sharpe ratio properties with random data."""
    returns_series = pd.Series(returns)

    sharpe = calculate_sharpe_ratio(returns_series)

    # Properties that should always hold
    assert isinstance(sharpe, float)
    assert -10 < sharpe < 10  # Reasonable range

    # If all returns positive, Sharpe should be positive
    if all(r > 0 for r in returns):
        assert sharpe > 0
```

---

## Mutation Testing

Verify test quality with mutation testing:

```bash
# Install
pip install mutmut

# Run mutation testing
mutmut run --paths-to-mutate=exhaustionlab/

# View results
mutmut results

# Show survived mutants (tests didn't catch them)
mutmut show

# Goal: 80%+ mutation score
```

---

## Mock vs Real Testing

### When to Mock

**Mock external services:**
- GitHub API (rate limits, costs)
- Reddit API (rate limits)
- LLM API (costs, latency)
- Binance API (in unit tests)

**Example:**

```python
@pytest.fixture
def mock_github_api(mocker):
    """Mock GitHub API responses."""
    mock_response = {
        'items': [{
            'name': 'test-strategy',
            'stargazers_count': 100,
            'html_url': 'https://github.com/test/strategy'
        }]
    }

    mocker.patch(
        'requests.Session.get',
        return_value=mocker.Mock(
            json=lambda: mock_response,
            status_code=200
        )
    )
```

### When to Use Real

**Use real services:**
- Integration tests (mark with `@pytest.mark.integration`)
- E2E tests
- Before production deployment

---

## Test Data Management

### Synthetic Data

```python
def create_realistic_ohlcv(
    start_price=100,
    num_bars=1000,
    volatility=0.02,
    trend=0.0001
):
    """Generate realistic OHLCV data."""
    prices = [start_price]
    for i in range(num_bars):
        # Geometric Brownian Motion
        change = np.random.normal(trend, volatility)
        prices.append(prices[-1] * (1 + change))

    closes = np.array(prices)
    highs = closes * (1 + abs(np.random.normal(0, 0.005, len(closes))))
    lows = closes * (1 - abs(np.random.normal(0, 0.005, len(closes))))
    opens = np.roll(closes, 1)

    return pd.DataFrame({
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': np.random.randint(1000, 10000, len(closes))
    })
```

### Real Data Snapshots

```python
# Store real data snapshots for deterministic testing
def load_test_snapshot(name: str) -> pd.DataFrame:
    """Load snapshot of real market data for testing."""
    path = Path(__file__).parent / "data" / "snapshots" / f"{name}.csv"
    return pd.read_csv(path)

# Create snapshots
def create_snapshot():
    """Create new snapshot of current market data."""
    from exhaustionlab.app.data.binance_rest import fetch_klines_csv_like

    data = fetch_klines_csv_like("BTCUSDT", "1h", limit=1000)
    data.to_csv("tests/data/snapshots/btc_2024.csv", index=False)
```

---

## Performance Testing

Test execution speed for time-sensitive operations:

```python
import time

def test_strategy_validation_performance():
    """Ensure validation completes within acceptable time."""
    validator = LiveTradingValidator()
    backtest_data = create_realistic_ohlcv(num_bars=10000)

    start = time.time()
    result = validator.validate_strategy_for_live_trading(
        strategy_code=MOCK_STRATEGY_CODE,
        backtest_data=backtest_data,
        strategy_type=MetaStrategyType.MOMENTUM,
        market_focus=MarketFocus.SPOT_CRYPTO
    )
    elapsed = time.time() - start

    assert elapsed < 60, f"Validation took {elapsed:.1f}s, should be <60s"
```

---

## Summary

**TDD Principles for ExhaustionLab:**

1. ✅ **Write tests first** - Define behavior before implementation
2. ✅ **Red-Green-Refactor** - Fail → Pass → Improve
3. ✅ **High coverage** - 80%+ overall, 100% for critical paths
4. ✅ **Fast feedback** - Unit tests run in <5s
5. ✅ **Integration confidence** - Full pipeline tested before deployment
6. ✅ **Mock external services** - Avoid costs and rate limits
7. ✅ **Test with real data** - Use snapshots for deterministic results
8. ✅ **Performance tests** - Ensure acceptable execution times

**Test before you code. Deploy with confidence. Protect the capital.**

---

*"Tests are the safety net. In trading, you can't afford to fall."*
