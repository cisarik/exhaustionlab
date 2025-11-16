"""
LLM-based Strategy Evolution Framework

Evolves complete trading strategies using LLM-coded mutations
instead of just parameter optimization. Integrates with PyneCore
for backtesting evaluation.
"""

from __future__ import annotations

import json
import subprocess
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random
import asyncio

import pandas as pd

from .engine import run_pyne
from .strategy_registry import StrategyRegistry, StrategyMetrics
from .multi_market_evaluator import MultiMarketEvaluator
from .strategy_genome import StrategyGenome
from ..config.fitness_config import GlobalFitnessConfig, get_fitness_config


class LLMStrategyMutator:
    """Real LLM-based mutation of trading strategies using local DeepSeek API."""

    def __init__(
        self,
        llm_endpoint: str = "http://127.0.0.1:1234",
        model_name: str = "deepseek/deepseek-r1-0528-qwen3-8b",
    ):
        try:
            # Import LLM components
            from ..llm import LocalLLMClient, LLMStrategyGenerator, PromptContext

            # Initialize LLM client
            self.client = LocalLLMClient(base_url=llm_endpoint, model_name=model_name)

            # Check connection
            if not self.client.test_connection():
                print("LLM connection failed, falling back to simple mutations")
                self.use_fallback = True
                self.llm_available = False
            else:
                self.use_fallback = False
                self.llm_available = True
                print(f"✅ Connected to LLM at {llm_endpoint}")

            # Initialize strategy generator
            self.generator = LLMStrategyGenerator(self.client)

        except ImportError as e:
            print(f"LLM components not available: {e}")
            self.use_fallback = True
            self.llm_available = False

        # Fallback simple mutator
        self.simple_mutator = SimpleBackupMutator()

    def mutate_strategy(
        self, genome: StrategyGenome, mutation_type: str = "random"
    ) -> StrategyGenome:
        """Apply LLM-based mutation to strategy."""

        if self.use_fallback or not self.llm_available:
            return self.simple_mutator.mutate_strategy(genome, mutation_type)

        try:
            # Create prompt context
            from ..llm import PromptContext

            context = PromptContext(
                strategy_type="signal",
                market_focus=["spot", "futures"],
                timeframe="1m",
                indicators_to_include=["RSI", "SMA", "MACD", "BB"],
                signal_logic=(
                    mutation_type
                    if mutation_type
                    in ["trend_following", "mean_reversion", "breakout", "exhaustion"]
                    else "trend_following"
                ),
                risk_profile="balanced",
            )

            # Perform LLM mutation
            result = self.generator.mutate_strategy(
                genome.pyne_code, mutation_type, context
            )

            if result.success and result.generated_code:
                # Convert to genome
                mutated_genome = self.generator.convert_to_strategy_genome(
                    result,
                    f"{genome.name}_llm_mut_{mutation_type}",
                    f"LLM-mutated strategy via {mutation_type}",
                )

                if mutated_genome:
                    # Preserve lineage information
                    mutated_genome.parent_ids = genome.parent_ids + [genome.name]
                    mutated_genome.generation = genome.generation + 1

                    print(
                        f"✅ Successful LLM mutation of {genome.name} via {mutation_type}"
                    )
                    return mutated_genome

            # Fall back to simple mutation if LLM fails
            print(f"⚠️ LLM mutation failed, using simple fallback")
            return self.simple_mutator.mutate_strategy(genome, mutation_type)

        except Exception as e:
            print(f"💥 LLM mutation error: {e}")
            return self.simple_mutator.mutate_strategy(genome, mutation_type)

    def get_mutation_stats(self) -> Dict[str, any]:
        """Get mutation statistics."""
        if self.use_fallback or not self.llm_available:
            return {"status": "fallback_mode", "llm_available": False}

        return {
            "status": "llm_active",
            "llm_available": True,
            "client_stats": self.client.get_stats(),
            "generator_stats": self.generator.get_generation_stats(),
        }


class SimpleBackupMutator:
    """Fallback simple mutator when LLM is unavailable."""

    def __init__(self):
        pass

    def mutate_strategy(
        self, genome: StrategyGenome, mutation_type: str = "random"
    ) -> StrategyGenome:
        """Apply simple parameter-based mutations."""

        if mutation_type == "parameter":
            mutated_params = self._mutate_parameters(genome.parameters, mutation_type)
            mutated_code = genome.pyne_code
        else:
            # Simple logic mutations
            mutated_code = self._simple_mutation(genome.pyne_code, mutation_type)
            mutated_params = genome.parameters

        return StrategyGenome(
            name=f"{genome.name}_simple_{mutation_type}",
            description=f"Simple mutation of {genome.name} via {mutation_type}",
            pine_code=self._convert_to_pine(mutated_code),
            pyne_code=mutated_code,
            parameters=mutated_params,
            generation=genome.generation + 1,
            parent_ids=[genome.name],
        )

    def _mutate_parameters(
        self, params: Dict[str, float], mutation_type: str
    ) -> Dict[str, float]:
        """Apply parameter mutations."""
        mutated = params.copy()
        for key in mutated:
            if random.random() < 0.3:  # 30% mutation rate
                if key in ["level1", "level2", "level3"]:
                    mutated[key] = max(5, min(20, mutated[key] + random.randint(-2, 2)))
                else:
                    mutated[key] *= random.uniform(0.8, 1.2)
        return mutated

    def _simple_mutation(self, code: str, mutation_type: str) -> str:
        """Apply simple code mutations."""
        if mutation_type == "parameter":
            # Parameter mutations handled separately
            return code
        elif mutation_type == "logic":
            # Simple logic change
            return code.replace("close[4]", "close[3]").replace("close[2]", "close[1]")
        elif mutation_type == "indicator":
            # Replace SMA with EMA
            return code.replace(".sma(", ".ema(")
        elif mutation_type == "timeframe":
            # Reduce lookback periods
            import re

            return re.sub(r"(\d+)", lambda m: str(int(m.group(1)) - 1), code)
        else:
            return code

    def _convert_to_pine(self, pyne_code: str) -> str:
        """Convert PyneCore code to Pine Script format."""
        return pyne_code.replace("from pynecore import", "//").replace(
            "plot(", "plotshape("
        )


class RobustStrategyEvolutionEngine:
    """Advanced LLM-based strategy evolution with multi-market testing and real-world validation."""

    def __init__(
        self,
        llm_mutator: LLMStrategyMutator,
        strategy_registry: StrategyRegistry,
        market_evaluator: MultiMarketEvaluator,
        fitness_config: Optional[GlobalFitnessConfig] = None,
    ):
        self.llm_mutator = llm_mutator
        self.registry = strategy_registry
        self.market_evaluator = market_evaluator
        self.fitness_config = fitness_config or get_fitness_config("BALANCED_DEMO")

        # Evolution parameters
        self.population: List[Tuple[str, str]] = []  # (strategy_id, version_id)
        self.generation_history: List[Dict] = []

    async def initialize_population(
        self,
        base_strategy: StrategyGenome,
        population_size: int = 10,
        variants_per_individual: int = 3,
    ) -> None:
        """Create initial population with multiple variants per individual."""
        # Save base strategy
        base_strategy_id = self.registry.save_strategy(
            base_strategy, "Initial base strategy"
        )
        base_version_id = self._get_current_version(base_strategy_id)

        print(
            f"[EVOLUTION] Initializing population with {population_size} individuals, {variants_per_individual} variants each"
        )

        # Create population with variants
        self.population = [(base_strategy_id, base_version_id)]

        # Generate variants for each individual
        for i in range(population_size - 1):
            # Create individual
            mutation_type = random.choice(
                ["parameter", "logic", "indicator", "timeframe"]
            )
            individual = self.llm_mutator.mutate_strategy(base_strategy, mutation_type)
            individual.name = f"gen1_individual_{i+1}"

            # Save individual
            individual_id = self.registry.save_strategy(
                individual, f"Generation 1 individual {i+1}"
            )
            individual_version_id = self._get_current_version(individual_id)

            # Create variants of this individual
            variant_config = {
                "count": variants_per_individual
                - 1,  # -1 because the individual itself counts as 1
                "mutation_types": ["parameter", "logic", "indicator"],
                "markets_focus": random.sample(["BTCUSDT", "ETHUSDT", "ADAUSDT"], 2),
            }

            variant_ids = self.registry.create_strategy_variant(
                individual_id, variant_config
            )

            # Add all variants (including the individual itself) to population
            self.population.append((individual_id, individual_version_id))
            for var_id in variant_ids:
                var_version_id = self._get_current_version(var_id)
                self.population.append((var_id, var_version_id))

        print(
            f"[EVOLUTION] Population initialized with {len(self.population)} total variants"
        )

    def _get_current_version(self, strategy_id: str) -> str:
        """Get current version ID for strategy."""
        with sqlite3.connect(self.registry.db_path) as conn:
            result = conn.execute(
                "SELECT current_version_id FROM strategies WHERE strategy_id = ?",
                (strategy_id,),
            ).fetchone()
            return result[0] if result else None

    async def evaluate_strategy_population(
        self, generation: int
    ) -> Dict[str, StrategyMetrics]:
        """Evaluate entire population across multiple markets with real-world metrics."""
        print(
            f"[EVOLUTION] Evaluating generation {generation} - {len(self.population)} strategies"
        )

        # Batch evaluate all strategies
        evaluation_results = await self.market_evaluator.batch_evaluate_population(
            self.population
        )

        print(f"[EVOLUTION] Completed {len(evaluation_results)} strategy evaluations")

        # Validate strategies for deployment readiness
        deployment_ready = []
        for (strategy_id, version_id), metrics in evaluation_results.items():
            if self._is_deployment_ready(metrics):
                deployment_ready.append((strategy_id, version_id))

        # Update deployment readiness in registry
        for strategy_id, version_id in deployment_ready:
            self.registry.update_deployment_readiness(strategy_id, version_id, True)

        print(
            f"[EVOLUTION] {len(deployment_ready)} strategies marked as deployment-ready"
        )

        return evaluation_results

    def _is_deployment_ready(self, metrics: StrategyMetrics) -> bool:
        """Check if strategy meets real-world deployment criteria using global config."""
        # Convert StrategyMetrics to dict for fitness calculation
        metrics_dict = {
            "total_pnl": metrics.total_pnl,
            "sharpe_ratio": metrics.sharpe_ratio,
            "max_drawdown": metrics.max_drawdown,
            "win_rate": metrics.win_rate,
            "num_trades": metrics.num_trades,
            "markets_tested": metrics.markets_tested,
            "slippage_impact": metrics.slippage_impact,
            "execution_delay_ms": metrics.execution_delay_ms,
            "market_impact": metrics.market_impact,
            "downside_deviation": metrics.downside_deviation,
            "volatility_adjusted_return": metrics.volatility_adjusted_return,
            "avg_daily_trades": metrics.num_trades
            / max(len(metrics.markets_tested), 1),
        }

        # Calculate composite fitness
        composite_fitness = self.fitness_config.calculate_composite_fitness(
            metrics_dict
        )

        # Use global config validation
        is_ready, reasons = self.fitness_config.is_deployment_ready(
            composite_fitness, metrics_dict
        )

        if not is_ready:
            self.logger.debug(f"Strategy not deployment-ready: {reasons}")

        return is_ready

    def _calculate_fitness_from_output(self, output_dir: Path) -> float:
        """Calculate fitness score from PyneCore output."""
        # Simplified fitness calculation
        # Would need to parse actual PyneCore results
        analysis_file = output_dir / "analysis.json"
        if analysis_file.exists():
            with open(analysis_file) as f:
                data = json.load(f)
                pnl = data.get("total_pnl", 0)
                sharpe = data.get("sharpe_ratio", 0)
                return pnl + 0.1 * sharpe
        return random.uniform(-1, 1)  # Random fallback for demo

    async def evolve_generation(
        self,
        generation: int,
        elite_size: int = 2,
        mutation_rate: float = 0.3,
        variants_per_offspring: int = 3,
    ) -> None:
        """Evolve population to next generation with comprehensive evaluation."""
        print(f"[EVOLUTION] Starting generation {generation}")

        # Evaluate current population
        evaluation_results = await self.evaluate_strategy_population(generation)

        # Sort strategies by fitness using global config
        def get_composite_fitness(item):
            strategy_id, metrics = item
            metrics_dict = {
                "total_pnl": metrics.total_pnl,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "win_rate": metrics.win_rate,
                "num_trades": metrics.num_trades,
                "markets_tested": metrics.markets_tested,
                "slippage_impact": metrics.slippage_impact,
                "execution_delay_ms": metrics.execution_delay_ms,
                "market_impact": metrics.market_impact,
                "downside_deviation": metrics.downside_deviation,
                "volatility_adjusted_return": metrics.volatility_adjusted_return,
                "avg_daily_trades": metrics.num_trades
                / max(len(metrics.markets_tested), 1),
            }
            return self.fitness_config.calculate_composite_fitness(metrics_dict)

        sorted_strategies = sorted(
            evaluation_results.items(), key=get_composite_fitness, reverse=True
        )

        # Generate generation summary
        best_strategy_id, best_metrics = sorted_strategies[0]
        best_fitness = get_composite_fitness((best_strategy_id, best_metrics))
        avg_fitness = sum(
            get_composite_fitness(item) for item in sorted_strategies
        ) / len(sorted_strategies)

        gen_summary = {
            "generation": generation,
            "best_fitness": best_fitness,
            "avg_fitness": avg_fitness,
            "population_size": len(self.population),
            "deployment_ready": sum(
                1 for (_, m) in sorted_strategies if self._is_deployment_ready(m)
            ),
            "diverse_markets": len(
                set().union(*[m.markets_tested for (_, m) in sorted_strategies])
            ),
            "best_strategy_id": best_strategy_id,
        }

        self.generation_history.append(gen_summary)

        print(
            f"[EVOLUTION] Gen {generation}: Best fitness: {best_fitness:.4f}, "
            f"Avg: {avg_fitness:.4f}, Deploy-ready: {gen_summary['deployment_ready']}"
        )

        # Selection and reproduction
        new_population = []

        # Elite strategies (preserve best)
        elite_strategy_ids = [sid for (sid, _), _ in sorted_strategies[:elite_size]]
        for strategy_id, version_id in elite_strategy_ids:
            new_population.append((strategy_id, version_id))

        # Generate offspring
        while len(new_population) < len(self.population):
            # Tournament selection from top 50%
            tournament_size = min(4, len(sorted_strategies) // 2)
            tournament = random.sample(
                sorted_strategies[: len(sorted_strategies) // 2], tournament_size
            )
            parent_strategy_id, parent_version_id = max(
                tournament, key=get_composite_fitness
            )[0]

            # Create offspring
            if random.random() < mutation_rate:
                # Mutate parent strategy
                parent_strategy = self.registry.get_strategy(parent_strategy_id)
                if parent_strategy:
                    parent_genome = StrategyGenome(
                        name=parent_strategy["name"],
                        description=parent_strategy["description"],
                        pine_code=parent_strategy["pine_code"],
                        pyne_code=parent_strategy["pyne_code"],
                        parameters=parent_strategy["parameters"],
                        generation=generation,
                    )

                    mutation_type = random.choice(
                        ["parameter", "logic", "indicator", "timeframe"]
                    )
                    offspring_genome = self.llm_mutator.mutate_strategy(
                        parent_genome, mutation_type
                    )
                    offspring_genome.name = (
                        f"gen{generation+1}_offspring_{len(new_population)}"
                    )

                    # Save offspring
                    offspring_id = self.registry.save_strategy(
                        offspring_genome,
                        f"Generation {generation+1} offspring via {mutation_type}",
                    )
                    offspring_version_id = self._get_current_version(offspring_id)

                    # Create variants of offspring
                    variant_config = {
                        "count": variants_per_offspring - 1,
                        "mutation_types": ["parameter", "logic"],
                        "markets_focus": random.sample(
                            ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT"], 2
                        ),
                    }

                    variant_ids = self.registry.create_strategy_variant(
                        offspring_id, variant_config
                    )

                    # Add offspring and variants
                    new_population.append((offspring_id, offspring_version_id))
                    for var_id in variant_ids:
                        var_version_id = self._get_current_version(var_id)
                        new_population.append((var_id, var_version_id))
            else:
                # Clone parent
                new_population.append((parent_strategy_id, parent_version_id))

        self.population = new_population[
            : len(self.population)
        ]  # Ensure size consistency

    async def run_evolution(
        self,
        generations: int = 15,
        population_size: int = 8,
        variants_per_individual: int = 3,
        convergence_patience: int = 5,
    ) -> Dict[str, Any]:
        """Run complete evolution process with convergence detection."""
        print(
            f"[EVOLUTION] Starting robust evolution: {generations} generations, "
            f"{population_size} individuals, {variants_per_individual} variants each"
        )

        # Initialize with base strategy
        base_strategy = create_exhaustion_base()
        await self.initialize_population(
            base_strategy, population_size, variants_per_individual
        )

        best_overall_fitness = -float("inf")
        no_improvement_count = 0

        for gen in range(generations):
            await self.evolve_generation(
                gen + 1, elite_size=2, variants_per_offspring=variants_per_individual
            )

            # Check for convergence
            current_best = self.generation_history[-1]["best_fitness"]
            if current_best > best_overall_fitness:
                best_overall_fitness = current_best
                no_improvement_count = 0
            else:
                no_improvement_count += 1

            # Early stopping if no improvement
            if no_improvement_count >= convergence_patience:
                print(f"[EVOLUTION] Convergence detected early at generation {gen + 1}")
                break

        # Get best deployment-ready strategies
        deployment_ready = self.registry.get_deployment_ready_strategies(min_markets=3)

        evolution_results = {
            "generations_completed": gen + 1,
            "final_population_size": len(self.population),
            "best_fitness": best_overall_fitness,
            "final_deployment_ready": len(deployment_ready),
            "generation_history": self.generation_history,
            "deployment_ready_strategies": deployment_ready,
            "convergence_reason": (
                "early_convergence"
                if no_improvement_count >= convergence_patience
                else "complete"
            ),
        }

        print(f"[EVOLUTION] Evolution complete!")
        print(f"[EVOLUTION] Best fitness: {best_overall_fitness:.4f}")
        print(f"[EVOLUTION] Deployment-ready strategies: {len(deployment_ready)}")

        return evolution_results


def create_exhaustion_base() -> StrategyGenome:
    """Create base exhaustion signal strategy."""
    with open("/home/agile/ExhaustionLab/scripts/pyne/exhaustion_signal.py") as f:
        pyne_code = f.read()

    with open("/home/agile/ExhaustionLab/scripts/pine/exhaustion_signal_v6.pine") as f:
        pine_code = f.read()

    return StrategyGenome(
        name="exhaustion_base",
        description="Base exhaustion signal strategy",
        pine_code=pine_code,
        pyne_code=pyne_code,
        parameters={"level1": 9, "level2": 12, "level3": 14},
    )


def create_exhaustion_main() -> StrategyGenome:
    """Export main function for GA optimizer."""
    return create_exhaustion_base()


async def main(
    population_size: int = 6,
    generations: int = 8,
    variants_per_individual: int = 3,
    fitness_config_name: str = "BALANCED_DEMO",
):
    """Main evolutionary process with robust multi-market evaluation."""
    print(f"[EVOLUTION] Starting robust LLM-based strategy evolution...")
    print(f"[EVOLUTION] Using fitness config: {fitness_config_name}")

    # Initialize components
    llm_mutator = LLMStrategyMutator()
    registry = StrategyRegistry()
    market_evaluator = MultiMarketEvaluator(registry)

    # Create fitness configuration
    fitness_config = get_fitness_config(fitness_config_name)

    # Create robust evolution engine
    engine = RobustStrategyEvolutionEngine(
        llm_mutator, registry, market_evaluator, fitness_config
    )

    # Run evolution with comprehensive evaluation
    evolution_results = await engine.run_evolution(
        generations=generations,
        population_size=population_size,
        variants_per_individual=variants_per_individual,
        convergence_patience=3,
    )

    # Display results
    print(f"\n" + "=" * 80)
    print("EVOLUTION RESULTS SUMMARY")
    print("=" * 80)
    print(f"Generations completed: {evolution_results['generations_completed']}")
    print(f"Best fitness achieved: {evolution_results['best_fitness']:.4f}")
    print(f"Population size: {evolution_results['final_population_size']}")
    print(f"Deployment-ready strategies: {evolution_results['final_deployment_ready']}")
    print(f"Convergence reason: {evolution_results['convergence_reason']}")

    # Show best strategies
    if evolution_results["deployment_ready_strategies"]:
        print(
            f"\nTop {min(3, len(evolution_results['deployment_ready_strategies']))} deployment-ready strategies:"
        )
        for i, strategy in enumerate(
            evolution_results["deployment_ready_strategies"][:3]
        ):
            print(
                f"  {i+1}. {strategy['name']} (fitness: {strategy['fitness']:.4f}, "
                f"trades: {strategy.get('total_tests', 'N/A')})"
            )

    # Save comprehensive results
    results_dir = Path("/home/agile/ExhaustionLab/evolution_results")
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"evolution_{timestamp}.json"

    with open(results_file, "w") as f:
        json.dump(evolution_results, f, indent=2, default=str)

    print(f"\nDetailed results saved to: {results_file}")

    # Save best strategies for deployment
    if evolution_results["deployment_ready_strategies"]:
        strategies_dir = results_dir / "deployable_strategies"
        strategies_dir.mkdir(exist_ok=True)

        for strategy in evolution_results["deployment_ready_strategies"][:5]:
            strategy_file = strategies_dir / f"{strategy['name']}.py"
            with open(strategy_file, "w") as f:
                f.write(strategy["pyne_code"])

            config_file = strategies_dir / f"{strategy['name']}_config.json"
            with open(config_file, "w") as f:
                config = {
                    "strategy_id": strategy["strategy_id"],
                    "parameters": strategy["parameters"],
                    "fitness": strategy["fitness"],
                    "deployment_score": strategy["deployment_score"],
                    "markets_tested": strategy["markets_tested"],
                }
                json.dump(config, f, indent=2)

        print(f"Top strategies saved for deployment: {strategies_dir}")

    return evolution_results


if __name__ == "__main__":
    asyncio.run(main())
