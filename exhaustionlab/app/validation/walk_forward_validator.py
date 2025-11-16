"""
Walk-Forward Validation

Out-of-sample testing to detect overfitting:
- Rolling window optimization
- In-sample vs out-of-sample performance
- Stability analysis
- Overfitting detection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from datetime import datetime

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class WalkForwardPeriod:
    """Single walk-forward period result."""

    period_id: int

    # Period definitions
    in_sample_start: datetime
    in_sample_end: datetime
    out_sample_start: datetime
    out_sample_end: datetime

    # Performance metrics
    in_sample_return: float
    out_sample_return: float
    in_sample_sharpe: float
    out_sample_sharpe: float
    in_sample_drawdown: float
    out_sample_drawdown: float

    # Overfitting indicators
    performance_degradation: float  # (IS - OOS) / IS
    sharpe_degradation: float

    # Validation
    passed: bool  # OOS meets minimum standards


@dataclass
class WalkForwardResult:
    """Complete walk-forward validation result."""

    # Overall metrics
    total_periods: int
    periods_passed: int
    pass_rate: float

    # Aggregated performance
    mean_in_sample_return: float
    mean_out_sample_return: float
    mean_in_sample_sharpe: float
    mean_out_sample_sharpe: float

    # Degradation analysis
    mean_performance_degradation: float
    mean_sharpe_degradation: float
    performance_degradation_std: float

    # Overfitting indicators
    overfitting_detected: bool
    overfitting_score: float  # 0-100, higher = more overfitting

    # Stability metrics
    out_sample_consistency: float  # Std of OOS returns
    performance_stable: bool

    # Individual period results
    periods: List[WalkForwardPeriod] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "total_periods": self.total_periods,
            "periods_passed": self.periods_passed,
            "pass_rate": self.pass_rate,
            "mean_out_sample_return": self.mean_out_sample_return,
            "mean_out_sample_sharpe": self.mean_out_sample_sharpe,
            "mean_performance_degradation": self.mean_performance_degradation,
            "overfitting_detected": self.overfitting_detected,
            "overfitting_score": self.overfitting_score,
            "performance_stable": self.performance_stable,
        }


class WalkForwardValidator:
    """
    Walk-forward validation for overfitting detection.

    Process:
    1. Divide data into overlapping windows
    2. Optimize on in-sample period
    3. Test on out-of-sample period
    4. Compare IS vs OOS performance
    5. Detect overfitting patterns
    """

    def __init__(
        self,
        in_sample_ratio: float = 0.7,
        out_sample_ratio: float = 0.3,
        min_out_sample_return: float = 0.05,
        min_out_sample_sharpe: float = 0.8,
        max_degradation: float = 0.5,  # Max 50% degradation allowed
    ):
        """
        Initialize walk-forward validator.

        Args:
            in_sample_ratio: Fraction of data for optimization (0.7 = 70%)
            out_sample_ratio: Fraction for testing
            min_out_sample_return: Minimum acceptable OOS return
            min_out_sample_sharpe: Minimum acceptable OOS Sharpe
            max_degradation: Maximum allowed performance degradation
        """
        self.in_sample_ratio = in_sample_ratio
        self.out_sample_ratio = out_sample_ratio
        self.min_out_sample_return = min_out_sample_return
        self.min_out_sample_sharpe = min_out_sample_sharpe
        self.max_degradation = max_degradation

    def validate(
        self,
        data: pd.DataFrame,
        strategy_func: Callable[[pd.DataFrame], Tuple[pd.DataFrame, pd.Series]],
        num_periods: int = 5,
        anchored: bool = False,
    ) -> WalkForwardResult:
        """
        Perform walk-forward validation.

        Args:
            data: OHLCV data with datetime index
            strategy_func: Strategy function (data -> trades, equity)
            num_periods: Number of walk-forward periods
            anchored: If True, in-sample always starts from beginning

        Returns:
            Walk-forward validation results
        """
        if len(data) < 200:
            raise ValueError("Insufficient data for walk-forward validation")

        # Calculate period sizes
        total_size = len(data)
        window_size = total_size // num_periods
        in_sample_size = int(window_size * self.in_sample_ratio)
        out_sample_size = window_size - in_sample_size

        logger.info(
            f"Walk-forward validation: {num_periods} periods, "
            f"IS size={in_sample_size}, OOS size={out_sample_size}"
        )

        # Run walk-forward periods
        periods = []
        for i in range(num_periods):
            if anchored:
                # Anchored: IS always from start
                in_start = 0
                in_end = in_sample_size + (i * out_sample_size)
            else:
                # Rolling: IS window moves
                in_start = i * window_size
                in_end = in_start + in_sample_size

            out_start = in_end
            out_end = min(out_start + out_sample_size, total_size)

            # Skip if insufficient OOS data
            if out_end - out_start < 50:
                logger.warning(f"Period {i}: insufficient OOS data, skipping")
                continue

            try:
                period_result = self._test_period(
                    data=data,
                    strategy_func=strategy_func,
                    in_start=in_start,
                    in_end=in_end,
                    out_start=out_start,
                    out_end=out_end,
                    period_id=i,
                )
                periods.append(period_result)

            except Exception as e:
                logger.error(f"Period {i} failed: {e}")
                continue

        if not periods:
            raise RuntimeError("All walk-forward periods failed")

        # Aggregate results
        return self._aggregate_periods(periods)

    def _test_period(
        self,
        data: pd.DataFrame,
        strategy_func: Callable,
        in_start: int,
        in_end: int,
        out_start: int,
        out_end: int,
        period_id: int,
    ) -> WalkForwardPeriod:
        """Test single walk-forward period."""
        # Extract periods
        in_sample_data = data.iloc[in_start:in_end]
        out_sample_data = data.iloc[out_start:out_end]

        # Run strategy on both periods
        in_trades, in_equity = strategy_func(in_sample_data)
        out_trades, out_equity = strategy_func(out_sample_data)

        # Calculate metrics
        in_return = (in_equity.iloc[-1] / in_equity.iloc[0]) - 1
        out_return = (out_equity.iloc[-1] / out_equity.iloc[0]) - 1

        in_sharpe = self._calculate_sharpe(in_equity)
        out_sharpe = self._calculate_sharpe(out_equity)

        in_dd = self._calculate_max_drawdown(in_equity)
        out_dd = self._calculate_max_drawdown(out_equity)

        # Calculate degradation
        perf_degradation = (
            (in_return - out_return) / abs(in_return) if in_return != 0 else 0
        )
        sharpe_degradation = (
            (in_sharpe - out_sharpe) / abs(in_sharpe) if in_sharpe != 0 else 0
        )

        # Validation
        passed = (
            out_return >= self.min_out_sample_return
            and out_sharpe >= self.min_out_sample_sharpe
            and perf_degradation <= self.max_degradation
        )

        return WalkForwardPeriod(
            period_id=period_id,
            in_sample_start=(
                data.index[in_start]
                if hasattr(data.index[in_start], "to_pydatetime")
                else datetime.now()
            ),
            in_sample_end=(
                data.index[in_end - 1]
                if hasattr(data.index[in_end - 1], "to_pydatetime")
                else datetime.now()
            ),
            out_sample_start=(
                data.index[out_start]
                if hasattr(data.index[out_start], "to_pydatetime")
                else datetime.now()
            ),
            out_sample_end=(
                data.index[out_end - 1]
                if hasattr(data.index[out_end - 1], "to_pydatetime")
                else datetime.now()
            ),
            in_sample_return=in_return,
            out_sample_return=out_return,
            in_sample_sharpe=in_sharpe,
            out_sample_sharpe=out_sharpe,
            in_sample_drawdown=in_dd,
            out_sample_drawdown=out_dd,
            performance_degradation=perf_degradation,
            sharpe_degradation=sharpe_degradation,
            passed=passed,
        )

    def _aggregate_periods(self, periods: List[WalkForwardPeriod]) -> WalkForwardResult:
        """Aggregate walk-forward period results."""
        total = len(periods)
        passed = sum(1 for p in periods if p.passed)
        pass_rate = passed / total

        # Aggregate metrics
        mean_in_return = np.mean([p.in_sample_return for p in periods])
        mean_out_return = np.mean([p.out_sample_return for p in periods])
        mean_in_sharpe = np.mean([p.in_sample_sharpe for p in periods])
        mean_out_sharpe = np.mean([p.out_sample_sharpe for p in periods])

        # Degradation metrics
        degradations = [p.performance_degradation for p in periods]
        mean_degradation = np.mean(degradations)
        std_degradation = np.std(degradations)

        sharpe_degradations = [p.sharpe_degradation for p in periods]
        mean_sharpe_degradation = np.mean(sharpe_degradations)

        # Overfitting detection
        overfitting_score = self._calculate_overfitting_score(
            mean_degradation, std_degradation, pass_rate
        )
        overfitting_detected = overfitting_score > 60  # Threshold

        # Stability analysis
        out_returns = [p.out_sample_return for p in periods]
        consistency = 1.0 - (np.std(out_returns) / (abs(np.mean(out_returns)) + 1e-6))
        performance_stable = consistency > 0.5 and pass_rate > 0.6

        return WalkForwardResult(
            total_periods=total,
            periods_passed=passed,
            pass_rate=pass_rate,
            mean_in_sample_return=mean_in_return,
            mean_out_sample_return=mean_out_return,
            mean_in_sample_sharpe=mean_in_sharpe,
            mean_out_sample_sharpe=mean_out_sharpe,
            mean_performance_degradation=mean_degradation,
            mean_sharpe_degradation=mean_sharpe_degradation,
            performance_degradation_std=std_degradation,
            overfitting_detected=overfitting_detected,
            overfitting_score=overfitting_score,
            out_sample_consistency=consistency,
            performance_stable=performance_stable,
            periods=periods,
        )

    def _calculate_sharpe(self, equity: pd.Series, risk_free: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        returns = equity.pct_change().dropna()
        if len(returns) < 2 or returns.std() == 0:
            return 0

        excess = returns - risk_free / 252
        return excess.mean() / returns.std() * np.sqrt(252)

    def _calculate_max_drawdown(self, equity: pd.Series) -> float:
        """Calculate maximum drawdown."""
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max
        return abs(drawdown.min())

    def _calculate_overfitting_score(
        self, mean_degradation: float, std_degradation: float, pass_rate: float
    ) -> float:
        """
        Calculate overfitting score (0-100).

        Higher score = more overfitting
        """
        # Degradation component (60%)
        if mean_degradation < 0:  # OOS better than IS (unlikely, but good)
            deg_score = 0
        elif mean_degradation > 1:  # > 100% degradation
            deg_score = 60
        else:
            deg_score = mean_degradation * 60

        # Inconsistency component (20%)
        inconsistency_score = min(20, std_degradation * 40)

        # Failure rate component (20%)
        failure_rate = 1 - pass_rate
        failure_score = failure_rate * 20

        total_score = deg_score + inconsistency_score + failure_score
        return min(100, max(0, total_score))

    def generate_report(self, result: WalkForwardResult) -> str:
        """Generate walk-forward validation report."""
        lines = [
            "=" * 80,
            "WALK-FORWARD VALIDATION REPORT",
            "=" * 80,
            "",
            "OVERVIEW:",
            f"  Total Periods: {result.total_periods}",
            f"  Periods Passed: {result.periods_passed}",
            f"  Pass Rate: {result.pass_rate:.1%}",
            "",
            "PERFORMANCE:",
            f"  Mean In-Sample Return: {result.mean_in_sample_return:.2%}",
            f"  Mean Out-Sample Return: {result.mean_out_sample_return:.2%}",
            f"  Mean In-Sample Sharpe: {result.mean_in_sample_sharpe:.2f}",
            f"  Mean Out-Sample Sharpe: {result.mean_out_sample_sharpe:.2f}",
            "",
            "DEGRADATION ANALYSIS:",
            f"  Mean Performance Degradation: {result.mean_performance_degradation:.1%}",
            f"  Mean Sharpe Degradation: {result.mean_sharpe_degradation:.1%}",
            f"  Degradation Std Dev: {result.performance_degradation_std:.2f}",
            "",
            "OVERFITTING ASSESSMENT:",
            f"  Overfitting Score: {result.overfitting_score:.1f}/100",
            f"  Overfitting Detected: {'YES' if result.overfitting_detected else 'NO'}",
            f"  Performance Stable: {'YES' if result.performance_stable else 'NO'}",
            f"  Out-Sample Consistency: {result.out_sample_consistency:.2f}",
            "",
            "PERIOD DETAILS:",
        ]

        for period in result.periods:
            lines.extend(
                [
                    f"  Period {period.period_id}:",
                    f"    In-Sample:  Return={period.in_sample_return:.2%}, Sharpe={period.in_sample_sharpe:.2f}",
                    f"    Out-Sample: Return={period.out_sample_return:.2%}, Sharpe={period.out_sample_sharpe:.2f}",
                    f"    Degradation: {period.performance_degradation:.1%}",
                    f"    Passed: {'YES' if period.passed else 'NO'}",
                ]
            )

        lines.append("=" * 80)

        return "\n".join(lines)
