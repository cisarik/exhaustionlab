"""
Enhanced Intelligent Orchestrator with Database Integration

Extends IntelligentOrchestrator with:
- Real strategy examples from database
- Performance-based example selection
- Adaptive learning from validation results
- Production-grade strategy generation
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from ..llm import LocalLLMClient, PromptContext
    from ..llm.enhanced_prompts import EnhancedPromptBuilder
    from ..llm.example_loader import ExampleLoader
    from .intelligent_orchestrator import EvolutionDirective
    from .quality_scorer import StrategyQualityScorer
    from .strategy_database import StrategyDatabase
except ImportError:
    # Standalone execution
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from exhaustionlab.app.llm.enhanced_prompts import EnhancedPromptBuilder
    from exhaustionlab.app.llm.example_loader import ExampleLoader
    from exhaustionlab.app.llm.llm_client import LocalLLMClient
    from exhaustionlab.app.llm.prompts import PromptContext
    from exhaustionlab.app.meta_evolution.intelligent_orchestrator import EvolutionDirective
    from exhaustionlab.app.meta_evolution.quality_scorer import StrategyQualityScorer
    from exhaustionlab.app.meta_evolution.strategy_database import StrategyDatabase


@dataclass
class PerformanceFeedback:
    """Performance feedback from backtesting or live trading."""

    strategy_id: str
    backtest_metrics: Dict[str, float]
    validation_score: float
    execution_quality: float
    issues_found: List[str]
    improvement_suggestions: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AdaptiveLearningState:
    """State of adaptive learning system."""

    successful_patterns: List[Dict[str, Any]]
    failed_patterns: List[Dict[str, Any]]
    parameter_trends: Dict[str, List[float]]
    quality_progression: List[float]
    best_performers: List[str]  # Strategy IDs

    def update_from_feedback(self, feedback: PerformanceFeedback):
        """Update learning state based on feedback."""
        if feedback.validation_score >= 70:
            self.successful_patterns.append(
                {
                    "strategy_id": feedback.strategy_id,
                    "metrics": feedback.backtest_metrics,
                    "score": feedback.validation_score,
                    "timestamp": feedback.timestamp,
                }
            )
            self.best_performers.append(feedback.strategy_id)
        else:
            self.failed_patterns.append(
                {
                    "strategy_id": feedback.strategy_id,
                    "issues": feedback.issues_found,
                    "score": feedback.validation_score,
                    "timestamp": feedback.timestamp,
                }
            )

        self.quality_progression.append(feedback.validation_score)


class EnhancedOrchestrator:
    """
    Enhanced orchestrator with database-backed learning.

    Features:
    - Load real strategies as examples
    - Select examples based on performance
    - Adapt generation strategy based on results
    - Track quality progression over time
    - Use production-validated strategies as seeds
    """

    def __init__(self, llm_client: LocalLLMClient, db_path: Optional[str] = None):
        """Initialize enhanced orchestrator."""
        self.llm_client = llm_client
        self.db = StrategyDatabase(db_path)
        self.scorer = StrategyQualityScorer()
        self.prompt_builder = EnhancedPromptBuilder(db_path)
        self.example_loader = ExampleLoader(db_path)

        self.logger = logging.getLogger(__name__)

        # Adaptive learning state
        self.learning_state = AdaptiveLearningState(
            successful_patterns=[],
            failed_patterns=[],
            parameter_trends={},
            quality_progression=[],
            best_performers=[],
        )

        # Generation history
        self.generation_history: List[Dict[str, Any]] = []

    def generate_strategy(
        self,
        directive: EvolutionDirective,
        use_best_examples: bool = True,
        num_examples: int = 3,
        adaptation_strength: float = 0.5,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate strategy with intelligent example selection.

        Args:
            directive: Evolution directive with requirements
            use_best_examples: Use best performers as examples
            num_examples: Number of examples to include
            adaptation_strength: How much to adapt based on history (0-1)

        Returns:
            (generated_code, metadata)
        """
        self.logger.info(f"🎯 Generating {directive.strategy_type} strategy...")

        # Select intelligent examples
        examples = self._select_intelligent_examples(directive, num_examples, use_best_examples)

        self.logger.info(f"  📚 Using {len(examples)} examples (avg quality: {np.mean([e.quality_score for e in examples]):.1f})")

        # Build context with adaptive parameters
        context = self._build_adaptive_context(directive, adaptation_strength)

        # Generate prompt with examples
        prompt = self.prompt_builder.build_strategy_prompt(context, include_examples=True, num_examples=num_examples)

        self.logger.info(f"  📝 Prompt size: {len(prompt)} chars")

        # Add performance-based guidance
        if self.learning_state.quality_progression:
            guidance = self._build_adaptive_guidance()
            prompt += f"\n\n## ADAPTIVE GUIDANCE\n{guidance}\n"

        # Generate with LLM
        try:
            from ..llm.llm_client import LLMRequest
        except ImportError:
            from exhaustionlab.app.llm.llm_client import LLMRequest

        request = LLMRequest(
            prompt=prompt,
            system_prompt=self._build_system_prompt(directive),
            temperature=self._adaptive_temperature(),
            max_tokens=2000,
        )

        self.logger.info(f"  🤖 Calling LLM (temp={request.temperature:.2f})...")

        try:
            response = self.llm_client.generate(request)

            if response.success and response.code_blocks:
                code = response.code_blocks[0]

                metadata = {
                    "directive": asdict(directive),
                    "examples_used": [e.name for e in examples],
                    "generation_time": response.request_time,
                    "prompt_size": len(prompt),
                    "code_size": len(code),
                    "temperature": request.temperature,
                    "adaptation_strength": adaptation_strength,
                    "timestamp": datetime.now().isoformat(),
                }

                # Track generation
                self.generation_history.append(metadata)

                self.logger.info(f"  ✅ Generated {len(code)} chars of code")

                return code, metadata
            else:
                error_msg = response.error_message or "No code generated"
                self.logger.error(f"  ❌ Generation failed: {error_msg}")
                return "", {"error": error_msg}

        except Exception as e:
            self.logger.error(f"  ❌ Exception during generation: {e}")
            return "", {"error": str(e)}

    def validate_and_improve(
        self,
        code: str,
        metadata: Dict[str, Any],
        backtest_results: Optional[Dict[str, float]] = None,
    ) -> PerformanceFeedback:
        """
        Validate generated strategy and provide feedback.

        Args:
            code: Generated strategy code
            metadata: Generation metadata
            backtest_results: Optional backtest metrics

        Returns:
            Performance feedback
        """
        self.logger.info("🔍 Validating generated strategy...")

        # Code validation
        try:
            from ..llm.validators import PyneCoreValidator
        except ImportError:
            from exhaustionlab.app.llm.validators import PyneCoreValidator
        validator = PyneCoreValidator()

        syntax_valid = validator.validate_syntax(code)
        structure = validator.validate_structure(code)
        api_valid = validator.validate_api_usage(code)
        quality_score = validator.calculate_quality_score(code)

        self.logger.info(f"  Code quality: {quality_score}/100")

        # Collect issues
        issues = []
        if not syntax_valid:
            issues.append("Syntax errors found")
        if not api_valid:
            issues.append("Invalid API usage")
        if not structure.get("has_main_logic"):
            issues.append("Missing main logic")

        # Calculate validation score
        validation_score = quality_score

        if backtest_results:
            # Incorporate backtest performance
            sharpe = backtest_results.get("sharpe_ratio", 0)
            drawdown = backtest_results.get("max_drawdown", 1)
            win_rate = backtest_results.get("win_rate", 0)

            performance_score = min(100, sharpe * 40) * 0.4 + (1 - drawdown) * 100 * 0.3 + win_rate * 100 * 0.3  # Sharpe contribution  # Drawdown contribution  # Win rate contribution

            validation_score = quality_score * 0.4 + performance_score * 0.6

            self.logger.info(f"  Performance score: {performance_score:.1f}/100")

        self.logger.info(f"  Overall validation: {validation_score:.1f}/100")

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(code, quality_score, backtest_results, issues)

        # Create feedback
        feedback = PerformanceFeedback(
            strategy_id=metadata.get("timestamp", "unknown"),
            backtest_metrics=backtest_results or {},
            validation_score=validation_score,
            execution_quality=quality_score / 100.0,
            issues_found=issues,
            improvement_suggestions=suggestions,
        )

        # Update learning state
        self.learning_state.update_from_feedback(feedback)

        return feedback

    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get statistics about adaptive learning."""
        if not self.learning_state.quality_progression:
            return {
                "total_generations": 0,
                "avg_quality": 0,
                "improvement_trend": 0,
                "success_rate": 0,
            }

        progression = self.learning_state.quality_progression

        # Calculate improvement trend
        if len(progression) > 1:
            recent = progression[-5:]  # Last 5
            early = progression[:5]  # First 5
            trend = np.mean(recent) - np.mean(early)
        else:
            trend = 0

        success_count = len(self.learning_state.successful_patterns)
        total_count = len(progression)

        return {
            "total_generations": total_count,
            "avg_quality": np.mean(progression),
            "best_quality": np.max(progression),
            "recent_avg": (np.mean(progression[-10:]) if len(progression) >= 10 else np.mean(progression)),
            "improvement_trend": trend,
            "success_rate": success_count / total_count if total_count > 0 else 0,
            "successful_strategies": success_count,
            "failed_strategies": len(self.learning_state.failed_patterns),
        }

    def _select_intelligent_examples(self, directive: EvolutionDirective, num_examples: int, use_best: bool) -> List[Any]:
        """Select most relevant examples based on directive and performance."""

        if use_best and self.learning_state.best_performers:
            # Use best performers from learning history
            best_ids = self.learning_state.best_performers[-num_examples:]
            examples = []
            for sid in best_ids:
                # Try to load from database (would need strategy ID mapping)
                pass

            if examples:
                return examples

        # Fall back to database search
        # Map directive to search criteria
        strategy_type = str(directive.strategy_type).lower()

        return self.example_loader.get_examples_by_type(strategy_type, count=num_examples)

    def _build_adaptive_context(self, directive: EvolutionDirective, adaptation_strength: float) -> PromptContext:
        """Build context with adaptive parameters."""

        # Base context from directive
        context = PromptContext(
            strategy_type="strategy",
            market_focus=[str(directive.market_focus).lower()],
            timeframe=directive.time_horizon,
            indicators_to_include=self._select_indicators(directive),
            signal_logic=str(directive.strategy_type).lower(),
            risk_profile=directive.risk_tolerance,
        )

        # Adapt based on learning history
        if self.learning_state.successful_patterns and adaptation_strength > 0:
            # Extract successful patterns
            successful_indicators = []
            for pattern in self.learning_state.successful_patterns[-5:]:
                # Extract indicators from successful strategies
                pass  # Would need to parse metrics

            # Blend with directive indicators
            if successful_indicators:
                context.indicators_to_include = list(set(context.indicators_to_include + successful_indicators))

        return context

    def _select_indicators(self, directive: EvolutionDirective) -> List[str]:
        """Select appropriate indicators based on directive."""
        type_mapping = {
            "momentum": ["RSI", "MACD", "STOCH"],
            "trend_following": ["EMA", "SMA", "ADX"],
            "mean_reversion": ["RSI", "BB", "STOCH"],
            "breakout": ["BB", "ATR", "DONCHIAN"],
        }

        strategy_type = str(directive.strategy_type).lower()
        return type_mapping.get(strategy_type, ["EMA", "RSI"])

    def _adaptive_temperature(self) -> float:
        """Calculate adaptive temperature based on learning progress."""
        if not self.learning_state.quality_progression:
            return 0.7  # Default

        recent_quality = np.mean(self.learning_state.quality_progression[-5:])

        if recent_quality >= 75:
            # High quality → lower temperature (exploit)
            return 0.5
        elif recent_quality >= 60:
            # Medium quality → balanced
            return 0.7
        else:
            # Low quality → higher temperature (explore)
            return 0.9

    def _build_system_prompt(self, directive: EvolutionDirective) -> str:
        """Build system prompt based on directive."""
        return f"""You are an expert quantitative trading strategist and Pine Script developer.

Your task: Create a {directive.strategy_type} strategy for {directive.market_focus} markets.

Requirements:
- Risk tolerance: {directive.risk_tolerance}
- Time horizon: {directive.time_horizon}
- Performance targets: {directive.performance_targets}

Generate production-ready PyneCore code that meets these specifications."""

    def _build_adaptive_guidance(self) -> str:
        """Build guidance based on learning history."""
        if not self.learning_state.quality_progression:
            return "No prior feedback available. Focus on code quality and correctness."

        recent_avg = np.mean(self.learning_state.quality_progression[-10:])

        guidance = f"Recent average quality: {recent_avg:.1f}/100\n\n"

        if recent_avg >= 75:
            guidance += "✅ Recent strategies have been high quality. Continue this approach but add innovation."
        elif recent_avg >= 60:
            guidance += "⚠️ Recent quality is moderate. Focus on improving validation scores and reducing issues."
        else:
            guidance += "❌ Recent quality is low. Review fundamentals: syntax correctness, API usage, and logic clarity."

        # Add specific improvements from failed patterns
        if self.learning_state.failed_patterns:
            common_issues = {}
            for pattern in self.learning_state.failed_patterns[-5:]:
                for issue in pattern["issues"]:
                    common_issues[issue] = common_issues.get(issue, 0) + 1

            if common_issues:
                guidance += "\n\nCommon issues to avoid:\n"
                for issue, count in sorted(common_issues.items(), key=lambda x: x[1], reverse=True)[:3]:
                    guidance += f"  - {issue} (occurred {count} times)\n"

        return guidance

    def _generate_suggestions(
        self,
        code: str,
        quality_score: float,
        backtest_results: Optional[Dict],
        issues: List[str],
    ) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if quality_score < 70:
            suggestions.append("Improve code quality: add comments, fix syntax, use proper API")

        if backtest_results:
            sharpe = backtest_results.get("sharpe_ratio", 0)
            drawdown = backtest_results.get("max_drawdown", 1)

            if sharpe < 1.0:
                suggestions.append("Improve Sharpe ratio: refine entry/exit conditions or risk management")

            if drawdown > 0.2:
                suggestions.append("Reduce drawdown: add stop loss, position sizing, or trend filters")

        if "Syntax errors" in issues:
            suggestions.append("Fix syntax errors before testing")

        if "Invalid API usage" in issues:
            suggestions.append("Review PyneCore API documentation and use correct functions")

        return suggestions


# Convenience function
def create_enhanced_orchestrator(
    llm_client: Optional[LocalLLMClient] = None,
) -> EnhancedOrchestrator:
    """Create enhanced orchestrator with default settings."""
    if llm_client is None:
        llm_client = LocalLLMClient()

    return EnhancedOrchestrator(llm_client)


if __name__ == "__main__":
    # Test enhanced orchestrator
    logging.basicConfig(level=logging.INFO)

    print("🚀 ENHANCED ORCHESTRATOR TEST\n")
    print("=" * 70)

    # Create orchestrator
    orch = create_enhanced_orchestrator()

    # Show learning statistics
    stats = orch.get_learning_statistics()
    print("\n📊 Learning Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Show database statistics
    db_stats = orch.example_loader.get_statistics()
    print("\n📚 Example Database:")
    print(f"  Total with code: {db_stats['total_with_code']}")
    print(f"  Avg quality: {db_stats['avg_quality']}")
    print(f"  Top indicators: {list(db_stats['indicators_used'].keys())[:5]}")

    print("\n✅ Enhanced orchestrator initialized successfully!")
