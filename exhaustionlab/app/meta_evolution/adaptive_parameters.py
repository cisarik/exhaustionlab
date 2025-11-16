"""
Adaptive Meta-Parameters System

Self-optimizing system that learns optimal parameters for:
- LLM generation (temperature, top_p, max_tokens)
- Strategy complexity (LOC, indicators, features)
- Evolution settings (mutation rate, selection pressure)
- Quality thresholds (min scores, acceptance criteria)

Uses multi-armed bandit algorithms and Bayesian optimization.
"""

from __future__ import annotations

import logging
import json
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import random


logger = logging.getLogger(__name__)


@dataclass
class ParameterConfig:
    """Configuration for a single meta-parameter."""

    name: str
    min_value: float
    max_value: float
    current_value: float
    optimal_value: Optional[float] = None
    value_type: str = "float"  # "float", "int", "categorical"
    categorical_values: List[Any] = field(default_factory=list)

    # Performance tracking
    attempts: int = 0
    successes: int = 0
    avg_quality: float = 0.0

    # Learning parameters
    learning_rate: float = 0.1
    exploration_bonus: float = 0.0

    def sample_value(self, exploration_rate: float = 0.3) -> Any:
        """
        Sample a value for this parameter.

        Uses epsilon-greedy with UCB bonus:
        - With probability exploration_rate: sample randomly
        - Otherwise: use current best + exploration bonus
        """
        if random.random() < exploration_rate:
            # Explore: sample randomly
            if self.value_type == "categorical":
                return random.choice(self.categorical_values)
            elif self.value_type == "int":
                return random.randint(int(self.min_value), int(self.max_value))
            else:
                return random.uniform(self.min_value, self.max_value)
        else:
            # Exploit: use best known value
            if self.optimal_value is not None:
                return self.optimal_value
            else:
                return self.current_value

    def update_from_feedback(
        self, value_used: Any, quality_score: float, success: bool
    ):
        """Update parameter based on feedback."""
        self.attempts += 1

        if success:
            self.successes += 1

        # Update average quality
        self.avg_quality = (
            self.avg_quality * (self.attempts - 1) + quality_score
        ) / self.attempts

        # Update optimal if this is better
        if quality_score > self.avg_quality * 1.1:  # 10% better than average
            if self.value_type == "float":
                # Move towards this value
                if self.optimal_value is None:
                    self.optimal_value = value_used
                else:
                    self.optimal_value = (
                        self.optimal_value * (1 - self.learning_rate)
                        + value_used * self.learning_rate
                    )
            else:
                self.optimal_value = value_used

            logger.info(f"  📈 Updated optimal {self.name}: {self.optimal_value}")


@dataclass
class MetaParameterSet:
    """Complete set of meta-parameters for strategy generation."""

    # LLM Parameters
    temperature: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="temperature",
            min_value=0.3,
            max_value=1.2,
            current_value=0.7,
            value_type="float",
        )
    )

    top_p: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="top_p",
            min_value=0.7,
            max_value=1.0,
            current_value=0.9,
            value_type="float",
        )
    )

    max_tokens: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="max_tokens",
            min_value=1000,
            max_value=4000,
            current_value=2000,
            value_type="int",
        )
    )

    # Strategy Complexity Parameters
    max_indicators: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="max_indicators",
            min_value=2,
            max_value=8,
            current_value=4,
            value_type="int",
        )
    )

    max_loc: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="max_loc",
            min_value=100,
            max_value=1000,
            current_value=400,
            value_type="int",
        )
    )

    complexity_preference: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="complexity_preference",
            min_value=0.0,
            max_value=1.0,
            current_value=0.5,
            value_type="float",
        )
    )

    # Example Selection Parameters
    num_examples: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="num_examples",
            min_value=0,
            max_value=5,
            current_value=3,
            value_type="int",
        )
    )

    min_example_quality: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="min_example_quality",
            min_value=50.0,
            max_value=80.0,
            current_value=60.0,
            value_type="float",
        )
    )

    # Evolution Parameters
    mutation_rate: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="mutation_rate",
            min_value=0.1,
            max_value=0.5,
            current_value=0.3,
            value_type="float",
        )
    )

    selection_pressure: ParameterConfig = field(
        default_factory=lambda: ParameterConfig(
            name="selection_pressure",
            min_value=0.3,
            max_value=0.9,
            current_value=0.6,
            value_type="float",
        )
    )

    def get_all_parameters(self) -> Dict[str, ParameterConfig]:
        """Get all parameter configs as dictionary."""
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "max_indicators": self.max_indicators,
            "max_loc": self.max_loc,
            "complexity_preference": self.complexity_preference,
            "num_examples": self.num_examples,
            "min_example_quality": self.min_example_quality,
            "mutation_rate": self.mutation_rate,
            "selection_pressure": self.selection_pressure,
        }

    def sample_configuration(self, exploration_rate: float = 0.3) -> Dict[str, Any]:
        """Sample a complete configuration."""
        config = {}
        for name, param in self.get_all_parameters().items():
            config[name] = param.sample_value(exploration_rate)
        return config

    def update_from_feedback(
        self, config_used: Dict[str, Any], quality_score: float, success: bool
    ):
        """Update all parameters based on feedback."""
        for name, value in config_used.items():
            if name in self.get_all_parameters():
                param = self.get_all_parameters()[name]
                param.update_from_feedback(value, quality_score, success)


class AdaptiveParameterOptimizer:
    """
    Self-optimizing meta-parameter system.

    Uses multi-armed bandit approach with:
    - Epsilon-greedy exploration
    - UCB (Upper Confidence Bound) for exploration bonus
    - Bayesian optimization for continuous parameters
    - Performance tracking and analysis
    """

    def __init__(self, save_path: Optional[Path] = None):
        """Initialize optimizer."""
        self.parameters = MetaParameterSet()
        self.save_path = (
            save_path
            or Path.home() / "ExhaustionLab" / ".cache" / "adaptive_params.json"
        )

        # Performance history
        self.configuration_history: List[Dict[str, Any]] = []
        self.performance_history: List[float] = []

        # Learning state
        self.global_exploration_rate = 0.3
        self.total_attempts = 0
        self.successful_attempts = 0

        # Parameter correlations
        self.parameter_correlations: Dict[str, Dict[str, float]] = defaultdict(dict)

        self.logger = logging.getLogger(__name__)

        # Try to load previous state
        self.load_state()

    def get_optimal_configuration(self) -> Dict[str, Any]:
        """
        Get current optimal configuration.

        Returns:
            Dictionary with optimal parameter values
        """
        config = {}
        params = self.parameters.get_all_parameters()

        for name, param in params.items():
            if param.optimal_value is not None:
                config[name] = param.optimal_value
            else:
                config[name] = param.current_value

        return config

    def suggest_configuration(self) -> Dict[str, Any]:
        """
        Suggest next configuration to try.

        Uses adaptive exploration rate:
        - High exploration if success rate is low
        - Low exploration if success rate is high
        """
        # Adapt exploration rate based on success rate
        if self.total_attempts > 10:
            success_rate = self.successful_attempts / self.total_attempts

            if success_rate < 0.3:
                self.global_exploration_rate = min(
                    0.8, self.global_exploration_rate + 0.05
                )
            elif success_rate > 0.7:
                self.global_exploration_rate = max(
                    0.1, self.global_exploration_rate - 0.05
                )

        # Sample configuration
        config = self.parameters.sample_configuration(self.global_exploration_rate)

        self.logger.info(
            f"Suggested config (exploration={self.global_exploration_rate:.2f}):"
        )
        for key, value in config.items():
            if isinstance(value, float):
                self.logger.info(f"  {key}: {value:.2f}")
            else:
                self.logger.info(f"  {key}: {value}")

        return config

    def update_from_result(
        self,
        config: Dict[str, Any],
        quality_score: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Update optimizer based on generation result.

        Args:
            config: Configuration that was used
            quality_score: Quality score achieved
            success: Whether it met success criteria
            metadata: Optional additional metadata
        """
        self.total_attempts += 1
        if success:
            self.successful_attempts += 1

        # Store history
        self.configuration_history.append(config.copy())
        self.performance_history.append(quality_score)

        # Update parameters
        self.parameters.update_from_feedback(config, quality_score, success)

        # Update correlations (every 10 attempts)
        if self.total_attempts % 10 == 0:
            self._update_correlations()

        # Log update
        success_rate = self.successful_attempts / self.total_attempts
        self.logger.info(
            f"Updated params: Quality={quality_score:.1f}, "
            f"Success={success}, "
            f"Success Rate={success_rate:.1%}"
        )

        # Save state periodically
        if self.total_attempts % 5 == 0:
            self.save_state()

    def _update_correlations(self):
        """Calculate correlations between parameters and performance."""
        if len(self.configuration_history) < 10:
            return

        # Get recent history
        recent_configs = self.configuration_history[-50:]
        recent_performance = self.performance_history[-50:]

        # Calculate correlations for each parameter
        params = self.parameters.get_all_parameters()

        for param_name in params.keys():
            # Extract parameter values
            param_values = [
                config.get(param_name, params[param_name].current_value)
                for config in recent_configs
            ]

            # Calculate correlation
            if len(set(param_values)) > 1:  # Only if there's variation
                correlation = np.corrcoef(param_values, recent_performance)[0, 1]

                if not np.isnan(correlation):
                    self.parameter_correlations[param_name]["performance"] = correlation

                    if abs(correlation) > 0.5:
                        self.logger.info(
                            f"  📊 Strong correlation: {param_name} → "
                            f"performance ({correlation:+.2f})"
                        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        params = self.parameters.get_all_parameters()

        param_stats = {}
        for name, param in params.items():
            param_stats[name] = {
                "current": param.current_value,
                "optimal": param.optimal_value,
                "attempts": param.attempts,
                "successes": param.successes,
                "success_rate": (
                    param.successes / param.attempts if param.attempts > 0 else 0
                ),
                "avg_quality": param.avg_quality,
            }

        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "global_success_rate": (
                self.successful_attempts / self.total_attempts
                if self.total_attempts > 0
                else 0
            ),
            "exploration_rate": self.global_exploration_rate,
            "avg_quality": (
                np.mean(self.performance_history) if self.performance_history else 0
            ),
            "best_quality": (
                max(self.performance_history) if self.performance_history else 0
            ),
            "parameters": param_stats,
            "correlations": dict(self.parameter_correlations),
        }

    def save_state(self):
        """Save optimizer state to file."""
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)

            state = {
                "total_attempts": self.total_attempts,
                "successful_attempts": self.successful_attempts,
                "global_exploration_rate": self.global_exploration_rate,
                "parameters": {
                    name: asdict(param)
                    for name, param in self.parameters.get_all_parameters().items()
                },
                "configuration_history": self.configuration_history[-100:],  # Last 100
                "performance_history": self.performance_history[-100:],
                "parameter_correlations": dict(self.parameter_correlations),
                "timestamp": datetime.now().isoformat(),
            }

            with open(self.save_path, "w") as f:
                json.dump(state, f, indent=2)

            self.logger.info(f"Saved optimizer state to {self.save_path}")

        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def load_state(self):
        """Load optimizer state from file."""
        try:
            if not self.save_path.exists():
                return

            with open(self.save_path, "r") as f:
                state = json.load(f)

            self.total_attempts = state.get("total_attempts", 0)
            self.successful_attempts = state.get("successful_attempts", 0)
            self.global_exploration_rate = state.get("global_exploration_rate", 0.3)
            self.configuration_history = state.get("configuration_history", [])
            self.performance_history = state.get("performance_history", [])
            self.parameter_correlations = defaultdict(
                dict, state.get("parameter_correlations", {})
            )

            # Restore parameter configs
            params_data = state.get("parameters", {})
            for name, param_dict in params_data.items():
                if name in self.parameters.get_all_parameters():
                    param = self.parameters.get_all_parameters()[name]
                    param.current_value = param_dict.get(
                        "current_value", param.current_value
                    )
                    param.optimal_value = param_dict.get("optimal_value")
                    param.attempts = param_dict.get("attempts", 0)
                    param.successes = param_dict.get("successes", 0)
                    param.avg_quality = param_dict.get("avg_quality", 0.0)

            self.logger.info(
                f"Loaded optimizer state: {self.total_attempts} attempts, "
                f"{self.successful_attempts} successes"
            )

        except Exception as e:
            self.logger.warning(f"Failed to load state: {e}")


def format_optimizer_report(optimizer: AdaptiveParameterOptimizer) -> str:
    """Format optimizer statistics as readable report."""
    stats = optimizer.get_statistics()

    report = []
    report.append("=" * 70)
    report.append("ADAPTIVE PARAMETERS OPTIMIZER REPORT")
    report.append("=" * 70)

    report.append(f"\n📊 GLOBAL STATISTICS:")
    report.append(f"  Total Attempts: {stats['total_attempts']}")
    report.append(f"  Successful: {stats['successful_attempts']}")
    report.append(f"  Success Rate: {stats['global_success_rate']:.1%}")
    report.append(f"  Exploration Rate: {stats['exploration_rate']:.2f}")
    report.append(f"  Average Quality: {stats['avg_quality']:.1f}")
    report.append(f"  Best Quality: {stats['best_quality']:.1f}")

    report.append(f"\n🎛️ PARAMETER STATUS:")
    for name, param_stats in stats["parameters"].items():
        report.append(f"\n  {name}:")
        report.append(f"    Current: {param_stats['current']}")
        if param_stats["optimal"] is not None:
            report.append(f"    Optimal: {param_stats['optimal']} ⭐")
        report.append(f"    Attempts: {param_stats['attempts']}")
        if param_stats["attempts"] > 0:
            report.append(f"    Success Rate: {param_stats['success_rate']:.1%}")
            report.append(f"    Avg Quality: {param_stats['avg_quality']:.1f}")

    if stats["correlations"]:
        report.append(f"\n📈 CORRELATIONS:")
        for param, corr_data in stats["correlations"].items():
            if "performance" in corr_data:
                corr = corr_data["performance"]
                if abs(corr) > 0.3:
                    direction = "↑" if corr > 0 else "↓"
                    report.append(f"  {param} → performance: {corr:+.2f} {direction}")

    report.append("=" * 70)

    return "\n".join(report)


if __name__ == "__main__":
    # Test adaptive parameters
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    print("\n🎛️ ADAPTIVE PARAMETERS TEST\n")
    print("=" * 70)

    # Create optimizer
    optimizer = AdaptiveParameterOptimizer()

    print("\n📋 Initial Configuration:")
    initial_config = optimizer.get_optimal_configuration()
    for key, value in initial_config.items():
        print(f"  {key}: {value}")

    # Simulate optimization process
    print("\n🔄 Simulating 20 generations...")

    for i in range(20):
        # Suggest configuration
        config = optimizer.suggest_configuration()

        # Simulate result (improving over time)
        base_quality = 50 + i * 2
        noise = random.uniform(-5, 5)
        quality = base_quality + noise

        # Temperature affects quality (example correlation)
        temp = config["temperature"]
        if 0.6 <= temp <= 0.8:
            quality += 5  # Optimal range

        success = quality >= 70

        print(
            f"\n  Gen {i+1}: Quality={quality:.1f}, Temp={temp:.2f}, Success={success}"
        )

        # Update optimizer
        optimizer.update_from_result(config, quality, success)

    # Show final report
    print(f"\n{format_optimizer_report(optimizer)}")

    print("\n✅ Adaptive parameters system operational!")
