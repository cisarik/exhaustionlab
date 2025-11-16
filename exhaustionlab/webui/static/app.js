const state = {
  overview: window.__SEED_OVERVIEW__ || null,
  sessions: [],
  strategies: [],
  selectedSession: null,
};

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    const message = detail?.detail || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return res.json();
}

function setHeroMetrics(overview) {
  if (!overview) return;
  const mappings = {
    totalStrategies: overview.total_strategies,
    bestFitness: overview.best_fitness?.toFixed
      ? overview.best_fitness.toFixed(3)
      : overview.best_fitness,
    avgFitness: overview.avg_fitness?.toFixed
      ? overview.avg_fitness.toFixed(3)
      : overview.avg_fitness,
    velocity: overview.velocity?.toFixed
      ? overview.velocity.toFixed(3)
      : overview.velocity,
  };
  Object.entries(mappings).forEach(([key, value]) => {
    const el = document.querySelector(`[data-metric="${key}"]`);
    if (el) el.textContent = value ?? "0";
  });
}

function renderPhaseBreakdown(overview) {
  const container = document.getElementById("phase-breakdown");
  if (!container || !overview) return;
  container.innerHTML = "";
  Object.entries(overview.phase_breakdown || {}).forEach(([phase, count]) => {
    const chip = document.createElement("div");
    chip.className = "phase-chip";
    chip.textContent = `${phase} · ${count}`;
    container.appendChild(chip);
  });
}

function drawEvolutionChart(points = []) {
  const svg = document.getElementById("evolution-chart");
  if (!svg) return;
  svg.innerHTML = "";
  svg.setAttribute("viewBox", "0 0 1000 260");

  if (!points.length) {
    const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", "50%");
    text.setAttribute("y", "50%");
    text.setAttribute("text-anchor", "middle");
    text.setAttribute("fill", "#94a3b8");
    text.textContent = "No data available";
    svg.appendChild(text);
    return;
  }

  const minFitness = Math.min(...points.map((p) => p.fitness));
  const maxFitness = Math.max(...points.map((p) => p.fitness));
  const range = maxFitness - minFitness || 1;

  const scaleX = (index) => {
    if (points.length === 1) return 500;
    const fraction = index / (points.length - 1);
    return 40 + fraction * 920;
  };
  const scaleY = (fitness) => {
    const normalized = (fitness - minFitness) / range;
    return 220 - normalized * 200;
  };

  const pathPieces = points.map((point, index) => {
    const command = index === 0 ? "M" : "L";
    return `${command} ${scaleX(index)} ${scaleY(point.fitness)}`;
  });

  const stroke = document.createElementNS("http://www.w3.org/2000/svg", "path");
  stroke.setAttribute("d", pathPieces.join(" "));
  stroke.setAttribute("fill", "none");
  stroke.setAttribute("stroke", "#58f5c3");
  stroke.setAttribute("stroke-width", "3");
  stroke.setAttribute("stroke-linecap", "round");
  stroke.setAttribute("stroke-linejoin", "round");

  const fillPath = `${pathPieces.join(" ")} L ${scaleX(points.length - 1)} 240 L 40 240 Z`;
  const fill = document.createElementNS("http://www.w3.org/2000/svg", "path");
  fill.setAttribute("d", fillPath);
  fill.setAttribute("fill", "rgba(88, 245, 195, 0.08)");

  svg.appendChild(fill);
  svg.appendChild(stroke);
}

function renderEvolutionEvents(events = []) {
  const container = document.getElementById("evolution-events");
  if (!container) return;
  container.innerHTML = "";
  if (!events.length) {
    container.innerHTML = '<div class="placeholder small">No recent events</div>';
    return;
  }
  events.forEach((event) => {
    const card = document.createElement("article");
    card.className = "event-card";
    card.innerHTML = `<strong>${event.title}</strong><span>${event.subtitle}</span>`;
    container.appendChild(card);
  });
}

function renderSessions(list = []) {
  const container = document.getElementById("llm-session-list");
  if (!container) return;
  container.innerHTML = "";
  if (!list.length) {
    container.innerHTML =
      '<div class="placeholder small">No debugger sessions found</div>';
    return;
  }
  list.forEach((session) => {
    const item = document.createElement("article");
    item.className = "session-item";
    if (state.selectedSession?.session_id === session.session_id) {
      item.classList.add("active");
    }
    const started = new Date(session.started_at).toLocaleString();
    item.innerHTML = `
      <strong>${session.model || "Unnamed session"}</strong>
      <small>${started}</small>
      <p>${session.preview || "—"}</p>
    `;
    item.addEventListener("click", () => loadSessionDetail(session.session_id));
    container.appendChild(item);
  });
}

function renderConversation(session) {
  const container = document.getElementById("llm-conversation");
  if (!container) return;
  container.innerHTML = "";
  if (!session) {
    container.innerHTML =
      '<div class="placeholder small">Select a session to inspect</div>';
    return;
  }
  session.messages.forEach((message) => {
    const bubble = document.createElement("article");
    bubble.className = `message ${message.role}`;
    bubble.innerHTML = `<strong>${message.role.toUpperCase()}</strong><div>${escapeHtml(
      message.content
    )}</div>`;
    container.appendChild(bubble);
  });
}

function escapeHtml(text = "") {
  const div = document.createElement("div");
  div.innerText = text;
  return div.innerHTML;
}

function renderStrategies(strategies = []) {
  const grid = document.getElementById("strategy-grid");
  if (!grid) return;
  grid.innerHTML = "";
  if (!strategies.length) {
    grid.innerHTML = '<div class="placeholder">No strategies yet.</div>';
    return;
  }
  strategies.forEach((strategy) => {
    const lastMetrics = strategy.recent_metrics?.[0]?.metrics_data || {};
    const card = document.createElement("article");
    card.className = "strategy-card";
    card.innerHTML = `
      <header>
        <div>
          <h3>${strategy.name}</h3>
          <p class="sub">Gen ${strategy.generation} · ${strategy.total_tests} tests</p>
        </div>
        <div class="badges">
          <span class="badge">fitness ${strategy.fitness.toFixed(3)}</span>
          ${strategy.tags
            .map((tag) => `<span class="badge">${tag}</span>`)
            .join("")}
        </div>
      </header>
      <div class="metrics">
        <div><span>Sharpe</span><strong>${(lastMetrics.sharpe_ratio ?? 0).toFixed(
          2
        )}</strong></div>
        <div><span>PnL</span><strong>${(lastMetrics.total_pnl ?? 0).toFixed(
          1
        )}%</strong></div>
        <div><span>Win rate</span><strong>${(
          (lastMetrics.win_rate ?? 0) * 100
        ).toFixed(0)}%</strong></div>
      </div>
      <p class="run-indicator" data-run-indicator="${strategy.strategy_id}">Ready for simulation.</p>
      <div class="actions">
        <button class="primary" data-simulate="${strategy.strategy_id}">Run simulation</button>
      </div>
    `;
    grid.appendChild(card);
  });

  document.querySelectorAll("[data-simulate]").forEach((button) => {
    button.addEventListener("click", () =>
      triggerSimulation(button.dataset.simulate, button)
    );
  });

  const heroSimulation = document.getElementById("launch-simulation");
  if (heroSimulation) {
    heroSimulation.disabled = !strategies.length;
    heroSimulation.onclick = () => {
      if (!strategies.length) return;
      const top = strategies[0];
      const button = document.querySelector(
        `[data-simulate="${top.strategy_id}"]`
      );
      if (button) button.click();
    };
  }
}

async function triggerSimulation(strategyId, button) {
  const indicator = document.querySelector(
    `[data-run-indicator="${strategyId}"]`
  );
  button.disabled = true;
  const original = button.textContent;
  button.textContent = "Simulating…";
  if (indicator) indicator.textContent = "Running multi-market evaluation…";
  try {
    const result = await fetchJson(
      `/api/strategies/${strategyId}/simulate`,
      { method: "POST" }
    );
    if (indicator && result.metrics) {
      const sharpe = result.metrics.sharpe_ratio?.toFixed(2) ?? "0.00";
      const pnl = result.metrics.total_pnl?.toFixed(1) ?? "0.0";
      const dd = result.metrics.max_drawdown
        ? (result.metrics.max_drawdown * 100).toFixed(1)
        : "0.0";
      indicator.textContent = `Sharpe ${sharpe} • PnL ${pnl}% • Max DD ${dd}%`;
    }
  } catch (error) {
    if (indicator) indicator.textContent = `⚠️ ${error.message}`;
  } finally {
    button.disabled = false;
    button.textContent = original;
  }
}

async function loadOverview() {
  try {
    const overview = await fetchJson("/api/evolution/overview");
    state.overview = overview;
    setHeroMetrics(overview);
    renderPhaseBreakdown(overview);
    drawEvolutionChart(overview.timeline || []);
    renderEvolutionEvents(overview.recent_events || []);
  } catch (error) {
    console.error("Failed to load overview", error);
  }
}

async function loadSessions() {
  try {
    const sessions = await fetchJson("/api/llm/sessions");
    state.sessions = sessions;
    renderSessions(sessions);
  } catch (error) {
    console.error("Failed to load sessions", error);
  }
}

async function loadSessionDetail(sessionId) {
  try {
    const session = await fetchJson(`/api/llm/sessions/${sessionId}`);
    state.selectedSession = session;
    renderSessions(state.sessions);
    renderConversation(session);
  } catch (error) {
    console.error("Failed to fetch session detail", error);
  }
}

// Strategy loading delegated to evolution.js
async function loadStrategies() {
  // Evolution.js handles Hall of Fame with refreshHallOfFame()
  if (typeof refreshHallOfFame === "function") {
    try {
      await refreshHallOfFame();
    } catch (error) {
      console.error("Failed to load strategies", error);
    }
  }
}

function attachHandlers() {
  document
    .getElementById("refresh-dashboard")
    ?.addEventListener("click", loadOverview);
  document
    .getElementById("refresh-sessions")
    ?.addEventListener("click", loadSessions);
  document
    .getElementById("refresh-strategies")
    ?.addEventListener("click", loadStrategies);
}

function hydrateSeedOverview() {
  if (!state.overview && window.__SEED_OVERVIEW__) {
    state.overview = window.__SEED_OVERVIEW__;
  }
  if (state.overview) {
    setHeroMetrics(state.overview);
    renderPhaseBreakdown(state.overview);
    drawEvolutionChart(state.overview.timeline || []);
    renderEvolutionEvents(state.overview.recent_events || []);
  }
}

hydrateSeedOverview();
attachHandlers();
loadSessions();
loadStrategies();
loadOverview();

// Chart management
let chartRefreshInterval = null;

async function loadChart() {
  const chartImg = document.getElementById("candlestick-chart");
  const loading = document.getElementById("chart-loading");
  const symbol = document.getElementById("chart-symbol")?.value || "ADAEUR";
  const timeframe = document.getElementById("chart-timeframe")?.value || "1m";
  const strategyId = document.getElementById("strategy-selector")?.value || "";
  const showTrades = document.getElementById("show-trades")?.checked || false;
  const showEquity = document.getElementById("show-equity")?.checked || false;

  if (!chartImg || !loading) return;

  // Show loading state
  loading.classList.remove("hidden");
  chartImg.style.opacity = "0.3";

  try {
    // Build chart URL with cache-busting timestamp
    const params = new URLSearchParams({
      symbol,
      timeframe,
      limit: "200",
      width: "1400",
      height: "800",
      signals: "true",
      volume: (!showEquity).toString(), // Volume or equity, not both
      _t: Date.now(), // Cache buster for real-time updates
    });

    // Add strategy overlay parameters if strategy selected
    if (strategyId) {
      params.set("strategy_id", strategyId);
      params.set("show_trades", showTrades.toString());
      params.set("show_equity", showEquity.toString());
    }

    const chartUrl = `/api/charts/candlestick.png?${params}`;

    // Preload image before showing
    const img = new Image();
    img.onload = () => {
      chartImg.src = chartUrl;
      chartImg.style.opacity = "1";
      loading.classList.add("hidden");
    };
    img.onerror = () => {
      console.error("Failed to load chart");
      loading.classList.add("hidden");
      chartImg.style.opacity = "1";
    };
    img.src = chartUrl;
  } catch (err) {
    console.error("Chart load error:", err);
    loading.classList.add("hidden");
    chartImg.style.opacity = "1";
  }
}

function startChartAutoRefresh() {
  if (chartRefreshInterval) {
    clearInterval(chartRefreshInterval);
  }
  // Auto-refresh every 30 seconds for live updates
  chartRefreshInterval = setInterval(loadChart, 30000);
}

function stopChartAutoRefresh() {
  if (chartRefreshInterval) {
    clearInterval(chartRefreshInterval);
    chartRefreshInterval = null;
  }
}

// Initialize chart on load
loadChart().catch(console.error);
startChartAutoRefresh();

// Chart controls
document
  .getElementById("chart-symbol")
  ?.addEventListener("change", () => loadChart().catch(console.error));
document
  .getElementById("chart-timeframe")
  ?.addEventListener("change", () => loadChart().catch(console.error));
document
  .getElementById("refresh-chart")
  ?.addEventListener("click", () => loadChart().catch(console.error));

// Trade/equity toggle handlers - reload chart when toggled
document
  .getElementById("show-trades")
  ?.addEventListener("change", () => loadChart().catch(console.error));
document
  .getElementById("show-equity")
  ?.addEventListener("change", () => loadChart().catch(console.error));
