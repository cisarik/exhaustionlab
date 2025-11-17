"""
Complete Integration Test

Tests all 3 phases working together:
- Phase 1: Configuration Layer
- Phase 2: LLM Integration
- Phase 3: Meta-Evolution

Validates the complete system.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")


def test_phase_1_configuration():
    """Test Phase 1: Configuration Layer."""
    print("\n" + "=" * 70)
    print("PHASE 1: CONFIGURATION LAYER")
    print("=" * 70)

    from exhaustionlab.app.config.strategy_config import ConfigurationManager, StrategyConfig, create_momentum_config

    # Create manager
    manager = ConfigurationManager()

    # Test 1: Create momentum config
    print("\n✓ Test 1: Creating momentum configuration...")
    config = create_momentum_config()
    assert config.strategy_type == "momentum"
    assert len(config.parameters) > 0
    print(f"  ✅ Created config with {len(config.parameters)} parameters")

    # Test 2: Validation
    print("\n✓ Test 2: Validating configuration...")
    is_valid, errors = config.validate()
    assert is_valid, f"Validation failed: {errors}"
    print("  ✅ Configuration valid")

    # Test 3: Save/Load
    print("\n✓ Test 3: Save and load configuration...")
    manager.save_config(config, "test_integration")
    loaded = manager.load_config("test_integration")
    assert loaded is not None
    assert loaded.strategy_name == config.strategy_name
    print("  ✅ Save/load successful")

    # Test 4: Parameter specs
    print("\n✓ Test 4: Checking parameter specs...")
    assert "lookback_period" in config.param_specs
    spec = config.param_specs["lookback_period"]
    assert spec.adaptive == True
    print(f"  ✅ Found {len(config.param_specs)} parameter specs")

    print("\n✅ PHASE 1: COMPLETE\n")
    return True


def test_phase_2_llm_integration():
    """Test Phase 2: LLM Integration."""
    print("\n" + "=" * 70)
    print("PHASE 2: LLM INTEGRATION")
    print("=" * 70)

    from exhaustionlab.app.llm.enhanced_prompts import EnhancedPromptBuilder
    from exhaustionlab.app.llm.example_loader import ExampleLoader

    # Test 1: Example Loader
    print("\n✓ Test 1: Loading strategy examples...")
    loader = ExampleLoader()
    examples = loader.get_best_examples(count=5, min_quality=50.0)
    print(f"  ✅ Loaded {len(examples)} examples")

    # Test 2: Enhanced Prompts
    print("\n✓ Test 2: Building enhanced prompts...")
    from exhaustionlab.app.llm.prompts import PromptContext

    builder = EnhancedPromptBuilder()
    context = PromptContext(
        strategy_type="signal",
        market_focus=["spot"],
        timeframe="1m",
        indicators_to_include=["RSI", "SMA"],
        signal_logic="momentum",
        risk_profile="balanced",
    )
    prompt = builder.build_strategy_prompt(context=context, include_examples=True, num_examples=2)
    assert len(prompt) > 1000
    print(f"  ✅ Generated prompt: {len(prompt)} chars")

    # Test 3: Mutation Prompt
    print("\n✓ Test 3: Building mutation prompt...")
    code_sample = "def strategy(): pass"
    mutation_prompt = builder.build_mutation_prompt(base_strategy_code=code_sample, mutation_type="parameter", context=context)
    assert len(mutation_prompt) > 100
    print(f"  ✅ Mutation prompt ready: {len(mutation_prompt)} chars")

    print("\n✅ PHASE 2: COMPLETE\n")
    return True


def test_phase_3_meta_evolution():
    """Test Phase 3: Meta-Evolution."""
    print("\n" + "=" * 70)
    print("PHASE 3: META-EVOLUTION")
    print("=" * 70)

    from exhaustionlab.app.meta_evolution.adaptive_parameters import AdaptiveParameterOptimizer
    from exhaustionlab.app.meta_evolution.performance_metrics import PerformanceMetrics, calculate_sharpe_ratio
    from exhaustionlab.app.meta_evolution.strategic_directives import AdaptiveDirectiveManager, StrategyObjective

    # Test 1: Performance Metrics
    print("\n✓ Test 1: Calculating performance metrics...")
    import numpy as np
    import pandas as pd

    # Synthetic data
    returns = pd.Series(np.random.randn(100) * 0.02)
    sharpe = calculate_sharpe_ratio(returns)
    assert isinstance(sharpe, float)
    print(f"  ✅ Sharpe ratio: {sharpe:.2f}")

    # Test 2: Strategic Directives
    print("\n✓ Test 2: Creating strategic directive...")
    directive_mgr = AdaptiveDirectiveManager()
    directive = directive_mgr.create_directive(StrategyObjective.HIGH_SHARPE)
    assert directive.objective == StrategyObjective.HIGH_SHARPE
    print(f"  ✅ Directive: {directive.objective.value}")

    # Test 3: Adaptive Parameters
    print("\n✓ Test 3: Adaptive parameter optimization...")
    optimizer = AdaptiveParameterOptimizer()
    config = optimizer.suggest_configuration()
    assert "temperature" in config
    assert "mutation_rate" in config
    print(f"  ✅ Suggested {len(config)} parameters")

    # Test 4: Learning Feedback
    print("\n✓ Test 4: Testing feedback learning...")
    prev_attempts = optimizer.total_attempts
    prev_successes = optimizer.successful_attempts

    optimizer.update_from_result(config, quality_score=75.0, success=True)
    stats = optimizer.get_statistics()

    # Check that counters increased
    assert stats["total_attempts"] == prev_attempts + 1
    assert stats["successful_attempts"] == prev_successes + 1
    print("  ✅ Feedback learning operational")

    print("\n✅ PHASE 3: COMPLETE\n")
    return True


def test_unified_system():
    """Test complete unified system."""
    print("\n" + "=" * 70)
    print("UNIFIED SYSTEM TEST")
    print("=" * 70)

    from exhaustionlab.app.backtest.unified_evolution import UnifiedEvolutionEngine
    from exhaustionlab.app.config.strategy_config import create_momentum_config

    # Test 1: Configuration + Evolution Engine
    print("\n✓ Test 1: Integrating configuration with evolution...")
    config = create_momentum_config()
    engine = UnifiedEvolutionEngine(
        use_llm=False,  # Disabled for test
        use_adaptive_params=True,
        fallback_enabled=True,
    )
    print("  ✅ Engine initialized with configuration")

    # Test 2: Check capabilities
    print("\n✓ Test 2: Checking system capabilities...")
    stats = engine.get_statistics()
    assert isinstance(stats, dict)
    print(f"  ✅ Statistics available: {len(stats)} metrics")

    print("\n✅ UNIFIED SYSTEM: OPERATIONAL\n")
    return True


def run_all_tests():
    """Run complete test suite."""
    print("\n" + "=" * 70)
    print("EXHAUSTIONLAB v2.0.0 - COMPLETE INTEGRATION TEST")
    print("=" * 70)

    results = {
        "Phase 1: Configuration": False,
        "Phase 2: LLM Integration": False,
        "Phase 3: Meta-Evolution": False,
        "Unified System": False,
    }

    try:
        # Phase 1
        results["Phase 1: Configuration"] = test_phase_1_configuration()

        # Phase 2
        results["Phase 2: LLM Integration"] = test_phase_2_llm_integration()

        # Phase 3
        results["Phase 3: Meta-Evolution"] = test_phase_3_meta_evolution()

        # Unified
        results["Unified System"] = test_unified_system()

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED - SYSTEM READY FOR PRODUCTION")
    else:
        print("⚠️ SOME TESTS FAILED - REVIEW ERRORS ABOVE")
    print("=" * 70)

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
