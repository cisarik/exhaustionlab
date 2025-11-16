"""
PyneCore Backtest Parser

Parses actual PyneCore output files to extract:
- Trade history with timestamps
- Equity curve from trades
- Position history
- Signals and executions
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Individual trade record."""

    trade_id: int
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    quantity: float
    side: str  # 'long' or 'short'
    pnl: float
    pnl_pct: float
    commission: float
    slippage: float
    reason: str  # exit reason
    duration_seconds: float

    @property
    def is_win(self) -> bool:
        return self.pnl > 0

    @property
    def is_loss(self) -> bool:
        return self.pnl < 0


@dataclass
class BacktestResult:
    """Complete backtest result with all metrics."""

    # Basic info
    strategy_name: str
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime

    # Trades
    trades: List[Trade]
    total_trades: int
    winning_trades: int
    losing_trades: int

    # Returns
    equity_curve: pd.Series
    returns: pd.Series
    cumulative_returns: pd.Series

    # Performance metrics
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int

    # Trade metrics
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float

    # Additional data
    raw_data: Dict = field(default_factory=dict)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert trades to DataFrame."""
        if not self.trades:
            return pd.DataFrame()

        return pd.DataFrame(
            [
                {
                    "trade_id": t.trade_id,
                    "entry_time": t.entry_time,
                    "exit_time": t.exit_time,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "quantity": t.quantity,
                    "side": t.side,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                    "commission": t.commission,
                    "reason": t.reason,
                    "duration_seconds": t.duration_seconds,
                }
                for t in self.trades
            ]
        )


class BacktestParser:
    """
    Parse PyneCore backtest output files.

    PyneCore typically outputs:
    - trades.json: List of executed trades
    - equity.json: Equity curve data
    - signals.json: Trading signals
    - summary.json: Summary metrics
    """

    def __init__(self):
        """Initialize parser."""
        pass

    def parse_backtest_directory(self, output_dir: Path) -> BacktestResult:
        """
        Parse complete backtest from output directory.

        Args:
            output_dir: Directory containing PyneCore output files

        Returns:
            Parsed backtest result
        """
        if not output_dir.exists():
            raise FileNotFoundError(f"Backtest directory not found: {output_dir}")

        logger.info(f"Parsing backtest from: {output_dir}")

        # Parse individual files
        trades = self._parse_trades(output_dir / "trades.json")
        equity_data = self._parse_equity(output_dir / "equity.json")
        summary = self._parse_summary(output_dir / "summary.json")

        # Build equity curve and returns from trades
        equity_curve, returns = self._build_equity_curve(trades)

        # Calculate metrics
        metrics = self._calculate_metrics(equity_curve, returns, trades)

        # Create result
        result = BacktestResult(
            strategy_name=summary.get("strategy_name", "Unknown"),
            symbol=summary.get("symbol", "Unknown"),
            timeframe=summary.get("timeframe", "Unknown"),
            start_date=self._parse_timestamp(summary.get("start_date")),
            end_date=self._parse_timestamp(summary.get("end_date")),
            trades=trades,
            total_trades=len(trades),
            winning_trades=sum(1 for t in trades if t.is_win),
            losing_trades=sum(1 for t in trades if t.is_loss),
            equity_curve=equity_curve,
            returns=returns,
            cumulative_returns=returns.cumsum(),
            total_return=metrics["total_return"],
            annualized_return=metrics["annualized_return"],
            sharpe_ratio=metrics["sharpe_ratio"],
            sortino_ratio=metrics["sortino_ratio"],
            max_drawdown=metrics["max_drawdown"],
            max_drawdown_duration=metrics["max_drawdown_duration"],
            win_rate=metrics["win_rate"],
            profit_factor=metrics["profit_factor"],
            avg_win=metrics["avg_win"],
            avg_loss=metrics["avg_loss"],
            largest_win=metrics["largest_win"],
            largest_loss=metrics["largest_loss"],
            raw_data={
                "equity_data": equity_data,
                "summary": summary,
            },
        )

        logger.info(
            f"Parsed {len(trades)} trades, return: {metrics['total_return']:.2%}"
        )

        return result

    def _parse_trades(self, trades_file: Path) -> List[Trade]:
        """Parse trades.json file."""
        if not trades_file.exists():
            logger.warning(f"Trades file not found: {trades_file}")
            return []

        with open(trades_file, "r") as f:
            data = json.load(f)

        trades = []
        for i, trade_data in enumerate(data.get("trades", [])):
            try:
                trade = Trade(
                    trade_id=trade_data.get("id", i),
                    entry_time=self._parse_timestamp(trade_data.get("entry_time")),
                    exit_time=self._parse_timestamp(trade_data.get("exit_time")),
                    entry_price=float(trade_data.get("entry_price", 0)),
                    exit_price=float(trade_data.get("exit_price", 0)),
                    quantity=float(trade_data.get("quantity", 0)),
                    side=trade_data.get("side", "long").lower(),
                    pnl=float(trade_data.get("pnl", 0)),
                    pnl_pct=float(trade_data.get("pnl_pct", 0)),
                    commission=float(trade_data.get("commission", 0)),
                    slippage=float(trade_data.get("slippage", 0)),
                    reason=trade_data.get("reason", "unknown"),
                    duration_seconds=float(trade_data.get("duration", 0)),
                )
                trades.append(trade)
            except Exception as e:
                logger.warning(f"Failed to parse trade {i}: {e}")
                continue

        return trades

    def _parse_equity(self, equity_file: Path) -> Dict:
        """Parse equity.json file."""
        if not equity_file.exists():
            logger.warning(f"Equity file not found: {equity_file}")
            return {}

        with open(equity_file, "r") as f:
            data = json.load(f)

        return data

    def _parse_summary(self, summary_file: Path) -> Dict:
        """Parse summary.json file."""
        if not summary_file.exists():
            logger.warning(f"Summary file not found: {summary_file}")
            return {}

        with open(summary_file, "r") as f:
            data = json.load(f)

        return data

    def _build_equity_curve(self, trades: List[Trade]) -> Tuple[pd.Series, pd.Series]:
        """
        Build equity curve from trades.

        Args:
            trades: List of trades

        Returns:
            Tuple of (equity_curve, returns)
        """
        if not trades:
            return pd.Series([1.0]), pd.Series([0.0])

        # Sort trades by exit time
        sorted_trades = sorted(trades, key=lambda t: t.exit_time)

        # Build equity curve
        equity = [1.0]  # Start with 1.0 (100%)
        timestamps = [sorted_trades[0].entry_time]

        for trade in sorted_trades:
            # Add equity point after trade
            equity.append(equity[-1] * (1 + trade.pnl_pct))
            timestamps.append(trade.exit_time)

        # Create series
        equity_curve = pd.Series(equity, index=timestamps)

        # Calculate returns
        returns = equity_curve.pct_change().dropna()

        return equity_curve, returns

    def _calculate_metrics(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        trades: List[Trade],
    ) -> Dict:
        """Calculate performance metrics from equity curve and trades."""

        # Basic return metrics
        if len(equity_curve) > 0:
            total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1.0
        else:
            total_return = 0.0

        # Annualized return
        if len(equity_curve) > 1:
            days = (equity_curve.index[-1] - equity_curve.index[0]).days
            years = days / 365.25
            if years > 0:
                annualized_return = (1 + total_return) ** (1 / years) - 1
            else:
                annualized_return = 0
        else:
            annualized_return = 0

        # Sharpe ratio
        if len(returns) > 1 and returns.std() > 0:
            sharpe = returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe = 0

        # Sortino ratio
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 1 and downside_returns.std() > 0:
            sortino = returns.mean() / downside_returns.std() * np.sqrt(252)
        else:
            sortino = 0

        # Max drawdown
        if len(equity_curve) > 1:
            running_max = equity_curve.cummax()
            drawdown = (equity_curve - running_max) / running_max
            max_drawdown = abs(drawdown.min())

            # Drawdown duration
            in_drawdown = drawdown < 0
            if in_drawdown.any():
                # Find longest drawdown period
                drawdown_periods = []
                current_period = 0
                for is_dd in in_drawdown:
                    if is_dd:
                        current_period += 1
                    else:
                        if current_period > 0:
                            drawdown_periods.append(current_period)
                        current_period = 0
                if current_period > 0:
                    drawdown_periods.append(current_period)

                max_drawdown_duration = max(drawdown_periods) if drawdown_periods else 0
            else:
                max_drawdown_duration = 0
        else:
            max_drawdown = 0
            max_drawdown_duration = 0

        # Trade metrics
        if trades:
            winning_trades = [t for t in trades if t.is_win]
            losing_trades = [t for t in trades if t.is_loss]

            win_rate = len(winning_trades) / len(trades)

            total_profit = sum(t.pnl for t in winning_trades)
            total_loss = abs(sum(t.pnl for t in losing_trades))
            profit_factor = total_profit / total_loss if total_loss > 0 else 0

            avg_win = (
                sum(t.pnl for t in winning_trades) / len(winning_trades)
                if winning_trades
                else 0
            )
            avg_loss = (
                sum(t.pnl for t in losing_trades) / len(losing_trades)
                if losing_trades
                else 0
            )

            largest_win = max((t.pnl for t in winning_trades), default=0)
            largest_loss = min((t.pnl for t in losing_trades), default=0)
        else:
            win_rate = 0
            profit_factor = 0
            avg_win = 0
            avg_loss = 0
            largest_win = 0
            largest_loss = 0

        return {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "max_drawdown": max_drawdown,
            "max_drawdown_duration": max_drawdown_duration,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
        }

    def _parse_timestamp(self, timestamp: any) -> datetime:
        """Parse timestamp from various formats."""
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except:
                return datetime.now()
        else:
            return datetime.now()


def parse_backtest_from_directory(output_dir: Path | str) -> BacktestResult:
    """
    Convenience function to parse backtest from directory.

    Args:
        output_dir: Path to PyneCore output directory

    Returns:
        Parsed backtest result
    """
    parser = BacktestParser()
    return parser.parse_backtest_directory(Path(output_dir))


def extract_trades_dataframe(backtest: BacktestResult) -> pd.DataFrame:
    """
    Extract trades as pandas DataFrame.

    Args:
        backtest: Parsed backtest result

    Returns:
        DataFrame with all trades
    """
    return backtest.to_dataframe()


def extract_equity_and_returns(backtest: BacktestResult) -> Tuple[pd.Series, pd.Series]:
    """
    Extract equity curve and returns.

    Args:
        backtest: Parsed backtest result

    Returns:
        Tuple of (equity_curve, returns)
    """
    return backtest.equity_curve, backtest.returns
