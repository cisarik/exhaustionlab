# ExhaustionLab Examples & Demo Scripts

This directory contains example scripts and integration tests for exploring ExhaustionLab features.

## 📚 Directory Structure

```
examples/
├── README.md                          # This file
├── debug_llm_*.py                     # LLM debugging tools
├── test_*_integration.py              # Integration test examples
├── test_*_generation.py               # Evolution generation examples
├── extract_*.py                       # Strategy extraction utilities
└── migrate_*.py                       # Database migration tools
```

## 🚀 Quick Start

### Run Examples
```bash
# From project root
cd examples/

# Run with Poetry
poetry run python test_basic_integration.py
poetry run python debug_llm_simple.py

# Or activate venv first
poetry shell
python test_chart_generation.py
```

## 📋 Script Descriptions

### LLM & Strategy Generation

#### `debug_llm_simple.py`
Basic LLM connectivity test with minimal configuration.
```bash
poetry run python examples/debug_llm_simple.py
```

#### `debug_llm_communication.py`
Advanced LLM debugging with detailed request/response logging.
```bash
poetry run python examples/debug_llm_communication.py
```

#### `test_llm_integration.py`
End-to-end LLM strategy generation test.
```bash
poetry run python examples/test_llm_integration.py
```

#### `test_llm_with_examples.py`
LLM generation with database-backed examples.
```bash
poetry run python examples/test_llm_with_examples.py
```

#### `test_improved_prompt.py`
Test enhanced prompt system with 10x larger prompts.
```bash
poetry run python examples/test_improved_prompt.py
```

---

### Evolution & Optimization

#### `test_meta_evolution.py`
Complete meta-evolution system test with adaptive parameters.
```bash
poetry run python examples/test_meta_evolution.py
```

#### `test_multiple_generations.py`
Multi-generation evolution with population tracking.
```bash
poetry run python examples/test_multiple_generations.py
```

---

### Integration Tests

#### `test_basic_integration.py`
Smoke test for core system integration.
```bash
poetry run python examples/test_basic_integration.py
```

#### `test_complete_integration.py`
Full system integration test (all components).
```bash
poetry run python examples/test_complete_integration.py
```

#### `test_chart_generation.py`
Chart rendering and visualization test.
```bash
poetry run python examples/test_chart_generation.py
```

#### `test_ui_startup.py`
PySide6 GUI startup and initialization test.
```bash
poetry run python examples/test_ui_startup.py
```

---

### Web Crawling & Extraction

#### `test_crawler_standalone.py`
Standalone web crawler test (GitHub/Reddit/TradingView).
```bash
poetry run python examples/test_crawler_standalone.py
```

#### `extract_strategies.py`
Extract strategies from knowledge base.
```bash
poetry run python examples/extract_strategies.py
```

#### `extract_full_strategies.py`
Extract strategies with full metadata.
```bash
poetry run python examples/extract_full_strategies.py
```

#### `extract_code_no_api.py`
Extract strategy code without API calls.
```bash
poetry run python examples/extract_code_no_api.py
```

---

### Validation & Deployment

#### `test_deployment_validation.py`
Test deployment readiness validation pipeline.
```bash
poetry run python examples/test_deployment_validation.py
```

---

### Database & Migration

#### `migrate_knowledge_base.py`
Migrate strategy knowledge base schema.
```bash
poetry run python examples/migrate_knowledge_base.py
```

---

## 🔧 Configuration

Most examples use environment variables from `.env`:

```bash
# Copy example config
cp .env.example .env

# Edit with your settings
nano .env
```

### Key Variables
```bash
# LLM Configuration
LLM_BASE_URL=http://127.0.0.1:1234/v1
LLM_MODEL=deepseek-r1-0528-qwen3-8b
LLM_TEMPERATURE=0.7

# Binance Configuration
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret

# Database
DB_PATH=~/.cache/exhaustionlab/strategies.db
```

## 📊 Expected Outputs

### LLM Tests
- ✅ Connection successful
- ✅ Strategy generated
- ✅ Code validation passed
- 📄 Output saved to `llm_test_outputs/`

### Evolution Tests
- ✅ Population initialized
- ✅ Generations completed
- ✅ Best strategy found
- 📊 Metrics: fitness, Sharpe, drawdown
- 📄 Results saved to `evolved_strategies/`

### Integration Tests
- ✅ All modules imported
- ✅ Core functionality working
- ✅ No critical errors

## 🐛 Troubleshooting

### LLM Connection Errors
```bash
# Check LLM server
curl http://127.0.0.1:1234/v1/models

# Fallback to offline mode (uses GA only)
export LLM_BASE_URL=""
```

### Import Errors
```bash
# Reinstall dependencies
poetry install --with dev

# Verify installation
poetry run python -c "import exhaustionlab; print('OK')"
```

### Database Errors
```bash
# Reset database
rm -f ~/.cache/exhaustionlab/strategies.db
poetry run python examples/migrate_knowledge_base.py
```

## 🧪 Running All Examples

```bash
# Run all examples sequentially
for script in examples/test_*.py; do
    echo "Running $script..."
    poetry run python "$script" || echo "Failed: $script"
done
```

## 📝 Contributing

When adding new examples:

1. **Name convention**: `{category}_{feature}.py`
   - `test_*` - Integration/feature tests
   - `debug_*` - Debugging tools
   - `extract_*` - Data extraction tools
   - `migrate_*` - Database migrations

2. **Documentation**: Add docstring with:
   ```python
   """
   Brief description of what this example demonstrates.

   Usage:
       poetry run python examples/your_script.py

   Expected output:
       - What the user should see
       - Where results are saved
   """
   ```

3. **Update this README**: Add entry in appropriate section

4. **Error handling**: Always use try/except with informative messages

5. **Cleanup**: Remove temporary files on exit

## 🔗 Related Documentation

- [Main README](../README.md) - Project overview
- [AGENTS.md](../AGENTS.md) - Architecture guide
- [CI_CD_SETUP.md](../CI_CD_SETUP.md) - Testing & CI/CD
- [LLM_INTEGRATION_GUIDE.md](../LLM_INTEGRATION_GUIDE.md) - LLM usage
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Production deployment

---

**Note**: These are examples and development tools. For production usage, see the main [DEPLOYMENT.md](../DEPLOYMENT.md) guide.
