"""
Deep Profit Analysis

Comprehensive profit analysis with:
- Return distribution analysis
- Trade-by-trade breakdown
- Statistical significance tests
- Risk-adjusted profit metrics
- Profit consistency validation
- Expected value calculations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

import pandas as pd
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class ProfitQuality(Enum):
    """Profit quality classification."""

    EXCELLENT = "excellent"  # High, consistent, low-risk
    GOOD = "good"  # Decent returns with acceptable risk
    ACCEPTABLE = "acceptable"  # Meets minimum standards
    MARGINAL = "marginal"  # Borderline profitable
    POOR = "poor"  # Unprofitable or too risky


@dataclass
class TradeAnalysis:
    """Analysis of individual trades."""

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int

    # Win/loss metrics
    win_rate: float
    loss_rate: float

    # Profit metrics
    total_profit: float
    total_loss: float
    net_profit: float
    profit_factor: float  # Gross profit / gross loss

    # Average trade metrics
    avg_profit: float
    avg_loss: float
    avg_win: float
    avg_loss_size: float

    # Extreme values
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int

    # Risk metrics
    risk_reward_ratio: float  # Avg win / avg loss
    kelly_criterion: float  # Optimal position size
    expectancy: float  # Expected value per trade

    # Distribution metrics
    profit_skewness: float  # Asymmetry of profit distribution
    profit_kurtosis: float  # Tail risk

    def to_dict(self) -> Dict:
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "net_profit": self.net_profit,
            "profit_factor": self.profit_factor,
            "avg_win": self.avg_win,
            "avg_loss_size": self.avg_loss_size,
            "risk_reward_ratio": self.risk_reward_ratio,
            "kelly_criterion": self.kelly_criterion,
            "expectancy": self.expectancy,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
        }


@dataclass
class ProfitMetrics:
    """Comprehensive profit metrics."""

    # Overall profitability
    total_return: float
    annualized_return: float
    cagr: float  # Compound annual growth rate

    # Return distribution
    mean_daily_return: float
    median_daily_return: float
    return_std: float
    return_skewness: float
    return_kurtosis: float

    # Profit consistency
    profitable_days_pct: float
    profitable_weeks_pct: float
    profitable_months_pct: float
    longest_winning_streak_days: int
    longest_losing_streak_days: int

    # Risk-adjusted returns
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    omega_ratio: float

    # Statistical validation
    t_statistic: float
    p_value: float
    statistically_significant: bool  # p < 0.05

    # Confidence intervals (95%)
    return_ci_lower: float
    return_ci_upper: float
    sharpe_ci_lower: float
    sharpe_ci_upper: float

    # Trade analysis
    trade_analysis: Optional[TradeAnalysis] = None

    # Quality assessment
    profit_quality: ProfitQuality = ProfitQuality.ACCEPTABLE
    quality_score: float = 0.0  # 0-100

    def to_dict(self) -> Dict:
        result = {
            "total_return": self.total_return,
            "annualized_return": self.annualized_return,
            "cagr": self.cagr,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "calmar_ratio": self.calmar_ratio,
            "profitable_days_pct": self.profitable_days_pct,
            "profitable_months_pct": self.profitable_months_pct,
            "statistically_significant": self.statistically_significant,
            "p_value": self.p_value,
            "profit_quality": self.profit_quality.value,
            "quality_score": self.quality_score,
        }

        if self.trade_analysis:
            result["trade_analysis"] = self.trade_analysis.to_dict()

        return result


class ProfitAnalyzer:
    """
    Deep profit analysis with statistical validation.

    Analyzes:
    - Return distributions
    - Trade-level profitability
    - Statistical significance
    - Risk-adjusted metrics
    - Profit consistency
    """

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        target_return: float = 0.0,
        confidence_level: float = 0.95,
    ):
        """
        Initialize profit analyzer.

        Args:
            risk_free_rate: Annual risk-free rate (default 2%)
            target_return: Minimum acceptable return
            confidence_level: Confidence level for intervals
        """
        self.risk_free_rate = risk_free_rate
        self.target_return = target_return
        self.confidence_level = confidence_level

    def analyze(
        self,
        equity_curve: pd.Series,
        trades_df: Optional[pd.DataFrame] = None,
        trading_days: int = 252,
    ) -> ProfitMetrics:
        """
        Perform comprehensive profit analysis.

        Args:
            equity_curve: Time series of equity values
            trades_df: DataFrame with trade details (optional)
            trading_days: Trading days per year

        Returns:
            Comprehensive profit metrics
        """
        # Calculate returns
        returns = equity_curve.pct_change().dropna()

        if len(returns) == 0:
            logger.warning("Empty returns series")
            return self._create_empty_metrics()

        # Overall profitability
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0
        annualized_return = self._annualize_return(
            total_return, len(returns), trading_days
        )
        cagr = self._calculate_cagr(equity_curve, trading_days)

        # Return distribution
        mean_daily = returns.mean()
        median_daily = returns.median()
        return_std = returns.std()
        return_skew = returns.skew()
        return_kurt = returns.kurtosis()

        # Profit consistency
        profitable_days = (returns > 0).sum() / len(returns)

        # Calculate weekly/monthly if enough data
        if len(returns) > 30:
            weekly_returns = returns.resample("W").sum()
            profitable_weeks = (
                (weekly_returns > 0).sum() / len(weekly_returns)
                if len(weekly_returns) > 0
                else 0
            )
        else:
            profitable_weeks = profitable_days

        if len(returns) > 90:
            monthly_returns = returns.resample("M").sum()
            profitable_months = (
                (monthly_returns > 0).sum() / len(monthly_returns)
                if len(monthly_returns) > 0
                else 0
            )
        else:
            profitable_months = profitable_days

        # Winning/losing streaks
        longest_win_streak = self._calculate_longest_streak(returns > 0)
        longest_loss_streak = self._calculate_longest_streak(returns < 0)

        # Risk-adjusted metrics
        sharpe = self._calculate_sharpe(returns, trading_days)
        sortino = self._calculate_sortino(returns, trading_days)
        calmar = self._calculate_calmar(equity_curve, annualized_return)
        omega = self._calculate_omega(returns)

        # Statistical validation
        t_stat, p_value = self._test_statistical_significance(returns, trading_days)
        statistically_significant = p_value < 0.05

        # Confidence intervals
        return_ci = self._calculate_return_ci(returns, trading_days)
        sharpe_ci = self._calculate_sharpe_ci(sharpe, len(returns))

        # Trade analysis (if available)
        trade_analysis = None
        if trades_df is not None and not trades_df.empty:
            trade_analysis = self._analyze_trades(trades_df)

        # Quality assessment
        profit_quality, quality_score = self._assess_profit_quality(
            total_return=total_return,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            win_rate=trade_analysis.win_rate if trade_analysis else profitable_days,
            statistically_significant=statistically_significant,
        )

        return ProfitMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            cagr=cagr,
            mean_daily_return=mean_daily,
            median_daily_return=median_daily,
            return_std=return_std,
            return_skewness=return_skew,
            return_kurtosis=return_kurt,
            profitable_days_pct=profitable_days,
            profitable_weeks_pct=profitable_weeks,
            profitable_months_pct=profitable_months,
            longest_winning_streak_days=longest_win_streak,
            longest_losing_streak_days=longest_loss_streak,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            omega_ratio=omega,
            t_statistic=t_stat,
            p_value=p_value,
            statistically_significant=statistically_significant,
            return_ci_lower=return_ci[0],
            return_ci_upper=return_ci[1],
            sharpe_ci_lower=sharpe_ci[0],
            sharpe_ci_upper=sharpe_ci[1],
            trade_analysis=trade_analysis,
            profit_quality=profit_quality,
            quality_score=quality_score,
        )

    def _analyze_trades(self, trades_df: pd.DataFrame) -> TradeAnalysis:
        """Analyze individual trades."""
        if "pnl" not in trades_df.columns:
            logger.warning("No PnL column in trades DataFrame")
            return self._create_empty_trade_analysis()

        pnl = trades_df["pnl"].dropna()

        if len(pnl) == 0:
            return self._create_empty_trade_analysis()

        # Basic statistics
        total_trades = len(pnl)
        winning_trades = (pnl > 0).sum()
        losing_trades = (pnl < 0).sum()
        breakeven_trades = (pnl == 0).sum()

        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        loss_rate = losing_trades / total_trades if total_trades > 0 else 0

        # Profit metrics
        total_profit = pnl[pnl > 0].sum()
        total_loss = abs(pnl[pnl < 0].sum())
        net_profit = pnl.sum()
        profit_factor = total_profit / total_loss if total_loss > 0 else float("inf")

        # Average metrics
        avg_profit = pnl.mean()
        avg_loss = pnl.median()
        avg_win = pnl[pnl > 0].mean() if winning_trades > 0 else 0
        avg_loss_size = abs(pnl[pnl < 0].mean()) if losing_trades > 0 else 0

        # Extreme values
        largest_win = pnl.max()
        largest_loss = pnl.min()

        # Consecutive wins/losses
        consecutive_wins = self._calculate_longest_streak(pnl > 0)
        consecutive_losses = self._calculate_longest_streak(pnl < 0)

        # Risk metrics
        risk_reward = avg_win / avg_loss_size if avg_loss_size > 0 else 0

        # Kelly criterion: f* = (p * r - q) / r
        # where p = win rate, q = loss rate, r = risk/reward ratio
        if avg_loss_size > 0 and avg_win > 0:
            r = avg_win / avg_loss_size
            kelly = (win_rate * r - loss_rate) / r
            kelly = max(0, min(kelly, 0.25))  # Cap at 25%
        else:
            kelly = 0

        # Expectancy: average profit per trade
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss_size)

        # Distribution metrics
        profit_skew = pnl.skew()
        profit_kurt = pnl.kurtosis()

        return TradeAnalysis(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            breakeven_trades=breakeven_trades,
            win_rate=win_rate,
            loss_rate=loss_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=net_profit,
            profit_factor=profit_factor,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            avg_win=avg_win,
            avg_loss_size=avg_loss_size,
            largest_win=largest_win,
            largest_loss=largest_loss,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            risk_reward_ratio=risk_reward,
            kelly_criterion=kelly,
            expectancy=expectancy,
            profit_skewness=profit_skew,
            profit_kurtosis=profit_kurt,
        )

    def _annualize_return(
        self, total_return: float, periods: int, trading_days: int
    ) -> float:
        """Annualize return."""
        if periods == 0:
            return 0
        years = periods / trading_days
        if years <= 0:
            return 0
        return total_return / years

    def _calculate_cagr(self, equity_curve: pd.Series, trading_days: int) -> float:
        """Calculate compound annual growth rate."""
        if len(equity_curve) < 2:
            return 0

        total_return = equity_curve.iloc[-1] / equity_curve.iloc[0]
        years = len(equity_curve) / trading_days

        if years <= 0 or total_return <= 0:
            return 0

        cagr = (total_return ** (1 / years)) - 1
        return cagr

    def _calculate_sharpe(self, returns: pd.Series, trading_days: int) -> float:
        """Calculate Sharpe ratio."""
        if len(returns) < 2 or returns.std() == 0:
            return 0

        excess_returns = returns - self.risk_free_rate / trading_days
        sharpe = excess_returns.mean() / returns.std() * np.sqrt(trading_days)
        return sharpe

    def _calculate_sortino(self, returns: pd.Series, trading_days: int) -> float:
        """Calculate Sortino ratio (downside deviation)."""
        if len(returns) < 2:
            return 0

        excess_returns = returns - self.target_return / trading_days
        downside_returns = returns[returns < self.target_return / trading_days]

        if len(downside_returns) == 0:
            return float("inf")

        downside_std = downside_returns.std()
        if downside_std == 0:
            return 0

        sortino = excess_returns.mean() / downside_std * np.sqrt(trading_days)
        return sortino

    def _calculate_calmar(
        self, equity_curve: pd.Series, annualized_return: float
    ) -> float:
        """Calculate Calmar ratio (return / max drawdown)."""
        if len(equity_curve) < 2:
            return 0

        running_max = equity_curve.cummax()
        drawdown = (equity_curve - running_max) / running_max
        max_drawdown = abs(drawdown.min())

        if max_drawdown == 0:
            return float("inf")

        calmar = annualized_return / max_drawdown
        return calmar

    def _calculate_omega(self, returns: pd.Series, threshold: float = 0) -> float:
        """Calculate Omega ratio."""
        gains = returns[returns > threshold].sum()
        losses = abs(returns[returns < threshold].sum())

        if losses == 0:
            return float("inf")

        omega = gains / losses
        return omega

    def _test_statistical_significance(
        self, returns: pd.Series, trading_days: int
    ) -> Tuple[float, float]:
        """Test if returns are statistically significant (t-test)."""
        if len(returns) < 2:
            return 0, 1.0

        # One-sample t-test against zero return
        t_stat, p_value = stats.ttest_1samp(returns, 0)

        return t_stat, p_value

    def _calculate_return_ci(
        self, returns: pd.Series, trading_days: int
    ) -> Tuple[float, float]:
        """Calculate confidence interval for returns."""
        if len(returns) < 2:
            return (0, 0)

        mean_return = returns.mean()
        std_return = returns.std()
        n = len(returns)

        # Calculate t-critical value
        alpha = 1 - self.confidence_level
        t_crit = stats.t.ppf(1 - alpha / 2, n - 1)

        # Annualized CI
        annual_mean = mean_return * trading_days
        annual_std = std_return * np.sqrt(trading_days)

        margin = t_crit * annual_std / np.sqrt(n)

        return (annual_mean - margin, annual_mean + margin)

    def _calculate_sharpe_ci(self, sharpe: float, n: int) -> Tuple[float, float]:
        """Calculate confidence interval for Sharpe ratio."""
        if n < 2:
            return (0, 0)

        # Approximate standard error of Sharpe ratio
        se = np.sqrt((1 + 0.5 * sharpe**2) / n)

        # Calculate CI
        alpha = 1 - self.confidence_level
        z_crit = stats.norm.ppf(1 - alpha / 2)

        margin = z_crit * se

        return (sharpe - margin, sharpe + margin)

    def _calculate_longest_streak(self, condition_series: pd.Series) -> int:
        """Calculate longest consecutive True streak."""
        if len(condition_series) == 0:
            return 0

        max_streak = 0
        current_streak = 0

        for value in condition_series:
            if value:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0

        return max_streak

    def _assess_profit_quality(
        self,
        total_return: float,
        sharpe: float,
        sortino: float,
        calmar: float,
        win_rate: float,
        statistically_significant: bool,
    ) -> Tuple[ProfitQuality, float]:
        """Assess overall profit quality."""
        # Calculate composite quality score
        score = 0

        # Return component (30%)
        if total_return > 1.0:  # >100% return
            score += 30
        elif total_return > 0.5:  # >50%
            score += 25
        elif total_return > 0.2:  # >20%
            score += 20
        elif total_return > 0:
            score += 10

        # Sharpe component (25%)
        if sharpe > 2.0:
            score += 25
        elif sharpe > 1.5:
            score += 20
        elif sharpe > 1.0:
            score += 15
        elif sharpe > 0.5:
            score += 10

        # Sortino component (15%)
        if sortino > 2.5:
            score += 15
        elif sortino > 1.8:
            score += 12
        elif sortino > 1.2:
            score += 8
        elif sortino > 0.8:
            score += 5

        # Calmar component (15%)
        if calmar > 3.0:
            score += 15
        elif calmar > 2.0:
            score += 12
        elif calmar > 1.0:
            score += 8
        elif calmar > 0.5:
            score += 5

        # Win rate component (10%)
        if win_rate > 0.6:
            score += 10
        elif win_rate > 0.5:
            score += 7
        elif win_rate > 0.4:
            score += 5

        # Statistical significance (5%)
        if statistically_significant:
            score += 5

        # Classify quality
        if score >= 85:
            quality = ProfitQuality.EXCELLENT
        elif score >= 70:
            quality = ProfitQuality.GOOD
        elif score >= 55:
            quality = ProfitQuality.ACCEPTABLE
        elif score >= 40:
            quality = ProfitQuality.MARGINAL
        else:
            quality = ProfitQuality.POOR

        return quality, score

    def _create_empty_metrics(self) -> ProfitMetrics:
        """Create empty metrics for edge cases."""
        return ProfitMetrics(
            total_return=0,
            annualized_return=0,
            cagr=0,
            mean_daily_return=0,
            median_daily_return=0,
            return_std=0,
            return_skewness=0,
            return_kurtosis=0,
            profitable_days_pct=0,
            profitable_weeks_pct=0,
            profitable_months_pct=0,
            longest_winning_streak_days=0,
            longest_losing_streak_days=0,
            sharpe_ratio=0,
            sortino_ratio=0,
            calmar_ratio=0,
            omega_ratio=0,
            t_statistic=0,
            p_value=1.0,
            statistically_significant=False,
            return_ci_lower=0,
            return_ci_upper=0,
            sharpe_ci_lower=0,
            sharpe_ci_upper=0,
            profit_quality=ProfitQuality.POOR,
            quality_score=0,
        )

    def _create_empty_trade_analysis(self) -> TradeAnalysis:
        """Create empty trade analysis."""
        return TradeAnalysis(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            win_rate=0,
            loss_rate=0,
            total_profit=0,
            total_loss=0,
            net_profit=0,
            profit_factor=0,
            avg_profit=0,
            avg_loss=0,
            avg_win=0,
            avg_loss_size=0,
            largest_win=0,
            largest_loss=0,
            consecutive_wins=0,
            consecutive_losses=0,
            risk_reward_ratio=0,
            kelly_criterion=0,
            expectancy=0,
            profit_skewness=0,
            profit_kurtosis=0,
        )

    def generate_report(self, metrics: ProfitMetrics) -> str:
        """Generate human-readable profit analysis report."""
        lines = [
            "=" * 80,
            "PROFIT ANALYSIS REPORT",
            "=" * 80,
            "",
            "PROFITABILITY:",
            f"  Total Return: {metrics.total_return:.2%}",
            f"  Annualized Return: {metrics.annualized_return:.2%}",
            f"  CAGR: {metrics.cagr:.2%}",
            f"  Mean Daily Return: {metrics.mean_daily_return:.4%}",
            "",
            "RISK-ADJUSTED METRICS:",
            f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f} (95% CI: [{metrics.sharpe_ci_lower:.2f}, {metrics.sharpe_ci_upper:.2f}])",
            f"  Sortino Ratio: {metrics.sortino_ratio:.2f}",
            f"  Calmar Ratio: {metrics.calmar_ratio:.2f}",
            f"  Omega Ratio: {metrics.omega_ratio:.2f}",
            "",
            "CONSISTENCY:",
            f"  Profitable Days: {metrics.profitable_days_pct:.1%}",
            f"  Profitable Weeks: {metrics.profitable_weeks_pct:.1%}",
            f"  Profitable Months: {metrics.profitable_months_pct:.1%}",
            f"  Longest Win Streak: {metrics.longest_winning_streak_days} days",
            f"  Longest Loss Streak: {metrics.longest_losing_streak_days} days",
            "",
            "STATISTICAL VALIDATION:",
            f"  T-Statistic: {metrics.t_statistic:.2f}",
            f"  P-Value: {metrics.p_value:.4f}",
            f"  Statistically Significant: {'YES' if metrics.statistically_significant else 'NO'}",
            "",
            "QUALITY ASSESSMENT:",
            f"  Quality Score: {metrics.quality_score:.1f}/100",
            f"  Profit Quality: {metrics.profit_quality.value.upper()}",
        ]

        if metrics.trade_analysis:
            ta = metrics.trade_analysis
            lines.extend(
                [
                    "",
                    "TRADE ANALYSIS:",
                    f"  Total Trades: {ta.total_trades}",
                    f"  Win Rate: {ta.win_rate:.1%}",
                    f"  Profit Factor: {ta.profit_factor:.2f}",
                    f"  Average Win: {ta.avg_win:.2%}",
                    f"  Average Loss: {ta.avg_loss_size:.2%}",
                    f"  Risk/Reward Ratio: {ta.risk_reward_ratio:.2f}",
                    f"  Kelly Criterion: {ta.kelly_criterion:.1%}",
                    f"  Expectancy: {ta.expectancy:.4%}",
                    f"  Largest Win: {ta.largest_win:.2%}",
                    f"  Largest Loss: {ta.largest_loss:.2%}",
                ]
            )

        lines.append("=" * 80)

        return "\n".join(lines)
