"""
Execution Quality Analysis

Analyzes trade execution quality including:
- Fill rates
- Price improvement
- Execution speed
- Order routing efficiency
- Adverse selection
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ExecutionVenue(Enum):
    """Execution venue types."""

    MAKER = "maker"  # Limit orders (provide liquidity)
    TAKER = "taker"  # Market orders (take liquidity)
    MIXED = "mixed"  # Mix of both


class ExecutionQuality(Enum):
    """Execution quality classification."""

    EXCELLENT = "excellent"  # < 2 bps worse than benchmark
    GOOD = "good"  # 2-5 bps worse
    ACCEPTABLE = "acceptable"  # 5-10 bps worse
    POOR = "poor"  # > 10 bps worse


@dataclass
class ExecutionMetrics:
    """Comprehensive execution quality metrics."""

    # Fill metrics
    total_orders: int
    filled_orders: int
    partially_filled: int
    rejected_orders: int
    fill_rate: float  # Percentage of orders filled

    # Execution price quality
    avg_fill_price_vs_signal_bps: float  # Price at fill vs signal price
    avg_price_improvement_bps: float  # Better than expected
    worst_fill_bps: float  # Worst execution
    best_fill_bps: float  # Best execution

    # Timing metrics
    avg_execution_time_ms: float  # Time from signal to fill
    median_execution_time_ms: float
    pct_filled_under_1s: float  # % filled within 1 second
    pct_filled_under_5s: float  # % filled within 5 seconds

    # Market impact
    avg_market_impact_bps: float  # Price moved against us
    temporary_impact_bps: float  # Immediate impact
    permanent_impact_bps: float  # Lasting impact

    # Adverse selection
    adverse_selection_cost_bps: float  # Cost of being picked off
    information_leakage_score: float  # 0-100, lower is better

    # Venue analysis
    maker_fill_rate: float
    taker_fill_rate: float
    maker_avg_improvement_bps: float
    taker_avg_cost_bps: float

    # Overall quality
    execution_quality: ExecutionQuality
    quality_score: float  # 0-100

    def to_dict(self) -> Dict:
        return {
            "fill_rate": self.fill_rate,
            "avg_execution_time_ms": self.avg_execution_time_ms,
            "avg_fill_price_vs_signal_bps": self.avg_fill_price_vs_signal_bps,
            "avg_market_impact_bps": self.avg_market_impact_bps,
            "execution_quality": self.execution_quality.value,
            "quality_score": self.quality_score,
        }


class ExecutionQualityAnalyzer:
    """
    Analyzes execution quality for trading strategies.

    Helps identify execution issues and opportunities for improvement.
    """

    def __init__(self):
        """Initialize execution quality analyzer."""
        pass

    def analyze_execution(
        self,
        trades_df: pd.DataFrame,
        signals_df: Optional[pd.DataFrame] = None,
    ) -> ExecutionMetrics:
        """
        Analyze execution quality from trades.

        Args:
            trades_df: DataFrame with executed trades
            signals_df: DataFrame with signals (optional, for comparison)

        Returns:
            Comprehensive execution metrics
        """
        if trades_df.empty:
            return self._create_empty_metrics()

        # Extract basic metrics
        total_orders = len(trades_df)
        filled_orders = len(trades_df[trades_df.get("status", "filled") == "filled"])
        partially_filled = len(
            trades_df[trades_df.get("status", "filled") == "partial"]
        )
        rejected_orders = len(
            trades_df[trades_df.get("status", "filled") == "rejected"]
        )
        fill_rate = filled_orders / total_orders if total_orders > 0 else 0

        # Price quality
        if (
            signals_df is not None
            and "signal_price" in signals_df.columns
            and "fill_price" in trades_df.columns
        ):
            price_diff = (
                trades_df["fill_price"] - signals_df["signal_price"]
            ) / signals_df["signal_price"]
            avg_fill_vs_signal = price_diff.mean() * 10000  # Convert to bps
            worst_fill = price_diff.max() * 10000
            best_fill = price_diff.min() * 10000
        else:
            # Estimate from spread
            avg_fill_vs_signal = 5.0  # 5 bps default
            worst_fill = 20.0
            best_fill = -2.0

        # Price improvement (negative is good)
        avg_price_improvement = (
            -abs(avg_fill_vs_signal) if avg_fill_vs_signal < 0 else 0
        )

        # Execution timing
        if "execution_time_ms" in trades_df.columns:
            execution_times = trades_df["execution_time_ms"]
            avg_exec_time = execution_times.mean()
            median_exec_time = execution_times.median()
            pct_under_1s = (execution_times <= 1000).sum() / len(execution_times) * 100
            pct_under_5s = (execution_times <= 5000).sum() / len(execution_times) * 100
        else:
            # Estimate based on order type
            avg_exec_time = 2000  # 2 seconds default
            median_exec_time = 1500
            pct_under_1s = 40
            pct_under_5s = 85

        # Market impact
        if "market_impact_bps" in trades_df.columns:
            avg_market_impact = trades_df["market_impact_bps"].mean()
            temporary_impact = avg_market_impact * 0.6  # 60% temporary
            permanent_impact = avg_market_impact * 0.4  # 40% permanent
        else:
            # Estimate based on order size and liquidity
            avg_market_impact = self._estimate_market_impact(trades_df)
            temporary_impact = avg_market_impact * 0.6
            permanent_impact = avg_market_impact * 0.4

        # Adverse selection (estimated)
        adverse_selection = self._estimate_adverse_selection(trades_df)
        information_leakage = self._estimate_information_leakage(trades_df)

        # Venue analysis
        if "venue" in trades_df.columns:
            maker_trades = trades_df[trades_df["venue"] == "maker"]
            taker_trades = trades_df[trades_df["venue"] == "taker"]

            maker_fill_rate = len(maker_trades) / len(trades_df) * 100
            taker_fill_rate = len(taker_trades) / len(trades_df) * 100

            # Maker orders typically get price improvement
            maker_avg_improvement = -1.0  # 1 bps improvement
            taker_avg_cost = 2.5  # 2.5 bps cost
        else:
            maker_fill_rate = 50  # Assume 50/50 mix
            taker_fill_rate = 50
            maker_avg_improvement = -1.0
            taker_avg_cost = 2.5

        # Calculate overall quality score
        quality_score = self._calculate_quality_score(
            fill_rate, avg_fill_vs_signal, avg_exec_time, avg_market_impact
        )

        # Classify quality
        if avg_fill_vs_signal < 2.0:
            quality = ExecutionQuality.EXCELLENT
        elif avg_fill_vs_signal < 5.0:
            quality = ExecutionQuality.GOOD
        elif avg_fill_vs_signal < 10.0:
            quality = ExecutionQuality.ACCEPTABLE
        else:
            quality = ExecutionQuality.POOR

        return ExecutionMetrics(
            total_orders=total_orders,
            filled_orders=filled_orders,
            partially_filled=partially_filled,
            rejected_orders=rejected_orders,
            fill_rate=fill_rate,
            avg_fill_price_vs_signal_bps=avg_fill_vs_signal,
            avg_price_improvement_bps=avg_price_improvement,
            worst_fill_bps=worst_fill,
            best_fill_bps=best_fill,
            avg_execution_time_ms=avg_exec_time,
            median_execution_time_ms=median_exec_time,
            pct_filled_under_1s=pct_under_1s,
            pct_filled_under_5s=pct_under_5s,
            avg_market_impact_bps=avg_market_impact,
            temporary_impact_bps=temporary_impact,
            permanent_impact_bps=permanent_impact,
            adverse_selection_cost_bps=adverse_selection,
            information_leakage_score=information_leakage,
            maker_fill_rate=maker_fill_rate,
            taker_fill_rate=taker_fill_rate,
            maker_avg_improvement_bps=maker_avg_improvement,
            taker_avg_cost_bps=taker_avg_cost,
            execution_quality=quality,
            quality_score=quality_score,
        )

    def compare_execution_venues(
        self,
        trades_df: pd.DataFrame,
    ) -> Dict[str, Dict]:
        """
        Compare execution quality across different venues.

        Args:
            trades_df: DataFrame with trades including venue information

        Returns:
            Dictionary with per-venue metrics
        """
        if "venue" not in trades_df.columns:
            return {}

        venues = trades_df["venue"].unique()
        venue_metrics = {}

        for venue in venues:
            venue_trades = trades_df[trades_df["venue"] == venue]
            metrics = self.analyze_execution(venue_trades)
            venue_metrics[venue] = metrics.to_dict()

        return venue_metrics

    def analyze_execution_drift(
        self,
        trades_df: pd.DataFrame,
        window_size: int = 50,
    ) -> Dict:
        """
        Analyze how execution quality changes over time.

        Args:
            trades_df: DataFrame with trades
            window_size: Rolling window size

        Returns:
            Dictionary with drift analysis
        """
        if len(trades_df) < window_size:
            return {"drift_detected": False, "message": "Insufficient data"}

        # Calculate rolling metrics
        if "fill_price" in trades_df.columns and "signal_price" in trades_df.columns:
            slippage = (
                (trades_df["fill_price"] - trades_df["signal_price"])
                / trades_df["signal_price"]
                * 10000
            )
            rolling_slippage = slippage.rolling(window=window_size).mean()

            # Check for significant drift
            first_window = rolling_slippage.iloc[window_size - 1]
            last_window = rolling_slippage.iloc[-1]
            drift_pct = (
                ((last_window - first_window) / abs(first_window)) * 100
                if first_window != 0
                else 0
            )

            drift_detected = abs(drift_pct) > 20  # 20% change is significant

            return {
                "drift_detected": drift_detected,
                "drift_percentage": drift_pct,
                "initial_slippage_bps": first_window,
                "current_slippage_bps": last_window,
                "trend": "improving" if drift_pct < 0 else "degrading",
            }

        return {"drift_detected": False, "message": "Insufficient price data"}

    def _estimate_market_impact(self, trades_df: pd.DataFrame) -> float:
        """Estimate market impact from trade data."""
        # If we have volume data, estimate impact
        if "order_size_usd" in trades_df.columns:
            avg_size = trades_df["order_size_usd"].mean()
            # Larger orders have more impact
            # Use square root model: impact ∝ √size
            base_impact = 2.0  # 2 bps base
            size_factor = np.sqrt(avg_size / 10000)  # Normalize to $10k
            return base_impact * size_factor
        return 3.0  # Default 3 bps

    def _estimate_adverse_selection(self, trades_df: pd.DataFrame) -> float:
        """Estimate adverse selection cost."""
        # Adverse selection: when market moves against us after our order
        # Higher for limit orders that sit in the book
        if "post_trade_price_move_bps" in trades_df.columns:
            # Negative moves (market moved against us) indicate adverse selection
            adverse_moves = trades_df[trades_df["post_trade_price_move_bps"] < 0]
            if len(adverse_moves) > 0:
                return abs(adverse_moves["post_trade_price_move_bps"].mean())

        # Estimate: maker orders typically suffer 1-2 bps adverse selection
        return 1.5

    def _estimate_information_leakage(self, trades_df: pd.DataFrame) -> float:
        """
        Estimate information leakage score.

        Information leakage: when our trading signals predict price moves
        that others can exploit.
        """
        # If large orders or predictable patterns, higher leakage
        if "order_size_usd" in trades_df.columns:
            avg_size = trades_df["order_size_usd"].mean()
            size_score = min(avg_size / 100000, 1.0) * 50  # Max 50 points
        else:
            size_score = 20

        # Check for pattern regularity
        if len(trades_df) > 10:
            # If trades happen at regular intervals, higher leakage risk
            if "timestamp" in trades_df.columns:
                time_diffs = trades_df["timestamp"].diff().dt.total_seconds()
                regularity = (
                    1 - (time_diffs.std() / time_diffs.mean())
                    if time_diffs.mean() > 0
                    else 0
                )
                pattern_score = regularity * 30  # Max 30 points
            else:
                pattern_score = 15
        else:
            pattern_score = 10

        # Total leakage score (0-100, lower is better)
        leakage_score = size_score + pattern_score
        return min(leakage_score, 100)

    def _calculate_quality_score(
        self,
        fill_rate: float,
        avg_slippage_bps: float,
        avg_exec_time_ms: float,
        avg_market_impact_bps: float,
    ) -> float:
        """
        Calculate overall execution quality score (0-100).

        Weights:
        - Fill rate: 30%
        - Price quality: 40%
        - Speed: 15%
        - Market impact: 15%
        """
        # Fill rate component (30%)
        fill_score = fill_rate * 30

        # Price quality component (40%)
        # Lower slippage is better
        if avg_slippage_bps < 2:
            price_score = 40
        elif avg_slippage_bps < 5:
            price_score = 35
        elif avg_slippage_bps < 10:
            price_score = 25
        else:
            price_score = max(0, 40 - avg_slippage_bps)

        # Speed component (15%)
        # Faster is better
        if avg_exec_time_ms < 1000:
            speed_score = 15
        elif avg_exec_time_ms < 5000:
            speed_score = 12
        else:
            speed_score = max(0, 15 - (avg_exec_time_ms / 1000))

        # Market impact component (15%)
        # Lower impact is better
        if avg_market_impact_bps < 3:
            impact_score = 15
        elif avg_market_impact_bps < 5:
            impact_score = 12
        elif avg_market_impact_bps < 10:
            impact_score = 8
        else:
            impact_score = max(0, 15 - avg_market_impact_bps)

        total_score = fill_score + price_score + speed_score + impact_score
        return min(100, max(0, total_score))

    def _create_empty_metrics(self) -> ExecutionMetrics:
        """Create empty metrics for edge cases."""
        return ExecutionMetrics(
            total_orders=0,
            filled_orders=0,
            partially_filled=0,
            rejected_orders=0,
            fill_rate=0,
            avg_fill_price_vs_signal_bps=0,
            avg_price_improvement_bps=0,
            worst_fill_bps=0,
            best_fill_bps=0,
            avg_execution_time_ms=0,
            median_execution_time_ms=0,
            pct_filled_under_1s=0,
            pct_filled_under_5s=0,
            avg_market_impact_bps=0,
            temporary_impact_bps=0,
            permanent_impact_bps=0,
            adverse_selection_cost_bps=0,
            information_leakage_score=0,
            maker_fill_rate=0,
            taker_fill_rate=0,
            maker_avg_improvement_bps=0,
            taker_avg_cost_bps=0,
            execution_quality=ExecutionQuality.POOR,
            quality_score=0,
        )

    def generate_execution_report(self, metrics: ExecutionMetrics) -> str:
        """Generate human-readable execution quality report."""
        lines = [
            "=" * 80,
            "EXECUTION QUALITY REPORT",
            "=" * 80,
            "",
            "FILL METRICS:",
            f"  Total Orders: {metrics.total_orders}",
            f"  Filled: {metrics.filled_orders} ({metrics.fill_rate:.1%})",
            f"  Partially Filled: {metrics.partially_filled}",
            f"  Rejected: {metrics.rejected_orders}",
            "",
            "PRICE QUALITY:",
            f"  Avg Fill vs Signal: {metrics.avg_fill_price_vs_signal_bps:.2f} bps",
            f"  Price Improvement: {metrics.avg_price_improvement_bps:.2f} bps",
            f"  Best Fill: {metrics.best_fill_bps:.2f} bps",
            f"  Worst Fill: {metrics.worst_fill_bps:.2f} bps",
            "",
            "EXECUTION SPEED:",
            f"  Avg Execution Time: {metrics.avg_execution_time_ms:.0f} ms",
            f"  Median Time: {metrics.median_execution_time_ms:.0f} ms",
            f"  Filled < 1s: {metrics.pct_filled_under_1s:.1f}%",
            f"  Filled < 5s: {metrics.pct_filled_under_5s:.1f}%",
            "",
            "MARKET IMPACT:",
            f"  Avg Impact: {metrics.avg_market_impact_bps:.2f} bps",
            f"  Temporary Impact: {metrics.temporary_impact_bps:.2f} bps",
            f"  Permanent Impact: {metrics.permanent_impact_bps:.2f} bps",
            "",
            "VENUE ANALYSIS:",
            f"  Maker Fill Rate: {metrics.maker_fill_rate:.1f}%",
            f"  Taker Fill Rate: {metrics.taker_fill_rate:.1f}%",
            f"  Maker Improvement: {metrics.maker_avg_improvement_bps:.2f} bps",
            f"  Taker Cost: {metrics.taker_avg_cost_bps:.2f} bps",
            "",
            "ADVERSE SELECTION:",
            f"  Cost: {metrics.adverse_selection_cost_bps:.2f} bps",
            f"  Information Leakage: {metrics.information_leakage_score:.1f}/100",
            "",
            "OVERALL QUALITY:",
            f"  Quality Score: {metrics.quality_score:.1f}/100",
            f"  Quality Rating: {metrics.execution_quality.value.upper()}",
            "",
            "=" * 80,
        ]

        return "\n".join(lines)
