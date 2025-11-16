#!/usr/bin/env python3
"""
SIMPLE LLM DEBUGGER - No database dependencies

Shows raw LLM communication without example database.
"""

import sys
import os
import json
import time
import requests
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path("llm_debug_logs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Create session directory
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
SESSION_DIR = OUTPUT_DIR / f"session_{timestamp}"
SESSION_DIR.mkdir(exist_ok=True)

print(
    f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   🔍 SIMPLE LLM COMMUNICATION DEBUGGER 🔍                    ║
║                                                                              ║
║  Shows FULL LLM communication without complex dependencies                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
)

# Configuration
BASE_URL = "http://127.0.0.1:1234"
MODEL_NAME = os.getenv("LLM_MODEL", "google/gemma-3n-e4b")
TEMPERATURE = 0.7

print(f"⚙️ Configuration:")
print(f"   URL: {BASE_URL}")
print(f"   Model: {MODEL_NAME}")
print(f"   Temperature: {TEMPERATURE}")
print(f"   Output: {SESSION_DIR}")
print()

# Step 1: Test connection
print("=" * 80)
print("🔌 TESTING CONNECTION")
print("=" * 80)

try:
    response = requests.get(f"{BASE_URL}/v1/models", timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Connected!")
        print(f"\n📊 Available models:")
        if "data" in data:
            for model in data["data"]:
                model_id = model.get("id", "unknown")
                marker = " ← SELECTED" if model_id == MODEL_NAME else ""
                print(f"   - {model_id}{marker}")
    else:
        print(f"❌ Connection failed: {response.status_code}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Cannot connect: {e}")
    print(f"\n💡 Make sure LM Studio is running on {BASE_URL}")
    sys.exit(1)

# Step 2: Build simple prompt
print(f"\n{'='*80}")
print("📝 BUILDING PROMPT")
print("=" * 80)

SYSTEM_PROMPT = """You are an expert trading strategy developer. You write clean, production-ready PyneCore code.

PyneCore is a Python framework that uses Pine Script concepts. Here's what you need to know:

IMPORTS:
```python
from pynecore import script, input, plot, color, Series
```

STRUCTURE:
```python
@script.indicator(title="Strategy Name", overlay=True)
def main():
    # 1. Define inputs
    period = input.int("Period", 14)
    
    # 2. Calculate indicators
    rsi_value = close.rsi(period)
    
    # 3. Generate signals
    buy_signal = rsi_value < 30
    sell_signal = rsi_value > 70
    
    # 4. Plot results
    plot(buy_signal, "Buy", color=color.green)
    plot(sell_signal, "Sell", color=color.red)
    
    return {"buy": buy_signal, "sell": sell_signal}
```

AVAILABLE INDICATORS:
- close.sma(length) - Simple Moving Average
- close.ema(length) - Exponential Moving Average
- close.rsi(length) - Relative Strength Index
- close.macd(fast, slow, signal) - MACD
- close.bb(length, std) - Bollinger Bands
- close.atr(length) - Average True Range

RULES:
1. Always use @script.indicator() decorator
2. Define main() function
3. Use input.int(), input.float() for parameters
4. Return dict with signal names
5. Keep code simple and clean
6. No external libraries needed"""

USER_PROMPT = """Create a simple momentum trading strategy using RSI and SMA.

Requirements:
- Use RSI(14) for momentum
- Use SMA(20) for trend
- Buy when: RSI < 30 AND price > SMA (oversold in uptrend)
- Sell when: RSI > 70 AND price < SMA (overbought in downtrend)
- Timeframe: 5 minutes
- Risk: Balanced

Generate complete, working PyneCore code. Use ```python``` code blocks."""

print(f"\n📊 System Prompt ({len(SYSTEM_PROMPT)} chars):")
print("-" * 80)
print(SYSTEM_PROMPT[:400])
print("...")
print("-" * 80)

print(f"\n📊 User Prompt ({len(USER_PROMPT)} chars):")
print("-" * 80)
print(USER_PROMPT)
print("-" * 80)

# Save prompts
with open(SESSION_DIR / "01_system_prompt.txt", "w") as f:
    f.write(SYSTEM_PROMPT)

with open(SESSION_DIR / "02_user_prompt.txt", "w") as f:
    f.write(USER_PROMPT)

print(f"\n💾 Prompts saved to {SESSION_DIR}")

# Step 3: Send to LLM
print(f"\n{'='*80}")
print("🚀 SENDING TO LLM")
print("=" * 80)

messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": USER_PROMPT},
]

payload = {
    "model": MODEL_NAME,
    "messages": messages,
    "temperature": TEMPERATURE,
    "top_p": 0.95,
    "max_tokens": 2000,
    "stream": False,
}

print(f"\n⚙️ Request parameters:")
print(f"   Model: {MODEL_NAME}")
print(f"   Temperature: {TEMPERATURE}")
print(f"   Max tokens: 2000")
print(f"   Messages: {len(messages)}")

# Save request
with open(SESSION_DIR / "03_request.json", "w") as f:
    json.dump(payload, f, indent=2)

print(f"\n⏳ Waiting for response...")
start_time = time.time()

try:
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions", json=payload, timeout=120
    )

    elapsed = time.time() - start_time

    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
        sys.exit(1)

    data = response.json()

    print(f"✅ Response received ({elapsed:.2f}s)")

    # Save raw response
    with open(SESSION_DIR / "04_response_raw.json", "w") as f:
        json.dump(data, f, indent=2)

    # Extract content
    content = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})

    # Save content
    with open(SESSION_DIR / "05_response_content.txt", "w") as f:
        f.write(content)

    print(f"\n💾 Response saved")

except Exception as e:
    print(f"❌ Request failed: {e}")
    sys.exit(1)

# Step 4: Analyze response
print(f"\n{'='*80}")
print("🔍 ANALYZING RESPONSE")
print("=" * 80)

print(f"\n📊 Statistics:")
print(f"   Content length: {len(content):,} chars")
print(f"   Lines: {len(content.splitlines())}")
print(f"   Request time: {elapsed:.2f}s")

if usage:
    print(f"\n🎯 Token usage:")
    for key, value in usage.items():
        print(f"   {key}: {value:,}")

print(f"\n{'='*80}")
print("📄 FULL RESPONSE CONTENT")
print("=" * 80)
print(content)
print("=" * 80)

# Step 5: Extract code blocks
import re

print(f"\n{'='*80}")
print("💻 EXTRACTING CODE")
print("=" * 80)

python_blocks = re.findall(r"```python\n(.*?)\n```", content, re.DOTALL)
if not python_blocks:
    python_blocks = re.findall(r"```\n(.*?)\n```", content, re.DOTALL)

if python_blocks:
    print(f"\n✅ Found {len(python_blocks)} code block(s)")

    for i, code in enumerate(python_blocks, 1):
        print(f"\n--- CODE BLOCK {i} ---")
        print("-" * 80)

        # Show with line numbers
        for line_num, line in enumerate(code.splitlines(), 1):
            print(f"{line_num:3d} | {line}")

        print("-" * 80)
        print(f"Lines: {len(code.splitlines())}")

        # Save code
        code_file = SESSION_DIR / f"06_code_block_{i}.py"
        with open(code_file, "w") as f:
            f.write(code)

        print(f"💾 Saved to: {code_file}")
else:
    print(f"\n⚠️ NO CODE BLOCKS FOUND!")
    print(f"\nLooking for indicators...")

    if "```" in content:
        print("   ✅ Found ``` markers")
        # Try to extract anything between ```
        all_blocks = re.findall(r"```(.*?)```", content, re.DOTALL)
        print(f"   Found {len(all_blocks)} blocks total")
        for i, block in enumerate(all_blocks, 1):
            print(f"\n   Block {i} preview:")
            print(f"   {block[:100]}...")

    if "def " in content or "from " in content:
        print("   ✅ Found Python-like code")
    else:
        print("   ❌ No Python code detected")

# Step 6: Basic validation
if python_blocks:
    print(f"\n{'='*80}")
    print("✅ BASIC VALIDATION")
    print("=" * 80)

    code = python_blocks[0]

    checks = {
        "@script.indicator": "Has @script decorator",
        "def main": "Has main() function",
        "input.": "Has input parameters",
        "plot(": "Has plot statements",
        "from pynecore": "Has pynecore imports",
        "return": "Has return statement",
    }

    print(f"\n🔍 Code structure checks:")
    passed = 0
    for pattern, description in checks.items():
        found = pattern in code
        passed += 1 if found else 0
        icon = "✅" if found else "❌"
        print(f"   {icon} {description}: {found}")

    score = (passed / len(checks)) * 100
    print(f"\n📊 Basic quality: {score:.0f}%")

    if score >= 80:
        print("   ⭐⭐⭐⭐⭐ EXCELLENT!")
    elif score >= 60:
        print("   ⭐⭐⭐⭐ GOOD")
    elif score >= 40:
        print("   ⭐⭐⭐ ACCEPTABLE")
    else:
        print("   ⭐⭐ POOR - Model hallucinating or not following instructions")

# Final summary
print(f"\n{'='*80}")
print("📋 SUMMARY")
print("=" * 80)

summary = {
    "timestamp": timestamp,
    "model": MODEL_NAME,
    "temperature": TEMPERATURE,
    "request_time_seconds": elapsed,
    "response_length": len(content),
    "code_blocks_found": len(python_blocks),
    "usage": usage,
    "output_directory": str(SESSION_DIR),
}

with open(SESSION_DIR / "00_SUMMARY.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"\n✅ Debug session complete!")
print(f"\n📁 All files saved to: {SESSION_DIR}")
print(f"\n📄 Files generated:")
for file in sorted(SESSION_DIR.iterdir()):
    size = file.stat().st_size
    print(f"   - {file.name} ({size:,} bytes)")

print(f"\n💡 Next steps:")
print(f"   1. Review 05_response_content.txt to see what the model generated")
print(f"   2. Check 06_code_block_1.py for extracted code")
print(f"   3. Look for hallucination patterns")
print(f"   4. Test with different models/temperatures")

if python_blocks:
    print(f"\n🎉 CODE WAS GENERATED! Check if it's valid or hallucinated.")
else:
    print(f"\n⚠️ NO CODE GENERATED! Model may not understand the task.")

print()
