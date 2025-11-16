"""
Meta-Evolution Configuration Framework

Intelligent configuration management for LLM-driven strategy evolution.
Provides examples, meta-parameters, and adaptive optimization.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from ..llm import PromptContext


class MetaStrategyType(Enum):
    """High-level strategy categories for meta-evolution."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    TREND_FOLLOWING = "trend_following"
    BREAKOUT = "breakout"
    EXHAUSTION = "exhaustion"
    VOLATILITY = "volatility"
    ARBITRAGE = "arbitrage"
    SENTIMENT = "sentiment"
    STATISTICAL = "statistical"
    HYBRID = "hybrid"


class MarketFocus(Enum):
    """Market specialization categories."""

    SPOT_CRYPTO = "spot_crypto"
    FUTURES_CRYPTO = "futures_crypto"
    OPTIONS_CRYPTO = "options_crypto"
    FX_MARKETS = "fx_markets"
    COMMODITIES = "commodities"
    EQUITIES = "equities"
    MULTI_ASSET = "multi_asset"


class EvolutionIntensity(Enum):
    """Evolution aggressiveness levels."""

    EXPLORATORY = "exploratory"  # High creativity, diverse mutations
    BALANCED = "balanced"  # Mix of exploration and exploitation
    EXPLOITATIVE = "exploitative"  # Focus on proven patterns
    AGGRESSIVE = "aggressive"  # Fast, high-risk mutations


@dataclass
class MetaParameters:
    """Meta-parameters that govern evolution process itself."""

    # Evolution settings
    strategy_type: MetaStrategyType
    market_focus: MarketFocus
    evolution_intensity: EvolutionIntensity

    # LLM interaction settings
    prompt_style: str = "quantitative"  # "creative", "conservative", "quantitative"
    context_examples: int = 3  # Number of example strategies to include
    domain_knowledge_depth: str = "advanced"  # "basic", "intermediate", "advanced"

    # Search space definition
    indicator_universe: List[str] = None
    timeframes: List[str] = None
    risk_levels: List[str] = None

    # Performance constraints
    max_drawdown_target: float = 0.15
    min_win_rate_target: float = 0.45
    expected_sharpe_target: float = 0.8
    max_positions_per_day: int = 100

    # Learning parameters
    learning_rate: float = 0.1
    adaptation_rate: float = 0.05
    diversity_threshold: float = 0.3

    def __post_init__(self):
        if self.indicator_universe is None:
            self.indicator_universe = [
                "RSI",
                "MACD",
                "BB",
                "ATR",
                "SMA",
                "EMA",
                "Stoch",
                "CCI",
                "ADX",
            ]
        if self.timeframes is None:
            self.timeframes = (
                ["1m", "5m", "15m", "1h"]
                if self.market_focus == MarketFocus.SPOT_CRYPTO
                else ["5m", "15m", "1h", "4h"]
            )
        if self.risk_levels is None:
            self.risk_levels = (
                ["conservative", "balanced"]
                if self.evolution_intensity == EvolutionIntensity.EXPLORATORY
                else ["balanced", "aggressive"]
            )

    def to_prompt_context(self) -> PromptContext:
        """Convert meta-parameters to LLM prompt context."""
        return PromptContext(
            strategy_type=self.strategy_type.value,
            market_focus=[self.market_focus.value],
            timeframe=self.timeframes[0] if self.timeframes else "1m",
            indicators_to_include=self.indicator_universe[:5],  # First 5 for prompt
            signal_logic=self.strategy_type.value,
            risk_profile=self.risk_levels[0] if self.risk_levels else "balanced",
        )


@dataclass
class StrategyExample:
    """Example trading strategy for context learning."""

    name: str
    description: str
    source: str  # "quantresearch", "github", "reddit", "medium", "papers"
    code: str
    performance_metrics: Optional[Dict[str, float]] = None
    market_conditions: Optional[str] = None
    risk_profile: Optional[str] = None
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MetaEvolutionConfig:
    """Central configuration management for meta-evolution system."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".exhaustionlab" / "meta_config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load base configurations
        self.strategy_templates = self._load_strategy_templates()
        self.example_database = self._load_example_database()

        # Initialize meta-parameters
        self.current_meta_params = self._initialize_meta_parameters()

        self.logger = logging.getLogger(__name__)

    def _load_strategy_templates(self) -> Dict[MetaStrategyType, Dict]:
        """Load strategy templates with specific characteristics."""
        return {
            MetaStrategyType.MOMENTUM: {
                "description": "Momentum-based strategies using price and volume acceleration",
                "key_indicators": [
                    "RSI",
                    "MACD",
                    "Rate of Change",
                    "Momentum Oscillator",
                ],
                "signal_patterns": [
                    "breakout_momentum",
                    "divergence_momentum",
                    "volume_confirm",
                ],
                "timeframe_preference": ["5m", "15m", "1h"],
                "risk_management": "dynamic_position_sizing",
                "market_conditions": "trending_markets",
                "examples": [
                    "RSI momentum with volume confirmation",
                    "MACD divergence strategy",
                    "Price momentum with ATR filter",
                ],
            },
            MetaStrategyType.MEAN_REVERSION: {
                "description": "Mean-reversion strategies using statistical boundaries",
                "key_indicators": [
                    "Bollinger Bands",
                    "RSI",
                    "Stochastic",
                    "CCI",
                    "Standard Deviation",
                ],
                "signal_patterns": [
                    "bollinger_band_revert",
                    "rsi_oversold",
                    "statistical_reversion",
                    "volatility_revert",
                ],
                "timeframe_preference": ["1m", "5m", "15m"],
                "risk_management": "tight_stops_reversion",
                "market_conditions": "sideways_markets, volatile_reversions",
                "examples": [
                    "Bollinger Band bounce with mean reversion",
                    "RSI oversold/overbought mean reversion",
                    "Statistical price reversal strategy",
                ],
            },
            MetaStrategyType.EXHAUSTION: {
                "description": "Pattern recognition for trend exhaustion and reversal",
                "key_indicators": [
                    "Custom exhaustion indicators",
                    "RSI",
                    "Volume",
                    "ATR",
                ],
                "signal_patterns": [
                    "multi_level_exhaustion",
                    "volume_exhaustion",
                    "price_pattern_exhaustion",
                ],
                "timeframe_preference": ["1m", "5m", "15m"],
                "risk_management": "level_position_sizing",
                "market_conditions": "trend_end_scenarios",
                "examples": [
                    "Multi-level exhaustion signal",
                    "Volume-based exhaustion identification",
                    "Price pattern exhaustion with RSI",
                ],
            },
            MetaStrategyType.TREND_FOLLOWING: {
                "description": "Trend identification and following with momentum",
                "key_indicators": ["SMA", "EMA", "ADX", "MACD", "Volume"],
                "signal_patterns": [
                    "moving_average_crossover",
                    "trend_follow_pullback",
                    "volume_confirmed_trend",
                ],
                "timeframe_preference": ["15m", "1h", "4h"],
                "risk_management": "trailing_stops_trend",
                "market_conditions": "established_trends",
                "examples": [
                    "Dual moving average crossover trend following",
                    "ADX-based trend strength following",
                    "Volume confirmed trend continuation",
                ],
            },
            MetaStrategyType.BREAKOUT: {
                "description": "Breakout identification from consolidation patterns",
                "key_indicators": [
                    "Bollinger Bands",
                    "ATR",
                    "Volume",
                    "Consolidation Patterns",
                ],
                "signal_patterns": [
                    "volatility_breakout",
                    "volume_spike_breakout",
                    "support_resistance_breakout",
                ],
                "timeframe_preference": ["5m", "15m", "1h"],
                "risk_management": "breakout_trailing_stops",
                "market_conditions": "pre_breakout_consolidation",
                "examples": [
                    "Volume confirmed volatility breakout",
                    "Support/resistance line breakout",
                    "Consolidation range expansion strategy",
                ],
            },
        }

    def _load_example_database(self) -> List[StrategyExample]:
        """Load example strategies from various sources."""
        examples = []

        # Built-in high-quality examples
        built_ins = [
            StrategyExample(
                name="Quantitative RSI Mean Reversion",
                description="Statistical mean reversion using RSI with volume filter",
                source="quantresearch",
                code=self._get_builtin_example("rsi_mean_reversion"),
                performance_metrics={
                    "sharpe_ratio": 1.2,
                    "max_drawdown": 0.08,
                    "win_rate": 0.52,
                    "total_return": 0.45,
                },
                market_conditions="sideways_crypto_markets",
                risk_profile="conservative",
                tags=["mean_reversion", "rsi", "volume", "conservative"],
            ),
            StrategyExample(
                name="MACD Momentum with Divergence",
                description="MACD momentum strategy with divergence detection",
                source="github",
                code=self._get_builtin_example("macd_momentum"),
                performance_metrics={
                    "sharpe_ratio": 0.9,
                    "max_drawdown": 0.12,
                    "win_rate": 0.48,
                    "total_return": 0.38,
                },
                market_conditions="trending_markets",
                risk_profile="balanced",
                tags=["momentum", "macd", "divergence", "trend"],
            ),
            StrategyExample(
                name="Volatility Breakout Strategy",
                description="ATR-based volatility breakout with volume confirmation",
                source="quantresearch",
                code=self._get_builtin_example("volatility_breakout"),
                performance_metrics={
                    "sharpe_ratio": 1.5,
                    "max_drawdown": 0.10,
                    "win_rate": 0.58,
                    "total_return": 0.62,
                },
                market_conditions="high_volatility",
                risk_profile="aggressive",
                tags=["breakout", "volatility", "atr", "volume"],
            ),
        ]

        examples.extend(built_ins)

        # Try to load external examples if directory exists
        example_dir = self.config_dir / "external_examples"
        if example_dir.exists():
            for file_path in example_dir.glob("*.py"):
                try:
                    with open(file_path) as f:
                        code = f.read()
                    # Parse metadata from file header (in real implementation)
                    examples.append(
                        StrategyExample(
                            name=file_path.stem,
                            description=f"External example from {file_path}",
                            source="external",
                            code=code,
                            tags=["external"],
                        )
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to load example {file_path}: {e}")

        return examples

    def _initialize_meta_parameters(self) -> MetaParameters:
        """Initialize default meta-parameters."""
        return MetaParameters(
            strategy_type=MetaStrategyType.HYBRID,
            market_focus=MarketFocus.SPOT_CRYPTO,
            evolution_intensity=EvolutionIntensity.BALANCED,
            prompt_style="quantitative",
            context_examples=3,
            domain_knowledge_depth="advanced",
        )

    def create_evolution_config(
        self,
        strategy_type: MetaStrategyType,
        market_focus: MarketFocus,
        intensity: EvolutionIntensity,
        custom_constraints: Optional[Dict] = None,
    ) -> MetaParameters:
        """Create tailored configuration for specific evolution run."""

        config = MetaParameters(
            strategy_type=strategy_type,
            market_focus=market_focus,
            evolution_intensity=intensity,
        )

        # Customize based on strategy type
        strategy_info = self.strategy_templates[strategy_type]
        config.indicator_universe = strategy_info["key_indicators"]
        config.timeframes = strategy_info["timeframe_preference"]

        # Customize based on intensity
        if intensity == EvolutionIntensity.EXPLORATORY:
            config.learning_rate = 0.15
            config.diversity_threshold = 0.4
            config.context_examples = 4
        elif intensity == EvolutionIntensity.AGGRESSIVE:
            config.learning_rate = 0.2
            config.max_drawdown_target = 0.25  # Higher risk tolerance
            config.max_positions_per_day = 150
        elif intensity == EvolutionIntensity.EXPLOITATIVE:
            config.learning_rate = 0.05
            config.diversity_threshold = 0.2
            config.context_examples = 2

        # Apply custom constraints
        if custom_constraints:
            for key, value in custom_constraints.items():
                if hasattr(config, key):
                    setattr(config, key, value)

        return config

    def get_context_examples(
        self, meta_params: MetaParameters, limit: int = 5
    ) -> List[StrategyExample]:
        """Get curated examples for LLM context based on meta-parameters."""

        # Filter examples based on strategy type and market
        strategy_type_filter = meta_params.strategy_type.value.lower()
        market_focus_filter = meta_params.market_focus.value.lower()

        filtered_examples = []
        for example in self.example_database:
            # Check for relevance
            tags_match = any(
                strategy_type_filter in tag.lower()
                or market_focus_filter in tag.lower()
                for tag in example.tags
            )

            desc_match = (
                strategy_type_filter in example.description.lower()
                or strategy_type_filter in example.name.lower()
            )

            if tags_match or desc_match:
                filtered_examples.append(example)

        # Sort by performance if available
        filtered_examples.sort(
            key=lambda x: (
                x.performance_metrics.get("sharpe_ratio", 0)
                if x.performance_metrics
                else 0
            ),
            reverse=True,
        )

        return filtered_examples[:limit]

    def create_llm_context(self, meta_params: MetaParameters) -> Dict[str, Any]:
        """Create comprehensive LLM context for strategy generation."""

        examples = self.get_context_examples(meta_params, meta_params.context_examples)
        strategy_info = self.strategy_templates.get(meta_params.strategy_type, {})

        context = {
            "strategy_specification": {
                "type": meta_params.strategy_type.value,
                "focus": meta_params.market_focus.value,
                "intensity": meta_params.evolution_intensity.value,
                "description": strategy_info.get("description", ""),
                "key_indicators": meta_params.indicator_universe,
                "signal_patterns": strategy_info.get("signal_patterns", []),
                "timeframe_preference": meta_params.timeframes,
                "risk_profile": (
                    meta_params.risk_levels[0]
                    if meta_params.risk_levels
                    else "balanced"
                ),
            },
            "performance_constraints": {
                "max_drawdown_target": meta_params.max_drawdown_target,
                "min_win_rate_target": meta_params.min_win_rate_target,
                "expected_sharpe_target": meta_params.expected_sharpe_target,
                "max_positions_per_day": meta_params.max_positions_per_day,
            },
            "learning_parameters": {
                "learning_rate": meta_params.learning_rate,
                "adaptation_rate": meta_params.adaptation_rate,
                "diversity_threshold": meta_params.diversity_threshold,
                "domain_knowledge_depth": meta_params.domain_knowledge_depth,
            },
            "examples": [
                {
                    "name": example.name,
                    "description": example.description,
                    "code": example.code,
                    "performance": example.performance_metrics,
                    "tags": example.tags,
                }
                for example in examples
            ],
            "evolution_directives": {
                "style": meta_params.prompt_style,
                "creativity_level": self._map_intensity_to_creativity(
                    meta_params.evolution_intensity
                ),
                "domain_focus": "quantitative_trading",
                "validation_requirements": [
                    "syntactically_valid",
                    "backtest_ready",
                    "live_trading_ready",
                ],
            },
        }

        return context

    def _map_intensity_to_creativity(self, intensity: EvolutionIntensity) -> str:
        """Map evolution intensity to LLM creativity level."""
        mapping = {
            EvolutionIntensity.EXPLORATORY: "creative",
            EvolutionIntensity.BALANCED: "balanced",
            EvolutionIntensity.EXPLOITATIVE: "conservative",
            EvolutionIntensity.AGGRESSIVE: "high_risk_creative",
        }
        return mapping[intensity]

    def update_meta_parameters(self, performance_feedback: Dict[str, float]):
        """Update meta-parameters based on performance feedback (adaptive learning)."""

        current_sharpe = performance_feedback.get("sharpe_ratio", 0)
        current_drawdown = performance_feedback.get("max_drawdown", 1.0)
        current_win_rate = performance_feedback.get("win_rate", 0.0)

        # Adaptive learning: adjust parameters based on performance
        if current_sharpe < self.current_meta_params.expected_sharpe_target:
            # Underperforming: increase learning rate and exploration
            self.current_meta_params.learning_rate = min(
                0.25, self.current_meta_params.learning_rate * 1.2
            )
            self.current_meta_params.diversity_threshold = min(
                0.5, self.current_meta_params.diversity_threshold * 1.1
            )
        elif current_sharpe > self.current_meta_params.expected_sharpe_target * 1.5:
            # Overperforming: focus on exploitation
            self.current_meta_params.learning_rate = max(
                0.05, self.current_meta_params.learning_rate * 0.8
            )
            self.current_meta_params.diversity_threshold = max(
                0.15, self.current_meta_params.diversity_threshold * 0.9
            )

        # Adjust risk targets based on realized risk
        if current_drawdown > self.current_meta_params.max_drawdown_target * 1.2:
            # Higher than expected drawdown: tighten risk management
            self.current_meta_params.max_drawdown_target *= 0.9
        elif current_drawdown < self.current_meta_params.max_drawdown_target * 0.5:
            # Much lower than expected: can take more risk
            self.current_meta_params.max_drawdown_target *= 1.1

    def save_configuration(self, filename: str = "meta_evolution_config.json"):
        """Save current configuration to file."""
        config_data = {
            "meta_parameters": asdict(self.current_meta_params),
            "strategy_templates": {
                k.value: v for k, v in self.strategy_templates.items()
            },
            "example_count": len(self.example_database),
        }

        file_path = self.config_dir / filename
        with open(file_path, "w") as f:
            json.dump(config_data, f, indent=2, default=str)

        self.logger.info(f"Configuration saved to {file_path}")

    def _get_builtin_example(self, name: str) -> str:
        """Get built-in example code."""
        if name == "rsi_mean_reversion":
            return '''"""
@pyne
"""
from pynecore import Series, input, plot, color, script, Range

@script.indicator(title="RSI Mean Reversion", overlay=False)
def main():
    # Inputs
    rsi_length = input.int("RSI Length", 14)
    rsi_oversold = input.float("RSI Oversold", 30)
    rsi_overbought = input.float("RSI Overbought", 70)
    volume_mult = input.float("Volume Multiplier", 1.5)
    
    # Calculations
    rsi = close.rsi(rsi_length)
    vol_ma = volume.sma(20)
    vol_spike = volume > vol_ma * volume_mult
    
    # Signals
    oversold = rsi < rsi_oversold and vol_spike
    overbought = rsi > rsi_overbought and vol_spike
    
    # Plot
    plot(rsi, "RSI", color=color.purple)
    plot(rsi_oversold, "Oversold", color=color.red)
    plot(rsi_overbought, "Overbought", color=color.green)
    plotshape(oversold and rsi > rsi_oversold, "Buy Signal", shape.triangleup, color=color.green)
    plotshape(overbought and rsi < rsi_overbought, "Sell Signal", shape.triangledown, color=color.red)
'''
        elif name == "macd_momentum":
            return '''"""
@pyne
"""
from pynecore import Series, input, plot, color, script

@script.indicator(title="MACD Momentum", overlay=False)
def main():
    # Inputs  
    fast = input.int("Fast", 12)
    slow = input.int("Slow", 26)
    signal = input.int("Signal", 9)
    
    # Calculations
    macd_line = (close.ema(fast) - close.ema(slow))
    signal_line = macd_line.ema(signal)
    histogram = macd_line - signal_line
    
    # Momentum detection
    macd_bull = macd_line > signal_line and macd_line[1] <= signal_line[1]
    macd_bear = macd_line < signal_line and macd_line[1] >= signal_line[1]
    
    # Plot
    plot(macd_line, "MACD", color=color.blue)
    plot(signal_line, "Signal", color=color.orange)
    plot(histogram * 10, "Histogram", color=histogram > 0 and color.green or color.red)
    plotshape(macd_bull, "MACD Bull", shape.arrowup, color=color.green, location=location.bottom)
    plotshape(macd_bear, "MACD Bear", shape.arrowdown, color=color.red, location=location.top)
'''
        elif name == "volatility_breakout":
            return '''"""
@pyne
"""
from pynecore import Series, input, plot, color, script, Range

@script.indicator(title="Volatility Breakout", overlay=True)
def main():
    # Inputs
    sma_len = input.int("SMA Length", 20)
    atr_len = input.int("ATR Length", 14)
    atr_mult = input.float("ATR Multiplier", 2.0)
    vol_mult = input.float("Volume Mult", 1.5)
    
    # Calculations
    sma = close.sma(sma_len)
    atr = Range.atr(atr_len)
    upper_band = sma + (atr * atr_mult)
    lower_band = sma - (atr * atr_mult)
    
    vol_ma = volume.sma(20)
    vol_spike = volume > vol_ma * vol_mult
    
    # Breakout signals
    buy_breakout = close[1] <= upper_band[1] and close > upper_band and vol_spike
    sell_breakout = close[1] >= lower_band[1] and close < lower_band and vol_spike
    
    # Plot
    plot(sma, "SMA", color=color.blue)
    plot(upper_band, "Upper", color=color.red)
    plot(lower_band, "Lower", color=color.green)
    plotshape(buy_breakout, "Buy Breakout", shape.triangleup, color=color.green, location=location.belowbar)
    plotshape(sell_breakout, "Sell Breakout", shape.triangledown, color=color.red, location=location.abovebar)
'''

        return f"# Example code for {name}\ndef main():\n    pass\n"
