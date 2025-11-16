"""
Demo Data Generator - Creates preset strategies with good metrics for UX
"""

from datetime import datetime, timedelta
import random
from typing import List, Dict, Any


def generate_demo_strategies(count: int = 8) -> List[Dict[str, Any]]:
    """Generate demo strategies with realistic good metrics"""

    strategy_names = [
        "Momentum Reversal Pro",
        "Volatility Breakout Elite",
        "RSI Divergence Hunter",
        "MACD Cross Advanced",
        "Bollinger Squeeze Master",
        "EMA Crossover Turbo",
        "Support Resistance Sniper",
        "Volume Profile Trader",
        "Fibonacci Retracement Pro",
        "Stochastic Momentum",
        "Ichimoku Cloud Strategy",
        "Keltner Channel Breakout",
    ]

    sources = ["llm_generated", "github", "tradingview", "hybrid"]

    strategies = []

    for i in range(min(count, len(strategy_names))):
        # Generate good metrics (biased towards profitable)
        fitness = random.uniform(0.65, 0.92)
        sharpe = random.uniform(1.5, 3.2)
        max_dd = random.uniform(0.08, 0.18)
        win_rate = random.uniform(0.58, 0.75)
        total_trades = random.randint(80, 250)
        profit_factor = random.uniform(1.5, 2.8)

        # Calculate derived metrics
        winning_trades = int(total_trades * win_rate)
        losing_trades = total_trades - winning_trades
        total_return = random.uniform(0.15, 0.45)  # 15-45% return

        strategy = {
            "strategy_id": f"demo-{i+1:03d}",
            "name": strategy_names[i],
            "description": f"AI-generated strategy with {sharpe:.1f} Sharpe ratio",
            "fitness": fitness,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "profit_factor": profit_factor,
            "total_return": total_return,
            "total_return_pct": total_return * 100,
            "source": random.choice(sources),
            "generation": random.randint(1, 10),
            "created_at": (
                datetime.now() - timedelta(days=random.randint(1, 30))
            ).isoformat(),
            "tags": ["momentum", "reversal", "profitable"],
            "code": f"# {strategy_names[i]} Strategy Code\n# Sharpe: {sharpe:.2f}, Win Rate: {win_rate*100:.1f}%\n\n# This is demo code\npass",
            "backtest_period": "30 days",
            "symbols_tested": ["ADAEUR", "BTCUSDT", "ETHUSDT"],
        }

        strategies.append(strategy)

    # Sort by fitness descending
    strategies.sort(key=lambda x: x["fitness"], reverse=True)

    return strategies


def generate_demo_backtest_result(strategy_id: str) -> Dict[str, Any]:
    """Generate realistic backtest result"""

    # Generate trade data points
    num_trades = random.randint(80, 200)
    trades = []

    entry_price = 100.0
    equity = 10000.0
    equity_curve = [(0, equity)]

    for i in range(num_trades):
        # Biased towards winning
        is_win = random.random() < 0.62

        if is_win:
            pnl_pct = random.uniform(0.01, 0.08)  # 1-8% gain
        else:
            pnl_pct = random.uniform(-0.05, -0.01)  # 1-5% loss

        exit_price = entry_price * (1 + pnl_pct)
        quantity = equity * 0.02 / entry_price  # 2% position size
        pnl = (exit_price - entry_price) * quantity

        equity += pnl
        equity_curve.append((i + 1, equity))

        trade = {
            "trade_id": i + 1,
            "entry_time": (
                datetime.now() - timedelta(days=30 - i * 30 / num_trades)
            ).isoformat(),
            "exit_time": (
                datetime.now()
                - timedelta(days=30 - i * 30 / num_trades)
                + timedelta(hours=random.randint(1, 48))
            ).isoformat(),
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "side": random.choice(["long", "short"]),
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "reason": random.choice(["signal", "take_profit", "stop_loss"]),
        }

        trades.append(trade)

        # Update entry price for next trade
        entry_price = exit_price

    # Calculate summary metrics
    winning = [t for t in trades if t["pnl"] > 0]
    losing = [t for t in trades if t["pnl"] <= 0]

    total_pnl = sum(t["pnl"] for t in trades)
    win_rate = len(winning) / len(trades) if trades else 0

    avg_win = sum(t["pnl"] for t in winning) / len(winning) if winning else 0
    avg_loss = abs(sum(t["pnl"] for t in losing) / len(losing)) if losing else 1
    profit_factor = (
        (sum(t["pnl"] for t in winning) / abs(sum(t["pnl"] for t in losing)))
        if losing
        else 0
    )

    # Calculate max drawdown
    peak = equity_curve[0][1]
    max_dd = 0
    for _, eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak
        if dd > max_dd:
            max_dd = dd

    return {
        "strategy_id": strategy_id,
        "start_equity": 10000,
        "end_equity": equity,
        "total_return": (equity - 10000) / 10000,
        "total_return_pct": ((equity - 10000) / 10000) * 100,
        "total_trades": len(trades),
        "winning_trades": len(winning),
        "losing_trades": len(losing),
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "max_drawdown": max_dd,
        "sharpe_ratio": random.uniform(1.5, 3.0),
        "trades": trades[-50:],  # Last 50 trades for display
        "equity_curve": equity_curve,
        "period": "30 days",
        "symbol": "ADAEUR",
        "timeframe": "1m",
    }


def get_quick_start_presets() -> List[Dict[str, Any]]:
    """Get quick-start paper trading presets"""
    return [
        {
            "name": "Conservative Starter",
            "description": "Low risk, steady gains - perfect for beginners",
            "risk": {
                "max_position_size": 0.01,  # 1%
                "max_daily_loss": 0.005,  # 0.5%
                "max_drawdown": 0.03,  # 3%
                "enable_stop_loss": True,
                "stop_loss_pct": 0.015,  # 1.5%
                "enable_take_profit": True,
                "take_profit_pct": 0.03,  # 3%
            },
            "expected": {
                "daily_return": "0.2-0.5%",
                "max_risk": "Low",
                "style": "Conservative",
            },
        },
        {
            "name": "Balanced Growth",
            "description": "Moderate risk, good returns - recommended for most users",
            "risk": {
                "max_position_size": 0.02,  # 2%
                "max_daily_loss": 0.01,  # 1%
                "max_drawdown": 0.05,  # 5%
                "enable_stop_loss": True,
                "stop_loss_pct": 0.02,  # 2%
                "enable_take_profit": True,
                "take_profit_pct": 0.05,  # 5%
            },
            "expected": {
                "daily_return": "0.5-1.5%",
                "max_risk": "Medium",
                "style": "Balanced",
            },
        },
        {
            "name": "Aggressive Trader",
            "description": "Higher risk, maximum gains - for experienced traders",
            "risk": {
                "max_position_size": 0.05,  # 5%
                "max_daily_loss": 0.02,  # 2%
                "max_drawdown": 0.10,  # 10%
                "enable_stop_loss": True,
                "stop_loss_pct": 0.03,  # 3%
                "enable_take_profit": True,
                "take_profit_pct": 0.08,  # 8%
            },
            "expected": {
                "daily_return": "1.5-3.0%",
                "max_risk": "High",
                "style": "Aggressive",
            },
        },
    ]


def generate_overview_metrics() -> Dict[str, Any]:
    """Generate overview metrics with good numbers"""
    return {
        "total_strategies": 8,
        "avg_fitness": 0.78,
        "best_fitness": 0.92,
        "total_backtests": 45,
        "active_deployments": 0,
        "total_trades_today": 0,
        "daily_pnl": 0.0,
        "evolution_velocity": 0.15,
    }
