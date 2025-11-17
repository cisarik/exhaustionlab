"""
Lightweight Global Fitness Configuration

Simple, centralized fitness scoring configuration
for strategy evaluation across different use cases.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class FitnessWeights:
    """Weight configuration for composite fitness calculation (0-1 scale)."""

    # Core profitability
    pnl: float = 0.25
    sharpe_ratio: float = 0.20

    # Risk management
    max_drawdown: float = 0.20  # Lower is better (inverted in calculation)
    win_rate: float = 0.15

    # Trading quality
    consistency: float = 0.10  # Downside deviation ratio
    trade_frequency: float = 0.05

    # Real-world factors
    slippage_resistance: float = 0.03
    execution_speed: float = 0.02

    # Bonus for market robustness
    market_diversity: float = 0.05

    def validate(self) -> bool:
        """Check if weights sum to approximately 1.0."""
        total = sum(
            [
                self.pnl,
                self.sharpe_ratio,
                self.max_drawdown,
                self.win_rate,
                self.consistency,
                self.trade_frequency,
                self.slippage_resistance,
                self.execution_speed,
                self.market_diversity,
            ]
        )
        return 0.95 <= total <= 1.05  # Allow small rounding errors

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pnl": self.pnl,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "consistency": self.consistency,
            "trade_frequency": self.trade_frequency,
            "slippage_resistance": self.slippage_resistance,
            "execution_speed": self.execution_speed,
            "market_diversity": self.market_diversity,
        }


@dataclass
class FitnessThresholds:
    """Validation thresholds for deployment readiness."""

    # Minimum performance requirements
    min_fitness_score: float = 0.3
    min_sharpe_ratio: float = 0.5
    min_win_rate: float = 0.45
    max_drawdown: float = 0.25
    min_trades_per_market: int = 10
    min_markets_tested: int = 3

    # Real-world constraints
    max_slippage_impact: float = 0.01  # 1%
    max_execution_delay_ms: float = 500
    max_market_impact: float = 0.05  # 5%

    # Trading frequency constraints
    min_trades_total: int = 30
    max_trades_per_day: int = 100


@dataclass
class FitnessNormalization:
    """Normalization ranges for different metrics."""

    pnl_max: float = 1000.0  # Max PnL for 1.0 score (%)
    sharpe_max: float = 3.0  # Max Sharpe for 1.0 score
    trade_freq_max: float = 50  # Max avg trades/day for 1.0
    slippage_tolerance: float = 0.05  # Max slippage for full penalty


class GlobalFitnessConfig:
    """Global fitness configuration manager."""

    # Preset configurations
    CONSERVATIVE = FitnessWeights(
        pnl=0.15,
        sharpe_ratio=0.30,
        max_drawdown=0.25,
        win_rate=0.20,
        consistency=0.15,
        trade_frequency=0.05,
        slippage_resistance=0.10,
        execution_speed=0.05,
        market_diversity=0.15,
    )

    BALANCED = FitnessWeights()  # Default values above

    AGGRESSIVE = FitnessWeights(
        pnl=0.35,
        sharpe_ratio=0.15,
        max_drawdown=0.15,
        win_rate=0.10,
        consistency=0.08,
        trade_frequency=0.12,
        slippage_resistance=0.02,
        execution_speed=0.03,
        market_diversity=0.08,
    )

    LIVE_TRADING = FitnessWeights(
        pnl=0.20,
        sharpe_ratio=0.25,
        max_drawdown=0.25,
        win_rate=0.20,
        consistency=0.20,
        trade_frequency=0.02,
        slippage_resistance=0.15,
        execution_speed=0.10,
        market_diversity=0.10,
    )

    # Preset thresholds
    DEMO_TRADING = FitnessThresholds(
        min_fitness_score=0.2,
        min_sharpe_ratio=0.3,
        min_win_rate=0.40,
        max_drawdown=0.35,
        min_trades_per_market=5,
        min_markets_tested=2,
        max_slippage_impact=0.02,
        max_execution_delay_ms=1000,
        min_trades_total=20,
        max_trades_per_day=200,
    )

    PRODUCTION_TRADING = FitnessThresholds(
        min_fitness_score=0.4,
        min_sharpe_ratio=0.8,
        min_win_rate=0.50,
        max_drawdown=0.20,
        min_trades_per_market=15,
        min_markets_tested=5,
        max_slippage_impact=0.008,
        max_execution_delay_ms=300,
        min_trades_total=50,
        max_trades_per_day=80,
    )

    # Default configs
    DEFAULT_WEIGHTS = BALANCED
    DEFAULT_THRESHOLDS = DEMO_TRADING

    def __init__(
        self,
        weights: Optional[FitnessWeights] = None,
        thresholds: Optional[FitnessThresholds] = None,
        normalization: Optional[FitnessNormalization] = None,
    ):
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS
        self.normalization = normalization or FitnessNormalization()

        # Validate weights
        if not self.weights.validate():
            raise ValueError("Fitness weights must sum to ~1.0")

    @classmethod
    def from_preset(cls, preset_name: str):
        """Create config from predefined preset."""
        preset_name = preset_name.upper()

        weights_map = {
            "CONSERVATIVE": cls.CONSERVATIVE,
            "BALANCED": cls.BALANCED,
            "AGGRESSIVE": cls.AGGRESSIVE,
            "LIVE_TRADING": cls.LIVE_TRADING,
        }

        thresholds_map = {
            "DEMO": cls.DEMO_TRADING,
            "PRODUCTION": cls.PRODUCTION_TRADING,
        }

        # Parse preset like "BALANCED_DEMO" or "AGGRESSIVE_PRODUCTION"
        parts = preset_name.split("_")
        if len(parts) == 2:
            weight_preset, threshold_preset = parts
            weights = weights_map.get(weight_preset, cls.BALANCED)
            thresholds = thresholds_map.get(threshold_preset, cls.DEMO_TRADING)
        else:
            weights = weights_map.get(preset_name, cls.BALANCED)
            thresholds = cls.DEMO_TRADING  # Default to demo thresholds

        return cls(weights=weights, thresholds=thresholds)

    def save_to_file(self, config_path: Path):
        """Save configuration to JSON file."""
        import json

        config_data = {
            "weights": self.weights.to_dict(),
            "thresholds": {
                "min_fitness_score": self.thresholds.min_fitness_score,
                "min_sharpe_ratio": self.thresholds.min_sharpe_ratio,
                "min_win_rate": self.thresholds.min_win_rate,
                "max_drawdown": self.thresholds.max_drawdown,
                "min_trades_per_market": self.thresholds.min_trades_per_market,
                "min_markets_tested": self.thresholds.min_markets_tested,
                "max_slippage_impact": self.thresholds.max_slippage_impact,
                "max_execution_delay_ms": self.thresholds.max_execution_delay_ms,
                "max_market_impact": self.thresholds.max_market_impact,
                "min_trades_total": self.thresholds.min_trades_total,
                "max_trades_per_day": self.thresholds.max_trades_per_day,
            },
            "normalization": {
                "pnl_max": self.normalization.pnl_max,
                "sharpe_max": self.normalization.sharpe_max,
                "trade_freq_max": self.normalization.trade_freq_max,
                "slippage_tolerance": self.normalization.slippage_tolerance,
            },
        }

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config_data, f, indent=2)

    @classmethod
    def load_from_file(cls, config_path: Path):
        """Load configuration from JSON file."""
        import json

        with open(config_path) as f:
            config_data = json.load(f)

        weights = FitnessWeights(**config_data["weights"])
        thresholds = FitnessThresholds(**config_data["thresholds"])
        normalization = FitnessNormalization(**config_data["normalization"])

        return cls(weights=weights, thresholds=thresholds, normalization=normalization)

    def normalize_metric(self, value: float, metric_type: str) -> float:
        """Normalize metric value to 0-1 scale."""
        norm_ranges = {
            "pnl": (0, self.normalization.pnl_max),
            "sharpe_ratio": (0, self.normalization.sharpe_max),
            "trade_frequency": (0, self.normalization.trade_freq_max),
            "slippage_impact": (0, self.normalization.slippage_tolerance),
            "execution_delay": (
                0,
                self.normalization.max_execution_delay_ms / 1000,
            ),  # Convert ms to seconds
        }

        if metric_type in norm_ranges:
            min_val, max_val = norm_ranges[metric_type]
            return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))

        # Special handling for inverted metrics (lower is better)
        if metric_type in ["max_drawdown"]:
            # Drawdown: 0% = 1.0, threshold% = 0.0
            threshold = self.thresholds.max_drawdown
            return max(0.0, 1.0 - (value / threshold))

        # Default: assume already normalized
        return max(0.0, min(1.0, value))

    def calculate_composite_fitness(self, metrics: Dict) -> float:
        """Calculate composite fitness score from metrics."""

        # Normalize each metric
        normalized = {}

        # Core metrics
        normalized["pnl"] = self.normalize_metric(abs(metrics.get("total_pnl", 0)), "pnl")
        normalized["sharpe_ratio"] = self.normalize_metric(max(0, metrics.get("sharpe_ratio", 0)), "sharpe_ratio")
        normalized["max_drawdown"] = self.normalize_metric(metrics.get("max_drawdown", 1.0), "max_drawdown")
        normalized["win_rate"] = metrics.get("win_rate", 0.0)  # Already 0-1
        normalized["trade_frequency"] = self.normalize_metric(metrics.get("avg_daily_trades", 25), "trade_frequency")

        # Consistency metric
        volatility_adj_return = metrics.get("volatility_adjusted_return", 0)
        downside_deviation = metrics.get("downside_deviation", 1.0)
        normalized["consistency"] = 1.0 - min(1.0, downside_deviation / max(volatility_adj_return, 0.1))

        # Real-world factors
        normalized["slippage_impact"] = 1.0 - self.normalize_metric(metrics.get("slippage_impact", 0.01), "slippage_impact")
        normalized["execution_speed"] = 1.0 - self.normalize_metric(metrics.get("execution_delay_ms", 100) / 1000, "execution_delay")

        # Market diversity bonus
        markets_tested = len(metrics.get("markets_tested", []))
        normalized["market_diversity"] = min(1.0, markets_tested / 5.0)

        # Calculate weighted sum
        weighted_score = (
            self.weights.pnl * normalized["pnl"]
            + self.weights.sharpe_ratio * normalized["sharpe_ratio"]
            + self.weights.max_drawdown * normalized["max_drawdown"]
            + self.weights.win_rate * normalized["win_rate"]
            + self.weights.consistency * normalized["consistency"]
            + self.weights.trade_frequency * normalized["trade_frequency"]
            + self.weights.slippage_resistance * normalized["slippage_impact"]
            + self.weights.execution_speed * normalized["execution_speed"]
            + self.weights.market_diversity * normalized["market_diversity"]
        )

        return weighted_score

    def is_deployment_ready(self, fitness_score: float, metrics: Dict) -> tuple[bool, str]:
        """Check if strategy is ready for deployment."""
        reasons = []

        if fitness_score < self.thresholds.min_fitness_score:
            reasons.append(f"Low fitness: {fitness_score:.3f} < {self.thresholds.min_fitness_score}")

        if metrics.get("sharpe_ratio", 0) < self.thresholds.min_sharpe_ratio:
            reasons.append(f"Low Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")

        if metrics.get("win_rate", 0) < self.thresholds.min_win_rate:
            reasons.append(f"Low win rate: {metrics.get('win_rate', 0):.2%}")

        if metrics.get("max_drawdown", 1.0) > self.thresholds.max_drawdown:
            reasons.append(f"High drawdown: {metrics.get('max_drawdown', 1.0):.2%}")

        markets_tested = len(metrics.get("markets_tested", []))
        if markets_tested < self.thresholds.min_markets_tested:
            reasons.append(f"Insufficient market testing: {markets_tested} markets")

        total_trades = metrics.get("num_trades", 0)
        markets_tested_f = markets_tested
        trades_per_market = total_trades / markets_tested_f if markets_tested_f > 0 else 0

        if trades_per_market < self.thresholds.min_trades_per_market:
            reasons.append(f"Low trades per market: {trades_per_market:.1f}")

        if metrics.get("slippage_impact", 0) > self.thresholds.max_slippage_impact:
            reasons.append(f"High slippage: {metrics.get('slippage_impact', 0):.3f}")

        if metrics.get("execution_delay_ms", 0) > self.thresholds.max_execution_delay_ms:
            reasons.append(f"Slow execution: {metrics.get('execution_delay_ms', 0)}ms")

        return len(reasons) == 0, "; ".join(reasons)


# Global instance for easy access
GLOBAL_FITNESS_CONFIG = GlobalFitnessConfig()


def get_fitness_config(preset: str = "BALANCED_DEMO") -> GlobalFitnessConfig:
    """Get fitness configuration from preset string."""
    return GlobalFitnessConfig.from_preset(preset)


def quick_update_weights(updates: Dict[str, float]) -> GlobalFitnessConfig:
    """Quickly update specific weights."""
    current_weights = GLOBAL_FITNESS_CONFIG.weights.to_dict()
    current_weights.update(updates)

    new_weights = FitnessWeights(**current_weights)
    return GlobalFitnessConfig(weights=new_weights, thresholds=GLOBAL_FITNESS_CONFIG.thresholds)
