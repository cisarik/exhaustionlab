/**
 * Backtesting UI
 */

let currentBacktestResult = null;

// Load presets
async function loadPresets() {
  try {
    const response = await fetch("/api/presets/paper-trading");
    if (!response.ok) return;

    const presets = await response.json();
    renderPresets(presets);
  } catch (error) {
    console.error("Failed to load presets:", error);
  }
}

// Render preset cards
function renderPresets(presets) {
  const grid = document.getElementById("preset-grid");
  if (!grid) return;

  grid.innerHTML = presets.map(preset => `
    <div class="preset-card">
      <div class="preset-header">
        <h4>${preset.name}</h4>
        <span class="risk-badge ${preset.expected.max_risk.toLowerCase()}">${preset.expected.max_risk} Risk</span>
      </div>
      <p class="preset-description">${preset.description}</p>
      <div class="preset-stats">
        <div class="preset-stat">
          <span>Expected Return</span>
          <strong>${preset.expected.daily_return}/day</strong>
        </div>
        <div class="preset-stat">
          <span>Style</span>
          <strong>${preset.expected.style}</strong>
        </div>
      </div>
      <button class="primary small" onclick='applyPreset(${JSON.stringify(preset).replace(/'/g, "&apos;")})'>
        Use This Preset
      </button>
    </div>
  `).join("");
}

// Apply preset
function applyPreset(preset) {
  alert(`Preset "${preset.name}" applied!\n\nRisk Settings:\n` +
    `- Position Size: ${(preset.risk.max_position_size*100).toFixed(1)}%\n` +
    `- Daily Loss Limit: ${(preset.risk.max_daily_loss*100).toFixed(1)}%\n` +
    `- Max Drawdown: ${(preset.risk.max_drawdown*100).toFixed(1)}%\n\n` +
    `These settings are now default for new deployments.`);
}

// Run backtest
async function runBacktest(strategyId) {
  const resultsDiv = document.getElementById("backtest-results");
  if (resultsDiv) {
    resultsDiv.style.display = "block";
    resultsDiv.scrollIntoView({ behavior: "smooth" });
  }

  // Show loading
  document.getElementById("bt-return").textContent = "Loading...";

  try {
    const response = await fetch("/api/backtest/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strategy_id: strategyId }),
    });

    if (!response.ok) throw new Error("Backtest failed");

    const data = await response.json();
    currentBacktestResult = data.result;

    displayBacktestResults(data.result);
  } catch (error) {
    console.error("Backtest error:", error);
    alert("Failed to run backtest: " + error.message);
  }
}

// Display results
function displayBacktestResults(result) {
  // Summary metrics
  document.getElementById("bt-return").textContent =
    `${result.total_return >= 0 ? '+' : ''}${result.total_return_pct.toFixed(2)}%`;
  document.getElementById("bt-return").className =
    `metric-value ${result.total_return >= 0 ? 'profit' : 'loss'}`;

  document.getElementById("bt-sharpe").textContent = result.sharpe_ratio.toFixed(2);
  document.getElementById("bt-winrate").textContent = `${(result.win_rate * 100).toFixed(1)}%`;
  document.getElementById("bt-drawdown").textContent = `${(result.max_drawdown * 100).toFixed(1)}%`;

  // Overview metrics
  document.getElementById("bt-total-trades").textContent = result.total_trades;
  document.getElementById("bt-winning").textContent = result.winning_trades;
  document.getElementById("bt-losing").textContent = result.losing_trades;
  document.getElementById("bt-pf").textContent = result.profit_factor.toFixed(2);
  document.getElementById("bt-avg-win").textContent = `$${result.avg_win.toFixed(2)}`;
  document.getElementById("bt-avg-loss").textContent = `$${result.avg_loss.toFixed(2)}`;

  // Trades list
  renderTradesList(result.trades);

  // Equity curve
  renderEquityCurve(result.equity_curve);
}

// Render trades list
function renderTradesList(trades) {
  const list = document.getElementById("bt-trades-list");
  if (!list) return;

  if (!trades || trades.length === 0) {
    list.innerHTML = '<p class="empty-state">No trades to display</p>';
    return;
  }

  list.innerHTML = trades.map(trade => `
    <div class="trade-item">
      <div class="trade-header">
        <span class="trade-side ${trade.side}">${trade.side.toUpperCase()}</span>
        <span class="trade-time">${new Date(trade.exit_time).toLocaleString()}</span>
      </div>
      <div class="trade-prices">
        <span>Entry: $${trade.entry_price.toFixed(4)}</span>
        <span>Exit: $${trade.exit_price.toFixed(4)}</span>
      </div>
      <div class="trade-result ${trade.pnl >= 0 ? 'profit' : 'loss'}">
        ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)} (${(trade.pnl_pct * 100).toFixed(2)}%)
      </div>
      <span class="trade-reason">${trade.reason}</span>
    </div>
  `).join("");
}

// Render equity curve (simple version)
function renderEquityCurve(equityCurve) {
  const canvas = document.getElementById("equity-chart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  // Clear canvas
  ctx.fillStyle = "#0d111a";
  ctx.fillRect(0, 0, width, height);

  if (!equityCurve || equityCurve.length === 0) return;

  // Find min/max
  const values = equityCurve.map(p => p[1]);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const range = maxVal - minVal;

  // Draw grid
  ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 5; i++) {
    const y = (height - 40) * i / 5 + 20;
    ctx.beginPath();
    ctx.moveTo(40, y);
    ctx.lineTo(width - 20, y);
    ctx.stroke();
  }

  // Draw line
  ctx.strokeStyle = "#58f5c3";
  ctx.lineWidth = 2;
  ctx.beginPath();

  equityCurve.forEach((point, i) => {
    const x = 40 + (width - 60) * i / (equityCurve.length - 1);
    const y = height - 40 - ((point[1] - minVal) / range) * (height - 60);

    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  });

  ctx.stroke();

  // Draw labels
  ctx.fillStyle = "#94a3b8";
  ctx.font = "12px sans-serif";
  ctx.fillText(`$${minVal.toFixed(0)}`, 5, height - 25);
  ctx.fillText(`$${maxVal.toFixed(0)}`, 5, 30);
}

// Deploy from backtest
function deployFromBacktest() {
  if (!currentBacktestResult) {
    alert("No backtest results available");
    return;
  }

  // Open deploy modal with strategy
  deployStrategy(currentBacktestResult.strategy_id, "Backtested Strategy");
}

// Export backtest
function exportBacktest() {
  if (!currentBacktestResult) return;

  const data = JSON.stringify(currentBacktestResult, null, 2);
  const blob = new Blob([data], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `backtest-${currentBacktestResult.strategy_id}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// Tab switching
function switchBacktestTab(tabName) {
  document.querySelectorAll(".results-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });

  document.querySelectorAll(".results-panel").forEach(panel => {
    panel.classList.toggle("active", panel.dataset.panel === tabName);
  });
}

// Global functions
window.applyPreset = applyPreset;
window.runBacktest = runBacktest;
window.deployFromBacktest = deployFromBacktest;
window.exportBacktest = exportBacktest;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  loadPresets();

  // Run backtest button
  const runBtn = document.getElementById("run-backtest-btn");
  if (runBtn) {
    runBtn.addEventListener("click", () => {
      // Run backtest for first demo strategy
      runBacktest("demo-001");
    });
  }

  // Tab switching
  document.querySelectorAll(".results-tab").forEach(tab => {
    tab.addEventListener("click", () => switchBacktestTab(tab.dataset.tab));
  });
});
