"""
Live Trading Service - Manages real-time strategy deployment and execution.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class TradingMode(str, Enum):
    """Trading mode options"""

    PAPER = "paper"  # Simulated trading with fake money
    LIVE = "live"  # Real trading with real money


class PositionSide(str, Enum):
    """Position direction"""

    LONG = "long"
    SHORT = "short"


class OrderStatus(str, Enum):
    """Order status"""

    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class RiskParameters:
    """Risk management parameters"""

    max_position_size: float = 0.02  # 2% of portfolio per trade
    max_daily_loss: float = 0.01  # 1% daily loss limit
    max_drawdown: float = 0.05  # 5% max drawdown before pause
    max_open_positions: int = 3  # Maximum concurrent positions
    enable_stop_loss: bool = True
    stop_loss_pct: float = 0.02  # 2% stop loss
    enable_take_profit: bool = True
    take_profit_pct: float = 0.05  # 5% take profit


@dataclass
class Position:
    """Active trading position"""

    position_id: str
    strategy_id: str
    symbol: str
    side: PositionSide
    entry_price: float
    quantity: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0

    def update_price(self, current_price: float):
        """Update current price and calculate unrealized P&L"""
        self.current_price = current_price
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (current_price - self.entry_price) * self.quantity
            self.unrealized_pnl_pct = (current_price - self.entry_price) / self.entry_price
        else:  # SHORT
            self.unrealized_pnl = (self.entry_price - current_price) * self.quantity
            self.unrealized_pnl_pct = (self.entry_price - current_price) / self.entry_price


@dataclass
class Trade:
    """Completed trade record"""

    trade_id: str
    strategy_id: str
    symbol: str
    side: PositionSide
    entry_price: float
    exit_price: float
    quantity: float
    entry_time: datetime
    exit_time: datetime
    pnl: float
    pnl_pct: float
    commission: float = 0.0
    reason: str = "signal"  # signal, stop_loss, take_profit, manual


@dataclass
class DeploymentConfig:
    """Configuration for deploying a strategy"""

    deployment_id: str
    strategy_id: str
    strategy_name: str
    mode: TradingMode
    symbols: List[str]
    timeframe: str
    risk_params: RiskParameters
    exchange: str = "binance"
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    testnet: bool = True


@dataclass
class DeploymentStatus:
    """Current status of a deployed strategy"""

    deployment_id: str
    strategy_id: str
    strategy_name: str
    mode: TradingMode
    status: str  # active, paused, stopped, error
    start_time: datetime
    uptime_seconds: float = 0.0

    # Performance metrics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    win_rate: float = 0.0

    # Current state
    open_positions: int = 0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0

    # Risk metrics
    current_drawdown: float = 0.0
    max_drawdown: float = 0.0

    # Errors
    last_error: Optional[str] = None
    error_count: int = 0


class LiveTradingService:
    """
    Manages live trading deployments.

    Features:
    - Deploy strategies to live/paper trading
    - Monitor positions in real-time
    - Apply risk management
    - Track performance
    - Emergency stop functionality
    """

    def __init__(self):
        self.deployments: Dict[str, DeploymentConfig] = {}
        self.deployment_status: Dict[str, DeploymentStatus] = {}
        self.positions: Dict[str, List[Position]] = {}  # deployment_id -> positions
        self.trade_history: Dict[str, List[Trade]] = {}  # deployment_id -> trades
        self.running_tasks: Dict[str, asyncio.Task] = {}

    async def deploy_strategy(
        self,
        strategy_id: str,
        strategy_name: str,
        mode: TradingMode,
        symbols: List[str],
        timeframe: str,
        risk_params: RiskParameters,
        exchange: str = "binance",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
    ) -> str:
        """
        Deploy a strategy for live/paper trading.

        Returns:
            deployment_id: Unique identifier for this deployment
        """
        deployment_id = str(uuid4())

        config = DeploymentConfig(
            deployment_id=deployment_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            mode=mode,
            symbols=symbols,
            timeframe=timeframe,
            risk_params=risk_params,
            exchange=exchange,
            api_key=api_key,
            api_secret=api_secret,
            testnet=testnet,
        )

        status = DeploymentStatus(
            deployment_id=deployment_id,
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            mode=mode,
            status="active",
            start_time=datetime.now(),
        )

        self.deployments[deployment_id] = config
        self.deployment_status[deployment_id] = status
        self.positions[deployment_id] = []
        self.trade_history[deployment_id] = []

        # Start trading loop
        task = asyncio.create_task(self._trading_loop(deployment_id))
        self.running_tasks[deployment_id] = task

        logger.info(f"Deployed strategy {strategy_name} (ID: {deployment_id}) in {mode} mode")
        return deployment_id

    async def stop_deployment(self, deployment_id: str, reason: str = "user_requested"):
        """Stop a deployment and close all positions"""
        if deployment_id not in self.deployments:
            raise ValueError(f"Deployment {deployment_id} not found")

        # Cancel trading task
        if deployment_id in self.running_tasks:
            self.running_tasks[deployment_id].cancel()
            try:
                await self.running_tasks[deployment_id]
            except asyncio.CancelledError:
                pass
            del self.running_tasks[deployment_id]

        # Close all open positions
        positions = self.positions.get(deployment_id, [])
        for pos in positions[:]:  # Copy list to avoid modification during iteration
            await self._close_position(deployment_id, pos.position_id, reason=reason)

        # Update status
        if deployment_id in self.deployment_status:
            self.deployment_status[deployment_id].status = "stopped"

        logger.info(f"Stopped deployment {deployment_id}: {reason}")

    async def emergency_stop_all(self):
        """Emergency stop - close all deployments immediately"""
        logger.warning("EMERGENCY STOP TRIGGERED - Closing all positions")

        deployment_ids = list(self.deployments.keys())
        for deployment_id in deployment_ids:
            await self.stop_deployment(deployment_id, reason="emergency_stop")

    def get_deployment_status(self, deployment_id: str) -> Optional[DeploymentStatus]:
        """Get current status of a deployment"""
        return self.deployment_status.get(deployment_id)

    def get_all_deployments(self) -> List[DeploymentStatus]:
        """Get status of all active deployments"""
        return list(self.deployment_status.values())

    def get_positions(self, deployment_id: str) -> List[Position]:
        """Get open positions for a deployment"""
        return self.positions.get(deployment_id, [])

    def get_trade_history(self, deployment_id: str, limit: int = 100) -> List[Trade]:
        """Get trade history for a deployment"""
        trades = self.trade_history.get(deployment_id, [])
        return sorted(trades, key=lambda t: t.exit_time, reverse=True)[:limit]

    async def _trading_loop(self, deployment_id: str):
        """Main trading loop for a deployment"""
        status = self.deployment_status[deployment_id]

        logger.info(f"Starting trading loop for {deployment_id}")

        try:
            while True:
                # Update uptime
                status.uptime_seconds = (datetime.now() - status.start_time).total_seconds()

                # Check risk limits
                if not self._check_risk_limits(deployment_id):
                    logger.warning(f"Risk limits exceeded for {deployment_id}, pausing")
                    status.status = "paused"
                    await asyncio.sleep(60)  # Wait before retry
                    continue

                # Generate signals (placeholder - would call actual strategy)
                # signal = await self._generate_signal(config)

                # For now, just update positions
                await self._update_positions(deployment_id)

                # Check for exit conditions
                await self._check_exit_conditions(deployment_id)

                # Sleep before next iteration
                await asyncio.sleep(1)  # 1 second for real-time responsiveness

        except asyncio.CancelledError:
            logger.info(f"Trading loop cancelled for {deployment_id}")
            raise
        except Exception as e:
            logger.error(f"Error in trading loop for {deployment_id}: {e}")
            status.status = "error"
            status.last_error = str(e)
            status.error_count += 1

    def _check_risk_limits(self, deployment_id: str) -> bool:
        """Check if risk limits are within bounds"""
        config = self.deployments[deployment_id]
        status = self.deployment_status[deployment_id]
        risk = config.risk_params

        # Check daily loss limit
        if abs(status.daily_pnl_pct) > risk.max_daily_loss:
            logger.warning(f"Daily loss limit exceeded: {status.daily_pnl_pct:.2%}")
            return False

        # Check max drawdown
        if abs(status.current_drawdown) > risk.max_drawdown:
            logger.warning(f"Max drawdown exceeded: {status.current_drawdown:.2%}")
            return False

        # Check max open positions
        if status.open_positions >= risk.max_open_positions:
            logger.debug(f"Max open positions reached: {status.open_positions}")
            return False

        return True

    async def _update_positions(self, deployment_id: str):
        """Update current prices and P&L for all positions"""
        positions = self.positions.get(deployment_id, [])

        for pos in positions:
            # Simulate price update (in real implementation, fetch from exchange)
            # pos.update_price(current_market_price)
            pass

    async def _check_exit_conditions(self, deployment_id: str):
        """Check if any positions should be closed"""
        config = self.deployments[deployment_id]
        positions = self.positions.get(deployment_id, [])

        for pos in positions[:]:  # Copy to avoid modification during iteration
            # Check stop loss
            if config.risk_params.enable_stop_loss and pos.stop_loss:
                if pos.current_price <= pos.stop_loss:
                    await self._close_position(deployment_id, pos.position_id, reason="stop_loss")
                    continue

            # Check take profit
            if config.risk_params.enable_take_profit and pos.take_profit:
                if pos.current_price >= pos.take_profit:
                    await self._close_position(deployment_id, pos.position_id, reason="take_profit")
                    continue

    async def _close_position(self, deployment_id: str, position_id: str, reason: str = "signal"):
        """Close a position and record the trade"""
        positions = self.positions.get(deployment_id, [])
        position = next((p for p in positions if p.position_id == position_id), None)

        if not position:
            return

        # Remove from active positions
        positions.remove(position)

        # Create trade record
        trade = Trade(
            trade_id=str(uuid4()),
            strategy_id=position.strategy_id,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=position.current_price,
            quantity=position.quantity,
            entry_time=position.entry_time,
            exit_time=datetime.now(),
            pnl=position.unrealized_pnl,
            pnl_pct=position.unrealized_pnl_pct,
            reason=reason,
        )

        # Add to history
        if deployment_id not in self.trade_history:
            self.trade_history[deployment_id] = []
        self.trade_history[deployment_id].append(trade)

        # Update status
        status = self.deployment_status[deployment_id]
        status.total_trades += 1
        status.total_pnl += trade.pnl
        status.total_pnl_pct += trade.pnl_pct
        status.open_positions = len(positions)

        if trade.pnl > 0:
            status.winning_trades += 1
        else:
            status.losing_trades += 1

        status.win_rate = status.winning_trades / status.total_trades if status.total_trades > 0 else 0.0

        logger.info(f"Closed position {position_id}: {trade.pnl:.2f} ({trade.pnl_pct:.2%}) - {reason}")


# Global instance
live_trading_service = LiveTradingService()
