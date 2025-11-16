#!/usr/bin/env python3
"""
DEBUG: Full LLM Communication Inspector

Shows EVERYTHING that's sent to and received from the LLM.
Saves all data to files for analysis.
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "exhaustionlab"))

from exhaustionlab.app.llm import LocalLLMClient, LLMRequest
from exhaustionlab.app.llm.enhanced_prompts import EnhancedPromptBuilder
from exhaustionlab.app.llm.prompts import PromptContext
from exhaustionlab.app.llm.validators import PyneCoreValidator


class LLMCommunicationDebugger:
    """Debugger that captures and displays full LLM communication."""

    def __init__(self, output_dir: str = "llm_debug_logs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Create timestamped session directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.output_dir / f"session_{timestamp}"
        self.session_dir.mkdir(exist_ok=True)

        print(f"🔍 DEBUG SESSION: {timestamp}")
        print(f"📁 Output directory: {self.session_dir}")
        print("=" * 80)

    def test_model_connection(self, base_url: str, model_name: str):
        """Test connection and show model details."""
        print(f"\n{'='*80}")
        print("🔌 TESTING MODEL CONNECTION")
        print(f"{'='*80}")

        print(f"\n📡 Target:")
        print(f"   URL: {base_url}")
        print(f"   Model: {model_name}")

        import requests

        try:
            # Test /v1/models endpoint
            response = requests.get(f"{base_url}/v1/models", timeout=5)
            print(f"\n✅ Connection successful!")
            print(f"   Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"\n📊 Available Models:")
                if "data" in data:
                    for model in data["data"]:
                        print(f"   - {model.get('id', 'unknown')}")
                else:
                    print(f"   {json.dumps(data, indent=2)}")

            return True

        except requests.exceptions.ConnectionError:
            print(f"\n❌ CONNECTION FAILED!")
            print(f"   Cannot connect to {base_url}")
            print(f"\n💡 Make sure LM Studio is running:")
            print(f"   1. Open LM Studio")
            print(f"   2. Go to 'Local Server' tab")
            print(f"   3. Load model: {model_name}")
            print(f"   4. Click 'Start Server'")
            return False

        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            return False

    def build_test_prompt(self, use_examples: bool = True):
        """Build a test prompt and show its contents."""
        print(f"\n{'='*80}")
        print("📝 BUILDING TEST PROMPT")
        print(f"{'='*80}")

        builder = EnhancedPromptBuilder()

        # Create simple test context
        context = PromptContext(
            strategy_type="strategy",
            market_focus=["spot"],
            timeframe="5m",
            indicators_to_include=["RSI", "SMA"],
            signal_logic="momentum",
            risk_profile="balanced",
        )

        print(f"\n📋 Context:")
        print(f"   Type: {context.strategy_type}")
        print(f"   Logic: {context.signal_logic}")
        print(f"   Indicators: {', '.join(context.indicators_to_include)}")
        print(f"   Timeframe: {context.timeframe}")
        print(f"   Risk: {context.risk_profile}")
        print(f"   Examples: {'YES' if use_examples else 'NO'}")

        # Build prompt
        if use_examples:
            prompt = builder.build_strategy_prompt(
                context, include_examples=True, num_examples=2
            )
        else:
            prompt = builder.build_strategy_prompt(context, include_examples=False)

        print(f"\n📊 Prompt Statistics:")
        print(f"   Total length: {len(prompt):,} characters")
        print(f"   Total lines: {len(prompt.splitlines())}")
        print(f"   Estimated tokens: ~{len(prompt) // 4}")

        # Save prompt
        prompt_file = self.session_dir / "01_prompt.txt"
        with open(prompt_file, "w") as f:
            f.write(prompt)

        print(f"\n💾 Saved to: {prompt_file}")

        # Show first and last parts
        lines = prompt.splitlines()
        print(f"\n📄 PROMPT BEGINNING (first 30 lines):")
        print("-" * 80)
        for i, line in enumerate(lines[:30], 1):
            print(f"{i:3d} | {line}")
        print("...")
        print("-" * 80)

        print(f"\n📄 PROMPT ENDING (last 20 lines):")
        print("-" * 80)
        for i, line in enumerate(lines[-20:], len(lines) - 19):
            print(f"{i:3d} | {line}")
        print("-" * 80)

        return prompt, context

    def send_to_llm(self, prompt: str, model_name: str, temperature: float = 0.7):
        """Send prompt to LLM and capture full response."""
        print(f"\n{'='*80}")
        print("🚀 SENDING TO LLM")
        print(f"{'='*80}")

        client = LocalLLMClient(model_name=model_name)

        # Create request
        request = LLMRequest(
            prompt=prompt,
            system_prompt="You are an expert Pine Script and PyneCore developer. Create clean, production-ready trading strategies.",
            temperature=temperature,
            top_p=0.95,
            max_tokens=3000,
        )

        print(f"\n⚙️ Request Parameters:")
        print(f"   Model: {model_name}")
        print(f"   Temperature: {temperature}")
        print(f"   Top P: 0.95")
        print(f"   Max Tokens: 3000")
        print(f"   System Prompt: {request.system_prompt[:80]}...")

        # Save request details
        request_file = self.session_dir / "02_request.json"
        with open(request_file, "w") as f:
            json.dump(
                {
                    "model": model_name,
                    "temperature": temperature,
                    "top_p": 0.95,
                    "max_tokens": 3000,
                    "system_prompt": request.system_prompt,
                    "prompt_length": len(prompt),
                    "prompt_lines": len(prompt.splitlines()),
                },
                f,
                indent=2,
            )

        print(f"💾 Request saved to: {request_file}")

        # Generate
        print(f"\n⏳ Waiting for LLM response...")
        start_time = time.time()

        try:
            response = client.generate(request)
            elapsed = time.time() - start_time

            print(f"\n✅ RESPONSE RECEIVED ({elapsed:.2f}s)")

            # Save raw response
            response_file = self.session_dir / "03_response_raw.txt"
            with open(response_file, "w") as f:
                f.write(response.content)

            print(f"💾 Raw response saved to: {response_file}")

            # Save response metadata
            metadata_file = self.session_dir / "04_response_metadata.json"
            with open(metadata_file, "w") as f:
                json.dump(
                    {
                        "success": response.success,
                        "content_length": len(response.content),
                        "code_blocks_found": len(response.code_blocks),
                        "request_time": response.request_time,
                        "usage": response.usage,
                        "error_message": response.error_message,
                        "metadata": response.metadata,
                    },
                    f,
                    indent=2,
                )

            print(f"💾 Metadata saved to: {metadata_file}")

            return response

        except Exception as e:
            print(f"\n❌ LLM ERROR: {e}")

            # Save error
            error_file = self.session_dir / "error.txt"
            with open(error_file, "w") as f:
                f.write(f"Error: {e}\n")
                import traceback

                f.write(traceback.format_exc())

            return None

    def analyze_response(self, response):
        """Analyze and display LLM response."""
        print(f"\n{'='*80}")
        print("🔍 ANALYZING RESPONSE")
        print(f"{'='*80}")

        if not response:
            print("\n❌ No response to analyze")
            return None

        print(f"\n📊 Response Statistics:")
        print(f"   Success: {response.success}")
        print(f"   Content length: {len(response.content):,} chars")
        print(f"   Lines: {len(response.content.splitlines())}")
        print(f"   Code blocks: {len(response.code_blocks)}")
        print(f"   Request time: {response.request_time:.2f}s")

        if response.usage:
            print(f"\n🎯 Token Usage:")
            for key, value in response.usage.items():
                print(f"   {key}: {value}")

        # Show full content
        print(f"\n📄 FULL RESPONSE CONTENT:")
        print("=" * 80)
        print(response.content)
        print("=" * 80)

        # Extract code blocks
        if response.code_blocks:
            print(f"\n💻 EXTRACTED CODE BLOCKS ({len(response.code_blocks)}):")

            for i, code_block in enumerate(response.code_blocks, 1):
                print(f"\n--- CODE BLOCK {i} ---")
                print("-" * 80)

                # Show code with line numbers
                for line_num, line in enumerate(code_block.splitlines(), 1):
                    print(f"{line_num:3d} | {line}")

                print("-" * 80)
                print(f"Lines: {len(code_block.splitlines())}")

                # Save code block
                code_file = self.session_dir / f"05_code_block_{i}.py"
                with open(code_file, "w") as f:
                    f.write(code_block)
                print(f"💾 Saved to: {code_file}")
        else:
            print(f"\n⚠️ NO CODE BLOCKS FOUND!")
            print("   Looking for code markers...")

            # Try to find code-like content
            if "```" in response.content:
                print("   ✅ Found ``` markers")
            if "def " in response.content:
                print("   ✅ Found 'def ' keywords")
            if "from pynecore" in response.content:
                print("   ✅ Found 'from pynecore' import")

        return response.code_blocks[0] if response.code_blocks else None

    def validate_code(self, code: str):
        """Validate generated code and show results."""
        print(f"\n{'='*80}")
        print("✅ VALIDATING CODE")
        print(f"{'='*80}")

        if not code:
            print("\n❌ No code to validate")
            return

        validator = PyneCoreValidator()

        # Syntax validation
        print(f"\n1️⃣ SYNTAX VALIDATION:")
        syntax_valid = validator.validate_syntax(code)
        print(f"   {'✅ PASS' if syntax_valid else '❌ FAIL'}")

        # Structure validation
        print(f"\n2️⃣ STRUCTURE VALIDATION:")
        structure = validator.validate_structure(code)

        checks = {
            "has_decorator": "Has @script decorator",
            "has_inputs": "Has input parameters",
            "has_main_logic": "Has main logic",
            "has_plots": "Has plot statements",
            "has_imports": "Has imports",
        }

        for key, desc in checks.items():
            status = structure.get(key, False)
            print(f"   {'✅' if status else '❌'} {desc}: {status}")

        # API validation
        print(f"\n3️⃣ API USAGE VALIDATION:")
        api_valid = validator.validate_api_usage(code)
        print(f"   {'✅ PASS' if api_valid else '❌ FAIL'}")

        # Full validation
        print(f"\n4️⃣ FULL VALIDATION:")
        result = validator.validate_pyne_code(code, check_runtime=False)

        print(f"   Valid: {result.is_valid}")
        print(f"   Issues: {len(result.issues)}")

        if result.issues:
            print(f"\n🚨 VALIDATION ISSUES:")
            for issue in result.issues:
                icon = "🛑" if issue.severity == "error" else "⚠️"
                print(f"\n   {icon} {issue.severity.upper()}: {issue.message}")
                if issue.line_number:
                    print(f"      Line: {issue.line_number}")
                if issue.suggestion:
                    print(f"      💡 Suggestion: {issue.suggestion}")

        # Quality score
        print(f"\n5️⃣ QUALITY SCORE:")
        score = validator.calculate_quality_score(code)
        print(f"   Score: {score}/100")

        if score >= 80:
            print(f"   ⭐⭐⭐⭐⭐ EXCELLENT!")
        elif score >= 60:
            print(f"   ⭐⭐⭐⭐ GOOD")
        elif score >= 40:
            print(f"   ⭐⭐⭐ ACCEPTABLE")
        elif score >= 20:
            print(f"   ⭐⭐ POOR")
        else:
            print(f"   ⭐ VERY POOR")

        # Save validation report
        report_file = self.session_dir / "06_validation_report.json"
        with open(report_file, "w") as f:
            json.dump(
                {
                    "syntax_valid": syntax_valid,
                    "structure": structure,
                    "api_valid": api_valid,
                    "is_valid": result.is_valid,
                    "issues": [
                        {
                            "severity": i.severity,
                            "message": i.message,
                            "line_number": i.line_number,
                            "suggestion": i.suggestion,
                        }
                        for i in result.issues
                    ],
                    "quality_score": score,
                },
                f,
                indent=2,
            )

        print(f"\n💾 Validation report saved to: {report_file}")

        return result

    def create_summary(self, prompt: str, response, code: str, validation):
        """Create final summary report."""
        print(f"\n{'='*80}")
        print("📋 SUMMARY REPORT")
        print(f"{'='*80}")

        summary = {
            "session_timestamp": self.session_dir.name,
            "prompt_length": len(prompt),
            "prompt_lines": len(prompt.splitlines()),
            "response_success": response.success if response else False,
            "response_length": len(response.content) if response else 0,
            "code_blocks_found": len(response.code_blocks) if response else 0,
            "code_generated": code is not None,
            "validation_passed": validation.is_valid if validation else False,
            "quality_score": 0,
        }

        if code:
            validator = PyneCoreValidator()
            summary["quality_score"] = validator.calculate_quality_score(code)
            summary["code_lines"] = len(code.splitlines())

        print(f"\n✅ Session complete!")
        print(f"\n📊 Key Metrics:")
        print(
            f"   Prompt: {summary['prompt_length']:,} chars, {summary['prompt_lines']} lines"
        )
        print(f"   Response: {summary['response_success']}")
        print(f"   Code found: {summary['code_generated']}")
        print(f"   Validation: {summary['validation_passed']}")
        print(f"   Quality: {summary['quality_score']}/100")

        # Save summary
        summary_file = self.session_dir / "00_SUMMARY.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n💾 Summary saved to: {summary_file}")
        print(f"\n📁 All files in: {self.session_dir}")

        # List all files
        print(f"\n📄 Generated files:")
        for file in sorted(self.session_dir.iterdir()):
            size = file.stat().st_size
            print(f"   - {file.name} ({size:,} bytes)")

        return summary


def main():
    """Run complete debugging session."""
    print(
        """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║                   🔍 LLM COMMUNICATION DEBUGGER 🔍                           ║
║                                                                              ║
║  This script will show you EVERYTHING that happens during LLM generation:   ║
║  - Full prompts sent                                                         ║
║  - Complete responses received                                               ║
║  - All validation errors                                                     ║
║  - Quality metrics                                                           ║
║                                                                              ║
║  All data is saved to files for detailed analysis.                          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    )

    # Configuration
    BASE_URL = "http://127.0.0.1:1234"
    MODEL_NAME = os.getenv("LLM_MODEL", "google/gemma-3n-e4b")
    TEMPERATURE = 0.7
    USE_EXAMPLES = True  # Set to False to test without examples

    print(f"⚙️ Configuration:")
    print(f"   URL: {BASE_URL}")
    print(f"   Model: {MODEL_NAME}")
    print(f"   Temperature: {TEMPERATURE}")
    print(f"   Use Examples: {USE_EXAMPLES}")
    print()

    # Create debugger
    debugger = LLMCommunicationDebugger()

    try:
        # Step 1: Test connection
        if not debugger.test_model_connection(BASE_URL, MODEL_NAME):
            print("\n❌ Cannot proceed without LLM connection")
            return 1

        # Step 2: Build prompt
        prompt, context = debugger.build_test_prompt(use_examples=USE_EXAMPLES)

        # Step 3: Send to LLM
        response = debugger.send_to_llm(prompt, MODEL_NAME, TEMPERATURE)

        if not response:
            print("\n❌ No response from LLM")
            return 1

        # Step 4: Analyze response
        code = debugger.analyze_response(response)

        # Step 5: Validate code
        validation = None
        if code:
            validation = debugger.validate_code(code)

        # Step 6: Create summary
        summary = debugger.create_summary(prompt, response, code, validation)

        # Final message
        print(f"\n{'='*80}")
        print("🎉 DEBUGGING SESSION COMPLETE!")
        print(f"{'='*80}")

        print(f"\n💡 Next steps:")
        print(f"   1. Review files in: {debugger.session_dir}")
        print(f"   2. Check 01_prompt.txt to see what was sent")
        print(f"   3. Check 03_response_raw.txt to see what was received")
        print(f"   4. Check 05_code_block_1.py for generated code")
        print(f"   5. Check 06_validation_report.json for issues")

        if summary["quality_score"] < 50:
            print(f"\n⚠️ Quality score is low ({summary['quality_score']}/100)")
            print(
                f"   This suggests the model is hallucinating or not following instructions."
            )
            print(f"   We need to improve the prompt or try a different model.")

        return 0

    except KeyboardInterrupt:
        print(f"\n\n⚠️ Interrupted by user")
        return 1

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
