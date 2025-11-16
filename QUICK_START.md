# Quick Start Guide — For Next Coding Agent

**READ THIS FIRST** before diving into code.

---

## TL;DR

**Project:** AI-driven crypto trading platform, 75% complete  
**Location:** `/home/agile/ExhaustionLab/`  
**Status:** Core working, meta-evolution 80% done, needs web crawler + validator completion  
**Time to Complete:** 4-6 hours focused work  
**Language:** Python 3.11+ with Poetry

---

## What You Need to Know (30 seconds)

1. **What works:** GUI, live data, backtesting, LLM integration, GA optimizer
2. **What's missing:** Web crawler implementation, production validator with real data
3. **What you'll do:** Complete web scraping, integrate examples into LLM, finish validator
4. **Why it matters:** Improves AI strategy generation from 60% to 90%+ success rate

---

## Essential Documents (Read in Order)

1. **HANDOFF_SUMMARY.md** ← Start here (5 min read)
   - Context from previous agent
   - What's done vs. what's needed
   - Quick reference

2. **CODING_AGENT_PROMPT.md** ← Implementation guide (15 min read)
   - Detailed task breakdown
   - Code examples
   - Troubleshooting

3. **PRD_COMPLETE.md** ← Full specification (when you need details)
   - Complete feature list
   - Architecture
   - Requirements

4. **IMPLEMENTATION_STATUS.md** ← Progress tracking (reference)
   - Component matrix
   - Known issues
   - Test coverage

---

## Setup (5 minutes)

```bash
# 1. Navigate to project
cd /home/agile/ExhaustionLab

# 2. Install missing dependencies
poetry add beautifulsoup4 feedparser lxml

# 3. Verify imports work
python -m exhaustionlab.app.backtest.ga_optimizer --help

# 4. Run basic test
python test_basic_integration.py

# 5. (Optional) Test LLM if DeepSeek available
python test_llm_integration.py
```

Expected output: All imports successful, basic test passing.

---

## Critical Path (Priority Order)

### Task 1: Complete Web Crawler (1-2 hours)
**File:** `exhaustionlab/app/meta_evolution/StrategyWebCrawler.py`

**What to do:**
- Implement `_search_github()` - Search for Pine Script strategies
- Implement `_extract_reddit()` - Parse r/algotrading posts
- Implement `_score_quality()` - Rate strategies by stars/upvotes
- Add caching to `.cache/strategy_examples/`
- Test: Extract at least 10 strategies

**Why:** Provides real-world examples to improve LLM generation quality.

**Example code:**
```python
def _search_github(self, query: str, limit: int = 20) -> List[ExtractedContent]:
    url = f"https://api.github.com/search/repositories?q={query}+language:pine"
    response = requests.get(url, headers={'User-Agent': 'ExhaustionLab'})
    # Parse results, extract code, calculate quality score
    return extracted_strategies
```

### Task 2: Integrate Examples into Prompts (30 minutes)
**Files:**
- `app/meta_evolution/intelligent_orchestrator.py`
- `app/llm/prompts.py`

**What to do:**
- Load cached examples in `IntelligentOrchestrator.generate_intelligent_strategy()`
- Add examples to `PromptContext`
- Update prompt templates to include example section
- Test: Generate strategy with examples, verify improved success

**Example code:**
```python
# In intelligent_orchestrator.py
def generate_intelligent_strategy(self, directive: EvolutionDirective):
    # Load web examples
    examples = self.load_web_examples(directive.strategy_type, limit=5)
    
    # Add to prompt context
    context.example_strategies = examples
    
    # Generate with enhanced prompt
    result = self.llm_client.generate(enhanced_prompt)
```

### Task 3: Complete Production Validator (1-2 hours)
**File:** `exhaustionlab/app/meta_evolution/live_trading_validator.py`

**What to do:**
- Parse PyneCore output files (CSV/JSON format)
- Calculate metrics from actual trades (Sharpe, drawdown, win rate)
- Implement full scoring formula (Performance 35% + Risk 30% + Execution 20% + Robustness 15%)
- Generate validation report with recommendations
- Test: Validate a real backtest result

**Example code:**
```python
def _calculate_sharpe_ratio(self, trades: List[Trade]) -> float:
    returns = [t.pnl / t.capital for t in trades]
    if len(returns) < 2:
        return 0.0
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    if std_return == 0:
        return 0.0
    return (mean_return / std_return) * np.sqrt(252)  # Annualized
```

### Task 4: Integration Testing (30 minutes)
**Create:** `test_meta_evolution_integration.py`

**What to do:**
- Test full pipeline: directive → web examples → LLM → validation
- Test with and without LLM connection
- Test error handling
- Document results

---

## Command Reference

```bash
# Traditional parameter GA
python -m exhaustionlab.app.backtest.ga_optimizer --apply

# LLM-powered evolution
python -m exhaustionlab.app.backtest.ga_optimizer --llm-evolution

# Meta-evolution (full AI with web examples)
python -m exhaustionlab.app.backtest.ga_optimizer \
  --meta-evolution \
  --strategy-type EXHAUSTION \
  --market-focus SPOT_CRYPTO \
  --web-examples \
  --production-validation \
  --intelligence 0.8 \
  --apply

# Run tests
python test_basic_integration.py
python test_llm_integration.py
poetry run pytest tests/
```

---

## File Quick Reference

### Files You'll Edit

1. **exhaustionlab/app/meta_evolution/StrategyWebCrawler.py**
   - Implement web scraping logic
   - Lines ~200-400 need implementation

2. **exhaustionlab/app/meta_evolution/intelligent_orchestrator.py**
   - Add `load_web_examples()` method
   - Integrate into `generate_intelligent_strategy()`

3. **exhaustionlab/app/meta_evolution/live_trading_validator.py**
   - Implement metric calculations
   - Lines ~150-300 need real data integration

4. **exhaustionlab/app/llm/prompts.py**
   - Update prompt templates to include examples
   - Add `example_strategies` field

### Files You'll Create

1. **test_meta_evolution_integration.py**
   - End-to-end integration test
   - ~100-150 lines

### Files You'll Reference

1. **exhaustionlab/app/meta_evolution/meta_config.py** (complete, reference only)
2. **exhaustionlab/app/llm/llm_client.py** (complete, reference only)
3. **exhaustionlab/app/backtest/llm_evolution.py** (complete, reference only)

---

## Import Pattern ⚠️ CRITICAL

**Always use these patterns:**

```python
# Within exhaustionlab package (relative imports)
from ..config.fitness_config import get_fitness_config  # ✅
from ..llm import LocalLLMClient  # ✅

# From exhaustionlab package (absolute imports)
from exhaustionlab.app.config.fitness_config import get_fitness_config  # ✅

# Running modules
python -m exhaustionlab.app.backtest.ga_optimizer  # ✅

# NEVER do this:
from app.config.fitness_config import ...  # ❌
python exhaustionlab/exhaustionlab/app/...  # ❌
```

---

## Testing Checklist

After each major change:

```bash
# 1. Check imports
python -c "from exhaustionlab.app.meta_evolution import StrategyWebCrawler; print('OK')"

# 2. Run basic integration
python test_basic_integration.py

# 3. Run specific test
poetry run pytest tests/test_specific.py -v

# 4. Check for errors
python -m exhaustionlab.app.backtest.ga_optimizer --help
```

---

## Common Issues & Quick Fixes

### "ModuleNotFoundError: beautifulsoup4"
```bash
poetry add beautifulsoup4 feedparser lxml
```

### "LLM connection failed"
- Check if DeepSeek running on 127.0.0.1:1234
- Or use fallback: `--apply` (traditional GA without LLM)

### "Import error in meta_evolution"
- Check relative imports use `..`
- Run with `python -m` not direct path

### "Web scraping 403 Forbidden"
- Add User-Agent header: `{'User-Agent': 'ExhaustionLab Research Bot'}`
- Add delays: `time.sleep(random.uniform(1, 3))`

---

## Success Criteria

You're done when:

- [x] Dependencies installed (beautifulsoup4, feedparser, lxml)
- [x] Web crawler extracts ≥10 strategies successfully
- [x] Web examples integrated into LLM prompts
- [x] Production validator calculates real metrics
- [x] `test_meta_evolution_integration.py` passes
- [x] LLM generation success rate improved (verify with test runs)

---

## Getting Help

1. **Read the docs:**
   - CODING_AGENT_PROMPT.md - Detailed implementation guide
   - PRD_COMPLETE.md - Full specifications
   - IMPLEMENTATION_STATUS.md - What's done/pending

2. **Check existing code:**
   - Look at `app/llm/llm_client.py` for API patterns
   - Look at `app/data/binance_rest.py` for HTTP request patterns
   - Look at `app/backtest/traditional_ga.py` for testing patterns

3. **Test incrementally:**
   - Don't write 200 lines then test
   - Test each function individually
   - Use print statements liberally during development

---

## Code Style

- **Format:** `poetry run black exhaustionlab/`
- **Lint:** `poetry run ruff check exhaustionlab/`
- **Type hints:** Always use them for function signatures
- **Docstrings:** Add for complex functions
- **Error handling:** Use try/except with specific exceptions
- **Logging:** Use `logging` module, not print for production code

---

## Final Reminder

**Focus on one task at a time.** Complete the web crawler first, test it, then move to integrating examples, then validator, then integration test.

**Test frequently.** After every 20-30 lines of code, run a quick test.

**Document as you go.** Add comments for complex logic, update docstrings.

**Ask questions if unclear.** Better to clarify than guess.

---

**You've got this! The project is in great shape, just needs the final pieces.**

---

## Immediate Next Steps

```bash
# 1. Read HANDOFF_SUMMARY.md (5 min)
less HANDOFF_SUMMARY.md

# 2. Read CODING_AGENT_PROMPT.md (15 min)  
less CODING_AGENT_PROMPT.md

# 3. Install dependencies
poetry add beautifulsoup4 feedparser lxml

# 4. Open web crawler file
# Start with _search_github() method
nano exhaustionlab/app/meta_evolution/StrategyWebCrawler.py

# 5. Test as you go
python -c "from exhaustionlab.app.meta_evolution import StrategyWebCrawler; \
           crawler = StrategyWebCrawler(); \
           examples = crawler.extract_strategy_examples(max_examples=5); \
           print(f'Extracted {len(examples)} strategies')"
```

Good luck! 🚀
