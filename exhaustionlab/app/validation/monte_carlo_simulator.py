"""
Monte Carlo Simulation for Robustness Testing

Stress-test strategies with:
- Parameter sensitivity analysis
- Bootstrap confidence intervals
- Worst-case scenario testing
- Probability of ruin calculation
- Random walk analysis
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SimulationType(Enum):
    """Types of Monte Carlo simulations."""

    BOOTSTRAP = "bootstrap"  # Resample returns
    PARAMETER_VARIATION = "parameter_variation"  # Vary strategy parameters
    RANDOM_ENTRY = "random_entry"  # Random entry timing
    MARKET_STRESS = "market_stress"  # Adverse conditions


@dataclass
class SimulationRun:
    """Single simulation run result."""

    run_id: int
    simulation_type: SimulationType

    # Performance metrics
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float

    # Parameters used (for sensitivity analysis)
    parameters: Optional[Dict] = None


@dataclass
class SimulationResult:
    """Complete Monte Carlo simulation result."""

    # Simulation settings
    num_simulations: int
    simulation_type: SimulationType

    # Distribution statistics
    mean_return: float
    median_return: float
    std_return: float
    min_return: float
    max_return: float

    # Confidence intervals (95%)
    return_ci_lower: float
    return_ci_upper: float
    sharpe_ci_lower: float
    sharpe_ci_upper: float

    # Risk metrics
    probability_of_profit: float  # P(return > 0)
    probability_of_ruin: float  # P(drawdown > 50%)
    value_at_risk_95: float  # 95% VaR
    conditional_var_95: float  # CVaR / Expected Shortfall

    # Robustness assessment
    robust_to_parameters: bool  # Consistent across parameter variations
    robust_to_timing: bool  # Consistent across different entry times
    robust_to_stress: bool  # Survives stress scenarios

    # Overall robustness score
    robustness_score: float  # 0-100

    # Individual runs
    runs: List[SimulationRun] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "num_simulations": self.num_simulations,
            "simulation_type": self.simulation_type.value,
            "mean_return": self.mean_return,
            "median_return": self.median_return,
            "std_return": self.std_return,
            "return_ci_lower": self.return_ci_lower,
            "return_ci_upper": self.return_ci_upper,
            "probability_of_profit": self.probability_of_profit,
            "probability_of_ruin": self.probability_of_ruin,
            "value_at_risk_95": self.value_at_risk_95,
            "robustness_score": self.robustness_score,
            "robust_to_parameters": self.robust_to_parameters,
            "robust_to_timing": self.robust_to_timing,
            "robust_to_stress": self.robust_to_stress,
        }


class MonteCarloSimulator:
    """
    Monte Carlo simulation for strategy robustness testing.

    Simulations:
    1. Bootstrap: Resample historical returns
    2. Parameter Sensitivity: Test with varied parameters
    3. Random Entry: Test different entry timings
    4. Market Stress: Test under adverse conditions
    """

    def __init__(
        self,
        num_simulations: int = 1000,
        confidence_level: float = 0.95,
        max_workers: int = 4,
        seed: Optional[int] = None,
    ):
        """
        Initialize Monte Carlo simulator.

        Args:
            num_simulations: Number of simulation runs
            confidence_level: Confidence level for intervals
            max_workers: Max parallel workers
            seed: Random seed for reproducibility
        """
        self.num_simulations = num_simulations
        self.confidence_level = confidence_level
        self.max_workers = max_workers

        if seed is not None:
            np.random.seed(seed)

    def run_bootstrap_simulation(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
    ) -> SimulationResult:
        """
        Bootstrap simulation: resample returns.

        Tests if observed performance could be due to luck.
        """
        logger.info(f"Running bootstrap simulation ({self.num_simulations} runs)")

        runs = []
        for i in range(self.num_simulations):
            # Resample returns with replacement
            resampled_returns = returns.sample(n=len(returns), replace=True)

            # Reconstruct equity curve
            sim_equity = pd.Series([1.0])
            for ret in resampled_returns:
                sim_equity = pd.concat([sim_equity, pd.Series([sim_equity.iloc[-1] * (1 + ret)])])

            # Calculate metrics
            total_return = (sim_equity.iloc[-1] / sim_equity.iloc[0]) - 1
            sharpe = self._calculate_sharpe(resampled_returns)
            max_dd = self._calculate_max_drawdown(sim_equity)
            win_rate = (resampled_returns > 0).sum() / len(resampled_returns)

            runs.append(
                SimulationRun(
                    run_id=i,
                    simulation_type=SimulationType.BOOTSTRAP,
                    total_return=total_return,
                    sharpe_ratio=sharpe,
                    max_drawdown=max_dd,
                    win_rate=win_rate,
                )
            )

        return self._aggregate_runs(runs, SimulationType.BOOTSTRAP)

    def run_parameter_sensitivity(
        self,
        strategy_func: Callable[[pd.DataFrame, Dict], Tuple[pd.DataFrame, pd.Series]],
        data: pd.DataFrame,
        base_params: Dict,
        param_ranges: Dict[str, Tuple[float, float]],
    ) -> SimulationResult:
        """
        Parameter sensitivity analysis.

        Tests strategy robustness to parameter variations.

        Args:
            strategy_func: Strategy function with parameters
            data: Market data
            base_params: Base parameters
            param_ranges: Dict of param -> (min, max) ranges
        """
        logger.info(f"Running parameter sensitivity analysis ({self.num_simulations} runs)")

        runs = []
        for i in range(self.num_simulations):
            # Generate random parameter variation
            varied_params = base_params.copy()
            for param, (min_val, max_val) in param_ranges.items():
                varied_params[param] = np.random.uniform(min_val, max_val)

            try:
                # Run strategy with varied parameters
                trades, equity = strategy_func(data, varied_params)

                # Calculate metrics
                total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
                returns = equity.pct_change().dropna()
                sharpe = self._calculate_sharpe(returns)
                max_dd = self._calculate_max_drawdown(equity)
                win_rate = (trades["pnl"] > 0).sum() / len(trades) if "pnl" in trades.columns and len(trades) > 0 else 0

                runs.append(
                    SimulationRun(
                        run_id=i,
                        simulation_type=SimulationType.PARAMETER_VARIATION,
                        total_return=total_return,
                        sharpe_ratio=sharpe,
                        max_drawdown=max_dd,
                        win_rate=win_rate,
                        parameters=varied_params,
                    )
                )

            except Exception as e:
                logger.warning(f"Simulation run {i} failed: {e}")
                continue

        if not runs:
            raise RuntimeError("All parameter sensitivity runs failed")

        return self._aggregate_runs(runs, SimulationType.PARAMETER_VARIATION)

    def run_random_entry_simulation(
        self,
        strategy_func: Callable[[pd.DataFrame], Tuple[pd.DataFrame, pd.Series]],
        data: pd.DataFrame,
        max_offset_pct: float = 0.2,
    ) -> SimulationResult:
        """
        Random entry timing simulation.

        Tests if strategy performance depends on specific entry timing.

        Args:
            strategy_func: Strategy function
            data: Market data
            max_offset_pct: Maximum data offset (% of total)
        """
        logger.info(f"Running random entry simulation ({self.num_simulations} runs)")

        total_len = len(data)
        max_offset = int(total_len * max_offset_pct)

        runs = []
        for i in range(self.num_simulations):
            # Random start offset
            offset = np.random.randint(0, max_offset)

            # Slice data
            sliced_data = data.iloc[offset:]

            if len(sliced_data) < 100:  # Minimum data
                continue

            try:
                # Run strategy
                trades, equity = strategy_func(sliced_data)

                # Calculate metrics
                total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
                returns = equity.pct_change().dropna()
                sharpe = self._calculate_sharpe(returns)
                max_dd = self._calculate_max_drawdown(equity)
                win_rate = (trades["pnl"] > 0).sum() / len(trades) if "pnl" in trades.columns and len(trades) > 0 else 0

                runs.append(
                    SimulationRun(
                        run_id=i,
                        simulation_type=SimulationType.RANDOM_ENTRY,
                        total_return=total_return,
                        sharpe_ratio=sharpe,
                        max_drawdown=max_dd,
                        win_rate=win_rate,
                    )
                )

            except Exception as e:
                logger.warning(f"Simulation run {i} failed: {e}")
                continue

        if not runs:
            raise RuntimeError("All random entry runs failed")

        return self._aggregate_runs(runs, SimulationType.RANDOM_ENTRY)

    def run_stress_test(
        self,
        strategy_func: Callable[[pd.DataFrame], Tuple[pd.DataFrame, pd.Series]],
        data: pd.DataFrame,
        stress_scenarios: Optional[List[str]] = None,
    ) -> SimulationResult:
        """
        Stress test with adverse market conditions.

        Tests strategy under:
        - Flash crashes
        - Extended drawdowns
        - High volatility spikes
        - Liquidity dry-ups

        Args:
            strategy_func: Strategy function
            data: Market data
            stress_scenarios: List of scenarios to test
        """
        scenarios = stress_scenarios or [
            "flash_crash",
            "extended_drawdown",
            "high_volatility",
        ]

        logger.info(f"Running stress test ({len(scenarios)} scenarios × {self.num_simulations // len(scenarios)} runs each)")

        runs = []
        runs_per_scenario = self.num_simulations // len(scenarios)

        for scenario in scenarios:
            for i in range(runs_per_scenario):
                # Apply stress scenario
                stressed_data = self._apply_stress_scenario(data.copy(), scenario)

                try:
                    # Run strategy on stressed data
                    trades, equity = strategy_func(stressed_data)

                    # Calculate metrics
                    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
                    returns = equity.pct_change().dropna()
                    sharpe = self._calculate_sharpe(returns)
                    max_dd = self._calculate_max_drawdown(equity)
                    win_rate = (trades["pnl"] > 0).sum() / len(trades) if "pnl" in trades.columns and len(trades) > 0 else 0

                    runs.append(
                        SimulationRun(
                            run_id=len(runs),
                            simulation_type=SimulationType.MARKET_STRESS,
                            total_return=total_return,
                            sharpe_ratio=sharpe,
                            max_drawdown=max_dd,
                            win_rate=win_rate,
                            parameters={"scenario": scenario},
                        )
                    )

                except Exception as e:
                    logger.warning(f"Stress test run {i} (scenario: {scenario}) failed: {e}")
                    continue

        if not runs:
            raise RuntimeError("All stress test runs failed")

        return self._aggregate_runs(runs, SimulationType.MARKET_STRESS)

    def _apply_stress_scenario(self, data: pd.DataFrame, scenario: str) -> pd.DataFrame:
        """Apply stress scenario to market data."""
        if scenario == "flash_crash":
            # Simulate flash crash: sudden 10-20% drop
            crash_idx = np.random.randint(len(data) // 4, 3 * len(data) // 4)
            crash_magnitude = np.random.uniform(0.10, 0.20)
            data.loc[data.index[crash_idx] :, ["open", "high", "low", "close"]] *= 1 - crash_magnitude

        elif scenario == "extended_drawdown":
            # Simulate extended bear market: gradual 30-50% decline
            start_idx = np.random.randint(0, len(data) // 3)
            end_idx = start_idx + np.random.randint(len(data) // 4, len(data) // 2)
            decline = np.linspace(1.0, np.random.uniform(0.5, 0.7), end_idx - start_idx)
            data.loc[data.index[start_idx:end_idx], ["open", "high", "low", "close"]] *= decline[:, np.newaxis]

        elif scenario == "high_volatility":
            # Increase volatility by 3-5x
            returns = data["close"].pct_change()
            volatility_multiplier = np.random.uniform(3, 5)
            stressed_returns = returns * volatility_multiplier
            stressed_close = (1 + stressed_returns).cumprod() * data["close"].iloc[0]
            data["close"] = stressed_close
            data["open"] = stressed_close * (1 + np.random.randn(len(data)) * 0.01)
            data["high"] = data[["open", "close"]].max(axis=1) * (1 + abs(np.random.randn(len(data)) * 0.01))
            data["low"] = data[["open", "close"]].min(axis=1) * (1 - abs(np.random.randn(len(data)) * 0.01))

        return data

    def _aggregate_runs(self, runs: List[SimulationRun], sim_type: SimulationType) -> SimulationResult:
        """Aggregate simulation runs into result."""
        returns = [r.total_return for r in runs]
        sharpes = [r.sharpe_ratio for r in runs]
        drawdowns = [r.max_drawdown for r in runs]

        # Distribution statistics
        mean_return = np.mean(returns)
        median_return = np.median(returns)
        std_return = np.std(returns)
        min_return = np.min(returns)
        max_return = np.max(returns)

        # Confidence intervals
        alpha = 1 - self.confidence_level
        return_ci = np.percentile(returns, [alpha / 2 * 100, (1 - alpha / 2) * 100])
        sharpe_ci = np.percentile(sharpes, [alpha / 2 * 100, (1 - alpha / 2) * 100])

        # Risk metrics
        prob_profit = (np.array(returns) > 0).sum() / len(returns)
        prob_ruin = (np.array(drawdowns) > 0.5).sum() / len(runs)
        var_95 = np.percentile(returns, 5)

        # CVaR: average of returns below VaR
        returns_below_var = [r for r in returns if r <= var_95]
        cvar_95 = np.mean(returns_below_var) if returns_below_var else var_95

        # Robustness assessment
        robust_to_params = sim_type == SimulationType.PARAMETER_VARIATION and std_return < abs(mean_return) * 0.5  # CV < 0.5

        robust_to_timing = sim_type == SimulationType.RANDOM_ENTRY and prob_profit > 0.7  # 70%+ profitable

        robust_to_stress = sim_type == SimulationType.MARKET_STRESS and mean_return > 0 and prob_profit > 0.6

        # Overall robustness score
        robustness_score = self._calculate_robustness_score(mean_return, std_return, prob_profit, prob_ruin, sharpe_ci)

        return SimulationResult(
            num_simulations=len(runs),
            simulation_type=sim_type,
            mean_return=mean_return,
            median_return=median_return,
            std_return=std_return,
            min_return=min_return,
            max_return=max_return,
            return_ci_lower=return_ci[0],
            return_ci_upper=return_ci[1],
            sharpe_ci_lower=sharpe_ci[0],
            sharpe_ci_upper=sharpe_ci[1],
            probability_of_profit=prob_profit,
            probability_of_ruin=prob_ruin,
            value_at_risk_95=var_95,
            conditional_var_95=cvar_95,
            robust_to_parameters=robust_to_params,
            robust_to_timing=robust_to_timing,
            robust_to_stress=robust_to_stress,
            robustness_score=robustness_score,
            runs=runs,
        )

    def _calculate_sharpe(self, returns: pd.Series, risk_free: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2 or returns.std() == 0:
            return 0

        excess = returns - risk_free / 252
        return excess.mean() / returns.std() * np.sqrt(252)

    def _calculate_max_drawdown(self, equity: pd.Series) -> float:
        """Calculate maximum drawdown."""
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        return abs(drawdown.min())

    def _calculate_robustness_score(
        self,
        mean_return: float,
        std_return: float,
        prob_profit: float,
        prob_ruin: float,
        sharpe_ci: Tuple[float, float],
    ) -> float:
        """
        Calculate robustness score (0-100).

        Higher = more robust
        """
        # Return consistency (30%)
        coef_var = std_return / (abs(mean_return) + 1e-6)
        consistency_score = max(0, 30 * (1 - min(1, coef_var)))

        # Probability of profit (25%)
        profit_score = prob_profit * 25

        # Probability of ruin (25%)
        ruin_score = (1 - prob_ruin) * 25

        # Sharpe stability (20%)
        sharpe_lower = sharpe_ci[0]
        sharpe_score = max(0, min(20, sharpe_lower * 10))

        total = consistency_score + profit_score + ruin_score + sharpe_score
        return min(100, max(0, total))

    def generate_report(self, result: SimulationResult) -> str:
        """Generate Monte Carlo simulation report."""
        lines = [
            "=" * 80,
            "MONTE CARLO SIMULATION REPORT",
            "=" * 80,
            "",
            "SIMULATION TYPE:",
            f"  Type: {result.simulation_type.value}",
            f"  Number of Runs: {result.num_simulations}",
            "",
            "RETURN DISTRIBUTION:",
            f"  Mean Return: {result.mean_return:.2%}",
            f"  Median Return: {result.median_return:.2%}",
            f"  Std Deviation: {result.std_return:.2%}",
            f"  Min Return: {result.min_return:.2%}",
            f"  Max Return: {result.max_return:.2%}",
            f"  95% CI: [{result.return_ci_lower:.2%}, {result.return_ci_upper:.2%}]",
            "",
            "RISK METRICS:",
            f"  Probability of Profit: {result.probability_of_profit:.1%}",
            f"  Probability of Ruin: {result.probability_of_ruin:.1%}",
            f"  Value at Risk (95%): {result.value_at_risk_95:.2%}",
            f"  Conditional VaR (95%): {result.conditional_var_95:.2%}",
            "",
            "ROBUSTNESS ASSESSMENT:",
            f"  Robustness Score: {result.robustness_score:.1f}/100",
            f"  Robust to Parameters: {'YES' if result.robust_to_parameters else 'N/A'}",
            f"  Robust to Timing: {'YES' if result.robust_to_timing else 'N/A'}",
            f"  Robust to Stress: {'YES' if result.robust_to_stress else 'N/A'}",
        ]

        lines.append("=" * 80)

        return "\n".join(lines)
