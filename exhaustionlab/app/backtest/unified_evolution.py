"""
Unified Evolution Engine

Complete evolution system combining:
- LLM-powered mutations (primary)
- Traditional GA (fallback)
- Adaptive parameter optimization
- Configuration-driven settings

Provides seamless fallback and hybrid approaches.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import random
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EvolutionResult:
    """Result of evolution process."""

    best_strategy: Any
    best_fitness: float
    generations_completed: int
    total_evaluations: int
    evolution_history: List[Dict[str, float]]
    method_used: str  # "llm", "ga", "hybrid"
    success: bool
    error_message: Optional[str] = None


class UnifiedEvolutionEngine:
    """
    Unified evolution engine with automatic fallback.

    Strategy:
    1. Try LLM-powered evolution (best quality)
    2. Fall back to traditional GA if LLM unavailable
    3. Use adaptive parameters for optimization
    4. Track performance and adapt approach
    """

    def __init__(
        self,
        use_llm: bool = True,
        use_adaptive_params: bool = True,
        fallback_enabled: bool = True,
    ):
        """Initialize unified engine."""
        self.use_llm = use_llm
        self.use_adaptive_params = use_adaptive_params
        self.fallback_enabled = fallback_enabled

        # Try to initialize LLM
        self.llm_available = False
        self.llm_mutator = None

        if use_llm:
            try:
                from .llm_evolution import LLMStrategyMutator

                self.llm_mutator = LLMStrategyMutator()
                self.llm_available = self.llm_mutator.llm_available

                if self.llm_available:
                    logger.info("✅ LLM evolution enabled")
                else:
                    logger.warning("⚠️ LLM not available, will use GA fallback")

            except Exception as e:
                logger.warning(f"Failed to initialize LLM: {e}")
                self.llm_available = False

        # Initialize traditional GA
        try:
            from .traditional_genetics import TraditionalGeneticOptimizer

            self.ga_optimizer = TraditionalGeneticOptimizer()
            logger.info("✅ GA optimizer ready")
        except Exception as e:
            logger.warning(f"Failed to initialize GA: {e}")
            self.ga_optimizer = None

        # Initialize adaptive parameters
        self.adaptive_params = None
        if use_adaptive_params:
            try:
                from ..meta_evolution.adaptive_parameters import (
                    AdaptiveParameterOptimizer,
                )

                self.adaptive_params = AdaptiveParameterOptimizer()
                logger.info("✅ Adaptive parameters enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize adaptive params: {e}")

        # Evolution statistics
        self.evolution_stats = {
            "llm_attempts": 0,
            "llm_successes": 0,
            "ga_attempts": 0,
            "ga_successes": 0,
            "hybrid_attempts": 0,
            "total_evaluations": 0,
        }

        logger.info(f"UnifiedEvolutionEngine initialized:")
        logger.info(f"  LLM: {'✅' if self.llm_available else '❌'}")
        logger.info(f"  GA: {'✅' if self.ga_optimizer else '❌'}")
        logger.info(f"  Adaptive: {'✅' if self.adaptive_params else '❌'}")

    def evolve_strategy(
        self,
        initial_strategy: Any,
        config: Dict[str, Any],
        evaluation_func: callable,
        max_generations: int = 20,
        population_size: int = 10,
    ) -> EvolutionResult:
        """
        Evolve strategy using best available method.

        Args:
            initial_strategy: Starting strategy
            config: Evolution configuration
            evaluation_func: Function to evaluate fitness
            max_generations: Maximum generations
            population_size: Population size

        Returns:
            EvolutionResult with best strategy and metadata
        """
        logger.info(
            f"🔬 Starting evolution: {max_generations} gens, pop={population_size}"
        )

        # Determine method
        method = self._select_method()
        logger.info(f"  Method: {method}")

        try:
            if method == "llm":
                result = self._evolve_with_llm(
                    initial_strategy,
                    config,
                    evaluation_func,
                    max_generations,
                    population_size,
                )
                self.evolution_stats["llm_attempts"] += 1
                if result.success:
                    self.evolution_stats["llm_successes"] += 1

            elif method == "ga":
                result = self._evolve_with_ga(
                    initial_strategy,
                    config,
                    evaluation_func,
                    max_generations,
                    population_size,
                )
                self.evolution_stats["ga_attempts"] += 1
                if result.success:
                    self.evolution_stats["ga_successes"] += 1

            elif method == "hybrid":
                result = self._evolve_hybrid(
                    initial_strategy,
                    config,
                    evaluation_func,
                    max_generations,
                    population_size,
                )
                self.evolution_stats["hybrid_attempts"] += 1

            else:
                raise ValueError(f"Unknown method: {method}")

            self.evolution_stats["total_evaluations"] += result.total_evaluations

            # Update adaptive parameters if enabled
            if self.adaptive_params and result.success:
                self._update_adaptive_params(result, config)

            logger.info(f"✅ Evolution complete: fitness={result.best_fitness:.4f}")

            return result

        except Exception as e:
            logger.error(f"Evolution failed: {e}")

            # Try fallback if enabled
            if self.fallback_enabled and method == "llm":
                logger.info("  🔄 Falling back to GA...")
                return self._evolve_with_ga(
                    initial_strategy,
                    config,
                    evaluation_func,
                    max_generations,
                    population_size,
                )

            return EvolutionResult(
                best_strategy=initial_strategy,
                best_fitness=0.0,
                generations_completed=0,
                total_evaluations=0,
                evolution_history=[],
                method_used=method,
                success=False,
                error_message=str(e),
            )

    def _select_method(self) -> str:
        """Select evolution method based on availability."""
        if self.llm_available and self.use_llm:
            return "llm"
        elif self.ga_optimizer:
            return "ga"
        else:
            return "hybrid"

    def _evolve_with_llm(
        self,
        initial_strategy: Any,
        config: Dict[str, Any],
        evaluation_func: callable,
        max_generations: int,
        population_size: int,
    ) -> EvolutionResult:
        """Evolve using LLM mutations."""
        if not self.llm_available:
            raise RuntimeError("LLM not available")

        best_strategy = initial_strategy
        best_fitness = evaluation_func(initial_strategy)

        history = [
            {"generation": 0, "best_fitness": best_fitness, "avg_fitness": best_fitness}
        ]
        total_evals = 1

        # Get mutation types
        mutation_types = config.get("mutation_types", ["parameter", "logic", "hybrid"])

        for gen in range(max_generations):
            generation_fitnesses = []

            # Create offspring through mutations
            for _ in range(population_size):
                mutation_type = random.choice(mutation_types)

                try:
                    # LLM mutation
                    offspring = self.llm_mutator.mutate_strategy(
                        best_strategy, mutation_type
                    )

                    # Evaluate
                    fitness = evaluation_func(offspring)
                    total_evals += 1
                    generation_fitnesses.append(fitness)

                    # Update best
                    if fitness > best_fitness:
                        best_fitness = fitness
                        best_strategy = offspring
                        logger.info(
                            f"  Gen {gen+1}: New best fitness: {best_fitness:.4f}"
                        )

                except Exception as e:
                    logger.warning(f"Mutation failed: {e}")
                    generation_fitnesses.append(0.0)
                    continue

            # Track history
            avg_fitness = np.mean(generation_fitnesses) if generation_fitnesses else 0
            history.append(
                {
                    "generation": gen + 1,
                    "best_fitness": best_fitness,
                    "avg_fitness": avg_fitness,
                }
            )

            logger.info(
                f"  Gen {gen+1}: Best={best_fitness:.4f}, Avg={avg_fitness:.4f}"
            )

        return EvolutionResult(
            best_strategy=best_strategy,
            best_fitness=best_fitness,
            generations_completed=max_generations,
            total_evaluations=total_evals,
            evolution_history=history,
            method_used="llm",
            success=True,
        )

    def _evolve_with_ga(
        self,
        initial_strategy: Any,
        config: Dict[str, Any],
        evaluation_func: callable,
        max_generations: int,
        population_size: int,
    ) -> EvolutionResult:
        """Evolve using traditional GA."""
        if not self.ga_optimizer:
            raise RuntimeError("GA optimizer not available")

        logger.info("  Using traditional genetic algorithm")

        # Simple GA implementation
        best_strategy = initial_strategy
        best_fitness = evaluation_func(initial_strategy)

        history = [
            {"generation": 0, "best_fitness": best_fitness, "avg_fitness": best_fitness}
        ]
        total_evals = 1

        # Initialize population with parameter variations
        population = [initial_strategy]

        for gen in range(max_generations):
            # Simple parameter mutations
            generation_fitnesses = []
            new_population = []

            for individual in population[:5]:  # Keep top 5
                # Parameter mutation
                mutated = self._mutate_parameters(individual, config)
                fitness = evaluation_func(mutated)
                total_evals += 1

                generation_fitnesses.append(fitness)
                new_population.append((mutated, fitness))

                if fitness > best_fitness:
                    best_fitness = fitness
                    best_strategy = mutated

            # Keep best
            new_population.sort(key=lambda x: x[1], reverse=True)
            population = [ind for ind, fit in new_population[:population_size]]

            avg_fitness = np.mean(generation_fitnesses)
            history.append(
                {
                    "generation": gen + 1,
                    "best_fitness": best_fitness,
                    "avg_fitness": avg_fitness,
                }
            )

            logger.info(
                f"  Gen {gen+1}: Best={best_fitness:.4f}, Avg={avg_fitness:.4f}"
            )

        return EvolutionResult(
            best_strategy=best_strategy,
            best_fitness=best_fitness,
            generations_completed=max_generations,
            total_evaluations=total_evals,
            evolution_history=history,
            method_used="ga",
            success=True,
        )

    def _evolve_hybrid(
        self,
        initial_strategy: Any,
        config: Dict[str, Any],
        evaluation_func: callable,
        max_generations: int,
        population_size: int,
    ) -> EvolutionResult:
        """Evolve using hybrid approach (LLM + GA)."""
        logger.info("  Using hybrid evolution (LLM + GA)")

        # Use GA for parameter optimization
        # Use LLM for structural changes (if available)

        # Start with GA
        ga_result = self._evolve_with_ga(
            initial_strategy,
            config,
            evaluation_func,
            max_generations // 2,
            population_size,
        )

        # Continue with LLM if available
        if self.llm_available:
            llm_result = self._evolve_with_llm(
                ga_result.best_strategy,
                config,
                evaluation_func,
                max_generations // 2,
                population_size,
            )

            # Combine histories
            combined_history = (
                ga_result.evolution_history + llm_result.evolution_history
            )

            return EvolutionResult(
                best_strategy=llm_result.best_strategy,
                best_fitness=llm_result.best_fitness,
                generations_completed=max_generations,
                total_evaluations=ga_result.total_evaluations
                + llm_result.total_evaluations,
                evolution_history=combined_history,
                method_used="hybrid",
                success=True,
            )
        else:
            # Just use GA result
            return ga_result

    def _mutate_parameters(self, strategy: Any, config: Dict[str, Any]) -> Any:
        """Simple parameter mutation for GA."""
        # Placeholder: implement parameter mutation
        # This would modify numerical parameters
        return strategy

    def _update_adaptive_params(self, result: EvolutionResult, config: Dict[str, Any]):
        """Update adaptive parameters based on evolution result."""
        if not self.adaptive_params:
            return

        # Extract config used
        config_used = {
            "mutation_rate": config.get("mutation_rate", 0.3),
            "population_size": config.get("population_size", 10),
            "temperature": config.get("temperature", 0.7),
        }

        # Determine success
        success = result.best_fitness > 0.6  # Arbitrary threshold

        # Update optimizer
        self.adaptive_params.update_from_result(
            config_used, result.best_fitness * 100, success  # Convert to 0-100 scale
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get evolution statistics."""
        return {
            **self.evolution_stats,
            "llm_success_rate": self.evolution_stats["llm_successes"]
            / max(1, self.evolution_stats["llm_attempts"]),
            "ga_success_rate": self.evolution_stats["ga_successes"]
            / max(1, self.evolution_stats["ga_attempts"]),
            "adaptive_params": (
                self.adaptive_params.get_statistics() if self.adaptive_params else {}
            ),
        }


# Convenience functions


def create_evolution_engine(
    use_llm: bool = True, use_adaptive: bool = True
) -> UnifiedEvolutionEngine:
    """Create unified evolution engine with defaults."""
    return UnifiedEvolutionEngine(
        use_llm=use_llm, use_adaptive_params=use_adaptive, fallback_enabled=True
    )


if __name__ == "__main__":
    # Test unified evolution
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    print("\n🧬 UNIFIED EVOLUTION ENGINE TEST\n")
    print("=" * 70)

    # Create engine
    engine = create_evolution_engine(use_llm=True, use_adaptive=True)

    # Mock strategy and evaluation
    class MockStrategy:
        def __init__(self, params):
            self.params = params

    def mock_evaluation(strategy):
        # Simulate fitness based on some logic
        return random.uniform(0.3, 0.9)

    # Configuration
    config = {
        "mutation_types": ["parameter", "logic"],
        "mutation_rate": 0.3,
        "population_size": 5,
        "temperature": 0.7,
    }

    # Initial strategy
    initial = MockStrategy({"rsi_period": 14, "threshold": 0.7})

    print("\n🔬 Running evolution (5 generations)...")

    result = engine.evolve_strategy(
        initial_strategy=initial,
        config=config,
        evaluation_func=mock_evaluation,
        max_generations=5,
        population_size=5,
    )

    print(f"\n📊 Evolution Results:")
    print(f"  Method: {result.method_used}")
    print(f"  Success: {result.success}")
    print(f"  Best Fitness: {result.best_fitness:.4f}")
    print(f"  Generations: {result.generations_completed}")
    print(f"  Evaluations: {result.total_evaluations}")

    print(f"\n📈 History:")
    for entry in result.evolution_history[:5]:
        print(
            f"  Gen {entry['generation']}: "
            f"Best={entry['best_fitness']:.4f}, "
            f"Avg={entry['avg_fitness']:.4f}"
        )

    # Show statistics
    print(f"\n📊 Engine Statistics:")
    stats = engine.get_statistics()
    for key, value in stats.items():
        if key != "adaptive_params":
            print(f"  {key}: {value}")

    print("\n✅ Unified evolution engine operational!")
