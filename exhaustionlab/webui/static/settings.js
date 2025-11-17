/**
 * Settings Management
 */

let currentSettings = {};

// Open settings modal
function openSettings() {
  const modal = document.getElementById("settings-modal");
  if (modal) {
    modal.style.display = "flex";
    loadSettings();
  }
}

// Close settings modal
function closeSettings() {
  const modal = document.getElementById("settings-modal");
  if (modal) {
    modal.style.display = "none";
  }
}

// Load settings from API
async function loadSettings() {
  try {
    const response = await fetch("/api/settings");
    if (!response.ok) throw new Error("Failed to load settings");

    currentSettings = await response.json();
    populateForm(currentSettings);
  } catch (error) {
    console.error("Load settings error:", error);
    alert("Failed to load settings: " + error.message);
  }
}

// Populate form with settings
function populateForm(settings) {
  // Exchange
  const ex = settings.exchange;
  document.getElementById("settings-exchange").value = ex.exchange;
  document.getElementById("settings-api-key").value = ex.api_key === "***MASKED***" ? "" : ex.api_key;
  document.getElementById("settings-api-secret").value = ex.api_secret === "***MASKED***" ? "" : ex.api_secret;
  document.getElementById("settings-testnet").checked = ex.testnet;
  document.getElementById("settings-default-symbol").value = ex.default_symbol;
  document.getElementById("settings-default-timeframe").value = ex.default_timeframe;

  // LLM
  const llm = settings.llm;
  document.getElementById("settings-llm-enabled").checked = llm.enabled;
  document.getElementById("settings-llm-provider").value = llm.provider;
  document.getElementById("settings-llm-url").value = llm.api_url;
  document.getElementById("settings-llm-key").value = llm.api_key === "***MASKED***" ? "" : llm.api_key;
  document.getElementById("settings-llm-model").value = llm.model;
  document.getElementById("settings-llm-temp").value = llm.temperature;
  document.getElementById("settings-llm-tokens").value = llm.max_tokens;
  document.getElementById("settings-llm-timeout").value = llm.timeout;

  // Risk
  const risk = settings.risk;
  document.getElementById("settings-risk-position").value = (risk.max_position_size * 100).toFixed(1);
  document.getElementById("settings-risk-daily").value = (risk.max_daily_loss * 100).toFixed(1);
  document.getElementById("settings-risk-drawdown").value = (risk.max_drawdown * 100).toFixed(1);
  document.getElementById("settings-risk-positions").value = risk.max_open_positions;
  document.getElementById("settings-risk-sl").checked = risk.enable_stop_loss;
  document.getElementById("settings-risk-sl-pct").value = (risk.stop_loss_pct * 100).toFixed(1);
  document.getElementById("settings-risk-tp").checked = risk.enable_take_profit;
  document.getElementById("settings-risk-tp-pct").value = (risk.take_profit_pct * 100).toFixed(1);

  // Evolution
  const evo = settings.evolution;
  document.getElementById("settings-evo-gens").value = evo.default_generations;
  document.getElementById("settings-evo-pop").value = evo.default_population;
  document.getElementById("settings-evo-llm").checked = evo.use_llm;
  document.getElementById("settings-evo-crawled").checked = evo.use_crawled;
  document.getElementById("settings-evo-days").value = evo.backtest_data_days;
  document.getElementById("settings-evo-metric").value = evo.fitness_metric;

  // UI
  const ui = settings.ui;
  document.getElementById("settings-ui-theme").value = ui.theme;
  document.getElementById("settings-ui-autorefresh").checked = ui.auto_refresh;
  document.getElementById("settings-ui-interval").value = ui.refresh_interval;
  document.getElementById("settings-ui-symbol").value = ui.chart_default_symbol;
  document.getElementById("settings-ui-tf").value = ui.chart_default_timeframe;
  document.getElementById("settings-ui-notifications").checked = ui.notifications_enabled;
  document.getElementById("settings-ui-sound").checked = ui.sound_enabled;
}

// Save settings
async function saveSettings() {
  const updates = {
    exchange: {
      exchange: document.getElementById("settings-exchange").value,
      api_key: document.getElementById("settings-api-key").value,
      api_secret: document.getElementById("settings-api-secret").value,
      testnet: document.getElementById("settings-testnet").checked,
      default_symbol: document.getElementById("settings-default-symbol").value,
      default_timeframe: document.getElementById("settings-default-timeframe").value,
    },
    llm: {
      enabled: document.getElementById("settings-llm-enabled").checked,
      provider: document.getElementById("settings-llm-provider").value,
      api_url: document.getElementById("settings-llm-url").value,
      api_key: document.getElementById("settings-llm-key").value,
      model: document.getElementById("settings-llm-model").value,
      temperature: parseFloat(document.getElementById("settings-llm-temp").value),
      max_tokens: parseInt(document.getElementById("settings-llm-tokens").value),
      timeout: parseInt(document.getElementById("settings-llm-timeout").value),
    },
    risk: {
      max_position_size: parseFloat(document.getElementById("settings-risk-position").value) / 100,
      max_daily_loss: parseFloat(document.getElementById("settings-risk-daily").value) / 100,
      max_drawdown: parseFloat(document.getElementById("settings-risk-drawdown").value) / 100,
      max_open_positions: parseInt(document.getElementById("settings-risk-positions").value),
      enable_stop_loss: document.getElementById("settings-risk-sl").checked,
      stop_loss_pct: parseFloat(document.getElementById("settings-risk-sl-pct").value) / 100,
      enable_take_profit: document.getElementById("settings-risk-tp").checked,
      take_profit_pct: parseFloat(document.getElementById("settings-risk-tp-pct").value) / 100,
    },
    evolution: {
      default_generations: parseInt(document.getElementById("settings-evo-gens").value),
      default_population: parseInt(document.getElementById("settings-evo-pop").value),
      use_llm: document.getElementById("settings-evo-llm").checked,
      use_crawled: document.getElementById("settings-evo-crawled").checked,
      backtest_data_days: parseInt(document.getElementById("settings-evo-days").value),
      fitness_metric: document.getElementById("settings-evo-metric").value,
    },
    ui: {
      theme: document.getElementById("settings-ui-theme").value,
      auto_refresh: document.getElementById("settings-ui-autorefresh").checked,
      refresh_interval: parseInt(document.getElementById("settings-ui-interval").value),
      chart_default_symbol: document.getElementById("settings-ui-symbol").value,
      chart_default_timeframe: document.getElementById("settings-ui-tf").value,
      notifications_enabled: document.getElementById("settings-ui-notifications").checked,
      sound_enabled: document.getElementById("settings-ui-sound").checked,
    },
  };

  try {
    const response = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    });

    if (!response.ok) throw new Error("Failed to save settings");

    alert("✅ Settings saved successfully!");
    closeSettings();
  } catch (error) {
    console.error("Save settings error:", error);
    alert("Failed to save settings: " + error.message);
  }
}

// Reset settings
async function resetSettings() {
  if (!confirm("Reset all settings to defaults?")) return;

  try {
    const response = await fetch("/api/settings/reset", { method: "POST" });
    if (!response.ok) throw new Error("Failed to reset settings");

    alert("✅ Settings reset to defaults!");
    await loadSettings();
  } catch (error) {
    console.error("Reset settings error:", error);
    alert("Failed to reset settings: " + error.message);
  }
}

// Validate exchange
async function validateExchange() {
  const msg = document.getElementById("exchange-validation");
  msg.textContent = "Testing...";
  msg.className = "validation-message info";

  try {
    const response = await fetch("/api/settings/validate/exchange");
    const result = await response.json();
    msg.textContent = result.message;
    msg.className = result.valid ? "validation-message success" : "validation-message error";
  } catch (error) {
    msg.textContent = "Connection test failed";
    msg.className = "validation-message error";
  }
}

// Validate LLM
async function validateLLM() {
  const msg = document.getElementById("llm-validation");
  msg.textContent = "Testing...";
  msg.className = "validation-message info";

  try {
    const response = await fetch("/api/settings/validate/llm");
    const result = await response.json();
    msg.textContent = result.message;
    msg.className = result.valid ? "validation-message success" : "validation-message error";
  } catch (error) {
    msg.textContent = "Connection test failed";
    msg.className = "validation-message error";
  }
}

// Tab switching
function switchTab(tabName) {
  // Update tab buttons
  document.querySelectorAll(".settings-tab").forEach(tab => {
    tab.classList.toggle("active", tab.dataset.tab === tabName);
  });

  // Update panels
  document.querySelectorAll(".settings-panel").forEach(panel => {
    panel.classList.toggle("active", panel.dataset.panel === tabName);
  });
}

// Global functions
window.openSettings = openSettings;
window.closeSettings = closeSettings;
window.saveSettings = saveSettings;
window.resetSettings = resetSettings;
window.validateExchange = validateExchange;
window.validateLLM = validateLLM;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  // Settings button
  const openBtn = document.getElementById("open-settings");
  if (openBtn) {
    openBtn.addEventListener("click", openSettings);
  }

  // Tab switching
  document.querySelectorAll(".settings-tab").forEach(tab => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
  });

  // Close on outside click
  const modal = document.getElementById("settings-modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) closeSettings();
    });
  }
});
