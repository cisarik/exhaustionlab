from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from random import Random
from typing import Dict, Iterable, Tuple

import numpy as np
import pandas as pd

from ..config.fitness_config import get_fitness_config
from ..config.indicator_params import SQUEEZE_PARAM_SPECS, save_squeeze_params, squeeze_param_bounds
from ..data.binance_rest import fetch_klines_csv_like
from ..meta_evolution import EvolutionDirective, EvolutionIntensity, IntelligentOrchestrator, LiveTradingValidator, MarketFocus, MetaevolutionConfig, MetaStrategyType
from .engine import run_pyne
from .indicators import compute_squeeze_momentum
from .llm_evolution import LLMStrategyMutator, RobustStrategyEvolutionEngine
from .multi_market_evaluator import MultiMarketEvaluator
from .strategy_registry import StrategyRegistry

# Fallback traditional GA systems


@dataclass
class GASettings:
    population: int = 24
    generations: int = 20
    mutation_rate: float = 0.2
    crossover_rate: float = 0.8
    elite: int = 2


def load_history(csv_path: Path | None, symbol: str, interval: str, limit: int) -> pd.DataFrame:
    if csv_path and csv_path.exists():
        df = pd.read_csv(csv_path)
        if "ts_open" not in df:
            raise ValueError("CSV must contain ts_open column")
        return df
    df = fetch_klines_csv_like(symbol=symbol, interval=interval, limit=limit)
    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(csv_path, index=False)
    return df


class GeneticSqueezeOptimizer:
    def __init__(self, df: pd.DataFrame, settings: GASettings, rng: Random | None = None):
        if df.empty:
            raise ValueError("DataFrame is empty")
        self.df = df.reset_index(drop=True)
        self.settings = settings
        self.bounds = squeeze_param_bounds()
        self.specs = {spec.name: spec for spec in SQUEEZE_PARAM_SPECS}
        self.rng = rng or Random()

    def random_candidate(self) -> Dict[str, float | int | bool]:
        sample = {}
        for spec in SQUEEZE_PARAM_SPECS:
            lo, hi, step = self.bounds[spec.name]
            if spec.kind == "bool":
                sample[spec.name] = bool(self.rng.getrandbits(1))
            elif spec.kind == "int":
                sample[spec.name] = int(self.rng.randrange(int(lo), int(hi) + 1, int(step)))
            else:
                sample[spec.name] = round(self.rng.uniform(float(lo), float(hi)), 6)
        return sample

    def evaluate(self, params: Dict[str, float | int | bool]) -> float:
        sqz = compute_squeeze_momentum(self.df, **params)
        hist = sqz["value"]
        positions = np.where(hist > 0, 1, np.where(hist < 0, -1, 0))
        positions = pd.Series(positions, index=self.df.index)
        positions = positions.replace(0, np.nan).ffill().fillna(0.0)
        returns = self.df["close"].pct_change().fillna(0.0)
        pnl = positions.shift(1).fillna(0.0) * returns
        equity = (1 + pnl).cumprod()
        if equity.empty:
            return -np.inf
        max_drawdown = (equity.cummax() - equity).max()
        sharpe = 0.0
        std = pnl.std()
        if std > 1e-9:
            sharpe = (pnl.mean() / std) * np.sqrt(len(pnl))
        fitness = float(equity.iloc[-1]) - (max_drawdown or 0.0) + 0.1 * sharpe
        return fitness

    def select_parent(self, population: Iterable[Tuple[Dict[str, float | int | bool], float]]) -> Dict[str, float | int | bool]:
        contenders = self.rng.sample(list(population), k=min(3, len(population)))
        return max(contenders, key=lambda item: item[1])[0]

    def crossover(self, a: Dict[str, float | int | bool], b: Dict[str, float | int | bool]) -> Dict[str, float | int | bool]:
        child = {}
        for key in a.keys():
            if self.rng.random() < 0.5:
                child[key] = a[key]
            else:
                child[key] = b[key]
        return child

    def mutate(self, candidate: Dict[str, float | int | bool]):
        for spec in SQUEEZE_PARAM_SPECS:
            if self.rng.random() > self.settings.mutation_rate:
                continue
            lo, hi, step = self.bounds[spec.name]
            if spec.kind == "bool":
                candidate[spec.name] = not bool(candidate[spec.name])
            elif spec.kind == "int":
                delta = self.rng.choice([-1, 1]) * int(step)
                candidate[spec.name] = int(max(lo, min(hi, candidate[spec.name] + delta)))
            else:
                span = hi - lo
                delta = self.rng.uniform(-0.1 * span, 0.1 * span)
                candidate[spec.name] = float(max(lo, min(hi, candidate[spec.name] + delta)))

    def run(self) -> Tuple[Dict[str, float | int | bool], float]:
        population = [self.random_candidate() for _ in range(self.settings.population)]
        scored = [(cand, self.evaluate(cand)) for cand in population]
        best = max(scored, key=lambda item: item[1])

        for gen in range(self.settings.generations):
            scored.sort(key=lambda item: item[1], reverse=True)
            new_population = [cand for cand, _ in scored[: self.settings.elite]]
            while len(new_population) < self.settings.population:
                parent_pool = scored[: max(4, self.settings.population // 2)]
                p1 = self.select_parent(parent_pool)
                p2 = self.select_parent(parent_pool)
                if self.rng.random() < self.settings.crossover_rate:
                    child = self.crossover(p1, p2)
                else:
                    child = dict(p1)
                self.mutate(child)
                new_population.append(child)
            scored = [(cand, self.evaluate(cand)) for cand in new_population]
            gen_best = max(scored, key=lambda item: item[1])
            if gen_best[1] > best[1]:
                best = gen_best
            print(f"[GA] Generation {gen+1}/{self.settings.generations} best fitness={gen_best[1]:.6f}")
        return best


def main():
    parser = argparse.ArgumentParser(description="Genetic optimizer for Squeeze Momentum parameters.")
    parser.add_argument(
        "--csv",
        type=Path,
        help="Historical CSV (ts_open,...). If missing, fetches via REST.",
    )
    parser.add_argument("--symbol", default="ADAEUR")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--limit", type=int, default=1500)
    parser.add_argument("--population", type=int, default=24)
    parser.add_argument("--generations", type=int, default=15)
    parser.add_argument("--mutation", type=float, default=0.2)
    parser.add_argument("--crossover", type=float, default=0.8)
    parser.add_argument("--elite", type=int, default=2)
    parser.add_argument("--seed", type=int, help="Optional RNG seed for reproducibility.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist best params to squeeze_params.json",
    )
    parser.add_argument(
        "--pyne-ohlcv",
        type=Path,
        help="Optional: run PyneCore on this .ohlcv with GA params.",
    )
    parser.add_argument(
        "--pyne-script",
        default="scripts/pyne/exhaustion_signal",
        help="PyneCore script to run when --pyne-ohlcv is provided.",
    )
    parser.add_argument("--pyne-bin", help="Override Pyne executable (default: 'pyne').")
    parser.add_argument("--pyne-timeout", type=int, default=300, help="Timeout for Pyne CLI (seconds).")

    # LLM Evolution options
    parser.add_argument(
        "--llm-evolution",
        action="store_true",
        help="Run LLM-based strategy evolution instead of parameter GA",
    )
    parser.add_argument(
        "--population-size",
        type=int,
        default=8,
        help="Population size for LLM evolution",
    )
    parser.add_argument(
        "--generations",
        type=int,
        default=10,
        help="Number of generations for LLM evolution",
    )
    parser.add_argument(
        "--elite-size",
        type=int,
        default=2,
        help="Number of elite strategies to preserve",
    )
    parser.add_argument(
        "--mutation-rate",
        type=float,
        default=0.3,
        help="Mutation rate for LLM evolution",
    )
    parser.add_argument(
        "--fitness-preset",
        default="BALANCED_DEMO",
        choices=[
            "AGGRESSIVE_DEMO",
            "BALANCED_RESEARCH",
            "CONSERVATIVE_PRODUCTION",
            "LIVE_TRADING_PRODUCTION",
        ],
        help="Fitness configuration preset for LLM evolution",
    )

    # Meta-evolution options
    parser.add_argument(
        "--meta-evolution",
        action="store_true",
        help="Enable advanced meta-evolution with intelligent orchestration",
    )
    parser.add_argument(
        "--strategy-type",
        default="HYBRID",
        choices=[t.value for t in MetaStrategyType],
        help="Meta-strategy type for intelligent generation",
    )
    parser.add_argument(
        "--market-focus",
        default="spot_crypto",
        choices=[m.value for m in MarketFocus],
        help="Market focus for strategy specialization",
    )
    parser.add_argument(
        "--evolution-intensity",
        default="BALANCED",
        choices=[i.value for i in EvolutionIntensity],
        help="Evolution intensity - exploration vs exploitation balance",
    )
    parser.add_argument(
        "--web-examples",
        action="store_true",
        help="Extract strategy examples from web for LLM context",
    )
    parser.add_argument(
        "--production-validation",
        action="store_true",
        help="Apply institutional-grade live trading validation",
    )
    parser.add_argument(
        "--intelligence",
        type=float,
        default=0.8,
        help="LLM creativity level (0.1-1.0, higher = more creative)",
    )

    args = parser.parse_args()

    df = load_history(args.csv, args.symbol, args.interval, args.limit)
    print(f"[GA] Loaded {len(df)} rows for {args.symbol} {args.interval}")

    if args.meta_evolution:
        # Advanced meta-evolution with intelligent orchestration
        print("[GA] Starting META-EVOLUTION with DeepSeek AI...")
        print(f"[GA] Strategy Type: {args.strategy_type}")
        print(f"[GA] Market Focus: {args.market_focus}")
        print(f"[GA] Evolution Intensity: {args.evolution_intensity}")
        print(f"[GA] Intelligence Level: {args.intelligence}")

        # Save data temp
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".ohlcv", delete=False) as f:
            df.to_csv(f.name, index=False)
            data_path = Path(f.name)

        try:
            # Initialize meta-evolution components
            meta_config = MetaevolutionConfig()
            fitness_config = get_fitness_config(args.fitness_preset)

            # Extract web examples if requested
            if args.web_examples:
                print("[GA] Extracting strategy examples from web...")
                from ..meta_evolution import StrategyWebCrawler

                crawler = StrategyWebCrawler()
                examples = crawler.extract_strategy_examples(max_examples=20)
                print(f"[GA] Extracted {len(examples)} high-quality examples")
                crawler.save_extracted_examples(examples)

            # Create evolution directive
            directive = EvolutionDirective(
                strategy_type=MetaStrategyType(args.strategy_type),
                market_focus=MarketFocus(args.market_focus),
                evolution_phase="balanced",  # Balanced approach
                performance_targets={
                    "min_sharpe": fitness_config.thresholds.min_sharpe_ratio,
                    "max_drawdown": fitness_config.thresholds.max_drawdown,
                    "win_rate": fitness_config.thresholds.min_win_rate,
                },
                risk_tolerance="conservative",
                time_horizon="swing",
                capital_constraints={"max_trades_per_day": 50},
            )

            # Set meta-parameters
            meta_params = meta_config.create_evolution_config(
                directive.strategy_type,
                directive.market_focus,
                EvolutionIntensity(args.evolution_intensity),
            )

            # Adjust for intelligence level
            meta_params.prompt_style = "creative" if args.intelligence > 0.7 else "quantitative"
            meta_params.domain_knowledge_depth = "advanced" if args.intelligence > 0.5 else "intermediate"

            # Initialize intelligent orchestrator
            llm_mutator = LLMStrategyMutator()
            if not llm_mutator.llm_available:
                print("[GA] ❌ LLM not available - meta-evolution requires LLM connection")
                return

            orchestrator = IntelligentOrchestrator(llm_mutator.client, meta_config)
            validator = LiveTradingValidator()

            # Generate intelligent strategy
            print("[GA] Creating intelligent strategy...")
            strategy_genome = orchestrator.generate_intelligent_strategy(directive)

            if not strategy_genome:
                print("[GA] ❌ Failed to generate strategy")
                return

            print(f"[GA] ✅ Generated strategy: {strategy_genome.name}")

            # Production validation if requested
            validation_results = None
            if args.production_validation:
                print("[GA] Running institutional-grade validation...")

                # Create synthetic backtest data for validation (in real implementation, use actual backtest)
                synthetic_backtest = df.copy()
                synthetic_backtest["returns"] = df["close"].pct_change().fillna(0)

                validation_results = validator.validate_strategy_for_live_trading(
                    strategy_genome.pyne_code,
                    synthetic_backtest,
                    directive.strategy_type,
                    directive.market_focus,
                )

                score = validation_results["metrics"].live_trading_score
                print(f"[GA] Live Trading Score: {score:.1f}/100")
                print(f"[GA] Ready for Live Trading: {'YES' if validation_results['is_live_trading_ready'] else 'NO'}")

                # Save validation results
                if args.apply:
                    validator.save_validation_results(validation_results, strategy_genome.name)

                # Display key metrics
                if validation_results["is_live_trading_ready"]:
                    print("[GA] 🎉 STRATEGY READY FOR LIVE DEPLOYMENT!")
                    print(f"[GA] Expected Sharpe: {validation_results['metrics'].sharpe_ratio:.2f}")
                    print(f"[GA] Expected Win Rate: {validation_results['metrics'].win_rate:.1%}")
                    print(f"[GA] Drawdown Risk: {validation_results['metrics'].max_drawdown:.1%}")
                else:
                    print("[GA] ⚠️ Strategy needs improvements:")
                    for issue in validation_results["issues"]:
                        print(f"[GA]   - {issue}")

            # Save final strategy
            if args.apply:
                output_dir = Path("/home/agile/ExhaustionLab/evolved_strategies")
                output_dir.mkdir(exist_ok=True)

                strategy_file = output_dir / f"{strategy_genome.name}_production.py"
                with open(strategy_file, "w") as f:
                    f.write(strategy_genome.pyne_code)

                config_file = output_dir / f"{strategy_genome.name}_config.json"
                config_data = {
                    "strategy_name": strategy_genome.name,
                    "description": strategy_genome.description,
                    "parameters": strategy_genome.parameters,
                    "directive": asdict(directive),
                    "validation": validation_results,
                }
                with open(config_file, "w") as f:
                    json.dump(config_data, f, indent=2, default=str)

                print(f"[GA] Saved production-ready strategy to: {strategy_file}")

        finally:
            if data_path.exists():
                data_path.unlink()

        return

    elif args.llm_evolution:
        # Traditional LLM-based strategy evolution
        print("[GA] Starting LLM-based strategy evolution...")

        # Save data temp for PyneCore
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ohlcv", delete=False) as f:
            df.to_csv(f.name, index=False)
            data_path = Path(f.name)

        try:
            llm_mutator = LLMStrategyMutator()

            # Initialize fitness config
            fitness_config = get_fitness_config(args.fitness_preset)
            print(f"[GA] Using preset: {args.fitness_preset}")

            # Initialize components
            registry = StrategyRegistry()
            market_evaluator = MultiMarketEvaluator(registry)

            # Create robust evolution engine
            engine = RobustStrategyEvolutionEngine(llm_mutator, registry, market_evaluator, fitness_config)

            # Run async evolution
            def run_evolution():
                return engine.run_evolution(generations=args.generations, population_size=args.population_size)

            # Use asyncio to run the async function
            import asyncio

            evolution_results = asyncio.run(run_evolution())

            print("\n[GA] LLM Evolution complete!")
            print(f"[GA] Generations: {evolution_results['generations_completed']}")
            print(f"[GA] Best fitness: {evolution_results['best_fitness']:.4f}")
            print(f"[GA] Deployment-ready: {evolution_results['final_deployment_ready']} strategies")

            if args.apply and evolution_results["deployment_ready_strategies"]:
                # Save deployment-ready strategies
                output_dir = Path("/home/agile/ExhaustionLab/evolved_strategies")
                output_dir.mkdir(exist_ok=True)

                for strategy in evolution_results["deployment_ready_strategies"][:3]:
                    with open(output_dir / f"{strategy['name']}.py", "w") as f:
                        f.write(strategy["pyne_code"])

                print(f"[GA] Saved top {len(evolution_results['deployment_ready_strategies'])} strategies to {output_dir}")

        finally:
            # Cleanup temp file
            if data_path.exists():
                data_path.unlink()

        return

    # Traditional parameter-based GA
    settings = GASettings(
        population=args.population,
        generations=args.generations,
        mutation_rate=args.mutation,
        crossover_rate=args.crossover,
        elite=args.elite,
    )
    rng = Random(args.seed) if args.seed is not None else Random()
    optimizer = GeneticSqueezeOptimizer(df, settings, rng=rng)
    params, fitness = optimizer.run()
    print("[GA] Best parameters:")
    for k, v in params.items():
        print(f"    {k}: {v}")
    print(f"[GA] Best fitness: {fitness:.6f}")
    if args.apply:
        save_squeeze_params(params)
        print("[GA] Saved params -> app/config/squeeze_params.json")
    if args.pyne_ohlcv:
        try:
            pyne_params = {k: _format_param_value(v) for k, v in params.items()}
            result = run_pyne(
                str(args.pyne_ohlcv),
                script_name=args.pyne_script,
                params=pyne_params,
                pyne_executable=args.pyne_bin,
                timeout=args.pyne_timeout,
            )
            print(f"[GA] PyneCore run finished -> {result.output_dir}")
        except Exception as exc:
            print(f"[GA] PyneCore run failed: {exc}")


def _format_param_value(value: float | int | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


if __name__ == "__main__":
    main()
