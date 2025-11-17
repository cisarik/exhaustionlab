/**
 * Live Trading Management
 * Handles strategy deployment, position monitoring, and trade history
 */

let activeDeployments = {};
let updateInterval = null;

/**
 * Open deployment modal
 */
function deployStrategy(strategyId, strategyName) {
  const modal = document.getElementById("deploy-modal");
  const titleElement = document.getElementById("deploy-modal-title");
  const strategyIdInput = document.getElementById("deploy-strategy-id");

  if (modal && titleElement && strategyIdInput) {
    titleElement.textContent = `Deploy: ${strategyName}`;
    strategyIdInput.value = strategyId;
    modal.style.display = "flex";
  }
}

/**
 * Close deployment modal
 */
function closeDeployModal() {
  const modal = document.getElementById("deploy-modal");
  if (modal) {
    modal.style.display = "none";
  }
}

/**
 * Confirm and execute deployment
 */
async function confirmDeploy() {
  const strategyId = document.getElementById("deploy-strategy-id")?.value;
  const strategyName = document.getElementById("deploy-modal-title")?.textContent.replace("Deploy: ", "");

  // Get form values
  const mode = document.querySelector('input[name="mode"]:checked')?.value || "paper";
  const symbols = document.getElementById("deploy-symbols")?.value.split(",").map(s => s.trim()) || ["ADAEUR"];
  const timeframe = document.getElementById("deploy-timeframe")?.value || "1m";

  const maxPositionSize = parseFloat(document.getElementById("deploy-position-size")?.value || 2) / 100;
  const maxDailyLoss = parseFloat(document.getElementById("deploy-daily-loss")?.value || 1) / 100;
  const maxDrawdown = parseFloat(document.getElementById("deploy-drawdown")?.value || 5) / 100;
  const maxOpenPositions = parseInt(document.getElementById("deploy-max-positions")?.value || 3);
  const enableStopLoss = document.getElementById("deploy-stop-loss")?.checked ?? true;
  const enableTakeProfit = document.getElementById("deploy-take-profit")?.checked ?? true;

  // Build request
  const request = {
    strategy_id: strategyId,
    strategy_name: strategyName,
    mode: mode,
    symbols: symbols,
    timeframe: timeframe,
    max_position_size: maxPositionSize,
    max_daily_loss: maxDailyLoss,
    max_drawdown: maxDrawdown,
    max_open_positions: maxOpenPositions,
    enable_stop_loss: enableStopLoss,
    stop_loss_pct: 0.02,
    enable_take_profit: enableTakeProfit,
    take_profit_pct: 0.05,
    exchange: "binance",
    testnet: true,
  };

  try {
    const response = await fetch("/api/trading/deploy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Deployment failed: ${response.statusText}`);
    }

    const result = await response.json();

    // Show success message
    showNotification(`✅ Strategy deployed successfully in ${mode} mode!`, "success");

    // Close modal
    closeDeployModal();

    // Refresh deployments
    await refreshDeployments();

    // Update deployment status badge
    updateDeploymentStatus(strategyId, result.deployment_id, mode);

    // Start auto-refresh if not already running
    if (!updateInterval) {
      updateInterval = setInterval(refreshTradingData, 2000); // Update every 2 seconds
    }

  } catch (error) {
    console.error("Deployment error:", error);
    showNotification(`❌ Deployment failed: ${error.message}`, "error");
  }
}

/**
 * Update deployment status badge on strategy info panel
 */
function updateDeploymentStatus(strategyId, deploymentId, mode) {
  activeDeployments[strategyId] = { deploymentId, mode };

  // Check if this strategy is currently selected
  const selector = document.getElementById("strategy-selector");
  if (selector && selector.value === strategyId) {
    showDeploymentBadge(mode);
  }
}

/**
 * Show deployment badge
 */
function showDeploymentBadge(mode) {
  const badge = document.getElementById("deployment-status");
  if (badge) {
    badge.className = `deployment-badge ${mode}`;
    badge.style.display = "flex";

    const statusText = badge.querySelector(".status-text");
    if (statusText) {
      statusText.textContent = mode === "paper" ? "PAPER TRADING" : "LIVE TRADING";
    }
  }
}

/**
 * Hide deployment badge
 */
function hideDeploymentBadge() {
  const badge = document.getElementById("deployment-status");
  if (badge) {
    badge.style.display = "none";
  }
}

/**
 * Refresh all deployments
 */
async function refreshDeployments() {
  try {
    const response = await fetch("/api/trading/deployments");
    if (!response.ok) return;

    const deployments = await response.json();

    // Update active deployments map
    activeDeployments = {};
    deployments.forEach(d => {
      activeDeployments[d.strategy_id] = {
        deploymentId: d.deployment_id,
        mode: d.mode,
      };
    });

    // Render deployments grid
    renderDeployments(deployments);

    // Show/hide emergency stop button
    const emergencyBtn = document.getElementById("emergency-stop-btn");
    if (emergencyBtn) {
      emergencyBtn.style.display = deployments.length > 0 ? "block" : "none";
    }

    // Update all positions
    await refreshAllPositions(deployments);

  } catch (error) {
    console.error("Failed to refresh deployments:", error);
  }
}

/**
 * Render deployments grid
 */
function renderDeployments(deployments) {
  const grid = document.getElementById("deployments-grid");
  if (!grid) return;

  if (deployments.length === 0) {
    grid.innerHTML = '<div class="placeholder">No active deployments. Deploy a strategy from Hall of Fame to start trading.</div>';
    return;
  }

  grid.innerHTML = deployments.map(d => `
    <div class="deployment-card" data-deployment-id="${d.deployment_id}">
      <div class="deployment-header">
        <h4>${d.strategy_name}</h4>
        <span class="mode-badge ${d.mode}">${d.mode.toUpperCase()}</span>
      </div>
      <div class="deployment-stats">
        <div class="stat">
          <span class="stat-label">Status</span>
          <span class="stat-value status-${d.status}">${d.status.toUpperCase()}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Uptime</span>
          <span class="stat-value">${formatDuration(d.uptime_seconds)}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Trades</span>
          <span class="stat-value">${d.total_trades}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Win Rate</span>
          <span class="stat-value">${(d.win_rate * 100).toFixed(1)}%</span>
        </div>
        <div class="stat">
          <span class="stat-label">Total P&L</span>
          <span class="stat-value ${d.total_pnl >= 0 ? 'profit' : 'loss'}">
            ${d.total_pnl >= 0 ? '+' : ''}${d.total_pnl.toFixed(2)} (${(d.total_pnl_pct * 100).toFixed(2)}%)
          </span>
        </div>
        <div class="stat">
          <span class="stat-label">Daily P&L</span>
          <span class="stat-value ${d.daily_pnl >= 0 ? 'profit' : 'loss'}">
            ${d.daily_pnl >= 0 ? '+' : ''}${d.daily_pnl.toFixed(2)} (${(d.daily_pnl_pct * 100).toFixed(2)}%)
          </span>
        </div>
        <div class="stat">
          <span class="stat-label">Open Positions</span>
          <span class="stat-value">${d.open_positions}</span>
        </div>
        <div class="stat">
          <span class="stat-label">Drawdown</span>
          <span class="stat-value">${(d.current_drawdown * 100).toFixed(2)}%</span>
        </div>
      </div>
      <div class="deployment-actions">
        <button class="btn-stop" onclick="stopDeployment('${d.deployment_id}')">⏹ Stop</button>
      </div>
    </div>
  `).join("");
}

/**
 * Refresh all positions for all deployments
 */
async function refreshAllPositions(deployments) {
  const allPositions = [];

  for (const deployment of deployments) {
    try {
      const response = await fetch(`/api/trading/positions/${deployment.deployment_id}`);
      if (response.ok) {
        const positions = await response.json();
        allPositions.push(...positions);
      }
    } catch (error) {
      console.error(`Failed to fetch positions for ${deployment.deployment_id}:`, error);
    }
  }

  renderPositions(allPositions);
}

/**
 * Render positions table
 */
function renderPositions(positions) {
  const tbody = document.getElementById("positions-tbody");
  if (!tbody) return;

  if (positions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No open positions</td></tr>';
    return;
  }

  tbody.innerHTML = positions.map(p => `
    <tr>
      <td><strong>${p.symbol}</strong></td>
      <td><span class="side-badge ${p.side}">${p.side.toUpperCase()}</span></td>
      <td>${p.entry_price.toFixed(4)}</td>
      <td>${p.current_price.toFixed(4)}</td>
      <td>${p.quantity.toFixed(4)}</td>
      <td class="${p.unrealized_pnl >= 0 ? 'profit' : 'loss'}">
        ${p.unrealized_pnl >= 0 ? '+' : ''}${p.unrealized_pnl.toFixed(2)}
      </td>
      <td class="${p.unrealized_pnl_pct >= 0 ? 'profit' : 'loss'}">
        ${p.unrealized_pnl_pct >= 0 ? '+' : ''}${(p.unrealized_pnl_pct * 100).toFixed(2)}%
      </td>
      <td>${formatDuration((new Date() - new Date(p.entry_time)) / 1000)}</td>
    </tr>
  `).join("");
}

/**
 * Stop a deployment
 */
async function stopDeployment(deploymentId) {
  if (!confirm("Stop this deployment and close all positions?")) {
    return;
  }

  try {
    const response = await fetch(`/api/trading/stop/${deploymentId}`, {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error("Failed to stop deployment");
    }

    showNotification("✅ Deployment stopped successfully", "success");
    await refreshDeployments();

  } catch (error) {
    console.error("Stop deployment error:", error);
    showNotification(`❌ Failed to stop: ${error.message}`, "error");
  }
}

/**
 * Emergency stop all deployments
 */
async function emergencyStopAll() {
  if (!confirm("🚨 EMERGENCY STOP - Close all positions immediately?")) {
    return;
  }

  try {
    const response = await fetch("/api/trading/emergency-stop", {
      method: "POST",
    });

    if (!response.ok) {
      throw new Error("Emergency stop failed");
    }

    showNotification("🚨 Emergency stop executed - All positions closed", "warning");
    await refreshDeployments();

    // Stop auto-refresh
    if (updateInterval) {
      clearInterval(updateInterval);
      updateInterval = null;
    }

  } catch (error) {
    console.error("Emergency stop error:", error);
    showNotification(`❌ Emergency stop failed: ${error.message}`, "error");
  }
}

/**
 * Refresh trading data (positions, deployments)
 */
async function refreshTradingData() {
  await refreshDeployments();
}

/**
 * Format duration in seconds to human-readable
 */
function formatDuration(seconds) {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
  return `${Math.floor(seconds / 86400)}d`;
}

/**
 * Show notification
 */
function showNotification(message, type = "info") {
  // Simple console log for now, can be enhanced with toast notifications
  console.log(`[${type.toUpperCase()}] ${message}`);
  alert(message);
}

// Global functions for onclick handlers
window.deployStrategy = deployStrategy;
window.closeDeployModal = closeDeployModal;
window.confirmDeploy = confirmDeploy;
window.stopDeployment = stopDeployment;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  // Emergency stop button
  const emergencyBtn = document.getElementById("emergency-stop-btn");
  if (emergencyBtn) {
    emergencyBtn.addEventListener("click", emergencyStopAll);
  }

  // Load initial deployments
  refreshDeployments();

  // Close modal on click outside
  const deployModal = document.getElementById("deploy-modal");
  if (deployModal) {
    deployModal.addEventListener("click", (e) => {
      if (e.target === deployModal) {
        closeDeployModal();
      }
    });
  }

  // Update deployment badge when strategy selector changes
  const strategySelector = document.getElementById("strategy-selector");
  if (strategySelector) {
    strategySelector.addEventListener("change", (e) => {
      const strategyId = e.target.value;
      if (strategyId && activeDeployments[strategyId]) {
        showDeploymentBadge(activeDeployments[strategyId].mode);
      } else {
        hideDeploymentBadge();
      }
    });
  }
});
