#!/usr/bin/env python3
"""
Test script for LLM integration with local DeepSeek API

Demonstrates PyneCore strategy generation and mutation using local LLM.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "exhaustionlab"))

from exhaustionlab.app.llm import LocalLLMClient, LLMStrategyGenerator, PromptContext
from exhaustionlab.app.llm.validators import PyneCoreValidator


def test_llm_connection():
    """Test basic LLM connection."""
    print("🔌 Testing LLM connection...")

    client = LocalLLMClient()

    if client.test_connection():
        print("✅ LLM connection successful!")
        print(f"📊 Client stats: {client.get_stats()}")
        return True
    else:
        print("❌ LLM connection failed!")
        return False


def test_simple_generation():
    """Test basic strategy generation."""
    print("\n🧪 Testing strategy generation...")

    client = LocalLLMClient()
    validator = PyneCoreValidator()

    if not client.test_connection():
        print("❌ Cannot test generation - LLM not available")
        return False

    # Create test context
    context = PromptContext(
        strategy_type="signal",
        market_focus=["spot"],
        timeframe="1m",
        indicators_to_include=["RSI", "SMA"],
        signal_logic="mean_reversion",
        risk_profile="balanced",
    )

    # Generate request
    generator = LLMStrategyGenerator(client)
    gen_request = generator.create_signal_strategy(
        "mean_reversion", "balanced", context
    )

    # Generate strategy
    result = generator.generate_strategy(gen_request)

    if result.success:
        print("✅ Strategy generation successful!")
        print(f"⏱️ Generation time: {result.generation_time:.2f}s")
        print(f"📝 Attempts: {result.attempts_made}")
        print("\n📄 Generated code snippet:")
        print("=" * 50)
        lines = result.generated_code.split("\n")[:20]  # First 20 lines
        for i, line in enumerate(lines, 1):
            print(f"{i:2d}: {line}")
        print("=" * 50)
        print(f"... ({len(result.generated_code.split())} more lines)")

        print(f"\n🔍 Validation: {result.validation_result.is_valid}")
        if result.validation_result.issues:
            print("⚠️ Validation issues:")
            for issue in result.validation_result.issues[:3]:
                print(f"   - {issue.message}")

        # Save generated strategy
        output_dir = "llm_test_outputs"
        os.makedirs(output_dir, exist_ok=True)

        with open(f"{output_dir}/test_strategy.py", "w") as f:
            f.write(result.generated_code)

        print(f"💾 Strategy saved to: {output_dir}/test_strategy.py")
        return True

    else:
        print("❌ Strategy generation failed!")
        print(f"🚫 Error: {result.error_message}")

        if result.validation_result and result.validation_result.issues:
            print("🔍 Validation failures:")
            for issue in result.validation_result.issues:
                if issue.severity == "error":
                    print(f"   🛑 {issue.message}")
                    if issue.suggestion:
                        print(f"      💡 {issue.suggestion}")

        return False


def test_mutation():
    """Test strategy mutation."""
    print("\n🔄 Testing strategy mutation...")

    # Base exhaustion strategy code
    base_code = '''
"""@pyne
"""
from pynecore import Series, input, plot, color, script, Persistent

@script.indicator(title="Exhaustion Signal", overlay=True)
def main():
    # Inputs
    level1 = input.int("Level 1", 9)
    level2 = input.int("Level 2", 12)
    level3 = input.int("Level 3", 14)
    
    # Persistent state
    cycle: Persistent[int] = 0
    bull: Persistent[int] = 0
    bear: Persistent[int] = 0
    
    # Logic here (simplified)
    plot(bull == level1, "Bull L1", color=color.green)
'''

    client = LocalLLMClient()
    if not client.test_connection():
        print("❌ Cannot test mutation - LLM not available")
        return False

    context = PromptContext(
        strategy_type="signal",
        market_focus=["spot"],
        timeframe="1m",
        indicators_to_include=["exhaustion"],
        signal_logic="exhaustion",
        risk_profile="balanced",
    )

    generator = LLMStrategyGenerator(client)
    result = generator.mutate_strategy(base_code, "parameter", context)

    if result.success:
        print("✅ Mutation successful!")
        print(f"⏱️ Mutation time: {result.generation_time:.2f}s")
        print("\n📄 Mutation preview (first 15 lines):")
        print("=" * 50)
        for i, line in enumerate(result.generated_code.split("\n")[:15], 1):
            print(f"{i:2d}: {line}")
        print("=" * 50)
        return True
    else:
        print("❌ Mutation failed!")
        print(f"🚫 Error: {result.error_message}")
        return False


def test_evolution_integration():
    """Test integration with evolution system."""
    print("\n🧬 Testing evolution system integration...")

    try:
        from exhaustionlab.app.backtest.llm_evolution import LLMStrategyMutator
        from exhaustionlab.app.backtest.llm_evolution import StrategyGenome

        # Create mutator
        mutator = LLMStrategyMutator()

        # Create test strategy genome
        base_genome = StrategyGenome(
            name="test_exhaustion",
            description="Test exhaustion strategy",
            pine_code="# Test Pine code",
            pyne_code="from pynecore import *; def main(): pass",
            parameters={"level1": 9, "level2": 12, "level3": 14},
            generation=0,
        )

        # Test mutation
        mutated = mutator.mutate_strategy(base_genome, "parameter")

        print(f"✅ Evolution integration successful!")
        print(f"📊 Mutation stats: {mutator.get_mutation_stats()}")
        print(f"🔄 Mutated: {base_genome.name} → {mutated.name}")
        return True

    except Exception as e:
        print(f"❌ Evolution integration failed: {e}")
        return False


def show_usage_examples():
    """Show usage examples for the LLM system."""
    print("\n💡 Usage Examples:")
    print("=" * 60)

    print(
        """
To use in your GA evolution:

```bash
# With LLM enabled (will auto-detect)
python -m exhaustionlab.app.backtest.ga_optimizer \\
  --llm-evolution \\
  --population-size 6 \\
  --generations 8 \\
  --fitness-preset AGGRESSIVE_DEMO
```

In Python code:

```python
from exhaustionlab.app.llm import LocalLLMClient, LLMStrategyGenerator

# Initialize
client = LocalLLMClient("http://127.0.0.1:1234")
generator = LLMStrategyGenerator(client)

# Create strategy
result = generator.create_signal_strategy('mean_reversion', 'balanced', context)
evolved = generator.generate_strategy(result)

# Mutate existing
mutated = generator.mutate_strategy(existing_code, 'parameter', context)
```
"""
    )


def main():
    """Run all integration tests."""
    print("🤖 LLM Integration Test Suite")
    print("=" * 60)

    tests = [
        test_llm_connection,
        test_mutation,
        test_simple_generation,
        test_evolution_integration,
    ]

    results = []
    for test in tests:
        try:
            success = test()
            results.append(success)
        except Exception as e:
            print(f"💥 Test failed with exception: {e}")
            results.append(False)

    # Summary
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed! LLM integration is ready!")
    else:
        print(f"⚠️  {total - passed} tests failed. Check setup.")

    # Show usage
    show_usage_examples()

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
