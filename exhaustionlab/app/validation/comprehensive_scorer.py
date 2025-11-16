"""
Comprehensive Strategy Scoring System

Implements the complete scoring formula:
- Performance: 35% (Sharpe 15%, Return 10%, Win Rate 10%)
- Risk: 30% (Drawdown 15%, Consistency 10%, Recovery 5%)
- Execution: 20% (Frequency 10%, Latency 5%, Slippage 5%)
- Robustness: 15% (Out-of-sample 7%, Cross-market 8%)

Total: 100 points
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd
import numpy as np

from .backtest_parser import BacktestResult
from .slippage_model import SlippageEstimator
from .execution_quality import ExecutionQualityAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ComponentScores:
    """Breakdown of all component scores."""

    # Performance (35%)
    sharpe_score: float  # 15%
    return_score: float  # 10%
    win_rate_score: float  # 10%
    performance_total: float  # 35%

    # Risk (30%)
    drawdown_score: float  # 15%
    consistency_score: float  # 10%
    recovery_score: float  # 5%
    risk_total: float  # 30%

    # Execution (20%)
    frequency_score: float  # 10%
    latency_score: float  # 5%
    slippage_score: float  # 5%
    execution_total: float  # 20%

    # Robustness (15%)
    out_of_sample_score: float  # 7%
    cross_market_score: float  # 8%
    robustness_total: float  # 15%

    # Overall
    total_score: float  # 100%

    def to_dict(self) -> Dict:
        return {
            "performance": {
                "sharpe": self.sharpe_score,
                "return": self.return_score,
                "win_rate": self.win_rate_score,
                "total": self.performance_total,
            },
            "risk": {
                "drawdown": self.drawdown_score,
                "consistency": self.consistency_score,
                "recovery": self.recovery_score,
                "total": self.risk_total,
            },
            "execution": {
                "frequency": self.frequency_score,
                "latency": self.latency_score,
                "slippage": self.slippage_score,
                "total": self.execution_total,
            },
            "robustness": {
                "out_of_sample": self.out_of_sample_score,
                "cross_market": self.cross_market_score,
                "total": self.robustness_total,
            },
            "total": self.total_score,
        }


class ComprehensiveScorer:
    """
    Calculate comprehensive strategy score.

    Scoring Formula:
    ═══════════════════════════════════════════════════════════════
    PERFORMANCE (35%):
      - Sharpe Ratio (15%): Score based on Sharpe > 1.5 target
      - Total Return (10%): Score based on > 30% annual target
      - Win Rate (10%): Score based on > 55% target

    RISK (30%):
      - Max Drawdown (15%): Score based on < 25% target
      - Consistency (10%): Monthly return consistency
      - Recovery Time (5%): Time to recover from drawdowns

    EXECUTION (20%):
      - Frequency (10%): Optimal frequency for market
      - Latency (5%): Execution speed requirements
      - Slippage (5%): Estimated slippage cost

    ROBUSTNESS (15%):
      - Out-of-Sample (7%): Walk-forward performance
      - Cross-Market (8%): Multi-market consistency
    ═══════════════════════════════════════════════════════════════
    """

    # Scoring thresholds
    SHARPE_TARGET = 1.5
    RETURN_TARGET = 0.30  # 30% annual
    WIN_RATE_TARGET = 0.55  # 55%
    DRAWDOWN_TARGET = 0.25  # 25% max
    CONSISTENCY_TARGET = 0.65  # 65%
    RECOVERY_TARGET_DAYS = 30  # 30 days

    def __init__(self):
        """Initialize scorer."""
        self.slippage_estimator = SlippageEstimator()
        self.execution_analyzer = ExecutionQualityAnalyzer()

    def calculate_comprehensive_score(
        self,
        backtest: BacktestResult,
        symbol: str,
        portfolio_size_usd: float = 100000,
        out_of_sample_ratio: Optional[float] = None,
        cross_market_pass_rate: Optional[float] = None,
    ) -> ComponentScores:
        """
        Calculate comprehensive score for a strategy.

        Args:
            backtest: Parsed backtest result
            symbol: Trading symbol
            portfolio_size_usd: Portfolio size for slippage estimation
            out_of_sample_ratio: Walk-forward OOS/IS ratio (optional)
            cross_market_pass_rate: Multi-market pass rate (optional)

        Returns:
            Complete component scores
        """
        # Calculate each component
        perf_scores = self._score_performance(backtest)
        risk_scores = self._score_risk(backtest)
        exec_scores = self._score_execution(backtest, symbol, portfolio_size_usd)
        robust_scores = self._score_robustness(
            out_of_sample_ratio, cross_market_pass_rate
        )

        # Calculate totals
        performance_total = (
            perf_scores["sharpe"] + perf_scores["return"] + perf_scores["win_rate"]
        )

        risk_total = (
            risk_scores["drawdown"]
            + risk_scores["consistency"]
            + risk_scores["recovery"]
        )

        execution_total = (
            exec_scores["frequency"] + exec_scores["latency"] + exec_scores["slippage"]
        )

        robustness_total = (
            robust_scores["out_of_sample"] + robust_scores["cross_market"]
        )

        total_score = (
            performance_total + risk_total + execution_total + robustness_total
        )

        return ComponentScores(
            sharpe_score=perf_scores["sharpe"],
            return_score=perf_scores["return"],
            win_rate_score=perf_scores["win_rate"],
            performance_total=performance_total,
            drawdown_score=risk_scores["drawdown"],
            consistency_score=risk_scores["consistency"],
            recovery_score=risk_scores["recovery"],
            risk_total=risk_total,
            frequency_score=exec_scores["frequency"],
            latency_score=exec_scores["latency"],
            slippage_score=exec_scores["slippage"],
            execution_total=execution_total,
            out_of_sample_score=robust_scores["out_of_sample"],
            cross_market_score=robust_scores["cross_market"],
            robustness_total=robustness_total,
            total_score=total_score,
        )

    def _score_performance(self, backtest: BacktestResult) -> Dict[str, float]:
        """
        Score performance metrics (35% total).

        - Sharpe Ratio (15%): Target > 1.5
        - Total Return (10%): Target > 30% annual
        - Win Rate (10%): Target > 55%
        """
        # Sharpe ratio (15 points max)
        sharpe = backtest.sharpe_ratio
        if sharpe >= self.SHARPE_TARGET:
            sharpe_score = 15.0
        elif sharpe >= 1.0:
            # Linear interpolation between 1.0 and 1.5
            sharpe_score = 10.0 + ((sharpe - 1.0) / (self.SHARPE_TARGET - 1.0)) * 5.0
        elif sharpe >= 0.5:
            # Linear interpolation between 0.5 and 1.0
            sharpe_score = 5.0 + ((sharpe - 0.5) / 0.5) * 5.0
        elif sharpe > 0:
            sharpe_score = (sharpe / 0.5) * 5.0
        else:
            sharpe_score = 0.0

        # Return (10 points max)
        annual_return = backtest.annualized_return
        if annual_return >= self.RETURN_TARGET:
            return_score = 10.0
        elif annual_return >= 0.15:  # 15%
            # Linear interpolation between 15% and 30%
            return_score = (
                5.0 + ((annual_return - 0.15) / (self.RETURN_TARGET - 0.15)) * 5.0
            )
        elif annual_return > 0:
            return_score = (annual_return / 0.15) * 5.0
        else:
            return_score = 0.0

        # Win rate (10 points max)
        win_rate = backtest.win_rate
        if win_rate >= self.WIN_RATE_TARGET:
            win_rate_score = 10.0
        elif win_rate >= 0.45:  # 45%
            # Linear interpolation between 45% and 55%
            win_rate_score = (
                5.0 + ((win_rate - 0.45) / (self.WIN_RATE_TARGET - 0.45)) * 5.0
            )
        elif win_rate > 0:
            win_rate_score = (win_rate / 0.45) * 5.0
        else:
            win_rate_score = 0.0

        return {
            "sharpe": sharpe_score,
            "return": return_score,
            "win_rate": win_rate_score,
        }

    def _score_risk(self, backtest: BacktestResult) -> Dict[str, float]:
        """
        Score risk metrics (30% total).

        - Max Drawdown (15%): Target < 25%
        - Consistency (10%): Monthly return consistency
        - Recovery Time (5%): Time to recover from drawdowns
        """
        # Max drawdown (15 points max)
        # Lower is better, so invert the score
        drawdown = backtest.max_drawdown
        if drawdown <= 0.15:  # < 15%
            drawdown_score = 15.0
        elif drawdown <= self.DRAWDOWN_TARGET:  # < 25%
            # Linear interpolation between 15% and 25%
            drawdown_score = (
                10.0
                + ((self.DRAWDOWN_TARGET - drawdown) / (self.DRAWDOWN_TARGET - 0.15))
                * 5.0
            )
        elif drawdown <= 0.40:  # < 40%
            drawdown_score = (
                5.0 + ((0.40 - drawdown) / (0.40 - self.DRAWDOWN_TARGET)) * 5.0
            )
        elif drawdown < 0.50:  # < 50%
            drawdown_score = ((0.50 - drawdown) / 0.10) * 5.0
        else:
            drawdown_score = 0.0

        # Consistency (10 points max)
        # Calculate consistency from returns
        if len(backtest.returns) > 30:
            # Monthly consistency
            monthly_returns = backtest.returns.resample("M").sum()
            if len(monthly_returns) > 0:
                positive_months = (monthly_returns > 0).sum() / len(monthly_returns)
                if positive_months >= self.CONSISTENCY_TARGET:
                    consistency_score = 10.0
                elif positive_months >= 0.50:
                    consistency_score = (
                        5.0
                        + ((positive_months - 0.50) / (self.CONSISTENCY_TARGET - 0.50))
                        * 5.0
                    )
                else:
                    consistency_score = (positive_months / 0.50) * 5.0
            else:
                consistency_score = 5.0  # Default
        else:
            # Not enough data, use trade-based consistency
            if backtest.total_trades > 0:
                consistency_score = backtest.win_rate * 10.0
            else:
                consistency_score = 0.0

        # Recovery time (5 points max)
        recovery_days = backtest.max_drawdown_duration
        if recovery_days <= self.RECOVERY_TARGET_DAYS:
            recovery_score = 5.0
        elif recovery_days <= 60:
            recovery_score = (
                3.0 + ((60 - recovery_days) / (60 - self.RECOVERY_TARGET_DAYS)) * 2.0
            )
        elif recovery_days <= 90:
            recovery_score = 1.0 + ((90 - recovery_days) / 30) * 2.0
        elif recovery_days <= 120:
            recovery_score = ((120 - recovery_days) / 30) * 1.0
        else:
            recovery_score = 0.0

        return {
            "drawdown": drawdown_score,
            "consistency": consistency_score,
            "recovery": recovery_score,
        }

    def _score_execution(
        self,
        backtest: BacktestResult,
        symbol: str,
        portfolio_size_usd: float,
    ) -> Dict[str, float]:
        """
        Score execution metrics (20% total).

        - Frequency (10%): Optimal frequency for market
        - Latency (5%): Execution speed requirements
        - Slippage (5%): Estimated slippage cost
        """
        trades_df = backtest.to_dataframe()

        # Calculate signal frequency
        if len(backtest.trades) > 1:
            days = (backtest.end_date - backtest.start_date).days
            if days > 0:
                signal_frequency = len(backtest.trades) / days
            else:
                signal_frequency = len(backtest.trades)
        else:
            signal_frequency = 0

        # Frequency score (10 points max)
        # Optimal frequency depends on market liquidity
        liquidity_info = self.slippage_estimator.get_symbol_liquidity_info(symbol)
        liquidity_class = liquidity_info["liquidity_class"]

        # Optimal frequencies by liquidity
        if liquidity_class == "very_high":
            optimal_freq = (2, 20)  # 2-20 signals/day optimal
        elif liquidity_class == "high":
            optimal_freq = (1, 10)
        elif liquidity_class == "medium":
            optimal_freq = (0.5, 5)
        else:
            optimal_freq = (0.2, 2)

        if optimal_freq[0] <= signal_frequency <= optimal_freq[1]:
            frequency_score = 10.0
        elif signal_frequency < optimal_freq[0]:
            # Too infrequent
            frequency_score = (signal_frequency / optimal_freq[0]) * 10.0
        else:
            # Too frequent - penalize linearly
            penalty = min(1.0, (signal_frequency - optimal_freq[1]) / optimal_freq[1])
            frequency_score = max(0, 10.0 * (1 - penalty))

        # Latency score (5 points max)
        # Estimate required execution speed
        if signal_frequency > 50:  # HFT
            required_latency_ms = 100
        elif signal_frequency > 10:
            required_latency_ms = 1000
        else:
            required_latency_ms = 5000

        # For now, assume reasonable execution (can be enhanced)
        latency_score = 4.0  # Default to 4/5

        # Slippage score (5 points max)
        # Lower slippage = higher score
        if not trades_df.empty:
            portfolio_slippage = self.slippage_estimator.estimate_portfolio_slippage(
                trades_df=trades_df,
                symbol=symbol,
                portfolio_size_usd=portfolio_size_usd,
            )

            avg_slippage_bps = portfolio_slippage["avg_slippage_per_trade_bps"]

            # Score based on slippage
            if avg_slippage_bps <= 5:  # < 5 bps
                slippage_score = 5.0
            elif avg_slippage_bps <= 10:
                slippage_score = 3.0 + ((10 - avg_slippage_bps) / 5) * 2.0
            elif avg_slippage_bps <= 20:
                slippage_score = 1.0 + ((20 - avg_slippage_bps) / 10) * 2.0
            elif avg_slippage_bps <= 30:
                slippage_score = ((30 - avg_slippage_bps) / 10) * 1.0
            else:
                slippage_score = 0.0
        else:
            slippage_score = 3.0  # Default

        return {
            "frequency": frequency_score,
            "latency": latency_score,
            "slippage": slippage_score,
        }

    def _score_robustness(
        self,
        out_of_sample_ratio: Optional[float],
        cross_market_pass_rate: Optional[float],
    ) -> Dict[str, float]:
        """
        Score robustness metrics (15% total).

        - Out-of-Sample (7%): Walk-forward OOS/IS ratio
        - Cross-Market (8%): Multi-market pass rate
        """
        # Out-of-sample score (7 points max)
        if out_of_sample_ratio is not None:
            # OOS/IS ratio (closer to 1.0 is better, > 0.7 is good)
            if out_of_sample_ratio >= 0.8:
                oos_score = 7.0
            elif out_of_sample_ratio >= 0.6:
                oos_score = 5.0 + ((out_of_sample_ratio - 0.6) / 0.2) * 2.0
            elif out_of_sample_ratio >= 0.4:
                oos_score = 3.0 + ((out_of_sample_ratio - 0.4) / 0.2) * 2.0
            elif out_of_sample_ratio > 0:
                oos_score = (out_of_sample_ratio / 0.4) * 3.0
            else:
                oos_score = 0.0
        else:
            # No walk-forward data, use partial credit
            oos_score = 4.0

        # Cross-market score (8 points max)
        if cross_market_pass_rate is not None:
            if cross_market_pass_rate >= 0.75:  # 75%+ pass rate
                cross_market_score = 8.0
            elif cross_market_pass_rate >= 0.60:
                cross_market_score = (
                    6.0 + ((cross_market_pass_rate - 0.60) / 0.15) * 2.0
                )
            elif cross_market_pass_rate >= 0.50:
                cross_market_score = (
                    4.0 + ((cross_market_pass_rate - 0.50) / 0.10) * 2.0
                )
            elif cross_market_pass_rate > 0:
                cross_market_score = (cross_market_pass_rate / 0.50) * 4.0
            else:
                cross_market_score = 0.0
        else:
            # No multi-market data, use partial credit
            cross_market_score = 5.0

        return {
            "out_of_sample": oos_score,
            "cross_market": cross_market_score,
        }

    def generate_score_report(self, scores: ComponentScores) -> str:
        """Generate human-readable score report."""
        lines = [
            "=" * 80,
            "COMPREHENSIVE STRATEGY SCORE",
            "=" * 80,
            "",
            f"TOTAL SCORE: {scores.total_score:.1f}/100",
            "",
            "COMPONENT BREAKDOWN:",
            "",
            f"PERFORMANCE ({scores.performance_total:.1f}/35):",
            f"  Sharpe Ratio: {scores.sharpe_score:.1f}/15",
            f"  Total Return: {scores.return_score:.1f}/10",
            f"  Win Rate: {scores.win_rate_score:.1f}/10",
            "",
            f"RISK ({scores.risk_total:.1f}/30):",
            f"  Max Drawdown: {scores.drawdown_score:.1f}/15",
            f"  Consistency: {scores.consistency_score:.1f}/10",
            f"  Recovery Time: {scores.recovery_score:.1f}/5",
            "",
            f"EXECUTION ({scores.execution_total:.1f}/20):",
            f"  Frequency: {scores.frequency_score:.1f}/10",
            f"  Latency: {scores.latency_score:.1f}/5",
            f"  Slippage: {scores.slippage_score:.1f}/5",
            "",
            f"ROBUSTNESS ({scores.robustness_total:.1f}/15):",
            f"  Out-of-Sample: {scores.out_of_sample_score:.1f}/7",
            f"  Cross-Market: {scores.cross_market_score:.1f}/8",
            "",
            "=" * 80,
        ]

        # Add grade
        if scores.total_score >= 85:
            grade = "A (EXCELLENT)"
        elif scores.total_score >= 75:
            grade = "B (GOOD)"
        elif scores.total_score >= 65:
            grade = "C (ACCEPTABLE)"
        elif scores.total_score >= 50:
            grade = "D (MARGINAL)"
        else:
            grade = "F (FAIL)"

        lines.append(f"GRADE: {grade}")
        lines.append("=" * 80)

        return "\n".join(lines)
