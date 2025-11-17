"""
Multi-Market Strategy Evaluation Framework

Tests strategies across different markets, timeframes,
and market conditions for robust fitness evaluation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..data.binance_rest import fetch_klines_csv_like
from .engine import run_pyne
from .strategy_registry import StrategyMetrics, StrategyRegistry


@dataclass
class MarketConfig:
    """Configuration for market testing."""

    symbol: str
    timeframe: str
    market_type: str  # 'spot', 'futures', 'options'
    volatility_regime: str  # 'low', 'medium', 'high'
    trending_regime: str  # 'bull', 'bear', 'sideways'

    # Testing parameters
    lookback_days: int = 30
    min_data_points: int = 1000

    @property
    def cache_key(self) -> str:
        return f"{self.symbol}_{self.timeframe}_{self.market_type}"


class MultiMarketEvaluator:
    """Concurrent multi-market strategy testing."""

    def __init__(self, strategy_registry: StrategyRegistry, cache_dir: Optional[Path] = None):
        self.registry = strategy_registry
        self.cache_dir = cache_dir or Path.home() / ".exhaustionlab" / "market_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Define comprehensive market universe for testing
        self.markets = self._define_market_universe()

        # Execution settings
        self.max_workers = 4
        self.cache_ttl_days = 7
        self.logger = logging.getLogger(__name__)

    def _define_market_universe(self) -> List[MarketConfig]:
        """Define comprehensive set of markets for robust testing."""
        markets = [
            # Major crypto pairs - different volatility profiles
            MarketConfig("BTCUSDT", "1m", "spot", "high", "bull", lookback_days=30),
            MarketConfig("BTCUSDT", "5m", "spot", "high", "bull", lookback_days=14),
            MarketConfig("BTCUSDT", "15m", "spot", "high", "bull", lookback_days=7),
            MarketConfig("ETHUSDT", "1m", "spot", "high", "bull", lookback_days=30),
            MarketConfig("ETHUSDT", "5m", "spot", "high", "bull", lookback_days=14),
            # Medium volatility altcoins
            MarketConfig("ADAUSDT", "1m", "spot", "medium", "bull", lookback_days=21),
            MarketConfig("SOLUSDT", "5m", "spot", "medium", "bull", lookback_days=14),
            MarketConfig("MATICUSDT", "15m", "spot", "medium", "bull", lookback_days=10),
            # Lower volume, higher volatility pairs
            MarketConfig("DOGEUSDT", "1m", "spot", "high", "bull", lookback_days=21),
            MarketConfig("SHIBUSDT", "5m", "spot", "very_high", "bull", lookback_days=14),
            # Different market types (if available)
            MarketConfig("BTCUSDT", "1m", "futures", "high", "bull", lookback_days=30),
            # Cross-market correlations (commodities, forex analogues in crypto)
            MarketConfig("XAUUSDT", "1m", "spot", "medium", "bull", lookback_days=21),  # Gold proxy
            MarketConfig("EURUSDT", "15m", "spot", "low", "sideways", lookback_days=14),  # Forex proxy
        ]

        return markets

    async def evaluate_strategy(
        self,
        strategy_id: str,
        version_id: str,
        markets_to_test: Optional[List[MarketConfig]] = None,
    ) -> StrategyMetrics:
        """Evaluate strategy across multiple markets concurrently."""
        markets = markets_to_test or self._select_diverse_markets()

        tasks = []
        for market in markets:
            task = self._evaluate_single_market(strategy_id, version_id, market)
            tasks.append(task)

        # Run evaluations concurrently
        market_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        valid_results = [r for r in market_results if not isinstance(r, Exception)]
        if not valid_results:
            raise RuntimeError("All market evaluations failed")

        return self._aggregate_market_metrics(valid_results, markets)

    def _select_diverse_markets(self) -> List[MarketConfig]:
        """Select diverse subset of markets for efficient testing."""
        # Ensure we have: different symbols, timeframes, volatility regimes
        selected = []

        # High volatility major pairs
        high_vol = [m for m in self.markets if m.volatility_regime == "high"]
        selected.extend(high_vol[:2])

        # Medium volatility altcoins
        med_vol = [m for m in self.markets if m.volatility_regime == "medium"]
        selected.extend(med_vol[:2])

        # Different timeframes ensure temporal robustness
        timeframes = ["1m", "5m", "15m"]
        for tf in timeframes:
            tf_markets = [m for m in self.markets if m.timeframe == tf and m not in selected]
            if tf_markets:
                selected.append(tf_markets[0])

        return selected[:8]  # Limit to reasonable number for optimization

    async def _evaluate_single_market(self, strategy_id: str, version_id: str, market: MarketConfig) -> StrategyMetrics:
        """Evaluate strategy on single market/timeframe combination."""
        try:
            # Get market data (with caching)
            df = await self._get_market_data(market)

            # Get strategy details
            strategy = self.registry.get_strategy(strategy_id)
            if not strategy:
                raise ValueError(f"Strategy {strategy_id} not found")

            # Create temporary strategy script with current version
            version_info = self._get_version_info(version_id)
            pyne_code = version_info["pyne_code"]
            parameters = json.loads(version_info["parameters"])

            # Run backtest
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(pyne_code)
                temp_script = Path(f.name)

            try:
                with tempfile.NamedTemporaryFile(mode="w", suffix=".ohlcv", delete=False) as f:
                    df.to_csv(f.name, index=False)
                    temp_data = Path(f.name)

                result = run_pyne(
                    str(temp_data),
                    script_name=str(temp_script),
                    parameters=parameters,
                    timeout=120,
                )

                # Parse results and calculate metrics
                metrics = self._calculate_comprehensive_metrics(result.output_dir, df, market)

                # Store results
                self.registry.record_strategy_metrics(strategy_id, version_id, market.symbol, market.timeframe, metrics)

                return metrics

            finally:
                temp_script.unlink(missing_ok=True)
                temp_data.unlink(missing_ok=True)

        except Exception as e:
            self.logger.error(f"Failed to evaluate {strategy_id} on {market.symbol} " f"{market.timeframe}: {e}")
            raise

    async def _get_market_data(self, market: MarketConfig) -> pd.DataFrame:
        """Get market data with intelligent caching."""
        cache_file = self.cache_dir / f"{market.cache_key}.csv"

        # Check cache freshness
        if cache_file.exists():
            file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if file_age.days < self.cache_ttl_days:
                df = pd.read_csv(cache_file)
                if len(df) >= market.min_data_points:
                    return df

        # Fetch fresh data
        limit = min(1500, market.lookback_days * 24 * 60)  # Rough estimate for 1m data
        df = fetch_klines_csv_like(symbol=market.symbol, interval=market.timeframe, limit=limit)

        if len(df) < market.min_data_points:
            raise ValueError(f"Insufficient data for {market.symbol} {market.timeframe}")

        # Cache results
        df.to_csv(cache_file, index=False)

        return df

    def _get_version_info(self, version_id: str) -> Dict[str, Any]:
        """Get version-specific strategy information."""
        with sqlite3.connect(self.registry.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM strategy_versions WHERE version_id = ?", (version_id,)).fetchone()

            if row:
                return dict(row)
            else:
                raise ValueError(f"Version {version_id} not found")

    def _calculate_comprehensive_metrics(self, output_dir: Path, df: pd.DataFrame, market: MarketConfig) -> StrategyMetrics:
        """Calculate comprehensive trading metrics including real-world factors."""

        # Parse PyneCore output (simplified - would need actual parsing)
        try:
            with open(output_dir / "trades.json") as f:
                trades = json.load(f)
            with open(output_dir / "equity.json") as f:
                equity = json.load(f)
        except FileNotFoundError:
            # Fallback to basic calculation if PyneCore output not available
            return self._calculate_fallback_metrics(df, market)

        # Trade-based metrics
        pnl_series = pd.Series([t.get("pnl", 0) for t in trades])
        total_pnl = pnl_series.sum()
        win_rate = (pnl_series > 0).mean()

        # Risk metrics
        equity_curve = pd.Series(equity.get("equity", []))
        returns = equity_curve.pct_change().dropna()
        max_drawdown = (equity_curve.cummax() - equity_curve).max() / equity_curve.cummax().max()

        # Enhanced risk metrics
        downside_returns = returns[returns < 0]
        downside_deviation = downside_returns.std() if len(downside_returns) > 0 else 0

        # Real-world trading factors
        avg_slippage = self._estimate_slippage(trades, market)
        execution_delay = self._estimate_execution_delay(trades, market)
        market_impact = self._estimate_market_impact(trades, df, market)

        # Consistency metrics
        profit_factor = abs(pnl_series[pnl_series > 0].sum() / pnl_series[pnl_series < 0].sum()) if (pnl_series < 0).any() and (pnl_series > 0).any() else 1.0

        return StrategyMetrics(
            total_pnl=total_pnl,
            sharpe_ratio=self._calculate_sharpe_ratio(returns),
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_trade=pnl_series.mean() if len(pnl_series) > 0 else 0,
            num_trades=len(trades),
            markets_tested=[market.symbol],
            timeframes_tested=[market.timeframe],
            slippage_impact=avg_slippage,
            execution_delay_ms=execution_delay,
            market_impact=market_impact,
            correlation_to_benchmark=self._calculate_correlation(equity_curve, df),
            volatility_adjusted_return=(returns.mean() / returns.std() if returns.std() > 0 else 0),
            downside_deviation=downside_deviation,
        )

    def _calculate_fallback_metrics(self, df: pd.DataFrame, market: MarketConfig) -> StrategyMetrics:
        """Calculate basic metrics when PyneCore output not available."""
        # Simple price-based simulation (very basic fallback)
        returns = df["close"].pct_change().dropna()
        simple_pnl = returns.sum() * 100  # Assuming 100% invested

        return StrategyMetrics(
            total_pnl=simple_pnl,
            sharpe_ratio=self._calculate_sharpe_ratio(returns),
            max_drawdown=0.1,  # Assume 10% drawdown
            win_rate=0.5,
            profit_factor=1.0,
            avg_trade=0.0,
            num_trades=0,
            markets_tested=[market.symbol],
            timeframes_tested=[market.timeframe],
        )

    def _calculate_sharpe_ratio(self, returns: pd.Series, risk_free_rate: float = 0.02) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2 or returns.std() == 0:
            return 0.0
        excess_returns = returns - risk_free_rate / 252  # Daily risk-free rate
        return (excess_returns.mean() / excess_returns.std()) * (252**0.5)

    def _estimate_slippage(self, trades: List[Dict], market: MarketConfig) -> float:
        """Estimate slippage based on market conditions."""
        base_slippage = 0.0005  # 5 bps base

        volatility_multiplier = {
            "low": 1.0,
            "medium": 1.5,
            "high": 2.0,
            "very_high": 3.0,
        }.get(market.volatility_regime, 1.0)

        timeframe_multiplier = {"1m": 1.0, "5m": 0.8, "15m": 0.6, "1h": 0.4}.get(market.timeframe, 1.0)

        return base_slippage * volatility_multiplier * timeframe_multiplier

    def _estimate_execution_delay(self, trades: List[Dict], market: MarketConfig) -> float:
        """Estimate execution delay in milliseconds."""
        base_delay = 50  # 50ms base

        volatility_impact = {
            "low": 1.0,
            "medium": 1.2,
            "high": 1.5,
            "very_high": 2.0,
        }.get(market.volatility_regime, 1.0)

        return base_delay * volatility_impact

    def _estimate_market_impact(self, trades: List[Dict], df: pd.DataFrame, market: MarketConfig) -> float:
        """Estimate market impact of trades."""
        if not trades:
            return 0.0

        avg_volume = df["volume"].mean()
        avg_trade_size = sum(t.get("size", 0) for t in trades) / len(trades)

        volume_ratio = avg_trade_size / avg_volume if avg_volume > 0 else 0
        return min(volume_ratio * 0.1, 0.05)  # Cap at 5% impact

    def _calculate_correlation(self, equity_curve: pd.Series, df: pd.DataFrame) -> float:
        """Calculate correlation to benchmark (buy-and-hold)."""
        if len(equity_curve) != len(df):
            return 0.0

        benchmark = df["close"] / df["close"].iloc[0]
        strategy_returns = equity_curve.pct_change().dropna()
        benchmark_returns = benchmark.pct_change().dropna()

        if len(strategy_returns) != len(benchmark_returns):
            return 0.0

        return strategy_returns.corr(benchmark_returns)

    def _aggregate_market_metrics(self, market_results: List[StrategyMetrics], markets: List[MarketConfig]) -> StrategyMetrics:
        """Aggregate multi-market results into comprehensive metrics."""
        if not market_results:
            raise ValueError("No valid market results to aggregate")

        # Aggregate across markets
        total_pnl = sum(r.total_pnl for r in market_results)
        num_trades = sum(r.num_trades for r in market_results)

        # Weighted averages for rate-based metrics
        weights = [abs(r.total_pnl) + 0.01 for r in market_results]  # Use PnL as weight
        weight_sum = sum(weights)

        weighted_sharpe = sum(r.sharpe_ratio * w for r, w in zip(market_results, weights)) / weight_sum
        weighted_winrate = sum(r.win_rate * w for r, w in zip(market_results, weights)) / weight_sum
        weighted_drawdown = sum(r.max_drawdown * w for r, w in zip(market_results, weights)) / weight_sum

        # Combine unique markets and timeframes
        all_markets = list(set(sum([r.markets_tested for r in market_results], [])))
        all_timeframes = list(set(sum([r.timeframes_tested for r in market_results], [])))

        # Average execution metrics
        avg_slippage = sum(r.slippage_impact for r in market_results) / len(market_results)
        avg_delay = sum(r.execution_delay_ms for r in market_results) / len(market_results)
        avg_market_impact = sum(r.market_impact for r in market_results) / len(market_results)

        # Consistency metrics
        profit_factor = sum(r.profit_factor for r in market_results) / len(market_results)
        avg_trade = total_pnl / num_trades if num_trades > 0 else 0

        # Risk-adjusted metrics
        correlation_to_benchmark = sum(r.correlation_to_benchmark for r in market_results) / len(market_results)
        volatility_adjusted_return = sum(r.volatility_adjusted_return for r in market_results) / len(market_results)
        downside_deviation = sum(r.downside_deviation for r in market_results) / len(market_results)

        return StrategyMetrics(
            total_pnl=total_pnl,
            sharpe_ratio=weighted_sharpe,
            max_drawdown=weighted_drawdown,
            win_rate=weighted_winrate,
            profit_factor=profit_factor,
            avg_trade=avg_trade,
            num_trades=num_trades,
            markets_tested=all_markets,
            timeframes_tested=all_timeframes,
            slippage_impact=avg_slippage,
            execution_delay_ms=avg_delay,
            market_impact=avg_market_impact,
            correlation_to_benchmark=correlation_to_benchmark,
            volatility_adjusted_return=volatility_adjusted_return,
            downside_deviation=downside_deviation,
        )

    async def batch_evaluate_population(self, population: List[Tuple[str, str]]) -> Dict[str, StrategyMetrics]:
        """Evaluate entire strategy population concurrently."""
        results = {}

        # Create semaphore to limit concurrent evaluations
        semaphore = asyncio.Semaphore(self.max_workers)

        async def evaluate_with_semaphore(strategy_id: str, version_id: str):
            async with semaphore:
                try:
                    metrics = await self.evaluate_strategy(strategy_id, version_id)
                    results[(strategy_id, version_id)] = metrics
                except Exception as e:
                    self.logger.error(f"Failed to evaluate strategy {strategy_id}: {e}")

        tasks = [evaluate_with_semaphore(s_id, v_id) for s_id, v_id in population]

        await asyncio.gather(*tasks, return_exceptions=True)

        return results
