/**
 * Evolution Control & Real-time Updates
 *
 * Handles:
 * - Starting/stopping evolution
 * - Server-Sent Events for real-time progress
 * - UI updates for status, metrics, and feed
 * - Hall of Fame updates
 */

let evolutionEventSource = null;
let evolutionActive = false;

/**
 * Start evolution process
 */
async function startEvolution() {
  const numGenerations = parseInt(document.getElementById("num-generations")?.value) || 5;
  const populationSize = parseInt(document.getElementById("population-size")?.value) || 3;
  const useLLM = document.getElementById("use-llm")?.checked ?? true;
  const useCrawled = document.getElementById("use-crawled")?.checked ?? true;

  const requestData = {
    num_generations: numGenerations,
    population_size: populationSize,
    use_llm: useLLM,
    use_crawled: useCrawled,
    symbol: "ADAEUR",
    timeframe: "1m",
  };

  try {
    // Disable start button
    const startBtn = document.getElementById("start-evolution");
    const stopBtn = document.getElementById("stop-evolution");
    if (startBtn) {
      startBtn.disabled = true;
      startBtn.textContent = "⏳ Starting...";
    }

    // Start evolution
    const response = await fetch("/api/evolution/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(requestData),
    });

    const result = await response.json();

    if (result.error) {
      console.error("Evolution start failed:", result.error);
      addFeedMessage(result.error, "error");
      if (startBtn) {
        startBtn.disabled = false;
        startBtn.textContent = "▶ Start Evolution";
      }
      return;
    }

    // Evolution started successfully
    evolutionActive = true;
    if (startBtn) startBtn.textContent = "⏳ Running...";
    if (stopBtn) stopBtn.disabled = false;

    // Connect to SSE stream
    connectEvolutionStream();

    // Start polling progress
    pollEvolutionProgress();

  } catch (err) {
    console.error("Evolution start error:", err);
    addFeedMessage(`Error starting evolution: ${err.message}`, "error");

    const startBtn = document.getElementById("start-evolution");
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.textContent = "▶ Start Evolution";
    }
  }
}

/**
 * Connect to Server-Sent Events stream for real-time updates
 */
function connectEvolutionStream() {
  if (evolutionEventSource) {
    evolutionEventSource.close();
  }

  console.log("Connecting to evolution SSE stream...");

  evolutionEventSource = new EventSource("/api/evolution/events");

  evolutionEventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleEvolutionEvent(data);
    } catch (err) {
      console.error("Failed to parse SSE message:", err);
    }
  };

  evolutionEventSource.onerror = (err) => {
    console.error("SSE error:", err);
    // Reconnection handled automatically by browser
  };

  evolutionEventSource.onopen = () => {
    console.log("SSE connection established");
  };
}

/**
 * Handle evolution event from SSE stream
 */
function handleEvolutionEvent(event) {
  const { event_type, generation, strategy_id, fitness, message, timestamp } = event;

  console.log("Evolution event:", event_type, message);

  // Add to feed
  let messageClass = "";
  if (event_type.includes("completed")) messageClass = "success";
  if (event_type.includes("error")) messageClass = "error";
  if (event_type.includes("started")) messageClass = "info";

  const formattedMessage = formatEventMessage(event);
  addFeedMessage(formattedMessage, messageClass);

  // Update status based on event type
  if (event_type === "evolution_completed") {
    evolutionComplete();
  } else if (event_type === "evolution_error") {
    evolutionError();
  }

  // Scroll feed to bottom
  const feedContent = document.getElementById("feed-content");
  if (feedContent) {
    feedContent.scrollTop = feedContent.scrollHeight;
  }
}

/**
 * Format event message for display
 */
function formatEventMessage(event) {
  const time = new Date(event.timestamp * 1000).toLocaleTimeString();
  const { event_type, generation, fitness, message } = event;

  let formatted = `<span class="timestamp">[${time}]</span> `;

  if (event_type === "evolution_started") {
    formatted += `🚀 ${message}`;
  } else if (event_type === "generation_started") {
    formatted += `📊 Generation ${generation}: ${message}`;
  } else if (event_type === "strategy_generated") {
    formatted += `🧬 ${message}`;
  } else if (event_type === "strategy_evaluated") {
    formatted += `✅ ${message} <span class="fitness">(Fitness: ${fitness?.toFixed(4)})</span>`;
  } else if (event_type === "generation_completed") {
    formatted += `✨ ${message}`;
  } else if (event_type === "evolution_completed") {
    formatted += `🎉 ${message}`;
  } else if (event_type === "evolution_error") {
    formatted += `❌ ${message}`;
  } else {
    formatted += message;
  }

  return formatted;
}

/**
 * Add message to evolution feed
 */
function addFeedMessage(message, className = "") {
  const feedContent = document.getElementById("feed-content");
  if (!feedContent) return;

  // Clear placeholder
  const placeholder = feedContent.querySelector(".feed-message");
  if (placeholder && placeholder.textContent.includes("Waiting to start")) {
    feedContent.innerHTML = "";
  }

  const messageDiv = document.createElement("div");
  messageDiv.className = `feed-message ${className}`;
  messageDiv.innerHTML = message;

  feedContent.appendChild(messageDiv);

  // Limit to last 50 messages
  while (feedContent.children.length > 50) {
    feedContent.removeChild(feedContent.firstChild);
  }
}

/**
 * Poll evolution progress periodically
 */
async function pollEvolutionProgress() {
  if (!evolutionActive) return;

  try {
    const response = await fetch("/api/evolution/progress");
    const progress = await response.json();

    updateEvolutionUI(progress);

    // Continue polling if not completed/error
    if (progress.status === "idle" || progress.status === "completed" || progress.status === "error") {
      evolutionActive = false;
    } else {
      setTimeout(pollEvolutionProgress, 2000); // Poll every 2 seconds
    }

  } catch (err) {
    console.error("Failed to fetch progress:", err);
    setTimeout(pollEvolutionProgress, 5000); // Retry after 5 seconds
  }
}

/**
 * Update evolution UI with progress data
 */
function updateEvolutionUI(progress) {
  const {
    status,
    current_generation,
    total_generations,
    strategies_evaluated,
    best_fitness,
    avg_fitness,
    elapsed_time,
  } = progress;

  // Update status text
  const statusText = document.getElementById("status-text");
  if (statusText) {
    statusText.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    statusText.className = status;
  }

  // Update progress bar
  const progressFill = document.getElementById("progress-fill");
  const progressText = document.getElementById("progress-text");
  if (progressFill && progressText) {
    const percentage = total_generations > 0 ? (current_generation / total_generations) * 100 : 0;
    progressFill.style.width = `${percentage}%`;
    progressText.textContent = `${current_generation}/${total_generations} generations`;
  }

  // Update metrics
  if (document.getElementById("best-fitness")) {
    document.getElementById("best-fitness").textContent = best_fitness.toFixed(3);
  }
  if (document.getElementById("avg-fitness")) {
    document.getElementById("avg-fitness").textContent = avg_fitness.toFixed(3);
  }
  if (document.getElementById("strategies-count")) {
    document.getElementById("strategies-count").textContent = strategies_evaluated;
  }
  if (document.getElementById("elapsed-time")) {
    document.getElementById("elapsed-time").textContent = `${Math.round(elapsed_time)}s`;
  }
}

/**
 * Evolution completed successfully
 */
function evolutionComplete() {
  evolutionActive = false;

  const startBtn = document.getElementById("start-evolution");
  const stopBtn = document.getElementById("stop-evolution");

  if (startBtn) {
    startBtn.disabled = false;
    startBtn.textContent = "▶ Start Evolution";
  }
  if (stopBtn) {
    stopBtn.disabled = true;
  }

  // Close SSE connection
  if (evolutionEventSource) {
    evolutionEventSource.close();
    evolutionEventSource = null;
  }

  // Refresh hall of fame
  refreshHallOfFame();
}

/**
 * Evolution encountered error
 */
function evolutionError() {
  evolutionActive = false;

  const startBtn = document.getElementById("start-evolution");
  const stopBtn = document.getElementById("stop-evolution");

  if (startBtn) {
    startBtn.disabled = false;
    startBtn.textContent = "▶ Start Evolution";
  }
  if (stopBtn) {
    stopBtn.disabled = true;
  }

  // Close SSE connection
  if (evolutionEventSource) {
    evolutionEventSource.close();
    evolutionEventSource = null;
  }
}

/**
 * Refresh hall of fame with latest strategies
 */
async function refreshHallOfFame() {
  try {
    const response = await fetch("/api/evolution/hall-of-fame?limit=10");
    const strategies = await response.json();

    console.log("Hall of Fame strategies:", strategies);

    // Update strategy grid (if exists in DOM)
    const gridElement = document.getElementById("strategy-grid");
    if (!gridElement) return;

    if (strategies.length === 0) {
      gridElement.innerHTML = '<div class="placeholder">No strategies yet. Start evolution to generate some!</div>';
      return;
    }

    // Render strategy cards
    gridElement.innerHTML = strategies.map(strategy => `
      <div class="strategy-card">
        <div class="strategy-header">
          <h3>${strategy.name}</h3>
          <span class="fitness-badge ${strategy.fitness >= 0.8 ? 'excellent' : strategy.fitness >= 0.6 ? 'good' : ''}">${strategy.fitness.toFixed(3)}</span>
        </div>
        <div class="strategy-metrics">
          <div class="metric">
            <span>Sharpe</span>
            <strong>${strategy.sharpe_ratio.toFixed(2)}</strong>
          </div>
          <div class="metric">
            <span>Max DD</span>
            <strong>${(strategy.max_drawdown * 100).toFixed(1)}%</strong>
          </div>
          <div class="metric">
            <span>Win Rate</span>
            <strong>${(strategy.win_rate * 100).toFixed(1)}%</strong>
          </div>
          <div class="metric">
            <span>Trades</span>
            <strong>${strategy.total_trades}</strong>
          </div>
        </div>
        <div class="strategy-footer">
          <div class="strategy-info-row">
            <span class="source">${strategy.source.replace('_', ' ')}</span>
            <span class="generation">Gen ${strategy.generation}</span>
          </div>
          <div class="strategy-actions">
            <button class="action-btn primary-glow" onclick="deployStrategy('${strategy.strategy_id}', '${strategy.name}')" title="Deploy for Trading">
              🚀 Deploy
            </button>
            <button class="action-btn" onclick="selectStrategyInChart('${strategy.strategy_id}')" title="View on Chart">
              📊
            </button>
            <button class="action-btn" onclick="viewStrategyCode('${strategy.strategy_id}')" title="View Code">
              👁️
            </button>
          </div>
        </div>
      </div>
    `).join("");

    // Also update strategy selector in chart panel
    updateStrategySelector(strategies);

  } catch (err) {
    console.error("Failed to refresh hall of fame:", err);
  }
}

/**
 * Update strategy selector dropdown
 */
function updateStrategySelector(strategies) {
  const selector = document.getElementById("strategy-selector");
  if (!selector) return;

  // Keep "Market View" option
  selector.innerHTML = '<option value="">Market View (No Strategy)</option>';

  // Add strategies
  strategies.forEach(strategy => {
    const option = document.createElement("option");
    option.value = strategy.strategy_id;
    option.textContent = `${strategy.name} (${strategy.fitness.toFixed(3)})`;
    option.dataset.fitness = strategy.fitness;
    option.dataset.sharpe = strategy.sharpe_ratio;
    option.dataset.drawdown = strategy.max_drawdown;
    option.dataset.winrate = strategy.win_rate;
    option.dataset.trades = strategy.total_trades;
    option.dataset.pf = strategy.profit_factor;
    selector.appendChild(option);
  });
}

/**
 * Handle strategy selection
 */
function onStrategySelected() {
  const selector = document.getElementById("strategy-selector");
  if (!selector) return;

  const selectedOption = selector.options[selector.selectedIndex];
  const strategyId = selector.value;

  const infoPanel = document.getElementById("strategy-info");
  if (!infoPanel) return;

  if (!strategyId) {
    // Market view - hide info
    infoPanel.style.display = "none";
    return;
  }

  // Show strategy info
  infoPanel.style.display = "block";

  // Update info values
  document.getElementById("info-fitness").textContent = parseFloat(selectedOption.dataset.fitness).toFixed(3);
  document.getElementById("info-sharpe").textContent = parseFloat(selectedOption.dataset.sharpe).toFixed(2);
  document.getElementById("info-drawdown").textContent = (parseFloat(selectedOption.dataset.drawdown) * 100).toFixed(1) + "%";
  document.getElementById("info-winrate").textContent = (parseFloat(selectedOption.dataset.winrate) * 100).toFixed(1) + "%";
  document.getElementById("info-trades").textContent = selectedOption.dataset.trades;
  document.getElementById("info-pf").textContent = parseFloat(selectedOption.dataset.pf).toFixed(2);

  // Color code fitness
  const fitnessElem = document.getElementById("info-fitness");
  if (parseFloat(selectedOption.dataset.fitness) >= 0.8) {
    fitnessElem.classList.add("positive");
    fitnessElem.classList.remove("negative");
  } else if (parseFloat(selectedOption.dataset.fitness) < 0.5) {
    fitnessElem.classList.add("negative");
    fitnessElem.classList.remove("positive");
  } else {
    fitnessElem.classList.remove("positive", "negative");
  }

  // Reload chart with strategy data
  if (typeof loadChart === "function") {
    loadChart().catch(console.error);
  }

  console.log("Selected strategy:", strategyId);
}

/**
 * View strategy code in modal
 */
async function viewStrategyCode(strategyId) {
  try {
    const response = await fetch(`/api/evolution/strategy-code/${strategyId}`);
    const data = await response.json();

    // Show modal with code
    showCodeModal(data.name, data.code, data.language);
  } catch (err) {
    console.error("Failed to load strategy code:", err);
    alert("Failed to load strategy code");
  }
}

/**
 * Show code viewer modal
 */
function showCodeModal(name, code, language) {
  // Check if modal exists, create if not
  let modal = document.getElementById("code-modal");

  if (!modal) {
    modal = document.createElement("div");
    modal.id = "code-modal";
    modal.className = "modal";
    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h3 id="code-modal-title">Strategy Code</h3>
          <button class="modal-close" onclick="closeCodeModal()">&times;</button>
        </div>
        <div class="modal-body">
          <pre id="code-modal-code"><code></code></pre>
        </div>
        <div class="modal-footer">
          <button class="primary ghost" onclick="copyCodeToClipboard()">📋 Copy</button>
          <button class="primary ghost" onclick="closeCodeModal()">Close</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }

  // Update content
  document.getElementById("code-modal-title").textContent = `${name} - Source Code`;
  document.getElementById("code-modal-code").querySelector("code").textContent = code;

  // Show modal
  modal.style.display = "flex";
}

/**
 * Close code modal
 */
function closeCodeModal() {
  const modal = document.getElementById("code-modal");
  if (modal) {
    modal.style.display = "none";
  }
}

/**
 * Copy code to clipboard
 */
async function copyCodeToClipboard() {
  const code = document.getElementById("code-modal-code").querySelector("code").textContent;
  try {
    await navigator.clipboard.writeText(code);
    alert("Code copied to clipboard!");
  } catch (err) {
    console.error("Failed to copy:", err);
    alert("Failed to copy code");
  }
}

/**
 * Select strategy in chart dropdown
 */
function selectStrategyInChart(strategyId) {
  const selector = document.getElementById("strategy-selector");
  if (selector) {
    selector.value = strategyId;
    // Trigger change event
    selector.dispatchEvent(new Event("change"));

    // Scroll to chart
    const chartPanel = document.getElementById("chart-panel");
    if (chartPanel) {
      chartPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }
}

// Make functions global for onclick handlers
window.closeCodeModal = closeCodeModal;
window.copyCodeToClipboard = copyCodeToClipboard;
window.viewStrategyCode = viewStrategyCode;
window.selectStrategyInChart = selectStrategyInChart;

/**
 * Initialize evolution controls
 */
function initEvolutionControls() {
  // Start button
  document.getElementById("start-evolution")?.addEventListener("click", startEvolution);

  // Stop button (placeholder for now)
  document.getElementById("stop-evolution")?.addEventListener("click", () => {
    evolutionActive = false;
    if (evolutionEventSource) {
      evolutionEventSource.close();
      evolutionEventSource = null;
    }
    addFeedMessage("Evolution stopped by user", "info");
  });

  // Strategy selector
  document.getElementById("strategy-selector")?.addEventListener("change", onStrategySelected);

  // Hero "Start Evolution" button - scroll to evolution panel
  document.getElementById("scroll-to-evolution")?.addEventListener("click", () => {
    const evolutionPanel = document.getElementById("evolution-control-panel");
    if (evolutionPanel) {
      evolutionPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      // Focus on start button after scroll
      setTimeout(() => {
        document.getElementById("start-evolution")?.focus();
      }, 500);
    }
  });

  // Load initial hall of fame
  refreshHallOfFame();

  console.log("Evolution controls initialized");
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initEvolutionControls);
} else {
  initEvolutionControls();
}
