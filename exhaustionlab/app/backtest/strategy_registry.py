"""
Persistent Strategy Registry with Version Control

Manages strategy storage, versioning, deployment readiness,
and multi-market fitness tracking.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .strategy_genome import StrategyGenome


@dataclass
class StrategyMetrics:
    """Real-world trading metrics for strategy evaluation."""

    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_trade: float
    num_trades: int
    markets_tested: List[str]
    timeframes_tested: List[str]

    # Real-time deployment metrics
    slippage_impact: float = 0.0
    execution_delay_ms: float = 0.0
    market_impact: float = 0.0

    # Robustness metrics
    correlation_to_benchmark: float = 0.0
    volatility_adjusted_return: float = 0.0
    downside_deviation: float = 0.0

    def composite_fitness(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Calculate composite fitness score for strategy comparison."""
        w = weights or {
            "pnl": 0.3,
            "sharpe": 0.25,
            "drawdown": 0.2,
            "win_rate": 0.15,
            "consistency": 0.1,
        }

        # Normalized metrics (0-1 scale, higher is better)
        normalized_pnl = min(1.0, max(0.0, self.total_pnl / 1000))  # Assuming 1000% is excellent
        normalized_sharpe = min(1.0, max(0.0, self.sharpe_ratio / 3.0))  # Sharpe > 3 is excellent
        normalized_drawdown = max(0.0, 1.0 - (self.max_drawdown / 0.5))  # 50% DD is terrible
        normalized_winrate = self.win_rate
        consistency = 1.0 - (self.downside_deviation / self.volatility_adjusted_return) if self.volatility_adjusted_return > 0 else 0

        fitness = w["pnl"] * normalized_pnl + w["sharpe"] * normalized_sharpe + w["drawdown"] * normalized_drawdown + w["win_rate"] * normalized_winrate + w["consistency"] * min(1.0, max(0.0, consistency))

        return fitness


@dataclass
class StrategyVersion:
    """Version control for strategies."""

    version_id: str
    parent_version_id: Optional[str]
    version_number: int
    created_at: datetime
    commit_hash: str  # Git-like hash of strategy content
    description: str
    tags: List[str]
    deployment_ready: bool = False
    validation_passed: bool = False


class StrategyRegistry:
    """Persistent storage and management of evolved strategies."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path.home() / ".exhaustionlab" / "strategies.db"
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for strategy storage."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS strategies (
                    strategy_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    pyne_code TEXT NOT NULL,
                    pine_code TEXT,
                    parameters TEXT NOT NULL,
                    current_version_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    parent_strategy_id TEXT,
                    generation INTEGER DEFAULT 0,
                    fitness REAL DEFAULT 0.0,
                    deployment_score REAL DEFAULT 0.0,
                    total_tests INTEGER DEFAULT 0,
                    markets_tested TEXT,  -- JSON array
                    tags TEXT  -- JSON array
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_versions (
                    version_id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    version_number INTEGER NOT NULL,
                    parent_version_id TEXT,
                    commit_hash TEXT NOT NULL,
                    pyne_code TEXT NOT NULL,
                    parameters TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT,
                    tags TEXT,
                    deployment_ready BOOLEAN DEFAULT FALSE,
                    validation_passed BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (strategy_id) REFERENCES strategies (strategy_id)
                )
            """
            )

            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS strategy_metrics (
                    metrics_id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    version_id TEXT NOT NULL,
                    market TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    test_start TIMESTAMP,
                    test_end TIMESTAMP,
                    metrics_data TEXT NOT NULL,  -- JSON serialized StrategyMetrics
                    FOREIGN KEY (strategy_id) REFERENCES strategies (strategy_id),
                    FOREIGN KEY (version_id) REFERENCES strategy_versions (version_id)
                )
            """
            )

            conn.executescript(
                """
                CREATE INDEX IF NOT EXISTS idx_strategy_fitness
                    ON strategies(fitness DESC);
                CREATE INDEX IF NOT EXISTS idx_strategy_deployment
                    ON strategies(deployment_score DESC);
                CREATE INDEX IF NOT EXISTS idx_metrics_market
                    ON strategy_metrics(market, timeframe);
            """
            )

    def save_strategy(self, genome: StrategyGenome, version_description: str = "") -> str:
        """Save strategy with version control."""
        strategy_id = str(uuid.uuid4())
        commit_hash = self._generate_commit_hash(genome.pyne_code, genome.parameters)

        with sqlite3.connect(self.db_path) as conn:
            # Insert main strategy
            conn.execute(
                """
                INSERT INTO strategies
                (strategy_id, name, description, pyne_code, pine_code, parameters,
                 parent_strategy_id, generation, fitness, total_tests, markets_tested, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    strategy_id,
                    genome.name,
                    genome.description,
                    genome.pyne_code,
                    genome.pine_code,
                    json.dumps(genome.parameters),
                    genome.parent_ids[0] if genome.parent_ids else None,
                    genome.generation,
                    genome.fitness,
                    0,  # total_tests starts at 0
                    json.dumps([]),  # markets_tested empty initially
                    json.dumps([]),  # tags empty initially
                ),
            )

            # Create initial version
            version_id = self._create_version(
                conn,
                strategy_id,
                1,
                None,
                commit_hash,
                genome.pyne_code,
                genome.parameters,
                version_description,
            )

            # Update current version
            conn.execute(
                "UPDATE strategies SET current_version_id = ? WHERE strategy_id = ?",
                (version_id, strategy_id),
            )

        return strategy_id

    def _create_version(
        self,
        conn,
        strategy_id: str,
        version_number: int,
        parent_version_id: Optional[str],
        commit_hash: str,
        pyne_code: str,
        parameters: Dict,
        description: str,
    ) -> str:
        """Create new strategy version."""
        version_id = str(uuid.uuid4())

        conn.execute(
            """
            INSERT INTO strategy_versions
            (version_id, strategy_id, version_number, parent_version_id,
             commit_hash, pyne_code, parameters, description, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                version_id,
                strategy_id,
                version_number,
                parent_version_id,
                commit_hash,
                pyne_code,
                json.dumps(parameters),
                description,
                json.dumps([]),
            ),
        )

        return version_id

    def record_strategy_metrics(
        self,
        strategy_id: str,
        version_id: str,
        market: str,
        timeframe: str,
        metrics: StrategyMetrics,
    ):
        """Record backtesting metrics for strategy on specific market/timeframe."""
        metrics_id = str(uuid.uuid4())

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO strategy_metrics
                (metrics_id, strategy_id, version_id, market, timeframe,
                 test_start, test_end, metrics_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    metrics_id,
                    strategy_id,
                    version_id,
                    market,
                    timeframe,
                    datetime.now(),
                    datetime.now(),
                    json.dumps(asdict(metrics)),
                ),
            )

            # Update strategy's aggregate metrics
            conn.execute(
                """
                UPDATE strategies
                SET fitness = COALESCE((
                    SELECT AVG(json_extract(metrics_data, '$.composite_fitness'))
                    FROM strategy_metrics
                    WHERE strategy_id = ? AND version_id = ?
                ), 0.0),
                total_tests = COALESCE((
                    SELECT COUNT(*) FROM strategy_metrics
                    WHERE strategy_id = ? AND version_id = ?
                ), 0)
                WHERE strategy_id = ?
            """,
                (strategy_id, version_id, strategy_id, version_id, strategy_id),
            )

    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve complete strategy information."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM strategies WHERE strategy_id = ?", (strategy_id,)).fetchone()

            if row:
                strategy = dict(row)
                strategy["parameters"] = json.loads(strategy["parameters"])
                strategy["markets_tested"] = json.loads(strategy.get("markets_tested", "[]"))
                strategy["tags"] = json.loads(strategy.get("tags", "[]"))
                return strategy
        return None

    def get_best_strategies(self, limit: int = 10, min_tests: int = 3, markets: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get top strategies by comprehensive fitness with robustness requirements."""
        query = """
            SELECT s.*,
                   COUNT(sm.metrics_id) as test_count,
                   COUNT(DISTINCT sm.market) as market_diversity
            FROM strategies s
            LEFT JOIN strategy_metrics sm ON s.strategy_id = sm.strategy_id
            WHERE s.fitness > 0
        """
        params = []

        if min_tests > 0:
            query += " AND (SELECT COUNT(*) FROM strategy_metrics WHERE strategy_id = s.strategy_id) >= ?"
            params.append(min_tests)

        if markets:
            placeholders = ",".join(["?" for _ in markets])
            query += f" AND s.strategy_id IN (SELECT strategy_id FROM strategy_metrics WHERE market IN ({placeholders}))"
            params.extend(markets)

        query += " GROUP BY s.strategy_id ORDER BY s.fitness DESC, market_diversity DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

            strategies = []
            for row in rows:
                strategy = dict(row)
                strategy["parameters"] = json.loads(strategy["parameters"])
                strategy["markets_tested"] = json.loads(strategy.get("markets_tested", "[]"))
                strategies.append(strategy)

            return strategies

    def update_deployment_readiness(
        self,
        strategy_id: str,
        version_id: str,
        ready: bool,
        validation_results: Optional[Dict] = None,
    ):
        """Mark strategy version as ready for real-time deployment."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                UPDATE strategy_versions
                SET deployment_ready = ?, validation_passed = ?
                WHERE version_id = ?
            """,
                (ready, validation_results is not None, version_id),
            )

            # Update parent strategy deployment score
            if ready:
                conn.execute(
                    """
                    UPDATE strategies
                    SET deployment_score = (
                        SELECT AVG(fitness)
                        FROM strategy_metrics sm
                        JOIN strategy_versions sv ON sm.version_id = sv.version_id
                        WHERE sm.strategy_id = ? AND sv.deployment_ready = TRUE
                    )
                    WHERE strategy_id = ?
                """,
                    (strategy_id, strategy_id),
                )

    def get_deployment_ready_strategies(self, min_markets: int = 2) -> List[Dict[str, Any]]:
        """Get strategies validated for real-time trading."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT s.*,
                       COUNT(DISTINCT sm.market) as tested_markets,
                       COUNT(sm.metrics_id) as total_tests
                FROM strategies s
                JOIN strategy_versions sv ON s.current_version_id = sv.version_id
                LEFT JOIN strategy_metrics sm ON s.strategy_id = sm.strategy_id
                WHERE sv.deployment_ready = TRUE
                  AND sv.validation_passed = TRUE
                GROUP BY s.strategy_id
                HAVING tested_markets >= ?
                ORDER BY s.deployment_score DESC, tested_markets DESC
            """,
                (min_markets,),
            ).fetchall()

            strategies = []
            for row in rows:
                strategy = dict(row)
                strategy["parameters"] = json.loads(strategy["parameters"])
                strategies.append(strategy)

            return strategies

    def get_top_strategies(self, limit: int = 10, include_metrics: bool = True) -> List[Dict[str, Any]]:
        """Return top strategies ordered by composite fitness."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT s.*
                FROM strategies s
                ORDER BY s.fitness DESC, s.generation DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()

        strategies: List[Dict[str, Any]] = []
        for row in rows:
            strategy = dict(row)
            strategy["parameters"] = json.loads(strategy["parameters"])
            strategy["markets_tested"] = json.loads(strategy.get("markets_tested", "[]"))
            strategy["tags"] = json.loads(strategy.get("tags", "[]"))
            if include_metrics:
                strategy["recent_metrics"] = self.get_recent_metrics(strategy["strategy_id"], 3)
            strategies.append(strategy)

        return strategies

    def get_recent_metrics(self, strategy_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetch most recent backtest metrics for a strategy."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM strategy_metrics
                WHERE strategy_id = ?
                ORDER BY test_end DESC
                LIMIT ?
            """,
                (strategy_id, limit),
            ).fetchall()

        metrics: List[Dict[str, Any]] = []
        for row in rows:
            record = dict(row)
            metrics_data = json.loads(record["metrics_data"])
            record["metrics_data"] = metrics_data
            metrics.append(record)

        return metrics

    def get_evolution_timeline(self, limit: int = 120) -> List[Dict[str, Any]]:
        """Return chronological view of strategies for visualization."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT strategy_id, name, generation, fitness, created_at
                FROM strategies
                ORDER BY datetime(created_at) ASC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()

        timeline = []
        for row in rows:
            entry = dict(row)
            timeline.append(entry)
        return timeline

    def _generate_commit_hash(self, pyne_code: str, parameters: Dict) -> str:
        """Generate git-like commit hash for strategy versioning."""
        content = f"{pyne_code}{json.dumps(parameters, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:12]

    def create_strategy_variant(self, strategy_id: str, variant_config: Dict[str, Any]) -> str:
        """Create x variants of a strategy with different parameter configurations."""
        strategy = self.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")

        num_variants = variant_config.get("count", 3)
        mutation_types = variant_config.get("mutation_types", ["parameter", "logic"])
        markets_focus = variant_config.get("markets_focus", ["BTCUSDT"])

        from .llm_evolution import LLMStrategyMutator

        mutator = LLMStrategyMutator()

        variant_ids = []
        for i in range(num_variants):
            # Create genome from strategy
            base_genome = StrategyGenome(
                name=f"{strategy['name']}_variant_{i+1}",
                description=f"Variant {i+1} of {strategy['name']}",
                pine_code=strategy["pine_code"],
                pyne_code=strategy["pyne_code"],
                parameters=strategy["parameters"].copy(),
                generation=strategy["generation"] + 1,
                parent_ids=[strategy_id],
            )

            # Apply mutation
            mutation_type = mutation_types[i % len(mutation_types)]
            variant_genome = mutator.mutate_strategy(base_genome, mutation_type)

            # Add variant-specific parameters
            variant_genome.parameters.update(
                {
                    "variant_num": i + 1,
                    "markets_focus": markets_focus,
                    "mutation_applied": mutation_type,
                }
            )

            # Save variant
            variant_id = self.save_strategy(
                variant_genome,
                f"Variant {i+1} via {mutation_type} for markets {markets_focus}",
            )
            variant_ids.append(variant_id)

        return variant_ids
