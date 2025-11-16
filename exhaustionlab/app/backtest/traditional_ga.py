"""
Traditional Genetic Algorithm (Fallback)

Fallback GA system that works without the LLM stack. The implementation is
intentionally lightweight—its primary goal is to provide a deterministic code
path for tests and emergency parameter tuning.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from ..config.indicator_params import save_squeeze_params
from ..data.binance_rest import fetch_klines_csv_like
from .traditional_genetics import TraditionalGenetics


def load_history(
    csv_path: Path | None, symbol: str, interval: str, limit: int
) -> pd.DataFrame:
    """Load market history from CSV or Binance REST helper."""
    if csv_path and csv_path.exists():
        df = pd.read_csv(csv_path)
        if "close" not in df:
            raise ValueError("CSV must contain standard OHLC columns")
        return df
    df = fetch_klines_csv_like(symbol=symbol, interval=interval, limit=limit)
    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
    return df


def calculate_traditional_fitness(params: Dict, returns: pd.Series) -> float:
    """Very simple risk-adjusted fitness function."""
    if returns.empty:
        return -float("inf")

    # Build naive long/short signals from a moving average crossover using params
    fast = int(params.get("length_bb", 20))
    slow = int(params.get("length_kc", 40))

    fast_ma = returns.rolling(max(3, fast)).mean()
    slow_ma = returns.rolling(max(5, slow)).mean()
    signal = (fast_ma > slow_ma).astype(float).replace(0, -1.0)

    pnl = signal.shift(1).fillna(0.0) * returns
    cumulative = (1 + pnl).cumprod()
    max_drawdown = (cumulative.cummax() - cumulative).max()
    sharpe = 0.0
    std = pnl.std()
    if std > 1e-9:
        sharpe = (pnl.mean() / std) * (len(pnl) ** 0.5)

    return float(cumulative.iloc[-1]) - (max_drawdown or 0.0) + 0.1 * sharpe


def run_traditional_ga(args):
    """Run traditional genetic algorithm without LLM integration."""
    print("[TRADITIONAL_GA] Starting fallback GA optimization...")

    df = load_history(
        getattr(args, "csv", None), args.symbol, args.interval, args.limit
    )
    returns = df["close"].pct_change().fillna(0.0).to_frame("returns")

    genetics = TraditionalGenetics()
    best_params, best_fitness = genetics.evolve_parameters(
        returns,
        population_size=args.population,
        generations=args.generations,
        mutation_rate=args.mutation,
        elite=max(1, args.elite),
        fitness_func=lambda params, data: calculate_traditional_fitness(
            params, data["returns"]
        ),
    )

    if getattr(args, "apply", False):
        save_squeeze_params(best_params)
        print("[TRADITIONAL_GA] Applied best parameters to squeeze_params.json")

    print(
        f"[TRADITIONAL_GA] Complete. Best fitness={best_fitness:.4f} "
        f"params={best_params}"
    )
    return True
