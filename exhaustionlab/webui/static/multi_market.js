/**
 * Multi-Market Testing Module
 *
 * Handles:
 * - Market/timeframe configuration
 * - Strategy testing across markets
 * - Results table with sorting and filtering
 */

let multiMarketData = [];
let currentSort = { column: 'avg_fitness', direction: 'desc' };
let selectedMarkets = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];
let selectedTimeframes = ['5m', '15m', '1h'];

/**
 * Initialize multi-market testing module
 */
function initMultiMarketTesting() {
  console.log("Initializing multi-market testing...");

  // Load available markets
  loadAvailableMarkets();

  // Setup event listeners
  setupMultiMarketListeners();

  // Try to load cached results
  loadMultiMarketResults();
}

/**
 * Setup event listeners for multi-market testing
 */
function setupMultiMarketListeners() {
  // Test all markets button
  const testBtn = document.getElementById('test-all-markets');
  if (testBtn) {
    testBtn.addEventListener('click', runMultiMarketTest);
  }

  // Configure markets button
  const configBtn = document.getElementById('configure-markets');
  if (configBtn) {
    configBtn.addEventListener('click', showMarketConfig);
  }

  // Apply config button
  const applyBtn = document.getElementById('apply-config');
  if (applyBtn) {
    applyBtn.addEventListener('click', applyConfigAndTest);
  }

  // Cancel config button
  const cancelBtn = document.getElementById('cancel-config');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', hideMarketConfig);
  }

  // Search input
  const searchInput = document.getElementById('strategy-search');
  if (searchInput) {
    searchInput.addEventListener('input', filterMultiMarketResults);
  }

  // Filter checkboxes
  const approvedFilter = document.getElementById('filter-approved');
  if (approvedFilter) {
    approvedFilter.addEventListener('change', filterMultiMarketResults);
  }

  const fitnessFilter = document.getElementById('filter-high-fitness');
  if (fitnessFilter) {
    fitnessFilter.addEventListener('change', filterMultiMarketResults);
  }

  // Table sorting
  const sortHeaders = document.querySelectorAll('.multi-market-table th.sortable');
  sortHeaders.forEach(header => {
    header.addEventListener('click', (e) => {
      const column = header.getAttribute('data-sort');
      sortMultiMarketTable(column);
    });
  });
}

/**
 * Load available markets and timeframes
 */
async function loadAvailableMarkets() {
  try {
    const response = await fetch('/api/multi-market/available-markets');
    const data = await response.json();

    // Populate market selector
    const marketSelector = document.getElementById('market-selector');
    if (marketSelector && data.symbols) {
      marketSelector.innerHTML = data.symbols.map(market => `
        <label class="checkbox-label">
          <input type="checkbox" value="${market.value}" ${selectedMarkets.includes(market.value) ? 'checked' : ''}>
          ${market.label}
        </label>
      `).join('');
    }

    // Populate timeframe selector
    const timeframeSelector = document.getElementById('timeframe-selector');
    if (timeframeSelector && data.timeframes) {
      timeframeSelector.innerHTML = data.timeframes.map(tf => `
        <label class="checkbox-label">
          <input type="checkbox" value="${tf.value}" ${selectedTimeframes.includes(tf.value) ? 'checked' : ''}>
          ${tf.label}
        </label>
      `).join('');
    }

  } catch (err) {
    console.error("Failed to load available markets:", err);
  }
}

/**
 * Show market configuration panel
 */
function showMarketConfig() {
  const configPanel = document.getElementById('market-config-panel');
  if (configPanel) {
    configPanel.style.display = 'block';
  }
}

/**
 * Hide market configuration panel
 */
function hideMarketConfig() {
  const configPanel = document.getElementById('market-config-panel');
  if (configPanel) {
    configPanel.style.display = 'none';
  }
}

/**
 * Apply configuration and run test
 */
async function applyConfigAndTest() {
  // Get selected markets
  const marketCheckboxes = document.querySelectorAll('#market-selector input[type="checkbox"]:checked');
  selectedMarkets = Array.from(marketCheckboxes).map(cb => cb.value);

  // Get selected timeframes
  const tfCheckboxes = document.querySelectorAll('#timeframe-selector input[type="checkbox"]:checked');
  selectedTimeframes = Array.from(tfCheckboxes).map(cb => cb.value);

  // Validate
  if (selectedMarkets.length === 0) {
    alert("Please select at least one market");
    return;
  }

  if (selectedTimeframes.length === 0) {
    alert("Please select at least one timeframe");
    return;
  }

  // Hide config panel
  hideMarketConfig();

  // Run test
  await runMultiMarketTest();
}

/**
 * Run multi-market test
 */
async function runMultiMarketTest() {
  const testBtn = document.getElementById('test-all-markets');

  try {
    // Disable button
    if (testBtn) {
      testBtn.disabled = true;
      testBtn.textContent = '⏳ Testing...';
    }

    // Show loading in table
    const tbody = document.getElementById('multi-market-tbody');
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="empty-state">
            <div class="spinner"></div>
            <p>Testing strategies across ${selectedMarkets.length} markets × ${selectedTimeframes.length} timeframes...</p>
            <p class="sub">This may take a few moments.</p>
          </td>
        </tr>
      `;
    }

    // Make API request
    const response = await fetch('/api/multi-market/test', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        strategy_ids: [],  // Empty = test all
        symbols: selectedMarkets,
        timeframes: selectedTimeframes,
        lookback_days: 30
      })
    });

    const result = await response.json();

    if (result.status === 'completed') {
      multiMarketData = result.results;
      renderMultiMarketTable();

      // Show success message
      addFeedMessage(
        `Multi-market testing completed! Tested ${result.total_strategies} strategies across ${result.total_markets} markets.`,
        'success'
      );
    } else {
      throw new Error(result.message || 'Test failed');
    }

  } catch (err) {
    console.error("Multi-market test failed:", err);
    addFeedMessage(`Multi-market test failed: ${err.message}`, 'error');

    const tbody = document.getElementById('multi-market-tbody');
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" class="empty-state">
            <p>❌ Test failed: ${err.message}</p>
            <p class="sub">Please try again or check the console for details.</p>
          </td>
        </tr>
      `;
    }

  } finally {
    // Re-enable button
    if (testBtn) {
      testBtn.disabled = false;
      testBtn.textContent = '🧪 Test All Markets';
    }
  }
}

/**
 * Load cached multi-market results
 */
async function loadMultiMarketResults() {
  try {
    const response = await fetch('/api/multi-market/results');
    const data = await response.json();

    if (data.status === 'completed' && data.results && data.results.length > 0) {
      multiMarketData = data.results;
      renderMultiMarketTable();
    }
  } catch (err) {
    console.log("No cached results available");
  }
}

/**
 * Render multi-market results table
 */
function renderMultiMarketTable() {
  const tbody = document.getElementById('multi-market-tbody');
  if (!tbody) return;

  // Apply filters
  let filteredData = filterData(multiMarketData);

  // Apply sorting
  filteredData = sortData(filteredData);

  if (filteredData.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9" class="empty-state">
          <p>No results match current filters.</p>
          <p class="sub">Try adjusting your filters or run a new test.</p>
        </td>
      </tr>
    `;
    return;
  }

  // Render rows
  tbody.innerHTML = filteredData.map(strategy => `
    <tr class="result-row ${strategy.status === 'approved' ? 'approved' : 'rejected'}">
      <td class="strategy-name">
        <strong>${strategy.strategy_name}</strong>
        <small>${strategy.strategy_id.substring(0, 8)}</small>
      </td>
      <td class="fitness-value">${strategy.avg_fitness.toFixed(4)}</td>
      <td class="sharpe-value">${strategy.avg_sharpe.toFixed(2)}</td>
      <td class="pass-rate-value">
        <div class="progress-bar">
          <div class="progress-fill" style="width: ${strategy.pass_rate * 100}%"></div>
        </div>
        <span>${(strategy.pass_rate * 100).toFixed(1)}%</span>
      </td>
      <td class="drawdown-value ${strategy.max_drawdown > 0.3 ? 'warning' : ''}">${(strategy.max_drawdown * 100).toFixed(1)}%</td>
      <td class="winrate-value">${(strategy.avg_win_rate * 100).toFixed(1)}%</td>
      <td class="markets-passed-value">
        <span class="${strategy.markets_passed < strategy.markets_tested * 0.6 ? 'warning' : 'success'}">
          ${strategy.markets_passed}/${strategy.markets_tested}
        </span>
      </td>
      <td class="status-value">
        <span class="status-badge ${strategy.status}">
          ${strategy.status === 'approved' ? '✓ Approved' : '✗ Rejected'}
        </span>
      </td>
      <td class="actions">
        <button class="btn-small" onclick="viewMarketDetails('${strategy.strategy_id}')">📊 Details</button>
        ${strategy.status === 'approved' ? `<button class="btn-small primary" onclick="deployStrategy('${strategy.strategy_id}')">🚀 Deploy</button>` : ''}
      </td>
    </tr>
  `).join('');
}

/**
 * Filter multi-market data based on search and filters
 */
function filterData(data) {
  const searchTerm = document.getElementById('strategy-search')?.value.toLowerCase() || '';
  const approvedOnly = document.getElementById('filter-approved')?.checked || false;
  const highFitnessOnly = document.getElementById('filter-high-fitness')?.checked || false;

  return data.filter(strategy => {
    // Search filter
    if (searchTerm && !strategy.strategy_name.toLowerCase().includes(searchTerm) && !strategy.strategy_id.includes(searchTerm)) {
      return false;
    }

    // Approved filter
    if (approvedOnly && strategy.status !== 'approved') {
      return false;
    }

    // High fitness filter
    if (highFitnessOnly && strategy.avg_fitness < 0.7) {
      return false;
    }

    return true;
  });
}

/**
 * Sort multi-market data
 */
function sortData(data) {
  const { column, direction } = currentSort;

  return [...data].sort((a, b) => {
    let aVal = a[column];
    let bVal = b[column];

    // Handle string comparisons
    if (typeof aVal === 'string') {
      aVal = aVal.toLowerCase();
      bVal = bVal.toLowerCase();
    }

    if (direction === 'asc') {
      return aVal > bVal ? 1 : -1;
    } else {
      return aVal < bVal ? 1 : -1;
    }
  });
}

/**
 * Sort multi-market table by column
 */
function sortMultiMarketTable(column) {
  // Toggle direction if same column
  if (currentSort.column === column) {
    currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
  } else {
    currentSort.column = column;
    currentSort.direction = 'desc';
  }

  // Update header classes
  const headers = document.querySelectorAll('.multi-market-table th.sortable');
  headers.forEach(header => {
    header.classList.remove('active', 'asc', 'desc');
    const icon = header.querySelector('.sort-icon');
    if (icon) icon.textContent = '↕';
  });

  // Mark active column
  const activeHeader = document.querySelector(`.multi-market-table th[data-sort="${column}"]`);
  if (activeHeader) {
    activeHeader.classList.add('active', currentSort.direction);
    const icon = activeHeader.querySelector('.sort-icon');
    if (icon) icon.textContent = currentSort.direction === 'asc' ? '↑' : '↓';
  }

  // Re-render table
  renderMultiMarketTable();
}

/**
 * Filter multi-market results
 */
function filterMultiMarketResults() {
  renderMultiMarketTable();
}

/**
 * View detailed market results for a strategy
 */
function viewMarketDetails(strategyId) {
  const strategy = multiMarketData.find(s => s.strategy_id === strategyId);
  if (!strategy) return;

  // Build detailed view
  const detailsHTML = `
    <div class="market-details-modal">
      <h3>${strategy.strategy_name}</h3>
      <p>Strategy ID: ${strategy.strategy_id}</p>

      <div class="summary-metrics">
        <div class="metric">
          <span class="label">Average Fitness</span>
          <span class="value">${strategy.avg_fitness.toFixed(4)}</span>
        </div>
        <div class="metric">
          <span class="label">Pass Rate</span>
          <span class="value">${(strategy.pass_rate * 100).toFixed(1)}%</span>
        </div>
        <div class="metric">
          <span class="label">Markets Passed</span>
          <span class="value">${strategy.markets_passed}/${strategy.markets_tested}</span>
        </div>
      </div>

      <h4>Per-Market Results</h4>
      <table class="market-details-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Timeframe</th>
            <th>Fitness</th>
            <th>Sharpe</th>
            <th>Max DD</th>
            <th>Win Rate</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${strategy.market_results.map(m => `
            <tr class="${m.passed ? 'passed' : 'failed'}">
              <td>${m.symbol}</td>
              <td>${m.timeframe}</td>
              <td>${m.fitness.toFixed(4)}</td>
              <td>${m.sharpe_ratio.toFixed(2)}</td>
              <td>${(m.max_drawdown * 100).toFixed(1)}%</td>
              <td>${(m.win_rate * 100).toFixed(1)}%</td>
              <td>${m.passed ? '✓ Pass' : '✗ Fail'}</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;

  // Show in modal (you'll need to add a modal component)
  alert("Market details view - implement modal here\n\n" +
        `Strategy: ${strategy.strategy_name}\n` +
        `Pass Rate: ${(strategy.pass_rate * 100).toFixed(1)}%\n` +
        `Markets Passed: ${strategy.markets_passed}/${strategy.markets_tested}`);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initMultiMarketTesting);
} else {
  initMultiMarketTesting();
}
