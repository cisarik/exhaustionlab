"""
Meta-Evolution Framework for Advanced LLM Strategy Generation

Provides intelligent orchestration, web crawling, and production-level validation
for creating profitable live trading strategies.
"""

from .intelligent_orchestrator import EvolutionDirective, IntelligentOrchestrator, IntelligentPrompt
from .live_trading_validator import LiveTradingValidator, create_institutional_validator
from .meta_config import EvolutionIntensity, MarketFocus, MetaEvolutionConfig, MetaParameters, MetaStrategyType
from .StrategyWebCrawler import StrategyWebCrawler

MetaevolutionConfig = MetaEvolutionConfig

__all__ = [
    "MetaEvolutionConfig",
    "MetaevolutionConfig",
    "MetaParameters",
    "MetaStrategyType",
    "MarketFocus",
    "EvolutionIntensity",
    "IntelligentOrchestrator",
    "EvolutionDirective",
    "IntelligentPrompt",
    "LiveTradingValidator",
    "create_institutional_validator",
    "StrategyWebCrawler",
]
