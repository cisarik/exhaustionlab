"""
Enhanced Multi-Market & Multi-Timeframe Testing

Tests strategies across:
- Multiple symbols (BTC, ETH, BNB, etc.)
- Multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- Different market conditions (bull, bear, sideways)
- Different volatility regimes

Provides comprehensive cross-market validation before deployment.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ..data.binance_rest import fetch_klines_csv_like
from ..meta_evolution.performance_metrics import PerformanceMetrics, calculate_comprehensive_metrics

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classification."""

    BULL = "bull"
    BEAR = "bear"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"


class VolatilityRegime(Enum):
    """Volatility classification."""

    LOW = "low"  # < 20% annualized
    MEDIUM = "medium"  # 20-50%
    HIGH = "high"  # 50-100%
    EXTREME = "extreme"  # > 100%


@dataclass
class MarketTestConfig:
    """Configuration for testing a single market/timeframe combination."""

    symbol: str
    timeframe: str
    lookback_days: int = 30
    min_trades: int = 10

    # Market classification (optional, will be auto-detected if None)
    regime: Optional[MarketRegime] = None
    volatility: Optional[VolatilityRegime] = None

    # Testing parameters
    enable_slippage: bool = True
    enable_fees: bool = True
    slippage_bps: float = 5.0  # 5 basis points
    fee_bps: float = 10.0  # 10 basis points (maker + taker)

    @property
    def cache_key(self) -> str:
        return f"{self.symbol}_{self.timeframe}_{self.lookback_days}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestResult:
    """Result from testing strategy on a single market/timeframe."""

    config: MarketTestConfig
    metrics: PerformanceMetrics

    # Execution details
    execution_time_seconds: float
    data_points: int
    validation_passed: bool
    validation_errors: List[str] = field(default_factory=list)

    # Market context
    detected_regime: Optional[MarketRegime] = None
    detected_volatility: Optional[VolatilityRegime] = None
    market_return: float = 0.0  # Buy-and-hold return for comparison

    # Raw data for deeper analysis
    trades_df: Optional[pd.DataFrame] = None
    equity_curve: Optional[pd.Series] = None
    returns_series: Optional[pd.Series] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding large dataframes)."""
        return {
            "config": self.config.to_dict(),
            "metrics": {
                "sharpe_ratio": self.metrics.sharpe_ratio,
                "sortino_ratio": self.metrics.sortino_ratio,
                "calmar_ratio": self.metrics.calmar_ratio,
                "total_return": self.metrics.total_return,
                "max_drawdown": self.metrics.max_drawdown,
                "win_rate": self.metrics.win_rate,
                "profit_factor": self.metrics.profit_factor,
                "total_trades": self.metrics.total_trades,
                "quality_score": self.metrics.quality_score,
            },
            "execution_time_seconds": self.execution_time_seconds,
            "data_points": self.data_points,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "detected_regime": (self.detected_regime.value if self.detected_regime else None),
            "detected_volatility": (self.detected_volatility.value if self.detected_volatility else None),
            "market_return": self.market_return,
        }


@dataclass
class AggregatedResults:
    """Aggregated results across multiple markets/timeframes."""

    # Overall performance
    mean_sharpe: float
    median_sharpe: float
    min_sharpe: float
    max_sharpe: float

    mean_drawdown: float
    max_drawdown: float

    mean_win_rate: float
    mean_profit_factor: float

    # Quality score distribution
    mean_quality_score: float
    min_quality_score: float
    std_quality_score: float

    # Consistency metrics
    markets_passed: int
    markets_failed: int
    pass_rate: float

    # Per-timeframe breakdown
    timeframe_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Per-symbol breakdown
    symbol_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Regime-specific performance
    regime_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Statistical tests
    sharpe_confidence_interval: Tuple[float, float] = (0.0, 0.0)
    performance_consistent: bool = False  # Based on statistical tests

    # Individual test results
    individual_results: List[TestResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "mean_sharpe": self.mean_sharpe,
            "median_sharpe": self.median_sharpe,
            "min_sharpe": self.min_sharpe,
            "max_sharpe": self.max_sharpe,
            "mean_drawdown": self.mean_drawdown,
            "max_drawdown": self.max_drawdown,
            "mean_win_rate": self.mean_win_rate,
            "mean_profit_factor": self.mean_profit_factor,
            "mean_quality_score": self.mean_quality_score,
            "min_quality_score": self.min_quality_score,
            "std_quality_score": self.std_quality_score,
            "markets_passed": self.markets_passed,
            "markets_failed": self.markets_failed,
            "pass_rate": self.pass_rate,
            "timeframe_performance": self.timeframe_performance,
            "symbol_performance": self.symbol_performance,
            "regime_performance": self.regime_performance,
            "sharpe_confidence_interval": self.sharpe_confidence_interval,
            "performance_consistent": self.performance_consistent,
        }


class EnhancedMultiMarketTester:
    """
    Enhanced multi-market testing with comprehensive validation.

    Features:
    - Test across multiple symbols simultaneously
    - Test across multiple timeframes
    - Automatic market regime detection
    - Statistical significance testing
    - Cross-market consistency validation
    - Realistic slippage and fee modeling
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_concurrent: int = 4,
        cache_ttl_days: int = 7,
    ):
        """
        Initialize multi-market tester.

        Args:
            cache_dir: Directory for caching market data
            max_concurrent: Maximum concurrent tests
            cache_ttl_days: Cache TTL in days
        """
        self.cache_dir = cache_dir or Path.home() / ".exhaustionlab" / "market_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_concurrent = max_concurrent
        self.cache_ttl_days = cache_ttl_days

        # Standard test configurations
        self.standard_symbols = [
            "BTCUSDT",  # Large cap, high liquidity
            "ETHUSDT",  # Large cap, high correlation to BTC
            "BNBUSDT",  # Exchange token
            "ADAUSDT",  # Mid cap
            "SOLUSDT",  # High volatility
            "DOGEUSDT",  # Meme coin, different dynamics
        ]

        self.standard_timeframes = [
            "1m",  # Scalping
            "5m",  # Short-term
            "15m",  # Medium-term
            "1h",  # Swing trading
            "4h",  # Position trading
        ]

    def create_test_matrix(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        lookback_days: int = 30,
    ) -> List[MarketTestConfig]:
        """
        Create comprehensive test matrix.

        Args:
            symbols: List of symbols (defaults to standard symbols)
            timeframes: List of timeframes (defaults to standard timeframes)
            lookback_days: Days of historical data

        Returns:
            List of test configurations
        """
        symbols = symbols or self.standard_symbols
        timeframes = timeframes or self.standard_timeframes

        configs = []
        for symbol in symbols:
            for timeframe in timeframes:
                config = MarketTestConfig(
                    symbol=symbol,
                    timeframe=timeframe,
                    lookback_days=lookback_days,
                )
                configs.append(config)

        logger.info(f"Created test matrix: {len(symbols)} symbols × " f"{len(timeframes)} timeframes = {len(configs)} tests")

        return configs

    async def test_strategy(
        self,
        strategy_func: Callable[[pd.DataFrame], Tuple[pd.DataFrame, pd.Series]],
        test_configs: Optional[List[MarketTestConfig]] = None,
        min_quality_score: float = 60.0,
        min_sharpe: float = 1.0,
    ) -> AggregatedResults:
        """
        Test strategy across multiple markets/timeframes.

        Args:
            strategy_func: Function that takes OHLCV data and returns (trades, equity)
            test_configs: List of test configurations (or None for standard matrix)
            min_quality_score: Minimum quality score to pass
            min_sharpe: Minimum Sharpe ratio to pass

        Returns:
            Aggregated results across all tests
        """
        # Create test matrix if not provided
        if test_configs is None:
            test_configs = self.create_test_matrix()

        # Run tests concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def test_with_semaphore(config: MarketTestConfig) -> TestResult:
            async with semaphore:
                return await self._test_single_market(strategy_func, config, min_quality_score, min_sharpe)

        tasks = [test_with_semaphore(config) for config in test_configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Test failed for {test_configs[i].symbol} " f"{test_configs[i].timeframe}: {result}")
            else:
                valid_results.append(result)

        if not valid_results:
            raise RuntimeError("All tests failed")

        # Aggregate results
        aggregated = self._aggregate_results(valid_results)

        logger.info(f"Testing complete: {aggregated.markets_passed}/{len(valid_results)} passed " f"(pass rate: {aggregated.pass_rate:.1%})")

        return aggregated

    async def _test_single_market(
        self,
        strategy_func: Callable[[pd.DataFrame], Tuple[pd.DataFrame, pd.Series]],
        config: MarketTestConfig,
        min_quality_score: float,
        min_sharpe: float,
    ) -> TestResult:
        """Test strategy on single market/timeframe."""
        start_time = datetime.now()

        try:
            # Get market data
            df = await self._get_market_data(config)

            # Detect market regime
            regime = self._detect_market_regime(df)
            volatility = self._detect_volatility_regime(df)

            # Run strategy
            trades_df, equity_curve = strategy_func(df)

            # Apply slippage and fees if enabled
            if config.enable_slippage or config.enable_fees:
                trades_df = self._apply_transaction_costs(trades_df, config.slippage_bps, config.fee_bps)
                equity_curve = self._recalculate_equity(trades_df)

            # Calculate returns
            returns = equity_curve.pct_change().dropna()

            # Calculate comprehensive metrics
            metrics = calculate_comprehensive_metrics(
                returns=returns,
                trades_df=trades_df,
                equity_curve=equity_curve,
            )

            # Validate results
            validation_passed, errors = self._validate_results(metrics, trades_df, min_quality_score, min_sharpe, config.min_trades)

            # Calculate market return for comparison
            market_return = (df["close"].iloc[-1] / df["close"].iloc[0]) - 1.0

            execution_time = (datetime.now() - start_time).total_seconds()

            return TestResult(
                config=config,
                metrics=metrics,
                execution_time_seconds=execution_time,
                data_points=len(df),
                validation_passed=validation_passed,
                validation_errors=errors,
                detected_regime=regime,
                detected_volatility=volatility,
                market_return=market_return,
                trades_df=trades_df,
                equity_curve=equity_curve,
                returns_series=returns,
            )

        except Exception as e:
            logger.error(f"Test failed for {config.symbol} {config.timeframe}: {e}")
            raise

    async def _get_market_data(self, config: MarketTestConfig) -> pd.DataFrame:
        """Get market data with caching."""
        cache_file = self.cache_dir / f"{config.cache_key}.csv"

        # Check cache
        if cache_file.exists():
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if file_age.days < self.cache_ttl_days:
                df = pd.read_csv(cache_file)
                if len(df) >= 100:  # Minimum data points
                    return df

        # Fetch fresh data
        limit = self._calculate_limit(config.timeframe, config.lookback_days)
        df = fetch_klines_csv_like(
            symbol=config.symbol,
            interval=config.timeframe,
            limit=limit,
        )

        if len(df) < 100:
            raise ValueError(f"Insufficient data for {config.symbol} {config.timeframe}")

        # Cache it
        df.to_csv(cache_file, index=False)

        return df

    def _calculate_limit(self, timeframe: str, lookback_days: int) -> int:
        """Calculate number of candles needed."""
        minutes_per_candle = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
        }.get(timeframe, 60)

        total_minutes = lookback_days * 24 * 60
        return min(1500, int(total_minutes / minutes_per_candle))

    def _detect_market_regime(self, df: pd.DataFrame) -> MarketRegime:
        """Detect market regime from price data."""
        returns = df["close"].pct_change().dropna()

        # Calculate trend
        price_change = (df["close"].iloc[-1] / df["close"].iloc[0]) - 1.0

        # Calculate volatility
        volatility = returns.std() * np.sqrt(252 * 24 * 60)  # Annualized

        # Classify regime
        if abs(price_change) < 0.05:  # Less than 5% movement
            return MarketRegime.SIDEWAYS
        elif volatility > 0.8:
            return MarketRegime.HIGH_VOLATILITY
        elif price_change > 0.1:
            return MarketRegime.BULL
        elif price_change < -0.1:
            return MarketRegime.BEAR
        else:
            return MarketRegime.SIDEWAYS

    def _detect_volatility_regime(self, df: pd.DataFrame) -> VolatilityRegime:
        """Detect volatility regime."""
        returns = df["close"].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252 * 24 * 60)  # Annualized

        if volatility < 0.2:
            return VolatilityRegime.LOW
        elif volatility < 0.5:
            return VolatilityRegime.MEDIUM
        elif volatility < 1.0:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME

    def _apply_transaction_costs(
        self,
        trades_df: pd.DataFrame,
        slippage_bps: float,
        fee_bps: float,
    ) -> pd.DataFrame:
        """Apply realistic slippage and fees to trades."""
        if trades_df.empty:
            return trades_df

        total_cost_bps = slippage_bps + fee_bps
        cost_multiplier = 1 - (total_cost_bps / 10000)

        # Apply to realized PnL
        if "pnl" in trades_df.columns:
            trades_df["pnl"] = trades_df["pnl"] * cost_multiplier

        return trades_df

    def _recalculate_equity(self, trades_df: pd.DataFrame) -> pd.Series:
        """Recalculate equity curve from adjusted trades."""
        if trades_df.empty:
            return pd.Series([1.0])

        equity = [1.0]
        for pnl in trades_df["pnl"]:
            equity.append(equity[-1] * (1 + pnl))

        return pd.Series(equity)

    def _validate_results(
        self,
        metrics: PerformanceMetrics,
        trades_df: pd.DataFrame,
        min_quality_score: float,
        min_sharpe: float,
        min_trades: int,
    ) -> Tuple[bool, List[str]]:
        """Validate test results."""
        errors = []

        # Check minimum trades
        if metrics.total_trades < min_trades:
            errors.append(f"Too few trades: {metrics.total_trades} < {min_trades}")

        # Check quality score
        if metrics.quality_score < min_quality_score:
            errors.append(f"Low quality score: {metrics.quality_score:.1f} < {min_quality_score}")

        # Check Sharpe ratio
        if metrics.sharpe_ratio < min_sharpe:
            errors.append(f"Low Sharpe: {metrics.sharpe_ratio:.2f} < {min_sharpe}")

        # Check for excessive drawdown
        if metrics.max_drawdown > 0.5:
            errors.append(f"Excessive drawdown: {metrics.max_drawdown:.1%}")

        return len(errors) == 0, errors

    def _aggregate_results(self, results: List[TestResult]) -> AggregatedResults:
        """Aggregate results across all tests."""
        # Extract metrics
        sharpe_ratios = [r.metrics.sharpe_ratio for r in results]
        drawdowns = [r.metrics.max_drawdown for r in results]
        win_rates = [r.metrics.win_rate for r in results]
        profit_factors = [r.metrics.profit_factor for r in results]
        quality_scores = [r.metrics.quality_score for r in results]

        # Overall statistics
        mean_sharpe = np.mean(sharpe_ratios)
        median_sharpe = np.median(sharpe_ratios)

        # Pass/fail counts
        passed = sum(1 for r in results if r.validation_passed)
        failed = len(results) - passed

        # Per-timeframe performance
        timeframe_perf = {}
        for tf in set(r.config.timeframe for r in results):
            tf_results = [r for r in results if r.config.timeframe == tf]
            timeframe_perf[tf] = {
                "mean_sharpe": np.mean([r.metrics.sharpe_ratio for r in tf_results]),
                "mean_quality": np.mean([r.metrics.quality_score for r in tf_results]),
                "pass_rate": sum(1 for r in tf_results if r.validation_passed) / len(tf_results),
            }

        # Per-symbol performance
        symbol_perf = {}
        for symbol in set(r.config.symbol for r in results):
            sym_results = [r for r in results if r.config.symbol == symbol]
            symbol_perf[symbol] = {
                "mean_sharpe": np.mean([r.metrics.sharpe_ratio for r in sym_results]),
                "mean_quality": np.mean([r.metrics.quality_score for r in sym_results]),
                "pass_rate": sum(1 for r in sym_results if r.validation_passed) / len(sym_results),
            }

        # Per-regime performance
        regime_perf = {}
        for regime in set(r.detected_regime for r in results if r.detected_regime):
            regime_results = [r for r in results if r.detected_regime == regime]
            regime_perf[regime.value] = {
                "mean_sharpe": np.mean([r.metrics.sharpe_ratio for r in regime_results]),
                "mean_quality": np.mean([r.metrics.quality_score for r in regime_results]),
                "pass_rate": sum(1 for r in regime_results if r.validation_passed) / len(regime_results),
            }

        # Statistical tests - confidence interval for Sharpe
        sharpe_std = np.std(sharpe_ratios)
        sharpe_ci = (
            mean_sharpe - 1.96 * sharpe_std / np.sqrt(len(sharpe_ratios)),
            mean_sharpe + 1.96 * sharpe_std / np.sqrt(len(sharpe_ratios)),
        )

        # Performance consistency check
        performance_consistent = sharpe_ci[0] > 0.5  # Lower bound > 0.5

        return AggregatedResults(
            mean_sharpe=mean_sharpe,
            median_sharpe=median_sharpe,
            min_sharpe=min(sharpe_ratios),
            max_sharpe=max(sharpe_ratios),
            mean_drawdown=np.mean(drawdowns),
            max_drawdown=max(drawdowns),
            mean_win_rate=np.mean(win_rates),
            mean_profit_factor=np.mean(profit_factors),
            mean_quality_score=np.mean(quality_scores),
            min_quality_score=min(quality_scores),
            std_quality_score=np.std(quality_scores),
            markets_passed=passed,
            markets_failed=failed,
            pass_rate=passed / len(results),
            timeframe_performance=timeframe_perf,
            symbol_performance=symbol_perf,
            regime_performance=regime_perf,
            sharpe_confidence_interval=sharpe_ci,
            performance_consistent=performance_consistent,
            individual_results=results,
        )

    def generate_report(self, results: AggregatedResults, output_path: Optional[Path] = None) -> str:
        """Generate human-readable test report."""
        lines = [
            "=" * 80,
            "MULTI-MARKET TESTING REPORT",
            "=" * 80,
            "",
            "OVERALL PERFORMANCE:",
            f"  Mean Sharpe Ratio: {results.mean_sharpe:.2f}",
            f"  Median Sharpe Ratio: {results.median_sharpe:.2f}",
            f"  Sharpe Range: [{results.min_sharpe:.2f}, {results.max_sharpe:.2f}]",
            f"  95% Confidence Interval: [{results.sharpe_confidence_interval[0]:.2f}, {results.sharpe_confidence_interval[1]:.2f}]",
            "",
            f"  Mean Quality Score: {results.mean_quality_score:.1f}/100",
            f"  Mean Win Rate: {results.mean_win_rate:.1%}",
            f"  Mean Profit Factor: {results.mean_profit_factor:.2f}",
            f"  Mean Drawdown: {results.mean_drawdown:.1%}",
            f"  Max Drawdown: {results.max_drawdown:.1%}",
            "",
            "VALIDATION RESULTS:",
            f"  Tests Passed: {results.markets_passed}/{results.markets_passed + results.markets_failed}",
            f"  Pass Rate: {results.pass_rate:.1%}",
            f"  Performance Consistent: {'YES' if results.performance_consistent else 'NO'}",
            "",
            "PER-TIMEFRAME PERFORMANCE:",
        ]

        for tf, perf in sorted(results.timeframe_performance.items()):
            lines.extend(
                [
                    f"  {tf}:",
                    f"    Mean Sharpe: {perf['mean_sharpe']:.2f}",
                    f"    Mean Quality: {perf['mean_quality']:.1f}",
                    f"    Pass Rate: {perf['pass_rate']:.1%}",
                ]
            )

        lines.extend(
            [
                "",
                "PER-SYMBOL PERFORMANCE:",
            ]
        )

        for symbol, perf in sorted(results.symbol_performance.items()):
            lines.extend(
                [
                    f"  {symbol}:",
                    f"    Mean Sharpe: {perf['mean_sharpe']:.2f}",
                    f"    Mean Quality: {perf['mean_quality']:.1f}",
                    f"    Pass Rate: {perf['pass_rate']:.1%}",
                ]
            )

        if results.regime_performance:
            lines.extend(
                [
                    "",
                    "PER-REGIME PERFORMANCE:",
                ]
            )

            for regime, perf in sorted(results.regime_performance.items()):
                lines.extend(
                    [
                        f"  {regime}:",
                        f"    Mean Sharpe: {perf['mean_sharpe']:.2f}",
                        f"    Mean Quality: {perf['mean_quality']:.1f}",
                        f"    Pass Rate: {perf['pass_rate']:.1%}",
                    ]
                )

        lines.append("=" * 80)

        report = "\n".join(lines)

        if output_path:
            output_path.write_text(report)

        return report
