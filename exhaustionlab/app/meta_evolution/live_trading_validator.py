"""
Live Trading Readiness Validator

Comprehensive validation system to determine if strategies are
truly ready for real-time deployment and profitable execution.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..llm.validators import PyneCoreValidator, ValidationIssue, ValidationResult
from .meta_config import MarketFocus, MetaStrategyType


@dataclass
class LiveTradingMetrics:
    """Comprehensive metrics for live trading readiness."""

    # Performance Metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    # Risk Metrics
    max_drawdown: float = 0.0
    ulcer_index: float = 0.0
    downside_deviation: float = 0.0
    var_95: float = 0.0  # Value at Risk 95%
    cvar_95: float = 0.0  # Conditional VAR 95%

    # Trading Statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_trade_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0

    # Execution Metrics
    avg_slippage: float = 0.0
    max_slippage: float = 0.0
    execution_delay_ms: float = 0.0
    fill_rate: float = 1.0  # % of trades that execute

    # Consistency Metrics
    monthly_volatility: float = 0.0
    stability_ratio: float = 0.0  # Consistency of returns
    correlation_to_benchmark: float = 0.0
    information_ratio: float = 0.0

    # Capacity Metrics
    max_position_size: float = 0.0
    market_impact_estimate: float = 0.0
    liquidity_requirements: float = 0.0

    # Quality Metrics
    code_complexity_score: float = 0.0
    backtest_rigor_score: float = 0.0
    robustness_score: float = 0.0
    production_readiness_score: float = 0.0

    @property
    def live_trading_score(self) -> float:
        """Overall live trading readiness score (0-100)."""

        # Performance component (35%)
        perf_score = self._calculate_performance_score() * 0.35

        # Risk component (30%)
        risk_score = self._calculate_risk_score() * 0.30

        # Execution component (20%)
        exec_score = self._calculate_execution_score() * 0.20

        # Quality component (15%)
        quality_score = self._calculate_quality_score() * 0.15

        total_score = perf_score + risk_score + exec_score + quality_score
        return min(100.0, max(0.0, total_score))

    def _calculate_performance_score(self) -> float:
        """Calculate performance component score (0-100)."""

        score = 50.0  # Base score

        # Sharpe ratio impact (max +25 points)
        if self.sharpe_ratio > 2.5:
            score += 25
        elif self.sharpe_ratio > 2.0:
            score += 20
        elif self.sharpe_ratio > 1.5:
            score += 15
        elif self.sharpe_ratio > 1.0:
            score += 10
        elif self.sharpe_ratio > 0.5:
            score += 5

        # Return impact (max +15 points)
        if self.annualized_return > 0.50:
            score += 15
        elif self.annualized_return > 0.30:
            score += 12
        elif self.annualized_return > 0.20:
            score += 8
        elif self.annualized_return > 0.10:
            score += 5
        elif self.annualized_return > 0.05:
            score += 2

        # Win rate impact (max +10 points)
        if self.win_rate > 0.65:
            score += 10
        elif self.win_rate > 0.55:
            score += 7
        elif self.win_rate > 0.45:
            score += 4
        elif self.win_rate > 0.35:
            score += 1
        elif self.win_rate < 0.25:
            score -= 5

        return min(100.0, max(0.0, score))

    def _calculate_risk_score(self) -> float:
        """Calculate risk management component score (0-100)."""

        score = 50.0  # Base score

        # Drawdown penalty (0 to -30 points)
        if self.max_drawdown > 0.40:
            score -= 30
        elif self.max_drawdown > 0.30:
            score -= 25
        elif self.max_drawdown > 0.25:
            score -= 20
        elif self.max_drawdown > 0.20:
            score -= 15
        elif self.max_drawdown > 0.15:
            score -= 10
        elif self.max_drawdown > 0.10:
            score -= 5
        elif self.max_drawdown < 0.05:
            score += 10

        # Volatility bonus (0 to +20 points)
        if self.monthly_volatility < 0.05:
            score += 20
        elif self.monthly_volatility < 0.08:
            score += 15
        elif self.monthly_volatility < 0.12:
            score += 10
        elif self.monthly_volatility < 0.15:
            score += 5

        # Stability bonus (0 to +10 points)
        if self.stability_ratio > 0.8:
            score += 10
        elif self.stability_ratio > 0.6:
            score += 7
        elif self.stability_ratio > 0.4:
            score += 4

        return min(100.0, max(0.0, score))

    def _calculate_execution_score(self) -> float:
        """Calculate execution component score (0-100)."""

        score = 50.0  # Base score

        # Slippage penalty (0 to -40 points)
        if self.avg_slippage > 0.02:  # > 2%
            score -= 40
        elif self.avg_slippage > 0.015:  # > 1.5%
            score -= 30
        elif self.avg_slippage > 0.01:  # > 1%
            score -= 20
        elif self.avg_slippage > 0.005:  # > 0.5%
            score -= 10
        elif self.avg_slippage < 0.002:  # < 0.2%
            score += 15

        # Execution delay penalty (0 to -30 points)
        if self.execution_delay_ms > 1000:  # > 1 second
            score -= 30
        elif self.execution_delay_ms > 500:  # > 500ms
            score -= 20
        elif self.execution_delay_ms > 200:  # > 200ms
            score -= 10
        elif self.execution_delay_ms < 50:  # < 50ms
            score += 20

        # Fill rate penalty (0 to -20 points)
        if self.fill_rate < 0.9:
            score -= 20
        elif self.fill_rate < 0.95:
            score -= 10
        elif self.fill_rate > 0.99:
            score += 10

        return min(100.0, max(0.0, score))

    def _calculate_quality_score(self) -> float:
        """Calculate code and backtest quality component score (0-100)."""

        score = 50.0  # Base score

        # Code quality bonus (0 to +30 points)
        if self.production_readiness_score > 0.9:
            score += 30
        elif self.production_readiness_score > 0.8:
            score += 25
        elif self.production_readiness_score > 0.7:
            score += 20
        elif self.production_readiness_score > 0.6:
            score += 15
        elif self.production_readiness_score > 0.5:
            score += 10
        elif self.production_readiness_score < 0.3:
            score -= 20

        # Backtest rigor bonus (0 to +20 points)
        if self.backtest_rigor_score > 0.9:
            score += 20
        elif self.backtest_rigor_score > 0.8:
            score += 15
        elif self.backtest_rigor_score > 0.7:
            score += 10
        elif self.backtest_rigor_score > 0.6:
            score += 5

        return min(100.0, max(0.0, score))


@dataclass
class TradingEnvironment:
    """Trading environment specifications for validation."""

    exchange_name: str = "binance"
    asset_classes: List[str] = field(default_factory=lambda: ["spot", "futures"])
    timeframes: List[str] = field(default_factory=lambda: ["1m", "5m", "15m", "1h"])
    minimum_liquidity: float = 10000000  # USD
    max_position_size: float = 1000000  # USD
    trading_hours: str = "24/7"  # Crypto is 24/7

    # Market conditions to test
    volatility_regimes: List[str] = field(default_factory=lambda: ["low", "medium", "high"])
    market_conditions: List[str] = field(default_factory=lambda: ["trending", "sideways", "volatile"])

    # Execution constraints
    max_slippage_tolerance: float = 0.01  # 1%
    max_execution_delay_ms: float = 500  # 500ms
    minimum_fill_rate: float = 0.95  # 95%

    # Capital constraints
    initial_capital: float = 100000  # $100k
    max_allocation_percent: float = 0.2  # 20% max per strategy


class LiveTradingValidator:
    """Comprehensive validator for live trading readiness."""

    def __init__(self, trading_env: Optional[TradingEnvironment] = None):
        self.trading_env = trading_env or TradingEnvironment()
        self.pyne_validator = PyneCoreValidator()
        self.logger = logging.getLogger(__name__)

        # Validation criteria thresholds
        self.thresholds = {
            # Performance thresholds
            "min_sharpe": 1.2,
            "min_annualized_return": 0.15,
            "min_win_rate": 0.45,
            "max_max_drawdown": 0.25,
            # Risk thresholds
            "max_monthly_volatility": 0.20,
            "min_stability_ratio": 0.3,
            # Execution thresholds
            "max_avg_slippage": 0.01,
            "max_execution_delay_ms": 500,
            "min_fill_rate": 0.95,
            # Quality thresholds
            "min_production_readiness": 0.7,
            "min_backtest_rigor": 0.6,
            "min_trades_per_month": 30,
            # Overall score threshold
            "min_live_trading_score": 70.0,
        }

    def validate_strategy_for_live_trading(
        self,
        strategy_code: str,
        backtest_data: pd.DataFrame,
        strategy_type: MetaStrategyType,
        market_focus: MarketFocus,
    ) -> Dict[str, Any]:
        """Comprehensive validation for live trading readiness."""

        # Initialize results
        validation_results = {
            "is_live_trading_ready": False,
            "metrics": LiveTradingMetrics(),
            "issues": [],
            "warnings": [],
            "recommendations": [],
            "validation_timestamp": datetime.now().isoformat(),
            "strategy_analysis": {},
        }

        # 1. Code Quality Validation
        code_validation = self._validate_code_quality(strategy_code)
        validation_results["code_validation"] = code_validation

        if not code_validation.is_valid:
            validation_results["issues"].append("Code fails basic validation")
            return validation_results

        # 2. Backtest Analysis
        backtest_metrics = self._analyze_backtest_performance(backtest_data, strategy_type, market_focus)
        validation_results["metrics"].update(backtest_metrics)

        # 3. Execution Analysis
        execution_analysis = self._analyze_execution_constraints(strategy_code, backtest_data)
        validation_results["metrics"].update(execution_analysis)

        # 4. Quality Scores
        quality_scores = self._calculate_quality_scores(strategy_code, backtest_data)
        validation_results["metrics"].update(quality_scores)

        # 5. Overall Assessment
        overall_score = validation_results["metrics"].live_trading_score
        validation_results["is_live_trading_ready"] = overall_score >= self.thresholds["min_live_trading_score"]

        # Generate issues and recommendations
        self._generate_validation_issues(validation_results, overall_score)

        return validation_results

    def _validate_code_quality(self, strategy_code: str) -> ValidationResult:
        """Validate PyneCore code quality."""

        # Basic syntax validation
        validation = self.pyne_validator.validate_pyne_code(strategy_code, check_runtime=True)

        if not validation.is_valid:
            return validation

        # Advanced quality assessment
        issues = []
        code_lines = strategy_code.split("\n")

        # Check for production-ready patterns
        has_error_handling = any("try:" in line or "except" in line for line in code_lines)
        has_constant_inputs = any("input." in line for line in code_lines)
        has_plots = any("plot(" in line or "plotshape" in line for line in code_lines)
        has_proper_structure = any("@script." in line for line in code_lines)

        if not has_error_handling:
            issues.append(
                ValidationIssue(
                    "warning",
                    None,
                    "No error handling detected",
                    "Wrap network or indicator logic with try/except blocks",
                )
            )

        if not has_constant_inputs:
            issues.append(
                ValidationIssue(
                    "warning",
                    None,
                    "No input parameters found",
                    "Add input() functions for configurability",
                )
            )

        if not has_plots:
            issues.append(
                ValidationIssue(
                    "warning",
                    None,
                    "No visualization plots found",
                    "Add plot() functions for signal visualization",
                )
            )

        if not has_proper_structure:
            issues.append(
                ValidationIssue(
                    "error",
                    None,
                    "Missing proper PyneCore structure",
                    "Add @script decorator and proper function definition",
                )
            )

        if len(code_lines) > 300:
            issues.append(
                ValidationIssue(
                    "warning",
                    None,
                    "Code complexity may be high",
                    "Consider breaking down complex logic",
                )
            )

        if len(code_lines) < 20:
            issues.append(ValidationIssue("error", None, "Code too simple", "Add comprehensive signal logic"))

        validation.issues.extend(issues)
        validation.is_valid = len([i for i in issues if i.severity == "error"]) == 0

        return validation

    def _analyze_backtest_performance(
        self,
        backtest_data: pd.DataFrame,
        strategy_type: MetaStrategyType,
        market_focus: MarketFocus,
    ) -> Dict:
        """Analyze backtest performance data."""

        if backtest_data.empty:
            return {
                "total_return": -1.0,
                "annualized_return": -1.0,
                "max_drawdown": 1.0,
                "sharpe_ratio": -1.0,
                "win_rate": 0.0,
                "total_trades": 0,
            }

        # Calculate returns
        if "returns" not in backtest_data.columns:
            # If no returns column, try to calculate from equity
            if "equity" in backtest_data.columns:
                backtest_data["returns"] = backtest_data["equity"].pct_change()
            else:
                return {"error": "No returns or equity data found"}

        returns = backtest_data["returns"].dropna()

        # Basic performance metrics
        total_return = (1 + returns).prod() - 1
        n_days = len(backtest_data) / (24 * 60)  # Assuming 1m data, convert to days
        annualized_return = (1 + total_return) ** (365.25 / max(n_days, 1)) - 1

        # Risk metrics
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdowns.min()

        # Sharpe ratio (annualized)
        if len(returns) > 1 and returns.std() > 0:
            daily_sharpe = returns.mean() / returns.std()
            sharpe_ratio = daily_sharpe * (252**0.5)
        else:
            sharpe_ratio = 0

        # Trading statistics
        if "trade_pnl" in backtest_data.columns:
            trades = backtest_data[backtest_data["trade_pnl"] != 0]["trade_pnl"]
            total_trades = len(trades)

            if total_trades > 0:
                win_trades = (trades > 0).sum()
                losing_trades = (trades < 0).sum()
                win_rate = win_trades / total_trades

                wins = trades[trades > 0]
                losses = trades[trades < 0]

                win_return = wins.mean() if len(wins) > 0 else 0
                loss_return = losses.mean() if len(losses) > 0 else 0

                profit_factor = wins.sum() / abs(losses.sum()) if losses.sum() != 0 else float("inf")
                avg_win = win_return
                avg_loss = abs(loss_return)
            else:
                total_trades = 0
                win_trades = 0
                losing_trades = 0
                win_rate = 0
                profit_factor = 1.0
                avg_win = 0
                avg_loss = 0
                win_return = 0
                loss_return = 0
        else:
            total_trades = 0
            win_trades = 0
            losing_trades = 0
            win_rate = 0
            profit_factor = 1.0
            avg_win = 0
            avg_loss = 0

        # Advanced metrics
        monthly_returns = returns.resample(f"{max(30, len(returns)//12)}h").sum() if len(returns) > 30 else [returns.sum()]
        monthly_volatility = monthly_returns.std() if len(monthly_returns) > 1 else 0

        avg_trade_return = trades.mean() if total_trades > 0 else 0

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "max_drawdown": abs(max_drawdown),
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "winning_trades": win_trades,
            "losing_trades": losing_trades,
            "profit_factor": profit_factor,
            "avg_trade_return": avg_trade_return,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "monthly_volatility": monthly_volatility,
        }

    def _analyze_execution_constraints(self, strategy_code: str, backtest_data: pd.DataFrame) -> Dict:
        """Analyze execution constraints and market impact."""

        # Estimate execution metrics based on strategy characteristics
        code_lower = strategy_code.lower()

        # Signal frequency estimation
        if "close[" in code_lower:
            # Count historical data references
            lookback_patterns = code_lower.count("[") - code_lower.count("close[1")  # Rough estimation
            avg_signal_frequency = 1.0 / (1 + lookback_patterns)  # Assuming 1m data
        else:
            avg_signal_frequency = 0.01  # Low frequency indicator

        # Complexity estimation for execution delay
        complexity_score = 0
        if any(comp in code_lower for comp in ["multiple", "nested", "loop", "array"]):
            complexity_score += 20
        if any(comp in code_lower for comp in ["calculate", "compute", "analyze"]):
            complexity_score += 10
        if len(strategy_code.split("\n")) > 200:
            complexity_score += 15

        execution_delay_ms = 50 + complexity_score  # Base delay 50ms + complexity

        # Slippage estimation based on volatility exposure
        if "volatility" in code_lower or "atr" in code_lower:
            avg_slippage = 0.008  # Higher slippage for volatility strategies
        elif "mean_reversion" in code_lower:
            avg_slippage = 0.006  # Medium slippage
        else:
            avg_slippage = 0.005  # Baseline slippage

        # Market impact estimation
        max_slippage = avg_slippage * 2.5  # Worst case

        # Fill rate estimation
        if "close" in code_lower and "cross" in code_lower:
            # High-frequency crossing strategies may have worse fill rates
            fill_rate = 0.90
        else:
            fill_rate = 0.98  # Most crypto strategies have good fill rates

        return {
            "avg_slippage": avg_slippage,
            "max_slippage": max_slippage,
            "execution_delay_ms": execution_delay_ms,
            "fill_rate": fill_rate,
            "signal_frequency": avg_signal_frequency,
        }

    def _calculate_quality_scores(self, strategy_code: str, backtest_data: pd.DataFrame) -> Dict:
        """Calculate comprehensive quality scores."""

        # Code complexity score
        code_lines = len(strategy_code.split("\n"))
        complexity_factors: List[int] = []

        if "import" in strategy_code.lower():
            complexity_factors.append(5)
        if "for" in strategy_code.lower() or "while" in strategy_code.lower():
            complexity_factors.append(10)
        if "try:" in strategy_code.lower():
            complexity_factors.append(3)
        if code_lines > 100:
            complexity_factors.append(8)

        code_complexity_score = min(1.0, sum(complexity_factors) / 50.0)

        # Backtest rigor score
        if len(backtest_data) > 10000:  # Good sample size
            backtest_rigor_score = 0.8
        elif len(backtest_data) > 5000:
            backtest_rigor_score = 0.6
        elif len(backtest_data) > 1000:
            backtest_rigor_score = 0.4
        else:
            backtest_rigor_score = 0.2

        # Production readiness score
        production_factors = []

        # Check for production patterns
        production_patterns = [
            "input.int(",
            "input.float(",
            "input.bool(",  # Parameterization
            "try:",
            "except:",  # Error handling
            "plot(",
            "plotshape(",  # Visualization
            "@script.",
            '"""@pyne"""',  # Proper structure
        ]

        for pattern in production_patterns:
            if pattern in strategy_code:
                production_factors.append(2)

        production_readiness_score = min(1.0, sum(production_factors) / 20.0)

        # Robustness score (based on backtest consistency)
        if "returns" in backtest_data.columns:
            returns = backtest_data["returns"].dropna()
            consistency_score = min(
                1.0,
                1.0 - returns.std() / abs(returns.mean()) if returns.mean() != 0 else 0,
            )
        else:
            consistency_score = 0.5

        return {
            "code_complexity_score": code_complexity_score,
            "backtest_rigor_score": backtest_rigor_score,
            "production_readiness_score": production_readiness_score,
            "robustness_score": consistency_score,
        }

    def _generate_validation_issues(self, validation_results: Dict, overall_score: float):
        """Generate specific issues and recommendations."""

        metrics = validation_results["metrics"]

        # Generate issues for failed criteria
        for criterion, threshold in self.thresholds.items():
            criterion_value = getattr(metrics, criterion, 0)

            if criterion == "min_sharpe" and criterion_value < threshold:
                validation_results["issues"].append(f"Sharpe ratio {metrics.sharpe_ratio:.2f} below threshold {threshold}")
                validation_results["recommendations"].append("Improve signal quality through better filtering or risk management")

            elif criterion == "max_max_drawdown" and criterion_value > threshold:
                validation_results["issues"].append(f"Maximum drawdown {metrics.max_drawdown:.1%} exceeds threshold {threshold:.1%}")
                validation_results["recommendations"].append("Enhance stop-loss logic and position sizing to reduce drawdown")

            elif criterion == "min_win_rate" and criterion_value < threshold:
                validation_results["issues"].append(f"Win rate {metrics.win_rate:.1%} below threshold {threshold:.1%}")
                validation_results["recommendations"].append("Add signal confirmation and filter to improve win rate")

            elif criterion == "max_avg_slippage" and criterion_value > threshold:
                validation_results["issues"].append(f"Average slippage {metrics.avg_slippage:.2%} exceeds threshold {threshold:.2%}")
                validation_results["recommendations"].append("Reduce trade frequency or implement slippage mitigation")

        # Generate warnings
        if overall_score < 50:
            validation_results["warnings"].append("Strategy shows significant weaknesses for live trading")
        elif overall_score < 70:
            validation_results["warnings"].append("Strategy has moderate issues that should be addressed")
        elif overall_score < 85:
            validation_results["warnings"].append("Strategy is good but could be optimized further")

        # Add overall recommendation
        if overall_score >= 70:
            validation_results["recommendations"].append("Strategy passes live trading requirements - consider small-scale deployment")
        else:
            validation_results["recommendations"].append("Strategy requires significant improvements before live deployment")

    def generate_validation_report(self, validation_results: Dict) -> str:
        """Generate comprehensive validation report."""

        score = validation_results["metrics"].live_trading_score
        is_ready = validation_results["is_live_trading_ready"]

        report = f"""
# LIVE TRADING VALIDATION REPORT
# Generated: {validation_results['validation_timestamp']}

## OVERALL STATUS
- **Live Trading Score: {score:.1f}/100**
- **Ready for Live Trading: {'YES' if is_ready else 'NO'}**

## PERFORMANCE METRICS
- Annualized Return: {validation_results['metrics'].annualized_return:.1%}
- Sharpe Ratio: {validation_results['metrics'].sharpe_ratio:.2f}
- Maximum Drawdown: {validation_results['metrics'].max_drawdown:.1%}
- Win Rate: {validation_results['metrics'].win_rate:.1%}
- Total Trades: {validation_results['metrics'].total_trades}

## EXECUTION METRICS
- Average Slippage: {validation_results['metrics'].avg_slippage:.2%}
- Execution Delay: {validation_results['metrics'].execution_delay_ms:.0f}ms
- Fill Rate: {validation_results['metrics'].fill_rate:.1%}

## QUALITY SCORES
- Production Readiness: {validation_results['metrics'].production_readiness_score:.1%}
- Code Complexity: {validation_results['metrics'].code_complexity_score:.1%}
- Backtest Rigor: {validation_results['metrics'].backtest_rigor_score:.1%}

"""

        if validation_results["issues"]:
            report += "\n## CRITICAL ISSUES\n"
            for issue in validation_results["issues"]:
                report += f"- {issue}\n"

        if validation_results["warnings"]:
            report += "\n## WARNINGS\n"
            for warning in validation_results["warnings"]:
                report += f"- {warning}\n"

        if validation_results["recommendations"]:
            report += "\n## RECOMMENDATIONS\n"
            for i, rec in enumerate(validation_results["recommendations"], 1):
                report += f"{i}. {rec}\n"

        return report

    def save_validation_results(
        self,
        validation_results: Dict,
        strategy_name: str,
        output_dir: Optional[Path] = None,
    ):
        """Save validation results to file."""

        if output_dir is None:
            output_dir = Path.home() / ".exhaustionlab" / "validation_reports"

        output_dir.mkdir(parents=True, exist_ok=True)

        # Save detailed results
        results_file = output_dir / f"{strategy_name}_validation.json"
        with open(results_file, "w") as f:
            json.dump(validation_results, f, indent=2, default=str)

        # Save report
        report_file = output_dir / f"{strategy_name}_report.md"
        report = self.generate_validation_report(validation_results)
        with open(report_file, "w") as f:
            f.write(report)

        self.logger.info(f"Validation results saved to {output_dir}")


def create_institutional_validator(
    capital_size: float = 100000,
    max_position_percent: float = 0.1,
    min_sharpe: float = 1.5,
) -> LiveTradingValidator:
    """Create validator for institutional-level trading."""

    env = TradingEnvironment(
        initial_capital=capital_size,
        max_position_size=capital_size * max_position_percent,
        max_allocation_percent=max_position_percent,
        max_slippage_tolerance=0.005,  # 0.5% for large positions
        max_execution_delay_ms=200,  # 200ms for institutional
        min_fill_rate=0.99,  # 99% fill rate required
    )

    validator = LiveTradingValidator(env)

    # Update thresholds for institutional standards
    validator.thresholds.update(
        {
            "min_sharpe": min_sharpe,
            "min_annualized_return": 0.25,  # Higher return requirement
            "min_live_trading_score": 85.0,  # Higher score requirement
            "max_avg_slippage": 0.005,  # Stricter slippage
            "max_execution_delay_ms": 200,
        }
    )

    return validator
