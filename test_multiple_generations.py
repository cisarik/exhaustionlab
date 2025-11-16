#!/usr/bin/env python3
"""
Test multiple generations to verify consistency

Tests that the improved prompts consistently produce
clean code without hallucinations.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "exhaustionlab"))

from exhaustionlab.app.llm import LocalLLMClient, LLMRequest
from exhaustionlab.app.llm.prompts import PromptContext
from exhaustionlab.app.llm.hallucination_detector import HallucinationDetector


def test_multiple_generations(num_tests=5):
    """Test multiple strategy generations."""
    print(
        f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                🧪 TESTING {num_tests} GENERATIONS FOR CONSISTENCY 🧪                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    )

    client = LocalLLMClient()
    detector = HallucinationDetector()

    # Test connection
    if not client.test_connection():
        print("❌ LLM not available")
        return 1

    print(f"✅ Connected to: {client.model_name}\n")

    # Test different strategy types
    test_cases = [
        {
            "name": "RSI + SMA Momentum",
            "context": PromptContext(
                strategy_type="signal",
                market_focus=["spot"],
                timeframe="5m",
                indicators_to_include=["RSI", "SMA"],
                signal_logic="momentum",
                risk_profile="balanced",
            ),
        },
        {
            "name": "EMA Crossover",
            "context": PromptContext(
                strategy_type="signal",
                market_focus=["spot"],
                timeframe="15m",
                indicators_to_include=["EMA"],
                signal_logic="trend_following",
                risk_profile="conservative",
            ),
        },
        {
            "name": "RSI Mean Reversion",
            "context": PromptContext(
                strategy_type="signal",
                market_focus=["spot"],
                timeframe="1h",
                indicators_to_include=["RSI", "SMA"],
                signal_logic="mean_reversion",
                risk_profile="aggressive",
            ),
        },
        {
            "name": "Multi-Indicator",
            "context": PromptContext(
                strategy_type="signal",
                market_focus=["spot"],
                timeframe="30m",
                indicators_to_include=["RSI", "EMA", "ATR"],
                signal_logic="trend_following",
                risk_profile="balanced",
            ),
        },
        {
            "name": "Simple RSI",
            "context": PromptContext(
                strategy_type="indicator",
                market_focus=["spot"],
                timeframe="5m",
                indicators_to_include=["RSI"],
                signal_logic="momentum",
                risk_profile="balanced",
            ),
        },
    ]

    results = []

    for i, test_case in enumerate(test_cases[:num_tests], 1):
        print(f"{'='*80}")
        print(f"TEST {i}/{min(num_tests, len(test_cases))}: {test_case['name']}")
        print(f"{'='*80}")

        # Generate prompt
        prompt_request = client.prompt_engine.generate_signal_strategy_prompt(
            test_case["context"]
        )

        print(f"\n⏳ Generating...")

        # Generate response
        response = client.generate(prompt_request)

        if not response.success:
            print(f"❌ Generation failed: {response.error_message}")
            results.append(
                {
                    "name": test_case["name"],
                    "success": False,
                    "hallucinations": "N/A",
                    "error": response.error_message,
                }
            )
            continue

        print(f"✅ Generated in {response.request_time:.2f}s")

        # Check for hallucinations
        if response.code_blocks:
            code = response.code_blocks[0]
            is_clean, issues = detector.validate_code(code)

            if is_clean:
                print(f"🎉 NO HALLUCINATIONS!")
                results.append(
                    {
                        "name": test_case["name"],
                        "success": True,
                        "hallucinations": 0,
                        "code_length": len(code),
                    }
                )
            else:
                print(f"⚠️  Found {len(issues)} hallucinations:")
                stats = detector.get_statistics(issues)
                for key, value in stats.items():
                    if value > 0:
                        print(f"   - {key}: {value}")

                results.append(
                    {
                        "name": test_case["name"],
                        "success": False,
                        "hallucinations": len(issues),
                        "issues": stats,
                    }
                )
        else:
            print(f"❌ No code generated")
            results.append(
                {
                    "name": test_case["name"],
                    "success": False,
                    "hallucinations": "N/A",
                    "error": "No code blocks",
                }
            )

        print()

    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print(f"{'='*80}\n")

    successful = sum(1 for r in results if r.get("success", False))
    total = len(results)

    print(f"Total tests: {total}")
    print(f"Successful: {successful} ({successful/total*100:.1f}%)")
    print(f"Failed: {total - successful}")

    # Detailed results
    print(f"\n📋 Detailed Results:\n")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("success", False) else "❌"
        halluc = result.get("hallucinations", "N/A")
        print(f"{i}. {status} {result['name']}: {halluc} hallucinations")
        if not result.get("success", False) and "error" in result:
            print(f"   Error: {result['error']}")

    # Overall verdict
    print(f"\n{'='*80}")
    if successful == total:
        print("🎉 EXCELLENT: All generations clean!")
        print("✅ Prompts are working consistently")
        verdict = 0
    elif successful >= total * 0.8:
        print("✅ GOOD: Most generations clean")
        print("⚠️  Some hallucinations, may need prompt tuning")
        verdict = 0
    else:
        print("⚠️  NEEDS IMPROVEMENT: Too many hallucinations")
        print("❌ Prompts need more work")
        verdict = 1

    print(f"{'='*80}\n")

    return verdict


if __name__ == "__main__":
    num_tests = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    sys.exit(test_multiple_generations(num_tests))
