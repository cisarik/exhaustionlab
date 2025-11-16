"""
Backend services that power the ExhaustionLab web UI.

These helpers translate on-disk artifacts (LLM debug logs),
strategy registry records, and evolution statistics into
JSON-friendly objects that the FastAPI layer can expose.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..app.backtest.multi_market_evaluator import MultiMarketEvaluator
from ..app.backtest.strategy_registry import StrategyRegistry, StrategyMetrics


LOGGER = logging.getLogger(__name__)


class LLMMessage(BaseModel):
    """Single message within an LLM debugging session."""

    role: str
    content: str
    kind: Optional[str] = None
    created_at: Optional[datetime] = None
    token_estimate: Optional[int] = None


class LLMSession(BaseModel):
    """Structured representation of a debugging session."""

    session_id: str
    started_at: datetime
    model: Optional[str] = None
    temperature: Optional[float] = None
    prompt_chars: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    messages: List[LLMMessage] = Field(default_factory=list)

    def to_summary(self) -> "LLMSessionSummary":
        """Return lightweight summary used by list view."""
        preview_source = next(
            (m for m in reversed(self.messages) if m.role == "assistant"),
            self.messages[-1] if self.messages else None,
        )
        preview = (preview_source.content if preview_source else "")[:200].strip()
        return LLMSessionSummary(
            session_id=self.session_id,
            started_at=self.started_at,
            model=self.model,
            temperature=self.temperature,
            prompt_chars=self.prompt_chars,
            preview=preview,
            metadata=self.metadata,
        )


class LLMSessionSummary(BaseModel):
    """Metadata returned when listing sessions."""

    session_id: str
    started_at: datetime
    model: Optional[str] = None
    temperature: Optional[float] = None
    prompt_chars: Optional[int] = None
    preview: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StrategyMetricRecord(BaseModel):
    """Single stored metrics row."""

    metrics_id: str
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None
    market: str
    timeframe: str
    metrics_data: Dict[str, Any]


class StrategySummary(BaseModel):
    """High-level card shown in hall of fame grid."""

    strategy_id: str
    name: str
    description: Optional[str] = None
    generation: int
    fitness: float
    deployment_score: Optional[float] = None
    total_tests: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    markets_tested: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    recent_metrics: List[StrategyMetricRecord] = Field(default_factory=list)


class SimulationResult(BaseModel):
    """Response payload once a strategy simulation finishes."""

    status: str
    strategy_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    detail: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None


class EvolutionPoint(BaseModel):
    """Timeline point for the evolution visualizer."""

    strategy_id: str
    name: str
    timestamp: Optional[datetime]
    generation: int
    fitness: float


class EvolutionEvent(BaseModel):
    """Headline item displayed next to the chart."""

    title: str
    subtitle: str
    timestamp: Optional[datetime]


class EvolutionOverview(BaseModel):
    """Aggregate statistics for the evolution dashboard."""

    total_strategies: int
    best_fitness: float
    avg_fitness: float
    velocity: float
    timeline: List[EvolutionPoint]
    recent_events: List[EvolutionEvent]
    phase_breakdown: Dict[str, int]


class LLMDebugLogStore:
    """Parses recorded debugger sessions for chat-style visualization."""

    def __init__(self, root_dir: Path | str = "llm_debug_logs"):
        self.root = Path(root_dir)

    def list_sessions(self, limit: int = 12) -> List[LLMSessionSummary]:
        """Return the most recent N sessions."""
        sessions: List[LLMSessionSummary] = []
        if not self.root.exists():
            return sessions

        for directory in sorted(self.root.iterdir(), reverse=True):
            if not directory.is_dir():
                continue
            session = self._parse_session(directory)
            if not session:
                continue
            sessions.append(session.to_summary())
            if len(sessions) >= limit:
                break
        return sessions

    def get_session(self, session_id: str) -> Optional[LLMSession]:
        """Return the structured session or None if not available."""
        candidate = self.root / session_id
        if not candidate.exists():
            # allow bare timestamp lookups even if directory contains prefix
            fallback = next(
                (
                    p
                    for p in self.root.iterdir()
                    if p.is_dir() and p.name.endswith(session_id)
                ),
                None,
            )
            candidate = fallback or candidate

        if not candidate or not candidate.exists():
            return None
        return self._parse_session(candidate)

    def _parse_session(self, directory: Path) -> Optional[LLMSession]:
        prompt_file = directory / "01_prompt.txt"
        response_file = directory / "03_response_raw.txt"
        request_file = directory / "02_request.json"

        if not prompt_file.exists():
            return None

        prompt_text = prompt_file.read_text().strip()
        response_text = (
            response_file.read_text().strip() if response_file.exists() else ""
        )
        metadata: Dict[str, Any] = {}
        if request_file.exists():
            try:
                metadata = json.loads(request_file.read_text())
            except json.JSONDecodeError:
                metadata = {}

        started_at = self._infer_timestamp(directory)
        prompt_chars = len(prompt_text)
        model = metadata.get("model")
        temperature = metadata.get("temperature")

        messages = []
        if system_prompt := metadata.get("system_prompt"):
            messages.append(
                LLMMessage(
                    role="system",
                    content=system_prompt.strip(),
                    kind="system",
                    token_estimate=self._estimate_tokens(system_prompt),
                    created_at=started_at,
                )
            )
        messages.append(
            LLMMessage(
                role="user",
                content=prompt_text,
                kind="prompt",
                token_estimate=self._estimate_tokens(prompt_text),
                created_at=started_at,
            )
        )
        if response_text:
            messages.append(
                LLMMessage(
                    role="assistant",
                    content=response_text,
                    kind="response",
                    token_estimate=self._estimate_tokens(response_text),
                    created_at=started_at,
                )
            )

        return LLMSession(
            session_id=directory.name,
            started_at=started_at,
            model=model,
            temperature=temperature,
            prompt_chars=prompt_chars,
            metadata=metadata,
            messages=messages,
        )

    def _infer_timestamp(self, directory: Path) -> datetime:
        name = directory.name
        for token in name.split("_"):
            if len(token) == 15 and token.isdigit():
                try:
                    return datetime.strptime(token, "%Y%m%d%H%M%S")
                except ValueError:
                    continue
            if len(token) == 9 and token.isdigit():
                continue
        # Known naming `session_YYYYMMDD_HHMMSS`
        parts = name.split("_")
        if len(parts) >= 3 and parts[1].isdigit() and parts[2].isdigit():
            try:
                return datetime.strptime(f"{parts[1]}_{parts[2]}", "%Y%m%d_%H%M%S")
            except ValueError:
                pass
        # Default to directory mtime
        return datetime.fromtimestamp(directory.stat().st_mtime)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Very rough heuristic for token counts."""
        if not text:
            return 0
        return max(1, len(text) // 4)


class StrategyDashboardService:
    """High-level API around the registry + evaluation pipeline."""

    def __init__(self, registry: Optional[StrategyRegistry] = None):
        self.registry = registry or StrategyRegistry()
        self.evaluator = MultiMarketEvaluator(self.registry)

    def list_top_strategies(self, limit: int = 8) -> List[StrategySummary]:
        records = self.registry.get_top_strategies(limit=limit)
        summaries: List[StrategySummary] = []
        for record in records:
            summaries.append(self._map_strategy_record(record))
        return summaries

    def get_strategy_detail(self, strategy_id: str) -> Optional[StrategySummary]:
        record = self.registry.get_strategy(strategy_id)
        if not record:
            return None
        record["recent_metrics"] = self.registry.get_recent_metrics(strategy_id, 6)
        return self._map_strategy_record(record)

    async def run_simulation(self, strategy_id: str) -> SimulationResult:
        """Kick off a multi-market evaluation and return structured response."""
        start = datetime.utcnow()
        strategy = self.registry.get_strategy(strategy_id)
        if not strategy:
            return SimulationResult(
                status="error",
                strategy_id=strategy_id,
                started_at=start,
                completed_at=datetime.utcnow(),
                detail="Strategy not found",
            )

        version_id = strategy.get("current_version_id")
        if not version_id:
            return SimulationResult(
                status="error",
                strategy_id=strategy_id,
                started_at=start,
                completed_at=datetime.utcnow(),
                detail="Strategy has no tracked version",
            )

        try:
            metrics: StrategyMetrics = await self.evaluator.evaluate_strategy(
                strategy_id=strategy_id,
                version_id=version_id,
            )
            payload = asdict(metrics)
            return SimulationResult(
                status="completed",
                strategy_id=strategy_id,
                started_at=start,
                completed_at=datetime.utcnow(),
                metrics=payload,
            )
        except Exception as exc:
            LOGGER.exception("Simulation failed for %s", strategy_id)
            return SimulationResult(
                status="error",
                strategy_id=strategy_id,
                started_at=start,
                completed_at=datetime.utcnow(),
                detail=str(exc),
            )

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    @staticmethod
    def _map_metric_row(row: Dict[str, Any]) -> StrategyMetricRecord:
        return StrategyMetricRecord(
            metrics_id=row["metrics_id"],
            test_start=StrategyDashboardService._parse_dt(row.get("test_start")),
            test_end=StrategyDashboardService._parse_dt(row.get("test_end")),
            market=row.get("market", ""),
            timeframe=row.get("timeframe", ""),
            metrics_data=row.get("metrics_data", {}),
        )

    def _map_strategy_record(self, record: Dict[str, Any]) -> StrategySummary:
        recent_metrics = [
            self._map_metric_row(row) for row in record.get("recent_metrics", [])
        ]
        return StrategySummary(
            strategy_id=record["strategy_id"],
            name=record["name"],
            description=record.get("description"),
            generation=record.get("generation", 0),
            fitness=record.get("fitness", 0.0),
            deployment_score=record.get("deployment_score"),
            total_tests=record.get("total_tests", 0),
            created_at=self._parse_dt(record.get("created_at")),
            updated_at=self._parse_dt(record.get("updated_at")),
            markets_tested=record.get("markets_tested") or [],
            tags=record.get("tags") or [],
            parameters=record.get("parameters") or {},
            recent_metrics=recent_metrics,
        )


class EvolutionAnalytics:
    """Aggregates registry data for the evolution visualizer."""

    def __init__(self, registry: StrategyRegistry):
        self.registry = registry

    def build_overview(self) -> EvolutionOverview:
        timeline_rows = self.registry.get_evolution_timeline(limit=160)
        timeline: List[EvolutionPoint] = [
            EvolutionPoint(
                strategy_id=row["strategy_id"],
                name=row["name"],
                timestamp=self._parse_dt(row.get("created_at")),
                generation=row.get("generation", 0),
                fitness=row.get("fitness", 0.0),
            )
            for row in timeline_rows
        ]

        total = len(timeline)
        best = max((p.fitness for p in timeline), default=0.0)
        avg = sum(p.fitness for p in timeline) / total if total else 0.0
        velocity = self._compute_velocity(timeline)
        phase_counts = self._phase_breakdown(timeline)
        events = self._build_events(timeline)

        return EvolutionOverview(
            total_strategies=total,
            best_fitness=round(best, 4),
            avg_fitness=round(avg, 4),
            velocity=velocity,
            timeline=timeline,
            recent_events=events,
            phase_breakdown=phase_counts,
        )

    @staticmethod
    def _compute_velocity(points: List[EvolutionPoint]) -> float:
        """Compare the last 5 fitness scores vs the previous 5."""
        if len(points) < 6:
            return 0.0
        last = [p.fitness for p in points[-5:]]
        prev = [p.fitness for p in points[-10:-5]] if len(points) >= 10 else []
        if not prev:
            return sum(last) / len(last) if last else 0.0
        last_avg = sum(last) / len(last)
        prev_avg = sum(prev) / len(prev)
        return round(last_avg - prev_avg, 4)

    @staticmethod
    def _phase_breakdown(points: List[EvolutionPoint]) -> Dict[str, int]:
        buckets = {"exploration": 0, "optimization": 0, "validation": 0}
        for point in points:
            gen = point.generation
            if gen <= 5:
                buckets["exploration"] += 1
            elif gen <= 15:
                buckets["optimization"] += 1
            else:
                buckets["validation"] += 1
        return buckets

    @staticmethod
    def _build_events(points: List[EvolutionPoint]) -> List[EvolutionEvent]:
        events: List[EvolutionEvent] = []
        for point in points[-5:]:
            events.append(
                EvolutionEvent(
                    title=point.name,
                    subtitle=f"Gen {point.generation} • Fitness {point.fitness:.3f}",
                    timestamp=point.timestamp,
                )
            )
        return events

    @staticmethod
    def _parse_dt(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None
