"""
Lightweight traditional genetics engine used by fallback GA workflows.

The implementation intentionally mirrors the parameter bounds defined in
`indicator_params` so that we can reuse the same strategy constraints even when
the LLM stack is unavailable.
"""

from __future__ import annotations

import random
from typing import Callable, Dict, List, Tuple, Union

import pandas as pd

from ..config.indicator_params import SQUEEZE_PARAM_SPECS, squeeze_param_bounds

Candidate = Dict[str, Union[int, float, bool]]
FitnessFunc = Callable[[Candidate, pd.DataFrame], float]


class TraditionalGenetics:
    """Very small GA focused purely on parameter evolution."""

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng or random.Random()
        self.bounds = squeeze_param_bounds()

    def generate_random_candidate(self) -> Candidate:
        """Create a random parameter set that respects squeeze bounds."""
        candidate: Candidate = {}
        for spec in SQUEEZE_PARAM_SPECS:
            lo, hi, step = self.bounds[spec.name]
            if spec.kind == "bool":
                candidate[spec.name] = bool(self.rng.getrandbits(1))
            elif spec.kind == "int":
                candidate[spec.name] = int(self.rng.randrange(int(lo), int(hi) + 1, max(1, int(step))))
            else:
                candidate[spec.name] = float(round(self.rng.uniform(float(lo), float(hi)), 6))
        return candidate

    def crossover(self, parent_a: Candidate, parent_b: Candidate) -> Candidate:
        """Uniform crossover that randomly chooses each gene from either parent."""
        child: Candidate = {}
        for key in parent_a.keys():
            child[key] = parent_a[key] if self.rng.random() < 0.5 else parent_b[key]
        return child

    def mutate(self, candidate: Candidate, rate: float):
        """Mutate a candidate in-place using simple perturbations."""
        for spec in SQUEEZE_PARAM_SPECS:
            if self.rng.random() > rate:
                continue
            lo, hi, step = self.bounds[spec.name]
            if spec.kind == "bool":
                candidate[spec.name] = not bool(candidate[spec.name])
            elif spec.kind == "int":
                delta = self.rng.choice([-1, 1]) * max(1, int(step))
                candidate[spec.name] = int(max(lo, min(hi, candidate[spec.name] + delta)))
            else:
                span = float(hi - lo)
                delta = self.rng.uniform(-0.1 * span, 0.1 * span)
                candidate[spec.name] = float(max(lo, min(hi, candidate[spec.name] + delta)))

    def evolve_parameters(
        self,
        returns: pd.DataFrame,
        population_size: int,
        generations: int,
        fitness_func: FitnessFunc,
        mutation_rate: float = 0.2,
        elite: int = 2,
    ) -> Tuple[Candidate, float]:
        """
        Execute a tiny GA loop and return the best candidate + score.

        Args:
            returns: Price returns dataframe/series used by the fitness function.
            population_size: Number of individuals per generation.
            generations: Number of generations to run.
            fitness_func: Callable that evaluates a candidate.
            mutation_rate: Probability of mutating each gene.
            elite: Number of top individuals to carry over unchanged.
        """
        if population_size <= 0 or generations <= 0:
            raise ValueError("population_size and generations must be positive")
        if returns.empty:
            raise ValueError("returns dataframe is empty")

        population: List[Candidate] = [self.generate_random_candidate() for _ in range(population_size)]

        def score_population(cands: List[Candidate]) -> List[Tuple[Candidate, float]]:
            return [(cand, fitness_func(cand, returns)) for cand in cands]

        scored = score_population(population)
        best = max(scored, key=lambda item: item[1])

        for _ in range(generations):
            scored.sort(key=lambda item: item[1], reverse=True)
            survivors = [cand for cand, _ in scored[:elite]]

            while len(survivors) < population_size:
                parents = self.rng.sample(scored[: max(4, len(scored))], 2)
                child = self.crossover(parents[0][0], parents[1][0])
                self.mutate(child, mutation_rate)
                survivors.append(child)

            scored = score_population(survivors)
            gen_best = max(scored, key=lambda item: item[1])
            if gen_best[1] > best[1]:
                best = gen_best

        return best
