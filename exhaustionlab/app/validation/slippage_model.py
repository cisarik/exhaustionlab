"""
Advanced Slippage Estimation Model

Estimates realistic slippage based on:
- Signal frequency (high frequency = more slippage)
- Market liquidity (order book depth, volume)
- Order size relative to market volume
- Volatility and spread
- Time of day effects
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime, time

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MarketLiquidity(Enum):
    """Market liquidity classification."""

    VERY_HIGH = "very_high"  # Top tier (BTC, ETH)
    HIGH = "high"  # Major coins
    MEDIUM = "medium"  # Mid caps
    LOW = "low"  # Small caps
    VERY_LOW = "very_low"  # Illiquid


class TimeOfDay(Enum):
    """Trading session classification."""

    ASIAN = "asian"  # Lower liquidity
    EUROPEAN = "european"  # Medium liquidity
    US = "us"  # Higher liquidity
    OVERLAP = "overlap"  # Highest liquidity


@dataclass
class LiquidityMetrics:
    """Market liquidity metrics."""

    # Volume-based metrics
    avg_24h_volume_usd: float  # 24h average volume
    avg_1h_volume_usd: float  # 1h average volume
    volume_volatility: float  # Std dev of volume

    # Order book metrics
    bid_ask_spread_bps: float  # Spread in basis points
    order_book_depth_1pct: float  # Liquidity within 1% of mid price
    order_book_depth_5pct: float  # Liquidity within 5% of mid price

    # Market quality
    liquidity_score: float  # 0-100, higher = more liquid
    market_impact_coefficient: float  # Price impact per $1M traded

    def classify_liquidity(self) -> MarketLiquidity:
        """Classify market liquidity."""
        if self.avg_24h_volume_usd > 1_000_000_000:  # > $1B
            return MarketLiquidity.VERY_HIGH
        elif self.avg_24h_volume_usd > 100_000_000:  # > $100M
            return MarketLiquidity.HIGH
        elif self.avg_24h_volume_usd > 10_000_000:  # > $10M
            return MarketLiquidity.MEDIUM
        elif self.avg_24h_volume_usd > 1_000_000:  # > $1M
            return MarketLiquidity.LOW
        else:
            return MarketLiquidity.VERY_LOW


@dataclass
class SlippageEstimate:
    """Slippage estimate for a trade."""

    # Base slippage components
    spread_cost_bps: float  # Bid-ask spread cost
    market_impact_bps: float  # Price impact
    execution_delay_bps: float  # Cost of execution delay
    volatility_slippage_bps: float  # Volatility-induced slippage

    # Total slippage
    total_slippage_bps: float  # Total estimated slippage

    # Confidence
    confidence_interval_lower_bps: float  # Lower bound (95% CI)
    confidence_interval_upper_bps: float  # Upper bound (95% CI)

    # Context
    signal_frequency: float  # Signals per day
    order_size_usd: float  # Order size
    liquidity_class: MarketLiquidity
    time_of_day: TimeOfDay

    def to_dict(self) -> Dict:
        return {
            "spread_cost_bps": self.spread_cost_bps,
            "market_impact_bps": self.market_impact_bps,
            "execution_delay_bps": self.execution_delay_bps,
            "volatility_slippage_bps": self.volatility_slippage_bps,
            "total_slippage_bps": self.total_slippage_bps,
            "confidence_interval": [
                self.confidence_interval_lower_bps,
                self.confidence_interval_upper_bps,
            ],
            "signal_frequency": self.signal_frequency,
            "order_size_usd": self.order_size_usd,
            "liquidity_class": self.liquidity_class.value,
            "time_of_day": self.time_of_day.value,
        }


class SlippageEstimator:
    """
    Advanced slippage estimation model.

    Estimates realistic trading costs based on market microstructure.
    """

    # Base spread costs by liquidity (in bps)
    BASE_SPREAD_COSTS = {
        MarketLiquidity.VERY_HIGH: 1.0,  # 0.01%
        MarketLiquidity.HIGH: 2.5,  # 0.025%
        MarketLiquidity.MEDIUM: 5.0,  # 0.05%
        MarketLiquidity.LOW: 10.0,  # 0.10%
        MarketLiquidity.VERY_LOW: 20.0,  # 0.20%
    }

    # Market impact coefficients (price impact per $1M traded)
    MARKET_IMPACT_COEFFICIENTS = {
        MarketLiquidity.VERY_HIGH: 0.5,  # 0.5 bps per $1M
        MarketLiquidity.HIGH: 1.5,  # 1.5 bps per $1M
        MarketLiquidity.MEDIUM: 5.0,  # 5 bps per $1M
        MarketLiquidity.LOW: 15.0,  # 15 bps per $1M
        MarketLiquidity.VERY_LOW: 50.0,  # 50 bps per $1M
    }

    def __init__(self):
        """Initialize slippage estimator."""
        self.liquidity_cache: Dict[str, LiquidityMetrics] = {}

    def estimate_slippage(
        self,
        symbol: str,
        order_size_usd: float,
        signal_frequency: float,  # Signals per day
        volatility: float,  # Annualized volatility
        liquidity_metrics: Optional[LiquidityMetrics] = None,
        timestamp: Optional[datetime] = None,
    ) -> SlippageEstimate:
        """
        Estimate slippage for a trade.

        Args:
            symbol: Trading symbol
            order_size_usd: Order size in USD
            signal_frequency: Number of signals per day
            volatility: Annualized volatility
            liquidity_metrics: Market liquidity metrics (optional)
            timestamp: Trade timestamp for time-of-day effects

        Returns:
            Detailed slippage estimate
        """
        # Get or estimate liquidity metrics
        if liquidity_metrics is None:
            liquidity_metrics = self._estimate_liquidity_metrics(symbol)

        liquidity_class = liquidity_metrics.classify_liquidity()

        # Determine time of day
        time_of_day = self._classify_time_of_day(timestamp)

        # 1. Spread cost
        spread_cost = self._calculate_spread_cost(
            liquidity_class, signal_frequency, time_of_day
        )

        # 2. Market impact
        market_impact = self._calculate_market_impact(
            order_size_usd, liquidity_metrics, liquidity_class
        )

        # 3. Execution delay cost
        execution_delay = self._calculate_execution_delay_cost(
            signal_frequency, volatility
        )

        # 4. Volatility slippage
        volatility_slippage = self._calculate_volatility_slippage(
            volatility, signal_frequency, liquidity_class
        )

        # Total slippage
        total_slippage = (
            spread_cost + market_impact + execution_delay + volatility_slippage
        )

        # Confidence interval (±30% for realistic range)
        ci_lower = total_slippage * 0.7
        ci_upper = total_slippage * 1.3

        return SlippageEstimate(
            spread_cost_bps=spread_cost,
            market_impact_bps=market_impact,
            execution_delay_bps=execution_delay,
            volatility_slippage_bps=volatility_slippage,
            total_slippage_bps=total_slippage,
            confidence_interval_lower_bps=ci_lower,
            confidence_interval_upper_bps=ci_upper,
            signal_frequency=signal_frequency,
            order_size_usd=order_size_usd,
            liquidity_class=liquidity_class,
            time_of_day=time_of_day,
        )

    def estimate_portfolio_slippage(
        self,
        trades_df: pd.DataFrame,
        symbol: str,
        portfolio_size_usd: float,
    ) -> Dict:
        """
        Estimate slippage for entire portfolio of trades.

        Args:
            trades_df: DataFrame with trade signals
            symbol: Trading symbol
            portfolio_size_usd: Total portfolio size

        Returns:
            Dictionary with portfolio-level slippage estimates
        """
        if trades_df.empty or len(trades_df) == 0:
            return {
                "total_slippage_cost_usd": 0,
                "avg_slippage_per_trade_bps": 0,
                "slippage_drag_annual_pct": 0,
            }

        # Calculate signal frequency
        if "timestamp" in trades_df.columns:
            time_range = (
                trades_df["timestamp"].max() - trades_df["timestamp"].min()
            ).total_seconds() / 86400
            signal_frequency = len(trades_df) / max(time_range, 1)
        else:
            signal_frequency = len(trades_df) / 30  # Assume 30 days

        # Estimate average order size
        avg_order_size_pct = 0.02  # 2% of portfolio per trade (default)
        if "position_size_pct" in trades_df.columns:
            avg_order_size_pct = trades_df["position_size_pct"].mean()

        avg_order_size_usd = portfolio_size_usd * avg_order_size_pct

        # Calculate volatility from price data
        if "returns" in trades_df.columns:
            volatility = trades_df["returns"].std() * np.sqrt(252)
        else:
            volatility = 0.8  # Default to 80% annual volatility for crypto

        # Get liquidity metrics
        liquidity_metrics = self._estimate_liquidity_metrics(symbol)

        # Estimate slippage for each trade
        slippage_estimates = []
        for idx, trade in trades_df.iterrows():
            timestamp = trade.get("timestamp", None)
            estimate = self.estimate_slippage(
                symbol=symbol,
                order_size_usd=avg_order_size_usd,
                signal_frequency=signal_frequency,
                volatility=volatility,
                liquidity_metrics=liquidity_metrics,
                timestamp=timestamp,
            )
            slippage_estimates.append(estimate)

        # Aggregate results
        avg_slippage_bps = np.mean([e.total_slippage_bps for e in slippage_estimates])

        # Total cost in USD
        total_slippage_cost_usd = sum(
            avg_order_size_usd * (e.total_slippage_bps / 10000)
            for e in slippage_estimates
        )

        # Annual drag (slippage per trade × trades per year)
        trades_per_year = signal_frequency * 365
        annual_drag_bps = avg_slippage_bps * trades_per_year
        annual_drag_pct = annual_drag_bps / 10000

        return {
            "total_trades": len(trades_df),
            "signal_frequency": signal_frequency,
            "avg_order_size_usd": avg_order_size_usd,
            "avg_slippage_per_trade_bps": avg_slippage_bps,
            "total_slippage_cost_usd": total_slippage_cost_usd,
            "slippage_drag_annual_pct": annual_drag_pct,
            "trades_per_year": trades_per_year,
            "slippage_breakdown": {
                "spread": np.mean([e.spread_cost_bps for e in slippage_estimates]),
                "market_impact": np.mean(
                    [e.market_impact_bps for e in slippage_estimates]
                ),
                "execution_delay": np.mean(
                    [e.execution_delay_bps for e in slippage_estimates]
                ),
                "volatility": np.mean(
                    [e.volatility_slippage_bps for e in slippage_estimates]
                ),
            },
        }

    def _calculate_spread_cost(
        self,
        liquidity_class: MarketLiquidity,
        signal_frequency: float,
        time_of_day: TimeOfDay,
    ) -> float:
        """
        Calculate spread cost.

        Higher frequency = pay spread more often
        Lower liquidity times = higher spread
        """
        base_spread = self.BASE_SPREAD_COSTS[liquidity_class]

        # Adjust for signal frequency
        # High frequency strategies pay spread more often
        frequency_multiplier = 1.0
        if signal_frequency > 10:  # > 10 signals/day
            frequency_multiplier = 1.5
        elif signal_frequency > 50:  # > 50 signals/day
            frequency_multiplier = 2.0

        # Adjust for time of day
        time_multiplier = {
            TimeOfDay.ASIAN: 1.3,  # Lower liquidity
            TimeOfDay.EUROPEAN: 1.1,
            TimeOfDay.US: 1.0,  # Best liquidity
            TimeOfDay.OVERLAP: 0.9,  # Highest liquidity
        }.get(time_of_day, 1.0)

        return base_spread * frequency_multiplier * time_multiplier

    def _calculate_market_impact(
        self,
        order_size_usd: float,
        liquidity_metrics: LiquidityMetrics,
        liquidity_class: MarketLiquidity,
    ) -> float:
        """
        Calculate market impact (price movement caused by order).

        Uses square-root model: Impact ∝ √(order_size / volume)
        """
        # Get market impact coefficient
        impact_coef = self.MARKET_IMPACT_COEFFICIENTS[liquidity_class]

        # Calculate impact based on order size
        # Square root model: larger orders have non-linear impact
        order_size_millions = order_size_usd / 1_000_000
        base_impact = impact_coef * np.sqrt(order_size_millions)

        # Adjust for actual liquidity
        liquidity_adjustment = 1.0
        if liquidity_metrics.order_book_depth_1pct > 0:
            # If order size > 10% of 1% depth, increase impact
            depth_ratio = order_size_usd / liquidity_metrics.order_book_depth_1pct
            if depth_ratio > 0.1:
                liquidity_adjustment = 1 + np.log1p(depth_ratio)

        return base_impact * liquidity_adjustment

    def _calculate_execution_delay_cost(
        self,
        signal_frequency: float,
        volatility: float,
    ) -> float:
        """
        Calculate cost of execution delay.

        Time between signal and execution causes slippage in volatile markets.
        """
        # Estimate execution delay based on signal frequency
        # High frequency = need faster execution
        if signal_frequency > 50:
            avg_delay_seconds = 100  # 100ms for HFT
        elif signal_frequency > 10:
            avg_delay_seconds = 1000  # 1 second for active
        else:
            avg_delay_seconds = 5000  # 5 seconds for slower strategies

        # Convert delay to fraction of day
        delay_fraction = avg_delay_seconds / 86400

        # Estimate price movement during delay
        # σ_delay = σ_annual × √(delay_fraction)
        daily_volatility = volatility / np.sqrt(252)
        delay_volatility = daily_volatility * np.sqrt(delay_fraction)

        # Cost is ~half of the volatility range (market can move either way)
        delay_cost_pct = delay_volatility * 0.5
        delay_cost_bps = delay_cost_pct * 10000

        return delay_cost_bps

    def _calculate_volatility_slippage(
        self,
        volatility: float,
        signal_frequency: float,
        liquidity_class: MarketLiquidity,
    ) -> float:
        """
        Calculate volatility-induced slippage.

        Higher volatility = wider spreads and more slippage.
        """
        # Base volatility effect
        # High volatility markets have higher slippage
        base_vol_slippage = volatility * 5  # 5 bps per 100% volatility

        # Frequency adjustment
        # High frequency strategies suffer more in volatile markets
        freq_multiplier = 1.0 + (signal_frequency / 100)

        # Liquidity adjustment
        # Less liquid markets have higher volatility slippage
        liquidity_multiplier = {
            MarketLiquidity.VERY_HIGH: 0.8,
            MarketLiquidity.HIGH: 1.0,
            MarketLiquidity.MEDIUM: 1.3,
            MarketLiquidity.LOW: 1.8,
            MarketLiquidity.VERY_LOW: 2.5,
        }.get(liquidity_class, 1.0)

        return base_vol_slippage * freq_multiplier * liquidity_multiplier

    def _estimate_liquidity_metrics(self, symbol: str) -> LiquidityMetrics:
        """
        Estimate liquidity metrics for a symbol.

        In production, this would query real exchange data.
        For now, use historical averages based on symbol.
        """
        # Check cache
        if symbol in self.liquidity_cache:
            return self.liquidity_cache[symbol]

        # Estimate based on common symbols
        # In production, fetch real data from exchange API
        if symbol in ["BTCUSDT", "BTCUSD", "ETHUSDT", "ETHUSD"]:
            metrics = LiquidityMetrics(
                avg_24h_volume_usd=5_000_000_000,  # $5B
                avg_1h_volume_usd=200_000_000,  # $200M
                volume_volatility=0.3,
                bid_ask_spread_bps=1.0,
                order_book_depth_1pct=50_000_000,  # $50M
                order_book_depth_5pct=200_000_000,  # $200M
                liquidity_score=95,
                market_impact_coefficient=0.5,
            )
        elif symbol in ["BNBUSDT", "SOLUSDT", "ADAUSDT"]:
            metrics = LiquidityMetrics(
                avg_24h_volume_usd=500_000_000,  # $500M
                avg_1h_volume_usd=20_000_000,  # $20M
                volume_volatility=0.4,
                bid_ask_spread_bps=2.5,
                order_book_depth_1pct=10_000_000,  # $10M
                order_book_depth_5pct=40_000_000,  # $40M
                liquidity_score=75,
                market_impact_coefficient=1.5,
            )
        else:
            # Default for unknown symbols (conservative estimate)
            metrics = LiquidityMetrics(
                avg_24h_volume_usd=50_000_000,  # $50M
                avg_1h_volume_usd=2_000_000,  # $2M
                volume_volatility=0.6,
                bid_ask_spread_bps=5.0,
                order_book_depth_1pct=1_000_000,  # $1M
                order_book_depth_5pct=5_000_000,  # $5M
                liquidity_score=50,
                market_impact_coefficient=5.0,
            )

        # Cache it
        self.liquidity_cache[symbol] = metrics

        return metrics

    def _classify_time_of_day(self, timestamp: Optional[datetime]) -> TimeOfDay:
        """Classify time of day for liquidity estimation."""
        if timestamp is None:
            return TimeOfDay.US  # Default

        hour = timestamp.hour

        # UTC hours
        if 0 <= hour < 7:
            return TimeOfDay.ASIAN
        elif 7 <= hour < 12:
            return TimeOfDay.OVERLAP  # Europe + Asia
        elif 12 <= hour < 17:
            return TimeOfDay.EUROPEAN
        elif 17 <= hour < 20:
            return TimeOfDay.OVERLAP  # Europe + US
        else:
            return TimeOfDay.US

    def get_symbol_liquidity_info(self, symbol: str) -> Dict:
        """Get liquidity information for a symbol."""
        metrics = self._estimate_liquidity_metrics(symbol)
        liquidity_class = metrics.classify_liquidity()

        return {
            "symbol": symbol,
            "liquidity_class": liquidity_class.value,
            "liquidity_score": metrics.liquidity_score,
            "avg_24h_volume_usd": metrics.avg_24h_volume_usd,
            "bid_ask_spread_bps": metrics.bid_ask_spread_bps,
            "order_book_depth_1pct_usd": metrics.order_book_depth_1pct,
            "market_impact_coef": metrics.market_impact_coefficient,
            "base_spread_cost_bps": self.BASE_SPREAD_COSTS[liquidity_class],
        }


def calculate_trading_costs(
    trades_df: pd.DataFrame,
    symbol: str,
    portfolio_size_usd: float,
    include_fees: bool = True,
    fee_bps: float = 10.0,  # 10 bps (0.1%)
) -> Dict:
    """
    Calculate total trading costs including slippage and fees.

    Args:
        trades_df: DataFrame with trades
        symbol: Trading symbol
        portfolio_size_usd: Portfolio size
        include_fees: Include exchange fees
        fee_bps: Fee in basis points

    Returns:
        Dictionary with comprehensive cost breakdown
    """
    estimator = SlippageEstimator()

    # Estimate slippage
    slippage_results = estimator.estimate_portfolio_slippage(
        trades_df, symbol, portfolio_size_usd
    )

    # Calculate fees
    if include_fees:
        total_fees_usd = (
            slippage_results["avg_order_size_usd"]
            * (fee_bps / 10000)
            * slippage_results["total_trades"]
        )
        annual_fee_drag_bps = fee_bps * slippage_results["trades_per_year"]
        annual_fee_drag_pct = annual_fee_drag_bps / 10000
    else:
        total_fees_usd = 0
        annual_fee_drag_bps = 0
        annual_fee_drag_pct = 0

    # Total costs
    total_costs_usd = slippage_results["total_slippage_cost_usd"] + total_fees_usd
    total_annual_drag_pct = (
        slippage_results["slippage_drag_annual_pct"] + annual_fee_drag_pct
    )

    return {
        "slippage": slippage_results,
        "fees": {
            "total_fees_usd": total_fees_usd,
            "fee_per_trade_bps": fee_bps,
            "annual_fee_drag_pct": annual_fee_drag_pct,
        },
        "total_costs": {
            "total_costs_usd": total_costs_usd,
            "total_annual_drag_pct": total_annual_drag_pct,
            "cost_as_pct_of_portfolio": (total_costs_usd / portfolio_size_usd) * 100,
        },
        "cost_breakdown_pct": {
            "slippage": (
                (slippage_results["total_slippage_cost_usd"] / total_costs_usd) * 100
                if total_costs_usd > 0
                else 0
            ),
            "fees": (
                (total_fees_usd / total_costs_usd) * 100 if total_costs_usd > 0 else 0
            ),
        },
    }
