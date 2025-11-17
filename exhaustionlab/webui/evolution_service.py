"""
Real-time Evolution Service for Web UI

Manages strategy generation, backtesting, and live evolution updates.
Provides WebSocket/SSE for real-time progress tracking.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

LOGGER = logging.getLogger(__name__)


class EvolutionStatus(str, Enum):
    """Evolution process status."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    GENERATING = "generating"
    BACKTESTING = "backtesting"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    ERROR = "error"


class StrategySource(str, Enum):
    """Source of strategy."""

    LLM_GENERATED = "llm_generated"
    GITHUB_CRAWLED = "github_crawled"
    TRADINGVIEW_CRAWLED = "tradingview_crawled"
    USER_SUBMITTED = "user_submitted"


@dataclass
class BacktestResult:
    """Results from strategy backtest."""

    strategy_id: str
    fitness: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    win_rate: float
    total_trades: int
    profit_factor: float
    trades: List[Dict[str, Any]]
    equity_curve: List[Dict[str, float]]
    metrics: Dict[str, Any]
    chart_path: Optional[str] = None


@dataclass
class EvolutionEvent:
    """Real-time evolution event."""

    event_type: str
    timestamp: float
    generation: int
    strategy_id: Optional[str] = None
    fitness: Optional[float] = None
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class EvolutionProgress(BaseModel):
    """Current evolution progress."""

    status: EvolutionStatus
    current_generation: int
    total_generations: int
    strategies_evaluated: int
    best_fitness: float
    avg_fitness: float
    current_strategy_id: Optional[str] = None
    elapsed_time: float
    estimated_remaining: Optional[float] = None
    recent_events: List[Dict[str, Any]] = []


class EvolutionService:
    """
    Main evolution service for web UI.

    Handles:
    - Strategy generation (LLM + crawled)
    - Backtesting with fitness calculation
    - Real-time progress updates
    - Result storage and retrieval
    """

    def __init__(self):
        self.status = EvolutionStatus.IDLE
        self.progress = EvolutionProgress(
            status=EvolutionStatus.IDLE,
            current_generation=0,
            total_generations=0,
            strategies_evaluated=0,
            best_fitness=0.0,
            avg_fitness=0.0,
            elapsed_time=0.0,
            recent_events=[],
        )

        self.evolution_task: Optional[asyncio.Task] = None
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.subscribers: List[asyncio.Queue] = []

        # Evolution state
        self.start_time: Optional[float] = None
        self.strategies: List[Dict[str, Any]] = []
        self.backtest_results: Dict[str, BacktestResult] = {}

        # Lazy-loaded components
        self._orchestrator = None
        self._llm_client = None
        self._strategy_registry = None
        self._crawler = None

    @property
    def orchestrator(self):
        """Lazy-load intelligent orchestrator."""
        if self._orchestrator is None:
            try:
                from ..app.llm.llm_client import LocalLLMClient
                from ..app.meta_evolution.intelligent_orchestrator import IntelligentOrchestrator
                from ..app.meta_evolution.meta_config import MetaEvolutionConfig

                self._llm_client = LocalLLMClient()
                config = MetaEvolutionConfig()
                self._orchestrator = IntelligentOrchestrator(self._llm_client, config)
                LOGGER.info("✓ Intelligent orchestrator initialized")
            except Exception as e:
                LOGGER.error(f"Failed to initialize orchestrator: {e}")
                self._orchestrator = None
        return self._orchestrator

    @property
    def strategy_registry(self):
        """Lazy-load strategy registry."""
        if self._strategy_registry is None:
            try:
                from ..app.backtest.strategy_registry import StrategyRegistry

                self._strategy_registry = StrategyRegistry()
                LOGGER.info("✓ Strategy registry initialized")
            except Exception as e:
                LOGGER.error(f"Failed to initialize registry: {e}")
                self._strategy_registry = None
        return self._strategy_registry

    @property
    def crawler(self):
        """Lazy-load strategy crawler."""
        if self._crawler is None:
            try:
                from ..app.meta_evolution.StrategyWebCrawler import StrategyWebCrawler

                self._crawler = StrategyWebCrawler()
                LOGGER.info("✓ Strategy crawler initialized")
            except Exception as e:
                LOGGER.error(f"Failed to initialize crawler: {e}")
                self._crawler = None
        return self._crawler

    async def start_evolution(
        self,
        num_generations: int = 5,
        population_size: int = 3,
        use_llm: bool = True,
        use_crawled: bool = True,
        symbol: str = "ADAEUR",
        timeframe: str = "1m",
    ) -> Dict[str, Any]:
        """
        Start evolution process.

        Args:
            num_generations: Number of evolution generations
            population_size: Strategies per generation
            use_llm: Generate strategies with LLM
            use_crawled: Include crawled strategies from GitHub/TradingView
            symbol: Trading symbol for backtesting
            timeframe: Timeframe for backtesting
        """
        if self.status not in [
            EvolutionStatus.IDLE,
            EvolutionStatus.COMPLETED,
            EvolutionStatus.ERROR,
        ]:
            return {"error": "Evolution already in progress"}

        # Reset state
        self.status = EvolutionStatus.INITIALIZING
        self.start_time = time.time()
        self.strategies = []
        self.backtest_results = {}

        self.progress = EvolutionProgress(
            status=EvolutionStatus.INITIALIZING,
            current_generation=0,
            total_generations=num_generations,
            strategies_evaluated=0,
            best_fitness=0.0,
            avg_fitness=0.0,
            elapsed_time=0.0,
            recent_events=[],
        )

        # Emit start event
        await self._emit_event(
            EvolutionEvent(
                event_type="evolution_started",
                timestamp=time.time(),
                generation=0,
                message=f"Starting evolution: {num_generations} generations, {population_size} strategies",
                data={
                    "num_generations": num_generations,
                    "population_size": population_size,
                    "use_llm": use_llm,
                    "use_crawled": use_crawled,
                },
            )
        )

        # Start evolution in background
        self.evolution_task = asyncio.create_task(
            self._run_evolution(
                num_generations,
                population_size,
                use_llm,
                use_crawled,
                symbol,
                timeframe,
            )
        )

        return {"status": "started", "task_id": id(self.evolution_task)}

    async def _run_evolution(
        self,
        num_generations: int,
        population_size: int,
        use_llm: bool,
        use_crawled: bool,
        symbol: str,
        timeframe: str,
    ):
        """Run the complete evolution process."""
        try:
            for generation in range(1, num_generations + 1):
                self.progress.current_generation = generation
                self.status = EvolutionStatus.GENERATING

                await self._emit_event(
                    EvolutionEvent(
                        event_type="generation_started",
                        timestamp=time.time(),
                        generation=generation,
                        message=f"Generation {generation}/{num_generations}",
                    )
                )

                # Generate strategies
                generation_strategies = []

                # LLM generation
                if use_llm and generation <= num_generations:
                    llm_strategies = await self._generate_llm_strategies(population_size, generation)
                    generation_strategies.extend(llm_strategies)

                # Include crawled strategies in first generation
                if use_crawled and generation == 1:
                    crawled_strategies = await self._load_crawled_strategies()
                    generation_strategies.extend(crawled_strategies[:population_size])

                # Backtest all strategies
                self.status = EvolutionStatus.BACKTESTING
                for strategy in generation_strategies:
                    result = await self._backtest_strategy(strategy, symbol, timeframe)
                    self.backtest_results[strategy["strategy_id"]] = result
                    self.progress.strategies_evaluated += 1

                    await self._emit_event(
                        EvolutionEvent(
                            event_type="strategy_evaluated",
                            timestamp=time.time(),
                            generation=generation,
                            strategy_id=strategy["strategy_id"],
                            fitness=result.fitness,
                            message=f"Fitness: {result.fitness:.4f}",
                            data=asdict(result),
                        )
                    )

                # Update progress
                self.status = EvolutionStatus.EVALUATING
                fitnesses = [r.fitness for r in self.backtest_results.values()]
                self.progress.best_fitness = max(fitnesses) if fitnesses else 0.0
                self.progress.avg_fitness = sum(fitnesses) / len(fitnesses) if fitnesses else 0.0
                self.progress.elapsed_time = time.time() - self.start_time

                await self._emit_event(
                    EvolutionEvent(
                        event_type="generation_completed",
                        timestamp=time.time(),
                        generation=generation,
                        fitness=self.progress.best_fitness,
                        message=f"Generation {generation} complete. Best: {self.progress.best_fitness:.4f}",
                    )
                )

            # Evolution complete
            self.status = EvolutionStatus.COMPLETED
            await self._emit_event(
                EvolutionEvent(
                    event_type="evolution_completed",
                    timestamp=time.time(),
                    generation=num_generations,
                    fitness=self.progress.best_fitness,
                    message=f"Evolution complete! Best fitness: {self.progress.best_fitness:.4f}",
                    data={
                        "total_strategies": len(self.backtest_results),
                        "best_fitness": self.progress.best_fitness,
                        "avg_fitness": self.progress.avg_fitness,
                        "elapsed_time": self.progress.elapsed_time,
                    },
                )
            )

        except Exception as e:
            LOGGER.exception(f"Evolution failed: {e}")
            self.status = EvolutionStatus.ERROR
            await self._emit_event(
                EvolutionEvent(
                    event_type="evolution_error",
                    timestamp=time.time(),
                    generation=self.progress.current_generation,
                    message=f"Error: {str(e)}",
                )
            )

    async def _generate_llm_strategies(self, count: int, generation: int) -> List[Dict[str, Any]]:
        """Generate strategies using LLM."""
        strategies = []

        for i in range(count):
            try:
                strategy_id = f"llm_gen{generation}_strat{i+1}_{int(time.time())}"

                # Placeholder for actual LLM generation
                # In real implementation, call orchestrator
                strategy = {
                    "strategy_id": strategy_id,
                    "name": f"LLM Strategy Gen{generation}-{i+1}",
                    "source": StrategySource.LLM_GENERATED,
                    "generation": generation,
                    "code": "# Placeholder LLM-generated strategy\npass",
                    "created_at": datetime.utcnow().isoformat(),
                }

                strategies.append(strategy)

                await self._emit_event(
                    EvolutionEvent(
                        event_type="strategy_generated",
                        timestamp=time.time(),
                        generation=generation,
                        strategy_id=strategy_id,
                        message=f"Generated strategy {i+1}/{count}",
                    )
                )

            except Exception as e:
                LOGGER.error(f"Failed to generate strategy: {e}")

        return strategies

    async def _load_crawled_strategies(self) -> List[Dict[str, Any]]:
        """Load strategies from GitHub/TradingView crawlers."""
        strategies = []

        # Placeholder for crawler integration
        # In real implementation, query crawler database

        return strategies

    async def _backtest_strategy(
        self,
        strategy: Dict[str, Any],
        symbol: str,
        timeframe: str,
    ) -> BacktestResult:
        """
        Backtest strategy and calculate fitness.

        Returns full backtest results including trades, equity curve, metrics.
        """
        # Simulate backtesting (replace with real backtest engine)
        await asyncio.sleep(0.5)  # Simulate processing time

        import random

        fitness = random.uniform(0.3, 0.95)

        result = BacktestResult(
            strategy_id=strategy["strategy_id"],
            fitness=fitness,
            sharpe_ratio=fitness * 2.5,
            max_drawdown=random.uniform(0.05, 0.25),
            total_return=random.uniform(-0.1, 0.5),
            win_rate=random.uniform(0.45, 0.75),
            total_trades=random.randint(50, 300),
            profit_factor=random.uniform(0.8, 2.5),
            trades=[],
            equity_curve=[],
            metrics={},
        )

        return result

    async def _emit_event(self, event: EvolutionEvent):
        """Emit event to all subscribers."""
        event_dict = {
            "event_type": event.event_type,
            "timestamp": event.timestamp,
            "generation": event.generation,
            "strategy_id": event.strategy_id,
            "fitness": event.fitness,
            "message": event.message,
            "data": event.data,
        }

        # Add to recent events
        self.progress.recent_events.append(event_dict)
        if len(self.progress.recent_events) > 20:
            self.progress.recent_events.pop(0)

        # Send to subscribers
        for queue in self.subscribers:
            try:
                await queue.put(event_dict)
            except Exception as e:
                LOGGER.error(f"Failed to send event to subscriber: {e}")

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to real-time evolution events."""
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from events."""
        if queue in self.subscribers:
            self.subscribers.remove(queue)

    def get_progress(self) -> Dict[str, Any]:
        """Get current evolution progress."""
        return self.progress.model_dump()

    def get_hall_of_fame(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top strategies by fitness."""
        sorted_strategies = sorted(self.backtest_results.items(), key=lambda x: x[1].fitness, reverse=True)

        hall_of_fame = []
        for strategy_id, result in sorted_strategies[:limit]:
            strategy_info = next((s for s in self.strategies if s["strategy_id"] == strategy_id), {})

            hall_of_fame.append(
                {
                    "strategy_id": strategy_id,
                    "name": strategy_info.get("name", strategy_id),
                    "fitness": result.fitness,
                    "sharpe_ratio": result.sharpe_ratio,
                    "max_drawdown": result.max_drawdown,
                    "total_return": result.total_return,
                    "win_rate": result.win_rate,
                    "total_trades": result.total_trades,
                    "profit_factor": result.profit_factor,
                    "source": strategy_info.get("source", "unknown"),
                    "generation": strategy_info.get("generation", 0),
                }
            )

        return hall_of_fame

    def get_backtest_result(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed backtest result for a strategy."""
        if strategy_id in self.backtest_results:
            return asdict(self.backtest_results[strategy_id])
        return None


# Global evolution service instance
_evolution_service = EvolutionService()


def get_evolution_service() -> EvolutionService:
    """Get global evolution service instance."""
    return _evolution_service
