"""
Strategy Validation Framework

Comprehensive testing and validation before deployment:
- Multi-market testing
- Multi-timeframe validation
- Profit analysis
- Walk-forward validation
- Monte Carlo simulation
- Deployment readiness scoring
- Advanced slippage estimation
- Execution quality analysis
"""

from .multi_market_tester import EnhancedMultiMarketTester, MarketTestConfig, TestResult
from .profit_analyzer import ProfitAnalyzer, ProfitMetrics, TradeAnalysis
from .walk_forward_validator import WalkForwardValidator, WalkForwardResult
from .monte_carlo_simulator import MonteCarloSimulator, SimulationResult
from .deployment_readiness import DeploymentReadinessScorer, ReadinessReport
from .slippage_model import (
    SlippageEstimator,
    SlippageEstimate,
    LiquidityMetrics,
    MarketLiquidity,
    calculate_trading_costs,
)
from .execution_quality import (
    ExecutionQualityAnalyzer,
    ExecutionMetrics,
    ExecutionQuality,
)
from .backtest_parser import (
    BacktestParser,
    BacktestResult,
    Trade,
    parse_backtest_from_directory,
    extract_trades_dataframe,
    extract_equity_and_returns,
)
from .comprehensive_scorer import (
    ComprehensiveScorer,
    ComponentScores,
)
from .report_generator import (
    ReportGenerator,
    ReportConfig,
    generate_validation_report,
)

__all__ = [
    "EnhancedMultiMarketTester",
    "MarketTestConfig",
    "TestResult",
    "ProfitAnalyzer",
    "ProfitMetrics",
    "TradeAnalysis",
    "WalkForwardValidator",
    "WalkForwardResult",
    "MonteCarloSimulator",
    "SimulationResult",
    "DeploymentReadinessScorer",
    "ReadinessReport",
    "SlippageEstimator",
    "SlippageEstimate",
    "LiquidityMetrics",
    "MarketLiquidity",
    "calculate_trading_costs",
    "ExecutionQualityAnalyzer",
    "ExecutionMetrics",
    "ExecutionQuality",
    "BacktestParser",
    "BacktestResult",
    "Trade",
    "parse_backtest_from_directory",
    "extract_trades_dataframe",
    "extract_equity_and_returns",
    "ComprehensiveScorer",
    "ComponentScores",
    "ReportGenerator",
    "ReportConfig",
    "generate_validation_report",
]
