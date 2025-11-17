#!/usr/bin/env python3
"""
Quick test to verify UI is loading correctly.
Run this and check browser console for any errors.
"""

print("=" * 70)
print("UI STARTUP CHECKLIST")
print("=" * 70)

print("\n✓ Starting server...")
print("  Command: poetry run uvicorn exhaustionlab.webui.server:app --reload --port 8080")
print("\n✓ Open browser:")
print("  URL: http://localhost:8080")
print("\n✓ Check Browser Console (F12):")
print("  - Look for JavaScript errors (red text)")
print("  - Verify app.js and evolution.js loaded")
print("  - Check if refreshHallOfFame() function exists")
print("\n✓ Verify Page Elements:")
print("  - Evolution Control Panel (top)")
print("  - Strategy Evolution chart section")
print("  - Hall of Fame section (should show placeholder or strategies)")
print("\n✓ Test Hall of Fame:")
print("  1. Open console and type: refreshHallOfFame()")
print("  2. Should see strategies or 'No strategies yet'")
print("\n✓ Check API Endpoints:")
print("  - GET http://localhost:8080/api/evolution/hall-of-fame")
print("  - GET http://localhost:8080/api/evolution/progress")
print("\n✓ Common Issues:")
print("  - 'refreshHallOfFame is not defined' → evolution.js not loaded")
print("  - Empty Hall of Fame → No strategies generated yet (expected)")
print("  - CSS issues → Hard refresh (Ctrl+Shift+R)")
print("  - API errors → Check server logs")
print("\n" + "=" * 70)
print("QUICK TESTS IN BROWSER CONSOLE:")
print("=" * 70)
print(
    """
// Test 1: Check if functions exist
typeof refreshHallOfFame
typeof loadChart
typeof startEvolution

// Test 2: Load Hall of Fame manually
await refreshHallOfFame()

// Test 3: Check evolution progress
const response = await fetch('/api/evolution/progress')
const data = await response.json()
console.log(data)

// Test 4: Get Hall of Fame data
const hof = await fetch('/api/evolution/hall-of-fame')
const strategies = await hof.json()
console.log(strategies)
"""
)
print("=" * 70)
