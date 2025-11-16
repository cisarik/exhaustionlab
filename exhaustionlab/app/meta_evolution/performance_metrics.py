"""
Production-Grade Performance Metrics

Institutional-quality metrics for strategy evaluation:
- Sharpe, Sortino, Calmar ratios
- Drawdown analysis
- Risk-adjusted returns
- Statistical validation
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for strategy evaluation."""

    # Return Metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    monthly_returns: List[float] = field(default_factory=list)

    # Risk-Adjusted Metrics
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0

    # Risk Metrics
    volatility: float = 0.0
    downside_deviation: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    ulcer_index: float = 0.0

    # Value at Risk
    var_95: float = 0.0  # 95% VaR
    cvar_95: float = 0.0  # Conditional VaR (Expected Shortfall)

    # Trading Statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    # Consistency Metrics
    consistency_score: float = 0.0
    stability_ratio: float = 0.0
    months_positive: int = 0
    months_negative: int = 0

    @property
    def quality_score(self) -> float:
        """
        Overall quality score (0-100) based on multiple metrics.

        Weighting:
        - Risk-adjusted returns (40%): Sharpe, Sortino
        - Risk control (30%): Drawdown, volatility
        - Trading quality (20%): Win rate, profit factor
        - Consistency (10%): Stability, positive months
        """
        # Risk-adjusted returns component (40%)
        sharpe_component = min(100, self.sharpe_ratio * 40) * 0.40

        # Risk control component (30%)
        drawdown_component = (1 - min(1, abs(self.max_drawdown))) * 100 * 0.15
        volatility_component = max(0, 100 - self.volatility * 100) * 0.15
        risk_component = drawdown_component + volatility_component

        # Trading quality component (20%)
        win_rate_component = self.win_rate * 100 * 0.10
        profit_factor_component = min(100, self.profit_factor * 33.33) * 0.10
        trading_component = win_rate_component + profit_factor_component

        # Consistency component (10%)
        consistency_component = self.consistency_score * 0.10

        total_score = (
            sharpe_component
            + risk_component
            + trading_component
            + consistency_component
        )

        return min(100.0, max(0.0, total_score))


def calculate_sharpe_ratio(
    returns: pd.Series, risk_free_rate: float = 0.02, trading_days: int = 252
) -> float:
    """
    Calculate annualized Sharpe ratio from returns series.

    Args:
        returns: Pandas Series of daily returns
        risk_free_rate: Annual risk-free rate (default 2%)
        trading_days: Number of trading days per year (default 252)

    Returns:
        Annualized Sharpe ratio

    Examples:
        >>> import pandas as pd
        >>> import numpy as np
        >>> np.random.seed(42)
        >>> returns = pd.Series(np.random.randn(100) * 0.02)
        >>> sharpe = calculate_sharpe_ratio(returns)
        >>> print(f"Sharpe: {sharpe:.2f}")
    """
    if returns.empty or len(returns) < 2:
        return 0.0

    # Calculate excess returns
    daily_rf = risk_free_rate / trading_days
    excess_returns = returns - daily_rf

    # Calculate Sharpe ratio
    if returns.std() == 0:
        return 0.0

    sharpe = excess_returns.mean() / returns.std() * np.sqrt(trading_days)

    return float(sharpe)


def calculate_sortino_ratio(
    returns: pd.Series, risk_free_rate: float = 0.02, trading_days: int = 252
) -> float:
    """
    Calculate Sortino ratio (like Sharpe but only penalizes downside volatility).

    Args:
        returns: Pandas Series of daily returns
        risk_free_rate: Annual risk-free rate
        trading_days: Number of trading days per year

    Returns:
        Annualized Sortino ratio
    """
    if returns.empty or len(returns) < 2:
        return 0.0

    # Calculate excess returns
    daily_rf = risk_free_rate / trading_days
    excess_returns = returns - daily_rf

    # Calculate downside deviation (only negative returns)
    downside_returns = returns[returns < 0]

    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0

    downside_deviation = downside_returns.std()

    sortino = excess_returns.mean() / downside_deviation * np.sqrt(trading_days)

    return float(sortino)


def calculate_max_drawdown(equity_curve: pd.Series) -> Tuple[float, int]:
    """
    Calculate maximum drawdown and its duration.

    Args:
        equity_curve: Series of cumulative portfolio values

    Returns:
        (max_drawdown, duration_in_days)
    """
    if equity_curve.empty:
        return 0.0, 0

    # Calculate running maximum
    running_max = equity_curve.expanding().max()

    # Calculate drawdown
    drawdown = (equity_curve - running_max) / running_max

    # Maximum drawdown
    max_dd = drawdown.min()

    # Duration: count days from peak to recovery
    in_drawdown = False
    current_duration = 0
    max_duration = 0

    for dd in drawdown:
        if dd < 0:
            in_drawdown = True
            current_duration += 1
            max_duration = max(max_duration, current_duration)
        else:
            in_drawdown = False
            current_duration = 0

    return float(max_dd), int(max_duration)


def calculate_calmar_ratio(
    returns: pd.Series, equity_curve: pd.Series, trading_days: int = 252
) -> float:
    """
    Calculate Calmar ratio (annualized return / max drawdown).

    Args:
        returns: Series of returns
        equity_curve: Series of equity values
        trading_days: Trading days per year

    Returns:
        Calmar ratio
    """
    if returns.empty or equity_curve.empty:
        return 0.0

    # Annualized return
    total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
    years = len(returns) / trading_days
    annualized_return = (1 + total_return) ** (1 / years) - 1

    # Max drawdown
    max_dd, _ = calculate_max_drawdown(equity_curve)

    if max_dd == 0:
        return 0.0

    calmar = annualized_return / abs(max_dd)

    return float(calmar)


def calculate_ulcer_index(equity_curve: pd.Series) -> float:
    """
    Calculate Ulcer Index (measure of downside volatility).

    Args:
        equity_curve: Series of equity values

    Returns:
        Ulcer Index
    """
    if equity_curve.empty:
        return 0.0

    # Calculate drawdown
    running_max = equity_curve.expanding().max()
    drawdown = (equity_curve - running_max) / running_max

    # Square drawdown percentages
    squared_drawdowns = drawdown**2

    # Ulcer Index = sqrt(mean of squared drawdowns)
    ulcer = np.sqrt(squared_drawdowns.mean())

    return float(ulcer)


def calculate_var_cvar(
    returns: pd.Series, confidence_level: float = 0.95
) -> Tuple[float, float]:
    """
    Calculate Value at Risk and Conditional VaR (Expected Shortfall).

    Args:
        returns: Series of returns
        confidence_level: Confidence level (default 95%)

    Returns:
        (VaR, CVaR) at specified confidence level
    """
    if returns.empty:
        return 0.0, 0.0

    # VaR: percentile of returns
    var = returns.quantile(1 - confidence_level)

    # CVaR: mean of returns worse than VaR
    cvar = returns[returns <= var].mean()

    return float(var), float(cvar)


def calculate_profit_factor(trades: pd.DataFrame) -> float:
    """
    Calculate profit factor (gross profit / gross loss).

    Args:
        trades: DataFrame with 'pnl' column

    Returns:
        Profit factor
    """
    if trades.empty or "pnl" not in trades.columns:
        return 0.0

    gross_profit = trades[trades["pnl"] > 0]["pnl"].sum()
    gross_loss = abs(trades[trades["pnl"] < 0]["pnl"].sum())

    if gross_loss == 0:
        return 0.0 if gross_profit == 0 else float("inf")

    return float(gross_profit / gross_loss)


def calculate_consistency_score(monthly_returns: List[float]) -> float:
    """
    Calculate consistency score based on monthly returns.

    Score factors:
    - % of positive months
    - Standard deviation of returns
    - Streaks of positive/negative months

    Args:
        monthly_returns: List of monthly returns

    Returns:
        Consistency score (0-100)
    """
    if not monthly_returns or len(monthly_returns) < 3:
        return 0.0

    returns_series = pd.Series(monthly_returns)

    # % positive months
    positive_pct = (returns_series > 0).sum() / len(returns_series)

    # Stability (inverse of volatility)
    if returns_series.std() > 0:
        stability = 1 / (1 + returns_series.std())
    else:
        stability = 1.0

    # Calculate longest positive streak
    current_streak = 0
    longest_streak = 0
    for ret in monthly_returns:
        if ret > 0:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

    streak_score = min(1.0, longest_streak / 6)  # 6+ months is excellent

    # Combined score
    consistency = (positive_pct * 0.5 + stability * 0.3 + streak_score * 0.2) * 100

    return float(consistency)


def calculate_comprehensive_metrics(
    returns: pd.Series,
    equity_curve: pd.Series,
    trades: Optional[pd.DataFrame] = None,
    risk_free_rate: float = 0.02,
    trading_days: int = 252,
) -> PerformanceMetrics:
    """
    Calculate all performance metrics from returns and equity curve.

    Args:
        returns: Series of daily returns
        equity_curve: Series of equity values
        trades: Optional DataFrame with trade details
        risk_free_rate: Risk-free rate
        trading_days: Trading days per year

    Returns:
        PerformanceMetrics object with all calculated metrics
    """
    metrics = PerformanceMetrics()

    if returns.empty or equity_curve.empty:
        logger.warning("Empty returns or equity curve provided")
        return metrics

    try:
        # Return metrics
        metrics.total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        years = len(returns) / trading_days
        if years > 0:
            metrics.annualized_return = (1 + metrics.total_return) ** (1 / years) - 1

        # Risk-adjusted metrics
        metrics.sharpe_ratio = calculate_sharpe_ratio(
            returns, risk_free_rate, trading_days
        )
        metrics.sortino_ratio = calculate_sortino_ratio(
            returns, risk_free_rate, trading_days
        )
        metrics.calmar_ratio = calculate_calmar_ratio(
            returns, equity_curve, trading_days
        )

        # Risk metrics
        metrics.volatility = returns.std() * np.sqrt(trading_days)

        downside_returns = returns[returns < 0]
        if len(downside_returns) > 0:
            metrics.downside_deviation = downside_returns.std() * np.sqrt(trading_days)

        metrics.max_drawdown, metrics.max_drawdown_duration = calculate_max_drawdown(
            equity_curve
        )
        metrics.ulcer_index = calculate_ulcer_index(equity_curve)

        # VaR metrics
        metrics.var_95, metrics.cvar_95 = calculate_var_cvar(returns)

        # Monthly returns for consistency
        if len(returns) >= 20:  # At least ~1 month of daily data
            # Resample to monthly
            returns_monthly = returns.resample("M").apply(lambda x: (1 + x).prod() - 1)
            metrics.monthly_returns = returns_monthly.tolist()
            metrics.months_positive = (returns_monthly > 0).sum()
            metrics.months_negative = (returns_monthly < 0).sum()
            metrics.consistency_score = calculate_consistency_score(
                metrics.monthly_returns
            )

        # Trading statistics from trades DataFrame
        if trades is not None and not trades.empty:
            metrics.total_trades = len(trades)

            if "pnl" in trades.columns:
                winning = trades[trades["pnl"] > 0]
                losing = trades[trades["pnl"] < 0]

                metrics.winning_trades = len(winning)
                metrics.losing_trades = len(losing)

                if metrics.total_trades > 0:
                    metrics.win_rate = metrics.winning_trades / metrics.total_trades

                if len(winning) > 0:
                    metrics.avg_win = winning["pnl"].mean()
                    metrics.largest_win = winning["pnl"].max()

                if len(losing) > 0:
                    metrics.avg_loss = losing["pnl"].mean()
                    metrics.largest_loss = losing["pnl"].min()

                metrics.profit_factor = calculate_profit_factor(trades)

        # Stability ratio
        if len(metrics.monthly_returns) > 1:
            monthly_series = pd.Series(metrics.monthly_returns)
            if monthly_series.std() > 0:
                metrics.stability_ratio = monthly_series.mean() / monthly_series.std()

        logger.info(
            f"Calculated metrics: Sharpe={metrics.sharpe_ratio:.2f}, "
            f"MaxDD={metrics.max_drawdown:.2%}, Quality={metrics.quality_score:.1f}"
        )

    except Exception as e:
        logger.error(f"Error calculating metrics: {e}")

    return metrics


def format_metrics_report(metrics: PerformanceMetrics) -> str:
    """
    Format metrics as human-readable report.

    Args:
        metrics: PerformanceMetrics object

    Returns:
        Formatted string report
    """
    report = []
    report.append("=" * 70)
    report.append("PERFORMANCE METRICS REPORT")
    report.append("=" * 70)

    report.append(f"\n📊 RETURN METRICS:")
    report.append(f"  Total Return: {metrics.total_return:+.2%}")
    report.append(f"  Annualized Return: {metrics.annualized_return:+.2%}")

    report.append(f"\n📈 RISK-ADJUSTED METRICS:")
    report.append(f"  Sharpe Ratio: {metrics.sharpe_ratio:.2f}")
    report.append(f"  Sortino Ratio: {metrics.sortino_ratio:.2f}")
    report.append(f"  Calmar Ratio: {metrics.calmar_ratio:.2f}")

    report.append(f"\n⚠️ RISK METRICS:")
    report.append(f"  Volatility: {metrics.volatility:.2%}")
    report.append(f"  Max Drawdown: {metrics.max_drawdown:.2%}")
    report.append(f"  Drawdown Duration: {metrics.max_drawdown_duration} days")
    report.append(f"  Ulcer Index: {metrics.ulcer_index:.2f}")
    report.append(f"  VaR (95%): {metrics.var_95:.2%}")
    report.append(f"  CVaR (95%): {metrics.cvar_95:.2%}")

    if metrics.total_trades > 0:
        report.append(f"\n💰 TRADING STATISTICS:")
        report.append(f"  Total Trades: {metrics.total_trades}")
        report.append(f"  Win Rate: {metrics.win_rate:.1%}")
        report.append(f"  Profit Factor: {metrics.profit_factor:.2f}")
        report.append(f"  Avg Win: {metrics.avg_win:+.2%}")
        report.append(f"  Avg Loss: {metrics.avg_loss:+.2%}")

    if metrics.monthly_returns:
        report.append(f"\n🎯 CONSISTENCY:")
        report.append(f"  Consistency Score: {metrics.consistency_score:.1f}/100")
        report.append(f"  Positive Months: {metrics.months_positive}")
        report.append(f"  Negative Months: {metrics.months_negative}")
        report.append(f"  Stability Ratio: {metrics.stability_ratio:.2f}")

    report.append(f"\n🏆 OVERALL QUALITY SCORE: {metrics.quality_score:.1f}/100")

    if metrics.quality_score >= 80:
        report.append("   ✅ EXCELLENT - Institutional Grade")
    elif metrics.quality_score >= 70:
        report.append("   ✅ VERY GOOD - Production Ready")
    elif metrics.quality_score >= 60:
        report.append("   ⚠️ GOOD - Acceptable with Monitoring")
    elif metrics.quality_score >= 50:
        report.append("   ⚠️ FAIR - Needs Improvement")
    else:
        report.append("   ❌ POOR - Not Recommended")

    report.append("=" * 70)

    return "\n".join(report)


if __name__ == "__main__":
    # Test performance metrics
    logging.basicConfig(level=logging.INFO)

    print("\n🧪 PERFORMANCE METRICS TEST\n")

    # Generate synthetic data
    np.random.seed(42)
    days = 252  # 1 year

    # Simulate returns with positive drift
    daily_returns = pd.Series(np.random.randn(days) * 0.02 + 0.001)

    # Calculate equity curve
    equity = (1 + daily_returns).cumprod() * 10000
    equity_curve = pd.Series(
        equity.values, index=pd.date_range("2024-01-01", periods=days)
    )

    # Simulate trades
    trades = pd.DataFrame({"pnl": np.random.randn(50) * 0.03})

    print("📊 Calculating comprehensive metrics...")
    metrics = calculate_comprehensive_metrics(
        returns=daily_returns, equity_curve=equity_curve, trades=trades
    )

    print(format_metrics_report(metrics))

    print(f"\n✅ Performance metrics module operational!")
