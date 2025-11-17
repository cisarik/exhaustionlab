"""
Strategy Configuration System

ParamSpec-driven configuration with validation for:
- Strategy parameters
- Evolution settings
- Risk management
- Performance targets

Integrates with adaptive parameters and meta-evolution.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

try:
    from .indicator_params import ParamSpec
except ImportError:
    from indicator_params import ParamSpec


logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


@dataclass(frozen=True)
class StrategyParamSpec(ParamSpec):
    """Extended ParamSpec for strategy parameters."""

    category: str = "general"  # "indicator", "risk", "entry", "exit", "general"
    required: bool = True
    adaptive: bool = False  # Can be optimized by adaptive parameters

    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate parameter value.

        Returns:
            (is_valid, error_message)
        """
        # Type validation
        if self.kind == "int" and not isinstance(value, int):
            return False, f"{self.name} must be integer, got {type(value)}"

        if self.kind == "float" and not isinstance(value, (int, float)):
            return False, f"{self.name} must be numeric, got {type(value)}"

        if self.kind == "bool" and not isinstance(value, bool):
            return False, f"{self.name} must be boolean, got {type(value)}"

        # Range validation
        if self.kind in ("int", "float"):
            if value < self.min_value:
                return False, f"{self.name}={value} below minimum {self.min_value}"
            if value > self.max_value:
                return False, f"{self.name}={value} above maximum {self.max_value}"

        return True, None


@dataclass
class StrategyConfig:
    """
    Complete strategy configuration.

    Combines:
    - Strategy-specific parameters
    - Evolution settings
    - Risk management
    - Performance targets
    """

    # Identity
    strategy_name: str
    strategy_type: str  # "momentum", "trend_following", "mean_reversion"

    # Strategy Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    param_specs: Dict[str, StrategyParamSpec] = field(default_factory=dict)

    # Evolution Settings
    population_size: int = 20
    max_generations: int = 50
    mutation_rate: float = 0.3
    crossover_rate: float = 0.7
    elite_ratio: float = 0.1

    # Risk Management
    max_position_size: float = 0.10  # 10% of capital
    max_daily_loss: float = 0.02  # 2%
    max_drawdown: float = 0.20  # 20%
    stop_loss_pct: float = 0.02  # 2%
    take_profit_pct: float = 0.04  # 4%

    # Performance Targets
    min_sharpe_ratio: float = 1.5
    min_win_rate: float = 0.50
    min_profit_factor: float = 1.5

    # Meta
    created_at: str = field(default_factory=lambda: str(pd.Timestamp.now()))
    updated_at: str = field(default_factory=lambda: str(pd.Timestamp.now()))

    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate complete configuration.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Validate all parameters against specs
        for param_name, value in self.parameters.items():
            if param_name in self.param_specs:
                spec = self.param_specs[param_name]
                is_valid, error = spec.validate(value)
                if not is_valid:
                    errors.append(error)

        # Check required parameters
        for spec_name, spec in self.param_specs.items():
            if spec.required and spec_name not in self.parameters:
                errors.append(f"Required parameter missing: {spec_name}")

        # Validate evolution settings
        if self.population_size < 2:
            errors.append("Population size must be >= 2")

        if not 0 <= self.mutation_rate <= 1:
            errors.append("Mutation rate must be between 0 and 1")

        if not 0 <= self.crossover_rate <= 1:
            errors.append("Crossover rate must be between 0 and 1")

        # Validate risk parameters
        if not 0 < self.max_position_size <= 1:
            errors.append("Max position size must be between 0 and 1")

        if not 0 < self.max_daily_loss <= 0.1:
            errors.append("Max daily loss should be between 0 and 10%")

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "strategy_name": self.strategy_name,
            "strategy_type": self.strategy_type,
            "parameters": self.parameters,
            "param_specs": {k: asdict(v) for k, v in self.param_specs.items()},
            "evolution": {
                "population_size": self.population_size,
                "max_generations": self.max_generations,
                "mutation_rate": self.mutation_rate,
                "crossover_rate": self.crossover_rate,
                "elite_ratio": self.elite_ratio,
            },
            "risk": {
                "max_position_size": self.max_position_size,
                "max_daily_loss": self.max_daily_loss,
                "max_drawdown": self.max_drawdown,
                "stop_loss_pct": self.stop_loss_pct,
                "take_profit_pct": self.take_profit_pct,
            },
            "targets": {
                "min_sharpe_ratio": self.min_sharpe_ratio,
                "min_win_rate": self.min_win_rate,
                "min_profit_factor": self.min_profit_factor,
            },
            "meta": {"created_at": self.created_at, "updated_at": self.updated_at},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StrategyConfig:
        """Create from dictionary."""
        # Reconstruct param specs
        param_specs = {}
        if "param_specs" in data:
            for name, spec_dict in data["param_specs"].items():
                param_specs[name] = StrategyParamSpec(**spec_dict)

        # Extract sections
        evolution = data.get("evolution", {})
        risk = data.get("risk", {})
        targets = data.get("targets", {})
        meta = data.get("meta", {})

        return cls(
            strategy_name=data["strategy_name"],
            strategy_type=data["strategy_type"],
            parameters=data.get("parameters", {}),
            param_specs=param_specs,
            population_size=evolution.get("population_size", 20),
            max_generations=evolution.get("max_generations", 50),
            mutation_rate=evolution.get("mutation_rate", 0.3),
            crossover_rate=evolution.get("crossover_rate", 0.7),
            elite_ratio=evolution.get("elite_ratio", 0.1),
            max_position_size=risk.get("max_position_size", 0.10),
            max_daily_loss=risk.get("max_daily_loss", 0.02),
            max_drawdown=risk.get("max_drawdown", 0.20),
            stop_loss_pct=risk.get("stop_loss_pct", 0.02),
            take_profit_pct=risk.get("take_profit_pct", 0.04),
            min_sharpe_ratio=targets.get("min_sharpe_ratio", 1.5),
            min_win_rate=targets.get("min_win_rate", 0.50),
            min_profit_factor=targets.get("min_profit_factor", 1.5),
            created_at=meta.get("created_at", str(pd.Timestamp.now())),
            updated_at=meta.get("updated_at", str(pd.Timestamp.now())),
        )


class ConfigurationManager:
    """
    Central configuration management system.

    Features:
    - Load/save configurations
    - Validation
    - Templates for common strategies
    - Integration with adaptive parameters
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize manager."""
        self.config_dir = config_dir or Path.home() / "ExhaustionLab" / ".cache" / "configs"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.configurations: Dict[str, StrategyConfig] = {}
        self.logger = logging.getLogger(__name__)

    def create_default_config(self, strategy_type: str) -> StrategyConfig:
        """Create default configuration for strategy type."""

        # Define common parameter specs
        common_specs = {
            "lookback_period": StrategyParamSpec(
                name="lookback_period",
                label="Lookback Period",
                default=20,
                min_value=5,
                max_value=200,
                step=1,
                kind="int",
                description="Number of bars for indicator calculation",
                category="indicator",
                adaptive=True,
            ),
            "signal_threshold": StrategyParamSpec(
                name="signal_threshold",
                label="Signal Threshold",
                default=0.7,
                min_value=0.0,
                max_value=1.0,
                step=0.1,
                kind="float",
                description="Minimum confidence for signal",
                category="entry",
                adaptive=True,
            ),
        }

        # Type-specific specs
        if strategy_type == "momentum":
            common_specs["rsi_period"] = StrategyParamSpec(
                name="rsi_period",
                label="RSI Period",
                default=14,
                min_value=2,
                max_value=50,
                step=1,
                kind="int",
                category="indicator",
                adaptive=True,
            )
            common_specs["rsi_overbought"] = StrategyParamSpec(
                name="rsi_overbought",
                label="RSI Overbought",
                default=70.0,
                min_value=60.0,
                max_value=90.0,
                step=1.0,
                kind="float",
                category="indicator",
                adaptive=True,
            )

        elif strategy_type == "trend_following":
            common_specs["fast_ma"] = StrategyParamSpec(
                name="fast_ma",
                label="Fast MA Period",
                default=10,
                min_value=5,
                max_value=50,
                step=1,
                kind="int",
                category="indicator",
                adaptive=True,
            )
            common_specs["slow_ma"] = StrategyParamSpec(
                name="slow_ma",
                label="Slow MA Period",
                default=30,
                min_value=10,
                max_value=200,
                step=1,
                kind="int",
                category="indicator",
                adaptive=True,
            )

        # Create config
        config = StrategyConfig(
            strategy_name=f"{strategy_type}_default",
            strategy_type=strategy_type,
            param_specs=common_specs,
            parameters={name: spec.default for name, spec in common_specs.items()},
        )

        return config

    def save_config(self, config: StrategyConfig, name: Optional[str] = None):
        """Save configuration to file."""
        name = name or config.strategy_name
        filepath = self.config_dir / f"{name}.json"

        # Validate first
        is_valid, errors = config.validate()
        if not is_valid:
            raise ConfigValidationError(f"Invalid configuration: {errors}")

        # Update timestamp
        import pandas as pd

        config.updated_at = str(pd.Timestamp.now())

        # Save
        with open(filepath, "w") as f:
            json.dump(config.to_dict(), f, indent=2)

        self.configurations[name] = config
        self.logger.info(f"Saved configuration: {name}")

    def load_config(self, name: str) -> Optional[StrategyConfig]:
        """Load configuration from file."""
        filepath = self.config_dir / f"{name}.json"

        if not filepath.exists():
            self.logger.warning(f"Configuration not found: {name}")
            return None

        with open(filepath, "r") as f:
            data = json.load(f)

        config = StrategyConfig.from_dict(data)

        # Validate
        is_valid, errors = config.validate()
        if not is_valid:
            self.logger.warning(f"Loaded config has errors: {errors}")

        self.configurations[name] = config
        self.logger.info(f"Loaded configuration: {name}")

        return config

    def list_configs(self) -> List[str]:
        """List available configurations."""
        return [f.stem for f in self.config_dir.glob("*.json")]

    def validate_config(self, config: StrategyConfig) -> Tuple[bool, List[str]]:
        """Validate configuration."""
        return config.validate()


# Convenience functions


def create_momentum_config() -> StrategyConfig:
    """Create default momentum strategy config."""
    manager = ConfigurationManager()
    return manager.create_default_config("momentum")


def create_trend_following_config() -> StrategyConfig:
    """Create default trend following config."""
    manager = ConfigurationManager()
    return manager.create_default_config("trend_following")


if __name__ == "__main__":
    # Test configuration system
    logging.basicConfig(level=logging.INFO)

    print("\n⚙️ STRATEGY CONFIGURATION SYSTEM TEST\n")
    print("=" * 70)

    # Create manager
    manager = ConfigurationManager()

    # Create momentum config
    print("\n📋 Creating momentum strategy config...")
    momentum_config = manager.create_default_config("momentum")

    print(f"  Strategy: {momentum_config.strategy_name}")
    print(f"  Type: {momentum_config.strategy_type}")
    print(f"  Parameters: {len(momentum_config.parameters)}")

    # Validate
    is_valid, errors = momentum_config.validate()
    print(f"\n✅ Validation: {'PASS' if is_valid else 'FAIL'}")
    if errors:
        for error in errors:
            print(f"  ❌ {error}")

    # Save
    print("\n💾 Saving configuration...")
    manager.save_config(momentum_config, "test_momentum")

    # Load
    print("\n📂 Loading configuration...")
    loaded = manager.load_config("test_momentum")
    print(f"  Loaded: {loaded.strategy_name}")

    # Show config
    print("\n📊 Configuration Details:")
    config_dict = loaded.to_dict()
    print("  Evolution:")
    for key, value in config_dict["evolution"].items():
        print(f"    {key}: {value}")

    print("  Risk Management:")
    for key, value in config_dict["risk"].items():
        print(f"    {key}: {value}")

    print("  Performance Targets:")
    for key, value in config_dict["targets"].items():
        print(f"    {key}: {value}")

    # List all
    print("\n📚 Available Configurations:")
    for config_name in manager.list_configs():
        print(f"  - {config_name}")

    print("\n✅ Configuration system operational!")
