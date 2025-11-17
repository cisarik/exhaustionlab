# Comprehensive Coding Agent Prompt — ExhaustionLab Meta-Evolution

## Context & Background

You are continuing work on **ExhaustionLab**, an AI-driven cryptocurrency trading platform. The previous coding agent's context window got full and output became garbled. This document provides complete context to continue the implementation.

### Project Overview

ExhaustionLab is a **production-grade trading platform** that combines:
1. **GUI**: TradingView-style interface (PySide6 + PyQtGraph)
2. **Live Data**: Binance REST/WebSocket streaming
3. **Backtesting**: PyneCore integration for Pine Script strategies
4. **AI Evolution**: LLM-powered strategy generation using DeepSeek
5. **Production Validation**: Institutional-grade live trading readiness assessment

**Project Location:** `/home/agile/ExhaustionLab/`

**Key Files:**
- Main entry: `exhaustionlab/app/backtest/ga_optimizer.py`
- LLM integration: `exhaustionlab/app/llm/`
- Meta-evolution: `exhaustionlab/app/meta_evolution/`
- Config: `exhaustionlab/app/config/`

---

## What's Already Working ✅

### 1. Core Infrastructure (100% Complete)
- ✅ PySide6 + PyQtGraph GUI with candlestick charts
- ✅ Binance REST API for historical data
- ✅ Binance WebSocket for real-time streaming
- ✅ Multi-panel layout (candles, indicators, volume)
- ✅ Signal overlays (L1/L2/L3 exhaustion markers)

### 2. Traditional Optimization (100% Complete)
- ✅ Genetic Algorithm for parameter optimization
- ✅ PyneCore CLI integration
- ✅ Fitness function framework
- ✅ Parameter persistence (`squeeze_params.json`)

### 3. LLM Integration (80% Complete)
- ✅ DeepSeek API client (`app/llm/llm_client.py`)
- ✅ Prompt engineering framework (`app/llm/prompts.py`)
- ✅ Code generation pipeline (`app/llm/strategy_generator.py`)
- ✅ Multi-layer validation (`app/llm/validators.py`)
- ⚠️ Generation quality needs improvement (~60% success rate)
- ⚠️ Web examples not yet integrated into prompts

### 4. Meta-Evolution Framework (80% Complete)
- ✅ Configuration management (`app/meta_evolution/meta_config.py`)
- ✅ Strategic directive system (`app/meta_evolution/intelligent_orchestrator.py`)
- ✅ Web crawler framework (`app/meta_evolution/StrategyWebCrawler.py`)
- ✅ Production validator structure (`app/meta_evolution/live_trading_validator.py`)
- ⚠️ Web scraping dependencies not installed (beautifulsoup4, feedparser)
- ⚠️ Needs integration testing
- ⚠️ Validator needs real backtest data integration

---

## What Needs to Be Completed 🚧

### Priority 1: Fix Dependencies & Import Issues

**Problem:** Missing dependencies, import path confusion

**Tasks:**
1. Install web scraping dependencies:
   ```bash
   cd /home/agile/ExhaustionLab
   poetry add beautifulsoup4 feedparser lxml
   ```

2. Fix any import path issues in `app/meta_evolution/`:
   - Use relative imports within the package
   - Verify all imports work with `python -m exhaustionlab.app.backtest.ga_optimizer --help`

3. Run basic integration test:
   ```bash
   python test_basic_integration.py
   ```

### Priority 2: Complete Web Crawler Implementation

**File:** `exhaustionlab/app/meta_evolution/StrategyWebCrawler.py`

**Current State:** Framework exists but needs actual extraction logic

**Tasks:**
1. Implement GitHub strategy search:
   - Search for Pine Script strategies in GitHub repositories
   - Look for keywords: "trading strategy", "pine script", "cryptocurrency"
   - Extract code, documentation, and metadata
   - Parse README files for performance metrics

2. Implement Reddit extraction:
   - Search r/algotrading, r/cryptocurrency, r/TradingView
   - Look for strategy discussions and code snippets
   - Extract upvoted strategies with community validation

3. Implement TradingView scraping (if legally permissible):
   - Extract popular published strategies
   - Parse strategy descriptions and parameters
   - Respect rate limits and terms of service

4. Add quality scoring:
   - GitHub stars/forks as quality indicator
   - Reddit upvotes/comments as community validation
   - Code complexity analysis (not too simple, not too complex)
   - Performance metrics if available

5. Implement caching:
   - Save extracted strategies to `.cache/strategy_examples/`
   - Use JSON format for easy loading
   - Add timestamp and source metadata
   - Implement cache expiration (7 days)

**Example Structure:**
```python
@dataclass
class ExtractedStrategy:
    source: str  # "github", "reddit", "tradingview"
    url: str
    title: str
    code: str
    description: str
    quality_score: float  # 0.0-1.0
    metadata: Dict[str, Any]
    extracted_at: datetime
```

### Priority 3: Integrate Web Examples into LLM Prompts

**Files:**
- `exhaustionlab/app/llm/prompts.py`
- `exhaustionlab/app/meta_evolution/intelligent_orchestrator.py`

**Tasks:**
1. Load cached strategy examples in orchestrator:
   ```python
   def load_web_examples(self, strategy_type: MetaStrategyType, limit: int = 5):
       """Load top quality examples for given strategy type."""
       cache_path = Path(".cache/strategy_examples/")
       # Load, filter by strategy_type, sort by quality_score, take top N
       return examples
   ```

2. Inject examples into prompt context:
   - Add `example_strategies` field to `PromptContext`
   - Format examples as part of system prompt
   - Include code snippets and descriptions
   - Emphasize successful patterns

3. Test generation improvement:
   - Run generation with vs without web examples
   - Measure success rate improvement
   - Validate strategy quality

### Priority 4: Complete Production Validator with Real Data

**File:** `exhaustionlab/app/meta_evolution/live_trading_validator.py`

**Current State:** Validation framework exists but uses synthetic data

**Tasks:**
1. Integrate with PyneCore backtest results:
   - Parse PyneCore output files
   - Extract all trades with timestamps, prices, PnL
   - Calculate metrics from real trade data

2. Implement all metric calculations:
   - Sharpe ratio (using actual returns)
   - Maximum drawdown (from equity curve)
   - Win rate (winning trades / total trades)
   - Consistency (monthly return volatility)
   - Recovery time (days to recover from drawdowns)

3. Add execution quality estimation:
   - Estimate slippage based on signal frequency and market liquidity
   - Calculate latency requirements
   - Assess fill probability

4. Implement live trading score calculation:
   - Weight metrics according to PRD spec (Performance 35%, Risk 30%, Execution 20%, Robustness 15%)
   - Return score 0-100
   - Generate detailed report with recommendations

5. Create validation report generator:
   - Save results to JSON
   - Generate human-readable summary
   - Include visualizations (equity curve, drawdown chart)
   - List issues and recommendations

### Priority 5: End-to-End Integration Test

**Create:** `test_meta_evolution_integration.py`

**Test Scenarios:**
1. **Basic Pipeline Test:**
   ```python
   def test_full_pipeline():
       # 1. Create evolution directive
       # 2. Load web examples
       # 3. Generate prompt
       # 4. Call LLM
       # 5. Validate code
       # 6. Run backtest (synthetic data OK for test)
       # 7. Calculate live trading score
       # 8. Verify score > 0
   ```

2. **Web Crawler Test:**
   ```python
   def test_web_crawler():
       crawler = StrategyWebCrawler()
       examples = crawler.extract_strategy_examples(max_examples=5)
       assert len(examples) > 0
       assert all(ex.quality_score > 0 for ex in examples)
   ```

3. **LLM Generation with Context:**
   ```python
   def test_llm_with_web_context():
       # Load web examples
       # Generate strategy with examples in context
       # Verify improved success rate
   ```

4. **Production Validation:**
   ```python
   def test_production_validator():
       # Create synthetic backtest results
       # Run validator
       # Verify score calculation
       # Check that issues are identified
   ```

---

## Command Reference

### Running GA Optimizer

**Traditional Parameter GA:**
```bash
cd /home/agile/ExhaustionLab
python -m exhaustionlab.app.backtest.ga_optimizer \
  --symbol ADAEUR \
  --interval 1m \
  --limit 1500 \
  --population 12 \
  --generations 8 \
  --apply
```

**LLM-Powered Evolution:**
```bash
python -m exhaustionlab.app.backtest.ga_optimizer \
  --llm-evolution \
  --population-size 6 \
  --generations 8 \
  --fitness-preset BALANCED_DEMO
```

**Meta-Evolution (Full AI):**
```bash
python -m exhaustionlab.app.backtest.ga_optimizer \
  --meta-evolution \
  --strategy-type EXHAUSTION \
  --market-focus SPOT_CRYPTO \
  --evolution-intensity BALANCED \
  --intelligence 0.8 \
  --web-examples \
  --production-validation \
  --apply
```

### Testing Commands

```bash
# Basic integration test
python test_basic_integration.py

# LLM integration test (requires DeepSeek server)
python test_llm_integration.py

# Check imports
python -m exhaustionlab.app.backtest.ga_optimizer --help

# Run pytest
poetry run pytest tests/
```

### Poetry Commands

```bash
# Install dependencies
poetry install

# Add new dependency
poetry add <package>

# Show installed packages
poetry show

# Activate virtual environment
poetry shell
```

---

## Important Implementation Notes

### 1. Import Path Issues

**CRITICAL:** Previous agent had issues with double paths like:
- ❌ `/home/agile/ExhaustionLab/exhaustionlab/exhaustionlab/app/...`
- ✅ `/home/agile/ExhaustionLab/exhaustionlab/app/...`

**Solution:**
- Always use relative imports within `exhaustionlab` package
- Run modules with `python -m exhaustionlab.app.module_name`
- Base directory is `/home/agile/ExhaustionLab`

**Example:**
```python
# In exhaustionlab/app/backtest/ga_optimizer.py
from ..config.fitness_config import get_fitness_config  # ✅ Correct
from exhaustionlab.app.config.fitness_config import get_fitness_config  # ✅ Also OK
from app.config.fitness_config import get_fitness_config  # ❌ Wrong
```

### 2. LLM Client Usage

**Check Connection First:**
```python
from exhaustionlab.app.llm import LocalLLMClient

client = LocalLLMClient()
if not client.test_connection():
    print("LLM not available, using fallback")
    # Use parameter-based GA or other fallback
```

**Error Handling:**
```python
try:
    result = generator.generate_strategy(request)
    if result.success:
        # Use generated code
    else:
        # Handle generation failure
        print(f"Generation failed: {result.error_message}")
except Exception as e:
    # Handle connection errors, timeouts, etc.
    print(f"LLM error: {e}")
```

### 3. Web Scraping Best Practices

**Rate Limiting:**
```python
import time
import random

def scrape_with_rate_limit(urls):
    for url in urls:
        # Random delay 1-3 seconds
        time.sleep(random.uniform(1, 3))
        # Make request
        response = requests.get(url, timeout=10)
        # Process response
```

**Respect robots.txt:**
```python
from urllib.robotparser import RobotFileParser

def can_fetch(url):
    rp = RobotFileParser()
    rp.set_url(url + "/robots.txt")
    rp.read()
    return rp.can_fetch("*", url)
```

**Error Handling:**
```python
def safe_extract(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return parse_content(response.text)
    except requests.RequestException as e:
        print(f"Failed to fetch {url}: {e}")
        return None
```

### 4. Testing Strategy

**Run Tests in This Order:**
1. Import tests: `python -m exhaustionlab.app.backtest.ga_optimizer --help`
2. Basic integration: `python test_basic_integration.py`
3. LLM integration: `python test_llm_integration.py` (if DeepSeek available)
4. Meta-evolution integration: `python test_meta_evolution_integration.py`
5. Full pytest suite: `poetry run pytest`

**Mock LLM for Tests:**
```python
class MockLLMClient:
    def test_connection(self):
        return True

    def complete(self, messages, **kwargs):
        # Return mock Pine Script code
        return {"choices": [{"message": {"content": MOCK_CODE}}]}
```

---

## Success Criteria

### Immediate Goals (This Session)

1. ✅ Install missing dependencies (beautifulsoup4, feedparser)
2. ✅ Fix any import errors in meta_evolution modules
3. ✅ Implement basic GitHub strategy search (even if just 1-2 examples)
4. ✅ Integrate web examples into LLM prompts
5. ✅ Test end-to-end meta-evolution pipeline

### Quality Metrics

- **LLM Generation Success Rate:** Target 80%+ (currently ~60%)
- **Web Extraction:** At least 10 quality examples per strategy type
- **Production Validation:** Working score calculation with real metrics
- **Integration Tests:** All tests passing

### Deliverables

1. **Updated Code:**
   - Fully functional web crawler
   - Integrated web examples in prompts
   - Complete production validator
   - Integration test suite

2. **Documentation:**
   - Updated PRD.md (already done)
   - Implementation notes
   - Known issues documented

3. **Test Results:**
   - Integration test passing
   - Evidence of improved generation quality
   - Example generated strategies saved

---

## Code Style & Standards

### Formatting
- Use **Black** for formatting: `poetry run black exhaustionlab/`
- Use **Ruff** for linting: `poetry run ruff check exhaustionlab/`
- Follow **PEP 8** conventions

### Type Hints
```python
def process_strategy(
    genome: StrategyGenome,
    config: MetaevolutionConfig
) -> Optional[ValidationResult]:
    """Process strategy with full type hints."""
    ...
```

### Documentation
```python
def complex_function(param1: str, param2: int) -> Dict[str, Any]:
    """
    Brief description of function.

    Longer explanation if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Dictionary with results

    Raises:
        ValueError: When invalid params provided

    Examples:
        >>> result = complex_function("test", 42)
        >>> result['status']
        'success'
    """
    ...
```

### Error Handling
```python
# Specific exceptions
try:
    result = risky_operation()
except ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    return fallback_result()
except ValueError as e:
    logger.error(f"Invalid value: {e}")
    raise
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return None
```

### Logging
```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

---

## Troubleshooting Guide

### Issue: Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'exhaustionlab'`

**Solution:**
```bash
cd /home/agile/ExhaustionLab
poetry install
poetry run python -m exhaustionlab.app.backtest.ga_optimizer --help
```

### Issue: LLM Connection Failed

**Symptom:** `Connection refused on 127.0.0.1:1234`

**Solution:**
1. Check if DeepSeek server is running
2. Use fallback to traditional GA:
   ```bash
   python -m exhaustionlab.app.backtest.ga_optimizer --apply
   ```

### Issue: Web Scraping Blocked

**Symptom:** `403 Forbidden` or `429 Too Many Requests`

**Solution:**
1. Add user agent header:
   ```python
   headers = {'User-Agent': 'ExhaustionLab Strategy Research Bot'}
   ```
2. Increase delays between requests
3. Use caching to avoid repeated requests

### Issue: Production Validator Fails

**Symptom:** `KeyError` or missing backtest data

**Solution:**
1. Verify PyneCore output format
2. Use synthetic data for testing:
   ```python
   synthetic_results = create_test_backtest_results()
   validator.validate_strategy_for_live_trading(code, synthetic_results, ...)
   ```

---

## Architecture Diagram

```
User
  ↓
Main GUI (main_window.py)
  ↓
GA Optimizer (ga_optimizer.py) ← CLI Entry Point
  ↓
  ├─→ Traditional GA (traditional_ga.py)
  ├─→ LLM Evolution (llm_evolution.py)
  │     ↓
  │   LLM Client (llm/llm_client.py) → DeepSeek API
  │     ↓
  │   Strategy Generator (llm/strategy_generator.py)
  │     ↓
  │   Validator (llm/validators.py)
  │
  └─→ Meta-Evolution (meta_evolution/)
        ↓
      Intelligent Orchestrator (intelligent_orchestrator.py)
        ↓
      ├─→ Web Crawler (StrategyWebCrawler.py) → GitHub/Reddit/TradingView
      ├─→ Prompt Engine (llm/prompts.py)
      └─→ Live Trading Validator (live_trading_validator.py)
            ↓
          PyneCore Backtest (engine.py) → PyneCore CLI
            ↓
          Strategy Registry (strategy_registry.py)
```

---

## Final Notes

### What the Previous Agent Was Trying to Do

The previous agent was working on completing the meta-evolution framework. They:
1. ✅ Created the configuration system
2. ✅ Implemented intelligent orchestrator
3. ✅ Built web crawler framework
4. ✅ Created production validator structure
5. ⚠️ Started integration but context window filled up
6. ⚠️ Output became garbled with mixing languages and broken syntax

### Key Lessons Learned

1. **Import paths are tricky** - stick to relative imports within package
2. **LLM needs fallbacks** - always have parameter-based GA as backup
3. **Web scraping needs care** - rate limiting, error handling, caching
4. **Test incrementally** - don't try to test everything at once
5. **Documentation is critical** - especially for complex integrations

### Your Mission

Complete the meta-evolution framework by:
1. Installing dependencies
2. Implementing web crawler extraction logic
3. Integrating web examples into LLM prompts
4. Completing production validator with real data
5. Writing comprehensive integration tests
6. Documenting everything

**Good luck! The codebase is in good shape, just needs the final pieces connected.**

---

## Quick Start Checklist

- [ ] Read this entire document
- [ ] Read PRD_COMPLETE.md
- [ ] Check current directory: `pwd` should be `/home/agile/ExhaustionLab`
- [ ] Install dependencies: `poetry add beautifulsoup4 feedparser lxml`
- [ ] Run import test: `python -m exhaustionlab.app.backtest.ga_optimizer --help`
- [ ] Run basic test: `python test_basic_integration.py`
- [ ] Pick a Priority 1 or 2 task and start coding
- [ ] Test your changes incrementally
- [ ] Document any issues or decisions
- [ ] Commit when a logical unit is complete

**Remember:** Focus on one task at a time. Test frequently. Document as you go.
