# Web UI Candlestick Charts - User Guide

## Overview

The ExhaustionLab web UI now features **beautiful, interactive candlestick charts** that display:
- Real-time price action with professional candlestick rendering
- Exhaustion signals (L1, L2, L3) overlaid on the chart
- Volume bars synchronized with price action
- Multiple symbols and timeframes
- Auto-refresh every 30 seconds
- Responsive design that works on all screen sizes

## Features

### Chart Display
- **High-quality PNG rendering** using matplotlib
- **Dark theme** matching the ExhaustionLab aesthetic
- **Candlestick visualization** with green (up) and red (down) candles
- **Volume panel** showing buying/selling pressure
- **Signal overlays** showing exhaustion L1/L2/L3 signals
- **Professional styling** with custom color scheme

### Interactive Controls
- **Symbol selector**: Choose from ADAEUR, BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT
- **Timeframe selector**: 1m, 5m, 15m, 1h, 4h
- **Refresh button**: Manually update the chart
- **Auto-refresh**: Charts automatically update every 30 seconds

### Performance
- **Smart caching**: Charts are cached for 30 seconds to reduce API calls
- **Async loading**: Charts load in the background with spinner
- **Smooth transitions**: Professional loading states

## Getting Started

### 1. Install Dependencies

The chart feature requires matplotlib and pillow:

```bash
poetry install
```

### 2. Start the Web Server

```bash
# Option 1: Using poetry
poetry run uvicorn exhaustionlab.webui.server:app --reload --port 8080

# Option 2: Using python module
poetry run python -m exhaustionlab.webui.server

# Option 3: Custom port
WEBUI_PORT=3000 poetry run python -m exhaustionlab.webui.server
```

### 3. Open in Browser

Navigate to: **http://localhost:8080**

You'll see the chart panel at the top of the page with controls to customize the view.

## API Endpoints

### Get Candlestick Chart

```
GET /api/charts/candlestick.png
```

**Parameters:**
- `symbol` (string): Trading pair (default: "ADAEUR")
- `timeframe` (string): Candle timeframe (default: "1m")
- `limit` (int): Number of candles (50-1000, default: 200)
- `width` (int): Chart width in pixels (400-3840, default: 1400)
- `height` (int): Chart height in pixels (300-2160, default: 800)
- `signals` (bool): Show exhaustion signals (default: true)
- `volume` (bool): Show volume panel (default: true)

**Example:**
```
http://localhost:8080/api/charts/candlestick.png?symbol=BTCUSDT&timeframe=5m&limit=200
```

### Clear Chart Cache

```
POST /api/charts/clear-cache
```

Clears all cached chart images to force regeneration.

## Architecture

### Chart Generation Flow

1. **Request** → API endpoint receives chart parameters
2. **Cache Check** → Looks for cached chart (30s TTL)
3. **Data Fetch** → Fetches klines from Binance REST API
4. **Signal Calculation** → Computes exhaustion signals
5. **Rendering** → Matplotlib draws candlesticks, signals, volume
6. **PNG Export** → Chart saved as PNG bytes
7. **Cache** → Result cached for future requests
8. **Response** → PNG image returned to browser

### Key Components

- **`chart_generator.py`** (345 LOC) - Main chart rendering engine
- **`api.py`** - FastAPI endpoints for chart access
- **`templates/index.html`** - Chart display section
- **`static/styles.css`** - Chart styling (spinner, containers)
- **`static/app.js`** - Chart loading logic and auto-refresh

### Chart Rendering Details

The chart generator uses **pure matplotlib** (no mplfinance dependency) to:
1. Create candlestick bodies using Rectangle patches
2. Draw wicks as vertical lines
3. Overlay signal markers at calculated price points
4. Add volume bars with color matching candle direction
5. Apply custom dark theme with ExhaustionLab colors

## Testing

### Manual Testing

```bash
# Generate a test chart
poetry run python test_chart_generation.py

# View the generated chart
xdg-open /tmp/test_candlestick.png  # Linux
open /tmp/test_candlestick.png      # macOS
```

### Integration Testing

```bash
# Start server in background
poetry run uvicorn exhaustionlab.webui.server:app --port 8080 &

# Test API endpoint
curl "http://localhost:8080/api/charts/candlestick.png?symbol=ADAEUR&timeframe=1m" \
  --output test.png

# Verify PNG
file test.png
```

## Customization

### Changing Colors

Edit `exhaustionlab/webui/chart_generator.py`:

```python
self.colors = {
    "bg": "#0a0e14",        # Background
    "axes_bg": "#0f1419",   # Chart background
    "grid": "#1a1f2e",      # Grid lines
    "text": "#cfd8dc",      # Text labels
    "muted": "#7e8ba3",     # Muted text
    "up": "#30ff85",        # Up candles
    "down": "#ff5252",      # Down candles
}
```

### Adding More Symbols

Edit `exhaustionlab/webui/templates/index.html`:

```html
<select id="chart-symbol" class="chart-control">
    <option value="ADAEUR">ADAEUR</option>
    <option value="BTCUSDT">BTCUSDT</option>
    <!-- Add more here -->
    <option value="DOGEUSDT">DOGEUSDT</option>
</select>
```

### Adjusting Auto-Refresh Interval

Edit `exhaustionlab/webui/static/app.js`:

```javascript
// Change from 30000 (30 seconds) to desired interval
chartRefreshInterval = setInterval(loadChart, 60000);  // 60 seconds
```

## Troubleshooting

### Charts Not Loading

**Issue**: Spinner shows but chart never appears

**Solutions**:
1. Check browser console for errors (F12)
2. Verify Binance API is accessible
3. Check server logs for exceptions
4. Try clearing cache: `POST /api/charts/clear-cache`

### Error: "No data available"

**Issue**: Chart shows error message

**Causes**:
- Symbol not available on Binance
- Binance API rate limit exceeded
- Network connectivity issues

**Solutions**:
- Use valid Binance symbols (check Binance.com)
- Wait a minute before retrying
- Check internet connection

### Charts Look Different

**Issue**: Colors or layout don't match expected

**Solutions**:
- Clear browser cache (Ctrl+F5)
- Check CSS file loaded correctly
- Verify matplotlib version: `poetry show matplotlib`

### Performance Issues

**Issue**: Charts load slowly

**Solutions**:
- Reduce `limit` parameter (fewer candles)
- Reduce chart dimensions
- Enable caching (default: 30s)
- Check server resources (CPU/memory)

## Performance Tips

1. **Use appropriate timeframes**: Higher timeframes (4h, 1d) need fewer data points
2. **Limit candles**: 100-200 candles is optimal for 1m-5m timeframes
3. **Cache benefits**: Subsequent requests within 30s are instant
4. **Responsive images**: Charts scale down on mobile automatically
5. **Disable signals**: Set `signals=false` for faster rendering

## Future Enhancements

Potential improvements (not yet implemented):

- [ ] Real-time WebSocket chart updates
- [ ] Interactive zooming and panning
- [ ] Multiple chart types (line, area, Heikin-Ashi)
- [ ] Drawing tools (trendlines, fibonacci)
- [ ] Technical indicators overlay (MA, RSI, MACD)
- [ ] Chart export (PNG, PDF, SVG)
- [ ] Custom timeframe ranges
- [ ] Multi-symbol comparison
- [ ] Chart templates and presets
- [ ] Mobile gesture controls

## Summary

The new chart feature provides **production-grade candlestick visualization** with:
- ✅ Beautiful, professional design
- ✅ Real-time data from Binance
- ✅ Exhaustion signals overlayed
- ✅ Volume analysis
- ✅ Smart caching
- ✅ Mobile responsive
- ✅ Auto-refresh
- ✅ Easy customization

**Files Modified:**
- `pyproject.toml` - Added matplotlib, pillow dependencies
- `exhaustionlab/webui/chart_generator.py` - Chart rendering engine (NEW)
- `exhaustionlab/webui/api.py` - Chart API endpoints
- `exhaustionlab/webui/templates/index.html` - Chart display section
- `exhaustionlab/webui/static/styles.css` - Chart styling
- `exhaustionlab/webui/static/app.js` - Chart loading logic
- `test_chart_generation.py` - Test script (NEW)

**Total Lines Added:** ~650 LOC

**Status:** ✅ **FULLY FUNCTIONAL**

Enjoy your new candlestick charts! 🎉📈
