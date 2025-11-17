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

from .backtest_parser import BacktestParser, BacktestResult, Trade, extract_equity_and_returns, extract_trades_dataframe, parse_backtest_from_directory
from .comprehensive_scorer import ComponentScores, ComprehensiveScorer
from .deployment_readiness import DeploymentReadinessScorer, ReadinessReport
from .execution_quality import ExecutionMetrics, ExecutionQuality, ExecutionQualityAnalyzer
from .monte_carlo_simulator import MonteCarloSimulator, SimulationResult
from .multi_market_tester import EnhancedMultiMarketTester, MarketTestConfig, TestResult
from .profit_analyzer import ProfitAnalyzer, ProfitMetrics, TradeAnalysis
from .report_generator import ReportConfig, ReportGenerator, generate_validation_report
from .slippage_model import LiquidityMetrics, MarketLiquidity, SlippageEstimate, SlippageEstimator, calculate_trading_costs
from .walk_forward_validator import WalkForwardResult, WalkForwardValidator

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
