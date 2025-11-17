#!/usr/bin/env python3
"""
Test IMPROVED prompt that explicitly prevents hallucinations
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

OUTPUT_DIR = Path("llm_debug_logs")
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
SESSION_DIR = OUTPUT_DIR / f"improved_{timestamp}"
SESSION_DIR.mkdir(parents=True, exist_ok=True)

print(
    f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    🧪 TESTING IMPROVED PROMPT 🧪                             ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
)

BASE_URL = "http://127.0.0.1:1234"
MODEL_NAME = "google/gemma-3n-e4b"

# IMPROVED SYSTEM PROMPT with explicit constraints
IMPROVED_SYSTEM_PROMPT = """You are an expert PyneCore trading strategy developer.

PyneCore is a Python framework for trading strategies. Follow these EXACT rules:

═══════════════════════════════════════════════════════════════════════════════
📦 REQUIRED IMPORTS (copy exactly):
═══════════════════════════════════════════════════════════════════════════════

from pynecore import Series, input, plot, color, script
from pynecore.lib import close

# OR alternative:
from pynecore import *
from pynecore.lib import close

═══════════════════════════════════════════════════════════════════════════════
📋 STRUCTURE TEMPLATE (follow exactly):
═══════════════════════════════════════════════════════════════════════════════

@script.indicator(title="Your Strategy Name", overlay=True)
def main():
    # 1. Define inputs (use ONLY input.int or input.float)
    period = input.int("Period", 14)

    # 2. Calculate indicators
    rsi = close.rsi(period)

    # 3. Generate signals (use & not 'and')
    buy = (rsi < 30) & (close > close.sma(20))
    sell = (rsi > 70) & (close < close.sma(20))

    # 4. Plot (use EXACT syntax below)
    plot(buy, "Buy", color=color.green)
    plot(sell, "Sell", color=color.red)

    return {"buy": buy, "sell": sell}

═══════════════════════════════════════════════════════════════════════════════
✅ ALLOWED plot() SYNTAX (ONLY THESE FORMS):
═══════════════════════════════════════════════════════════════════════════════

plot(value, "Label", color=color.XXX)

Where color.XXX can ONLY be:
  - color.green
  - color.red
  - color.blue
  - color.yellow
  - color.white
  - color.black

═══════════════════════════════════════════════════════════════════════════════
❌ FORBIDDEN - DO NOT USE:
═══════════════════════════════════════════════════════════════════════════════

# ❌ NO style parameter
plot(x, "Label", style=plot.Style.POINT)  # WRONG!

# ❌ NO title parameter
plot(x, "Label", title="X")  # WRONG!

# ❌ NO linewidth, linestyle, etc.
plot(x, "Label", linewidth=2)  # WRONG!

# ❌ NO custom colors
color.purple   # WRONG!
color.orange   # WRONG!

# ❌ NO 'and'/'or' operators for Series
buy = rsi < 30 and close > sma  # WRONG!

# ✅ USE '&' and '|' instead
buy = (rsi < 30) & (close > sma)  # CORRECT!

═══════════════════════════════════════════════════════════════════════════════
📊 AVAILABLE INDICATORS:
═══════════════════════════════════════════════════════════════════════════════

close.sma(length)              # Simple Moving Average
close.ema(length)              # Exponential Moving Average
close.rsi(length)              # Relative Strength Index
close.macd(fast, slow, signal) # MACD (returns tuple)
close.atr(length)              # Average True Range

═══════════════════════════════════════════════════════════════════════════════
🔍 WORKING EXAMPLE:
═══════════════════════════════════════════════════════════════════════════════

from pynecore import Series, input, plot, color, script
from pynecore.lib import close

@script.indicator(title="RSI Crossover", overlay=True)
def main():
    # Inputs
    rsi_period = input.int("RSI Period", 14)
    threshold = input.float("Threshold", 30.0)

    # Calculate
    rsi = close.rsi(rsi_period)

    # Signals (NOTE: Use & not and!)
    oversold = rsi < threshold
    overbought = rsi > (100 - threshold)

    # Plot (NOTE: Only 3 parameters!)
    plot(oversold, "Oversold", color=color.green)
    plot(overbought, "Overbought", color=color.red)

    return {"oversold": oversold, "overbought": overbought}

═══════════════════════════════════════════════════════════════════════════════

Generate code that EXACTLY matches these rules. NO improvisation on the API!"""

USER_PROMPT = """Create a momentum trading strategy using RSI and SMA.

Requirements:
- Use RSI(14) for momentum detection
- Use SMA(20) for trend direction
- Buy signal: RSI < 30 AND price > SMA (oversold in uptrend)
- Sell signal: RSI > 70 AND price < SMA (overbought in downtrend)
- Timeframe: 5 minutes
- Risk: Balanced

IMPORTANT: Follow the PyneCore API rules EXACTLY. Use & operator, not 'and'!"""

# Test both models
MODELS_TO_TEST = [
    "google/gemma-3n-e4b",
    "deepseek/deepseek-r1-0528-qwen3-8b",
]


def test_model(model_name):
    """Test a single model with improved prompt."""
    print(f"\n{'='*80}")
    print(f"🤖 TESTING: {model_name}")
    print(f"{'='*80}")

    messages = [
        {"role": "system", "content": IMPROVED_SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ]

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000,
    }

    print(f"\n⏳ Sending request...")
    start = time.time()

    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=120)

        elapsed = time.time() - start

        if response.status_code != 200:
            print(f"❌ Failed: {response.status_code}")
            return None

        data = response.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        print(f"✅ Response received ({elapsed:.2f}s)")
        print(f"   Tokens: {usage.get('total_tokens', 'N/A')}")
        print(f"   Length: {len(content)} chars")

        # Save
        model_safe_name = model_name.replace("/", "_")
        with open(SESSION_DIR / f"{model_safe_name}_response.txt", "w") as f:
            f.write(content)

        # Extract code
        import re

        code_blocks = re.findall(r"```python\n(.*?)\n```", content, re.DOTALL)
        if not code_blocks:
            code_blocks = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)

        if code_blocks:
            code = code_blocks[0]
            with open(SESSION_DIR / f"{model_safe_name}_code.py", "w") as f:
                f.write(code)

            # Check for hallucinations
            print(f"\n🔍 Hallucination Check:")

            issues = []
            if "style=" in code:
                issues.append("❌ Found 'style=' parameter (hallucination)")
            else:
                print("   ✅ No 'style=' parameter")

            if "title=" in code and "@script.indicator" not in code.split("title=")[0]:
                issues.append("❌ Found 'title=' in plot() (hallucination)")
            else:
                print("   ✅ No 'title=' in plot()")

            if "color.purple" in code or "color.orange" in code:
                issues.append("❌ Found invalid colors (hallucination)")
            else:
                print("   ✅ Only standard colors used")

            if " and " in code and "# and" not in code:
                # Check if it's in a boolean expression
                lines_with_and = [l for l in code.split("\n") if " and " in l and not l.strip().startswith("#")]
                if any("=" in l and " and " in l for l in lines_with_and):
                    issues.append("⚠️ Found 'and' operator (should use &)")
                else:
                    print("   ✅ No 'and' operator in boolean expressions")
            else:
                print("   ✅ No 'and' operator issues")

            if "from pynecore.lib import close" not in code and "from pynecore import *" not in code:
                if "close.rsi" in code or "close.sma" in code:
                    issues.append("⚠️ Uses 'close' but doesn't import from pynecore.lib")
            else:
                print("   ✅ Proper imports")

            if issues:
                print(f"\n⚠️ Issues found:")
                for issue in issues:
                    print(f"   {issue}")
                return False
            else:
                print(f"\n🎉 NO HALLUCINATIONS DETECTED!")
                return True
        else:
            print(f"\n❌ No code blocks found")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# Test all models
print(f"\n📊 Testing {len(MODELS_TO_TEST)} models with improved prompt...")
print(f"Output directory: {SESSION_DIR}")

results = {}
for model in MODELS_TO_TEST:
    result = test_model(model)
    results[model] = result
    time.sleep(1)  # Brief pause between requests

# Summary
print(f"\n{'='*80}")
print("📋 SUMMARY")
print(f"{'='*80}")

for model, result in results.items():
    if result is True:
        status = "✅ CLEAN (no hallucinations)"
    elif result is False:
        status = "⚠️ HAS ISSUES"
    else:
        status = "❌ FAILED"

    print(f"   {model}: {status}")

print(f"\n📁 All results saved to: {SESSION_DIR}")
print()
