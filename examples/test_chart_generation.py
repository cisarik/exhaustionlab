#!/usr/bin/env python3
"""Quick test to verify chart generation works."""

import sys
from pathlib import Path

# Test chart generation
print("Testing chart generation...")
try:
    from exhaustionlab.webui.chart_generator import ChartGenerator

    # Create generator
    gen = ChartGenerator(cache_dir=Path("/tmp/test_charts"))
    print("✓ ChartGenerator initialized")

    # Generate a test chart
    print("Generating test chart for ADAEUR 1m...")
    img_bytes = gen.generate_chart(
        symbol="ADAEUR",
        timeframe="1m",
        limit=100,
        width=800,
        height=600,
        show_signals=True,
        show_volume=True,
    )

    print(f"✓ Chart generated successfully ({len(img_bytes)} bytes)")

    # Save test output
    test_file = Path("/tmp/test_candlestick.png")
    test_file.write_bytes(img_bytes)
    print(f"✓ Saved test chart to: {test_file}")

    print("\n✅ Chart generation test PASSED!")
    print(f"\nYou can view the test chart at: {test_file}")

except Exception as exc:
    print(f"\n❌ Chart generation test FAILED: {exc}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
