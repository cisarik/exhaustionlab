"""
Strategic Directive System with Adaptive Learning

Intelligent meta-evolution orchestration that:
- Defines strategic goals and constraints
- Adapts based on performance feedback
- Learns from successful/failed attempts
- Optimizes directive parameters over time
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import json

try:
    from .performance_metrics import PerformanceMetrics, calculate_comprehensive_metrics
except ImportError:
    from performance_metrics import PerformanceMetrics, calculate_comprehensive_metrics


logger = logging.getLogger(__name__)


class StrategyObjective(Enum):
    """High-level strategy objectives."""

    MAXIMIZE_RETURNS = "maximize_returns"
    MINIMIZE_RISK = "minimize_risk"
    BALANCED = "balanced"
    HIGH_SHARPE = "high_sharpe"
    LOW_DRAWDOWN = "low_drawdown"
    CONSISTENT_INCOME = "consistent_income"


class MarketCondition(Enum):
    """Market condition classifications."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"
    CALM = "calm"
    UNKNOWN = "unknown"


@dataclass
class PerformanceTarget:
    """Specific performance targets for strategy."""

    min_sharpe_ratio: float = 1.5
    max_drawdown: float = 0.20  # 20%
    min_win_rate: float = 0.50  # 50%
    min_profit_factor: float = 1.5
    min_monthly_return: float = 0.02  # 2% per month
    max_volatility: float = 0.30  # 30% annualized

    def meets_target(self, metrics: PerformanceMetrics) -> Tuple[bool, List[str]]:
        """
        Check if metrics meet performance targets.

        Returns:
            (meets_all_targets, list_of_failures)
        """
        failures = []

        if metrics.sharpe_ratio < self.min_sharpe_ratio:
            failures.append(
                f"Sharpe {metrics.sharpe_ratio:.2f} < target {self.min_sharpe_ratio}"
            )

        if abs(metrics.max_drawdown) > self.max_drawdown:
            failures.append(
                f"Drawdown {abs(metrics.max_drawdown):.2%} > target {self.max_drawdown:.2%}"
            )

        if metrics.win_rate < self.min_win_rate and metrics.total_trades > 0:
            failures.append(
                f"Win rate {metrics.win_rate:.1%} < target {self.min_win_rate:.1%}"
            )

        if metrics.profit_factor < self.min_profit_factor and metrics.total_trades > 0:
            failures.append(
                f"Profit factor {metrics.profit_factor:.2f} < target {self.min_profit_factor}"
            )

        if metrics.volatility > self.max_volatility:
            failures.append(
                f"Volatility {metrics.volatility:.2%} > target {self.max_volatility:.2%}"
            )

        return len(failures) == 0, failures


@dataclass
class StrategicDirective:
    """
    Complete strategic directive for meta-evolution.

    Defines what to optimize for and constraints to respect.
    """

    # Identity
    directive_id: str
    created_at: datetime = field(default_factory=datetime.now)

    # Objective
    objective: StrategyObjective = StrategyObjective.BALANCED
    description: str = ""

    # Market Context
    market_condition: MarketCondition = MarketCondition.UNKNOWN
    target_markets: List[str] = field(default_factory=lambda: ["crypto"])
    timeframes: List[str] = field(default_factory=lambda: ["15m", "1h"])

    # Performance Targets
    performance_targets: PerformanceTarget = field(default_factory=PerformanceTarget)

    # Strategy Parameters
    preferred_indicators: List[str] = field(default_factory=list)
    strategy_types: List[str] = field(
        default_factory=lambda: ["momentum", "trend_following"]
    )
    risk_profile: str = "balanced"  # "conservative", "balanced", "aggressive"

    # Constraints
    max_complexity: int = 500  # Max LOC
    require_stop_loss: bool = True
    require_position_sizing: bool = True
    max_indicators: int = 5

    # Capital & Risk
    initial_capital: float = 10000.0
    max_position_size: float = 0.10  # 10% of capital
    max_daily_loss: float = 0.02  # 2% daily loss limit

    # Adaptation Parameters
    learning_rate: float = 0.5  # How fast to adapt (0-1)
    exploration_rate: float = 0.3  # How much to explore vs exploit

    # Performance History
    attempts: int = 0
    successes: int = 0
    best_sharpe: float = 0.0
    best_quality_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "directive_id": self.directive_id,
            "objective": self.objective.value,
            "description": self.description,
            "market_condition": self.market_condition.value,
            "target_markets": self.target_markets,
            "timeframes": self.timeframes,
            "performance_targets": asdict(self.performance_targets),
            "preferred_indicators": self.preferred_indicators,
            "strategy_types": self.strategy_types,
            "risk_profile": self.risk_profile,
            "constraints": {
                "max_complexity": self.max_complexity,
                "require_stop_loss": self.require_stop_loss,
                "require_position_sizing": self.require_position_sizing,
                "max_indicators": self.max_indicators,
            },
            "capital": {
                "initial": self.initial_capital,
                "max_position_size": self.max_position_size,
                "max_daily_loss": self.max_daily_loss,
            },
            "adaptation": {
                "learning_rate": self.learning_rate,
                "exploration_rate": self.exploration_rate,
            },
            "history": {
                "attempts": self.attempts,
                "successes": self.successes,
                "best_sharpe": self.best_sharpe,
                "best_quality_score": self.best_quality_score,
            },
        }


class AdaptiveDirectiveManager:
    """
    Manages strategic directives with adaptive learning.

    Capabilities:
    - Create directives based on objectives
    - Update directives based on performance
    - Learn optimal parameters over time
    - Suggest directive improvements
    """

    def __init__(self):
        """Initialize directive manager."""
        self.directives: Dict[str, StrategicDirective] = {}
        self.performance_history: Dict[str, List[PerformanceMetrics]] = {}
        self.learning_insights: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)

    def create_directive(
        self,
        objective: StrategyObjective,
        market_condition: MarketCondition = MarketCondition.UNKNOWN,
        description: str = "",
    ) -> StrategicDirective:
        """
        Create new strategic directive.

        Args:
            objective: Primary objective
            market_condition: Current market condition
            description: Human-readable description

        Returns:
            New StrategicDirective
        """
        directive_id = f"{objective.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Create directive with objective-specific defaults
        directive = StrategicDirective(
            directive_id=directive_id,
            objective=objective,
            description=description or f"Strategy for {objective.value}",
            market_condition=market_condition,
        )

        # Customize based on objective
        self._customize_for_objective(directive, objective)

        # Store directive
        self.directives[directive_id] = directive
        self.performance_history[directive_id] = []

        self.logger.info(f"Created directive: {directive_id} ({objective.value})")

        return directive

    def update_from_performance(
        self, directive_id: str, metrics: PerformanceMetrics, code_complexity: int = 0
    ):
        """
        Update directive based on strategy performance.

        Args:
            directive_id: Directive to update
            metrics: Performance metrics
            code_complexity: Code complexity (LOC)
        """
        if directive_id not in self.directives:
            self.logger.error(f"Directive {directive_id} not found")
            return

        directive = self.directives[directive_id]

        # Update history
        directive.attempts += 1
        self.performance_history[directive_id].append(metrics)

        # Check if meets targets
        meets_targets, failures = directive.performance_targets.meets_target(metrics)

        if meets_targets:
            directive.successes += 1
            self.logger.info(
                f"✅ Directive {directive_id}: Success! ({directive.successes}/{directive.attempts})"
            )
        else:
            self.logger.info(f"⚠️ Directive {directive_id}: Failed targets: {failures}")

        # Update best performance
        if metrics.sharpe_ratio > directive.best_sharpe:
            directive.best_sharpe = metrics.sharpe_ratio
            self.logger.info(f"  🏆 New best Sharpe: {metrics.sharpe_ratio:.2f}")

        if metrics.quality_score > directive.best_quality_score:
            directive.best_quality_score = metrics.quality_score
            self.logger.info(f"  🏆 New best quality: {metrics.quality_score:.1f}")

        # Adaptive learning
        self._adapt_directive(directive, metrics, meets_targets)

    def _customize_for_objective(
        self, directive: StrategicDirective, objective: StrategyObjective
    ):
        """Customize directive parameters based on objective."""

        if objective == StrategyObjective.MAXIMIZE_RETURNS:
            directive.risk_profile = "aggressive"
            directive.performance_targets.min_sharpe_ratio = 1.0
            directive.performance_targets.max_drawdown = 0.30
            directive.max_position_size = 0.15
            directive.strategy_types = ["momentum", "breakout"]
            directive.preferred_indicators = ["RSI", "MACD", "ATR"]

        elif objective == StrategyObjective.MINIMIZE_RISK:
            directive.risk_profile = "conservative"
            directive.performance_targets.min_sharpe_ratio = 2.0
            directive.performance_targets.max_drawdown = 0.10
            directive.max_position_size = 0.05
            directive.strategy_types = ["mean_reversion", "range_trading"]
            directive.preferred_indicators = ["BB", "RSI", "STOCH"]

        elif objective == StrategyObjective.BALANCED:
            directive.risk_profile = "balanced"
            directive.performance_targets.min_sharpe_ratio = 1.5
            directive.performance_targets.max_drawdown = 0.20
            directive.max_position_size = 0.10
            directive.strategy_types = ["momentum", "trend_following"]
            directive.preferred_indicators = ["EMA", "RSI", "MACD"]

        elif objective == StrategyObjective.HIGH_SHARPE:
            directive.risk_profile = "balanced"
            directive.performance_targets.min_sharpe_ratio = 2.5
            directive.performance_targets.max_drawdown = 0.15
            directive.max_position_size = 0.08
            directive.strategy_types = ["momentum", "mean_reversion"]
            directive.preferred_indicators = ["RSI", "EMA", "BB"]

        elif objective == StrategyObjective.LOW_DRAWDOWN:
            directive.risk_profile = "conservative"
            directive.performance_targets.min_sharpe_ratio = 1.2
            directive.performance_targets.max_drawdown = 0.12
            directive.max_position_size = 0.06
            directive.strategy_types = ["trend_following", "mean_reversion"]
            directive.preferred_indicators = ["SMA", "EMA", "ATR"]

        elif objective == StrategyObjective.CONSISTENT_INCOME:
            directive.risk_profile = "balanced"
            directive.performance_targets.min_sharpe_ratio = 1.8
            directive.performance_targets.max_drawdown = 0.15
            directive.performance_targets.min_win_rate = 0.60
            directive.max_position_size = 0.08
            directive.strategy_types = ["mean_reversion", "range_trading"]
            directive.preferred_indicators = ["BB", "RSI", "MACD"]

    def _adapt_directive(
        self, directive: StrategicDirective, metrics: PerformanceMetrics, success: bool
    ):
        """
        Adapt directive parameters based on results.

        Uses reinforcement learning principles:
        - Increase exploration if consistently failing
        - Tighten constraints if succeeding
        - Adjust targets based on achieved performance
        """
        learning_rate = directive.learning_rate

        # Calculate success rate
        success_rate = (
            directive.successes / directive.attempts if directive.attempts > 0 else 0
        )

        # Adapt exploration rate
        if success_rate < 0.3:
            # Low success → increase exploration
            directive.exploration_rate = min(0.8, directive.exploration_rate + 0.1)
            self.logger.info(
                f"  📈 Increasing exploration to {directive.exploration_rate:.2f}"
            )
        elif success_rate > 0.7:
            # High success → reduce exploration (exploit)
            directive.exploration_rate = max(0.1, directive.exploration_rate - 0.05)
            self.logger.info(
                f"  📉 Reducing exploration to {directive.exploration_rate:.2f}"
            )

        # Adapt targets based on achieved performance
        if success and directive.attempts >= 3:
            # Gradually raise bar if succeeding
            if metrics.sharpe_ratio > directive.performance_targets.min_sharpe_ratio:
                new_target = directive.performance_targets.min_sharpe_ratio * (
                    1 + learning_rate * 0.1
                )
                directive.performance_targets.min_sharpe_ratio = new_target
                self.logger.info(f"  🎯 Raising Sharpe target to {new_target:.2f}")

            if (
                abs(metrics.max_drawdown)
                < directive.performance_targets.max_drawdown * 0.8
            ):
                new_target = directive.performance_targets.max_drawdown * (
                    1 - learning_rate * 0.1
                )
                directive.performance_targets.max_drawdown = max(0.05, new_target)
                self.logger.info(f"  🎯 Tightening drawdown target to {new_target:.2%}")

        elif not success and directive.attempts >= 5:
            # Relax constraints if consistently failing
            if (
                metrics.sharpe_ratio
                < directive.performance_targets.min_sharpe_ratio * 0.5
            ):
                new_target = directive.performance_targets.min_sharpe_ratio * (
                    1 - learning_rate * 0.15
                )
                directive.performance_targets.min_sharpe_ratio = max(0.5, new_target)
                self.logger.info(f"  🔽 Lowering Sharpe target to {new_target:.2f}")

    def get_best_directive(self) -> Optional[StrategicDirective]:
        """Get directive with best performance history."""
        if not self.directives:
            return None

        best_directive = None
        best_score = 0

        for directive in self.directives.values():
            if directive.best_quality_score > best_score:
                best_score = directive.best_quality_score
                best_directive = directive

        return best_directive

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about all directives."""
        if not self.directives:
            return {
                "total_directives": 0,
                "total_attempts": 0,
                "total_successes": 0,
                "success_rate": 0,
            }

        total_attempts = sum(d.attempts for d in self.directives.values())
        total_successes = sum(d.successes for d in self.directives.values())

        return {
            "total_directives": len(self.directives),
            "total_attempts": total_attempts,
            "total_successes": total_successes,
            "success_rate": (
                total_successes / total_attempts if total_attempts > 0 else 0
            ),
            "best_sharpe": max(
                (d.best_sharpe for d in self.directives.values()), default=0
            ),
            "best_quality": max(
                (d.best_quality_score for d in self.directives.values()), default=0
            ),
        }

    def save_directives(self, filepath: str):
        """Save all directives to JSON file."""
        data = {
            "directives": {k: v.to_dict() for k, v in self.directives.items()},
            "timestamp": datetime.now().isoformat(),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Saved {len(self.directives)} directives to {filepath}")


# Convenience functions


def create_balanced_directive() -> StrategicDirective:
    """Create balanced directive for general use."""
    manager = AdaptiveDirectiveManager()
    return manager.create_directive(
        objective=StrategyObjective.BALANCED,
        description="Balanced risk-reward strategy for crypto markets",
    )


def create_high_sharpe_directive() -> StrategicDirective:
    """Create directive optimized for Sharpe ratio."""
    manager = AdaptiveDirectiveManager()
    return manager.create_directive(
        objective=StrategyObjective.HIGH_SHARPE,
        description="High Sharpe ratio strategy with moderate risk",
    )


if __name__ == "__main__":
    # Test strategic directives
    logging.basicConfig(level=logging.INFO)

    print("\n🎯 STRATEGIC DIRECTIVES TEST\n")
    print("=" * 70)

    # Create manager
    manager = AdaptiveDirectiveManager()

    # Create different directives
    print("\n📋 Creating directives...")

    balanced = manager.create_directive(
        StrategyObjective.BALANCED,
        MarketCondition.BULL,
        "Balanced strategy for bull market",
    )

    high_sharpe = manager.create_directive(
        StrategyObjective.HIGH_SHARPE,
        MarketCondition.VOLATILE,
        "High Sharpe strategy for volatile conditions",
    )

    print(f"  ✅ Created {len(manager.directives)} directives")

    # Simulate performance feedback
    print("\n📊 Simulating performance feedback...")

    import numpy as np

    np.random.seed(42)

    for i in range(5):
        # Simulate improving performance
        metrics = PerformanceMetrics(
            sharpe_ratio=1.0 + i * 0.3,
            max_drawdown=-0.20 + i * 0.02,
            win_rate=0.50 + i * 0.05,
            profit_factor=1.5 + i * 0.2,
            quality_score=50 + i * 8,
        )

        print(f"\n  Iteration {i+1}:")
        print(f"    Sharpe: {metrics.sharpe_ratio:.2f}")
        print(f"    Quality: {metrics.quality_score:.1f}")

        manager.update_from_performance(balanced.directive_id, metrics, 300)

    # Show statistics
    print("\n📈 Final Statistics:")
    stats = manager.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Show directive state
    print(f"\n🎯 Balanced Directive State:")
    print(f"  Attempts: {balanced.attempts}")
    print(f"  Successes: {balanced.successes}")
    print(f"  Success Rate: {balanced.successes/balanced.attempts:.1%}")
    print(f"  Best Sharpe: {balanced.best_sharpe:.2f}")
    print(f"  Best Quality: {balanced.best_quality_score:.1f}")
    print(f"  Exploration Rate: {balanced.exploration_rate:.2f}")
    print(
        f"  Current Sharpe Target: {balanced.performance_targets.min_sharpe_ratio:.2f}"
    )

    print("\n✅ Strategic directives system operational!")
