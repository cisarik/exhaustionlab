# 🔧 UI Debugging Guide - What to Check

Based on the screenshots, here's what to verify and fix:

## Quick Checks

### 1. Browser Console (F12 → Console Tab)
Check for errors:
```javascript
// Should see these loaded:
✓ app.js loaded
✓ evolution.js loaded
✓ No red errors

// Test if functions exist:
typeof refreshHallOfFame  // should be "function"
typeof loadChart          // should be "function"
typeof startEvolution     // should be "function"
```

### 2. Hall of Fame Section
**Expected**: Should show either:
- "No strategies yet. Start evolution to generate some!" (if no strategies)
- Strategy cards with metrics (if evolution has run)

**If Empty/Broken**:
```javascript
// In browser console, manually trigger:
await refreshHallOfFame()
```

### 3. Strategy Cards Styling
Cards should have:
- ✓ Strategy name as heading
- ✓ Fitness badge (green if ≥0.8, blue if ≥0.6)
- ✓ 4 metric boxes (Sharpe, Max DD, Win Rate, Trades)
- ✓ Footer with source + generation
- ✓ Action buttons (📊 View Chart, 👁️ View Code)

### 4. CSS Loading
Hard refresh to ensure latest CSS:
- **Windows/Linux**: Ctrl + Shift + R
- **Mac**: Cmd + Shift + R

### 5. API Endpoints Test
```bash
# Test these URLs in browser or curl:
curl http://localhost:8080/api/evolution/progress
curl http://localhost:8080/api/evolution/hall-of-fame
curl http://localhost:8080/api/charts/candlestick.png?symbol=ADAEUR&timeframe=1m
```

## Common Issues & Fixes

### Issue 1: "refreshHallOfFame is not defined"
**Cause**: evolution.js not loaded
**Fix**: Check that `<script src="/static/evolution.js"></script>` is in index.html

### Issue 2: Hall of Fame shows "Loading..." forever
**Cause**: API endpoint not responding
**Fix**:
```javascript
// Check API manually:
fetch('/api/evolution/hall-of-fame')
  .then(r => r.json())
  .then(console.log)
```

### Issue 3: Strategy cards have no styling
**Cause**: CSS not applied
**Fix**:
1. Hard refresh (Ctrl+Shift+R)
2. Check styles.css loaded in Network tab
3. Verify CSS classes match (strategy-card, strategy-header, etc.)

### Issue 4: "No strategies yet" - Expected!
**This is normal** if you haven't run evolution yet.

**To test with dummy data**:
```javascript
// In console, create fake strategy for testing UI:
const testStrategy = {
  strategy_id: 'test-123',
  name: 'Test Strategy',
  fitness: 0.85,
  sharpe_ratio: 2.1,
  max_drawdown: 0.12,
  win_rate: 0.68,
  total_trades: 147,
  profit_factor: 2.3,
  source: 'llm_generated',
  generation: 1
};

// Update dropdown
updateStrategySelector([testStrategy]);
```

### Issue 5: Evolution panel empty
**Check**:
- `#evolution-chart` exists
- `#evolution-events` exists
- `#phase-breakdown` exists

## Files to Verify

### 1. Check HTML Structure
```bash
grep -n "strategy-grid\|evolution-control-panel\|chart-panel" exhaustionlab/webui/templates/index.html
```
Should show these sections exist.

### 2. Check CSS Classes
```bash
grep -n "\.strategy-card\|\.fitness-badge\|\.action-btn" exhaustionlab/webui/static/styles.css
```
Should show styles are defined.

### 3. Check JavaScript Functions
```bash
grep -n "function refreshHallOfFame\|function loadChart\|function startEvolution" exhaustionlab/webui/static/evolution.js
```
Should show functions are defined.

## Expected vs Actual

### ✅ What Should Work Right Now:
- ✓ Page loads without errors
- ✓ All panels visible
- ✓ Hall of Fame shows "No strategies yet" (if no data)
- ✓ Evolution controls render
- ✓ Chart loads basic candlesticks
- ✓ All buttons clickable (even if no data to show)

### 🔄 What Needs Real Data:
- Evolution progress (need to run evolution)
- Hall of Fame strategies (need to run evolution)
- Strategy selection (need strategies first)
- Backtest overlays (need strategy selected + backtested)

## Test Sequence

1. **Start server**: `poetry run uvicorn exhaustionlab.webui.server:app --reload --port 8080`

2. **Open browser**: `http://localhost:8080`

3. **Check sections exist**:
   - Hero metrics (top)
   - Evolution Control Panel
   - Strategy Visualization
   - Evolution Pulse (old panel)
   - Hall of Fame
   - LLM Debugger

4. **Test Hall of Fame manually**:
   ```javascript
   // In console:
   await refreshHallOfFame()
   ```

5. **If empty** (expected!):
   - Shows "No strategies yet. Start evolution to generate some!"
   - This is CORRECT behavior

6. **To test with data** - Run evolution:
   - Click "🧬 Start Evolution" button
   - Configure parameters
   - Click "▶ Start Evolution"
   - Watch real-time progress
   - Hall of Fame populates when complete

## Screenshots Analysis

Based on your screenshots (7_3, 7_4, 7_5), likely issues:

1. **Hall of Fame cards styling** → Fixed with new CSS
2. **Strategy grid not populating** → Normal if no evolution run yet
3. **Action buttons not visible** → Fixed with action-btn CSS
4. **Evolution panel layout** → Check if controls render properly

## Next Steps

1. Hard refresh browser (Ctrl+Shift+R)
2. Open console (F12)
3. Check for errors
4. Try `await refreshHallOfFame()` in console
5. Expected result: "No strategies yet" message

**If you see this message, UI IS WORKING!** 🎉

You just need to run evolution to generate strategies.

---

**Need more help?** Share:
- Console errors (if any)
- What you see in Hall of Fame section
- Whether buttons are clickable
