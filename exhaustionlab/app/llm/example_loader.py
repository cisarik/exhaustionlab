"""
Example Loader for LLM Prompts

Loads real trading strategies from database and formats them
for inclusion in LLM prompts to improve generation quality.
"""

from __future__ import annotations

import logging

# Import database
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from exhaustionlab.app.meta_evolution.strategy_database import Strategy, StrategyDatabase


@dataclass
class StrategyExample:
    """Formatted strategy example for LLM prompt."""

    name: str
    description: str
    code_snippet: str
    indicators: List[str]
    features: Dict[str, bool]
    quality_score: float
    complexity: str

    def to_prompt_format(self, max_lines: int = 50) -> str:
        """Format example for LLM prompt."""
        # Truncate code if too long
        code_lines = self.code_snippet.split("\n")
        if len(code_lines) > max_lines:
            code_snippet = "\n".join(code_lines[:max_lines]) + "\n// ... (truncated)"
        else:
            code_snippet = self.code_snippet

        return f"""
### Example: {self.name} (Quality: {self.quality_score:.1f}/100, Complexity: {self.complexity})

**Description**: {self.description or 'Advanced trading strategy'}

**Indicators Used**: {', '.join(self.indicators) if self.indicators else 'Various'}

**Features**:
{self._format_features()}

**Code Sample**:
```pine
{code_snippet}
```
"""

    def _format_features(self) -> str:
        """Format features list."""
        if not self.features:
            return "- Standard indicator logic"

        active_features = [k.replace("_", " ").title() for k, v in self.features.items() if v]
        if not active_features:
            return "- Standard indicator logic"

        return "\n".join(f"- {f}" for f in active_features)


class ExampleLoader:
    """
    Load and format trading strategy examples from database.

    Provides intelligent selection of examples based on:
    - Strategy type (indicator, signal, strategy)
    - Indicators used
    - Quality score
    - Code complexity
    - Market focus
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize example loader."""
        self.db = StrategyDatabase(db_path)
        self.logger = logging.getLogger(__name__)
        self._cache = {}

    def get_best_examples(
        self,
        count: int = 3,
        min_quality: float = 60.0,
        indicators: Optional[List[str]] = None,
        complexity: Optional[str] = None,
    ) -> List[StrategyExample]:
        """
        Get best strategy examples.

        Args:
            count: Number of examples to return
            min_quality: Minimum quality score
            indicators: Filter by indicators (e.g., ['RSI', 'MACD'])
            complexity: Filter by complexity ('simple', 'medium', 'complex')

        Returns:
            List of formatted strategy examples
        """
        # Build cache key
        cache_key = f"{count}_{min_quality}_{indicators}_{complexity}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Get strategies from database
        strategies = self.db.search(
            has_code=True,
            min_quality_score=min_quality,
            limit=count * 3,  # Get more to filter
        )

        if not strategies:
            self.logger.warning("No strategies found in database with code!")
            return []

        # Filter by indicators if specified
        if indicators:
            strategies = [s for s in strategies if s.indicators_used and any(ind.upper() in [i.upper() for i in s.indicators_used] for ind in indicators)]

        # Filter by complexity if specified
        if complexity:
            strategies = self._filter_by_complexity(strategies, complexity)

        # Convert to examples
        examples = []
        for strategy in strategies[:count]:
            example = self._strategy_to_example(strategy)
            if example:
                examples.append(example)

        # Cache result
        self._cache[cache_key] = examples

        return examples

    def get_examples_by_type(self, strategy_type: str, count: int = 2) -> List[StrategyExample]:
        """
        Get examples for specific strategy type.

        Args:
            strategy_type: 'indicator', 'signal', 'strategy', 'momentum', 'mean_reversion'
            count: Number of examples

        Returns:
            List of relevant examples
        """
        # Map strategy type to search criteria
        type_mapping = {
            "indicator": {"min_quality": 50, "max_complexity": 100},
            "signal": {"min_quality": 55, "max_complexity": 200},
            "strategy": {"min_quality": 60, "max_complexity": 500},
            "momentum": {"indicators": ["RSI", "MACD", "EMA"]},
            "mean_reversion": {"indicators": ["RSI", "BB", "STOCH"]},
            "trend_following": {"indicators": ["EMA", "SMA", "ADX"]},
            "breakout": {"indicators": ["BB", "ATR", "DONCHIAN"]},
        }

        criteria = type_mapping.get(strategy_type, {})

        return self.get_best_examples(
            count=count,
            min_quality=criteria.get("min_quality", 50),
            indicators=criteria.get("indicators"),
        )

    def get_simple_example(self) -> Optional[StrategyExample]:
        """Get one simple, high-quality example."""
        examples = self.get_best_examples(count=1, min_quality=60, complexity="simple")
        return examples[0] if examples else None

    def get_complex_example(self) -> Optional[StrategyExample]:
        """Get one complex, high-quality example."""
        examples = self.get_best_examples(count=1, min_quality=65, complexity="complex")
        return examples[0] if examples else None

    def format_examples_for_prompt(self, examples: List[StrategyExample], max_lines_per_example: int = 50) -> str:
        """
        Format multiple examples for inclusion in LLM prompt.

        Args:
            examples: List of strategy examples
            max_lines_per_example: Maximum lines of code per example

        Returns:
            Formatted string for prompt
        """
        if not examples:
            return "No examples available."

        formatted = ["## REAL STRATEGY EXAMPLES\n"]
        formatted.append("Here are real-world trading strategies for reference:\n")

        for idx, example in enumerate(examples, 1):
            formatted.append(example.to_prompt_format(max_lines_per_example))
            if idx < len(examples):
                formatted.append("\n---\n")

        formatted.append("\n## YOUR TASK\n")
        formatted.append("Create a new strategy inspired by these examples but with your own unique approach.\n")

        return "\n".join(formatted)

    def _strategy_to_example(self, strategy: Strategy) -> Optional[StrategyExample]:
        """Convert database Strategy to StrategyExample."""
        if not strategy.pine_code:
            return None

        # Determine complexity
        if strategy.lines_of_code:
            if strategy.lines_of_code < 100:
                complexity = "simple"
            elif strategy.lines_of_code < 300:
                complexity = "medium"
            else:
                complexity = "complex"
        else:
            complexity = "medium"

        # Clean code snippet
        code_snippet = self._clean_code(strategy.pine_code)

        return StrategyExample(
            name=strategy.name or "Unknown Strategy",
            description=strategy.description or strategy.title or "",
            code_snippet=code_snippet,
            indicators=strategy.indicators_used or [],
            features=strategy.features or {},
            quality_score=strategy.quality_score or 0,
            complexity=complexity,
        )

    def _clean_code(self, code: str) -> str:
        """Clean and format code for prompt."""
        # Remove excessive blank lines
        lines = code.split("\n")
        cleaned = []
        prev_blank = False

        for line in lines:
            is_blank = not line.strip()
            if is_blank and prev_blank:
                continue  # Skip consecutive blank lines
            cleaned.append(line)
            prev_blank = is_blank

        return "\n".join(cleaned)

    def _filter_by_complexity(self, strategies: List[Strategy], complexity: str) -> List[Strategy]:
        """Filter strategies by complexity level."""
        if complexity == "simple":
            return [s for s in strategies if s.lines_of_code and s.lines_of_code < 100]
        elif complexity == "medium":
            return [s for s in strategies if s.lines_of_code and 100 <= s.lines_of_code < 300]
        elif complexity == "complex":
            return [s for s in strategies if s.lines_of_code and s.lines_of_code >= 300]
        else:
            return strategies

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about available examples."""
        all_strategies = self.db.search(has_code=True, limit=1000)

        if not all_strategies:
            return {
                "total_with_code": 0,
                "avg_quality": 0,
                "avg_loc": 0,
                "indicators_used": {},
            }

        # Calculate statistics
        total = len(all_strategies)
        avg_quality = sum(s.quality_score or 0 for s in all_strategies) / total
        avg_loc = sum(s.lines_of_code or 0 for s in all_strategies) / total

        # Count indicators
        from collections import Counter

        all_indicators = []
        for s in all_strategies:
            if s.indicators_used:
                all_indicators.extend(s.indicators_used)

        indicator_counts = dict(Counter(all_indicators).most_common(10))

        return {
            "total_with_code": total,
            "avg_quality": round(avg_quality, 2),
            "avg_loc": round(avg_loc, 0),
            "indicators_used": indicator_counts,
            "complexity_distribution": {
                "simple": len([s for s in all_strategies if s.lines_of_code and s.lines_of_code < 100]),
                "medium": len([s for s in all_strategies if s.lines_of_code and 100 <= s.lines_of_code < 300]),
                "complex": len([s for s in all_strategies if s.lines_of_code and s.lines_of_code >= 300]),
            },
        }


# Convenience functions


def load_examples_for_prompt(
    count: int = 3,
    strategy_type: Optional[str] = None,
    indicators: Optional[List[str]] = None,
    min_quality: float = 60.0,
) -> str:
    """
    Quick function to load and format examples for LLM prompt.

    Args:
        count: Number of examples
        strategy_type: Filter by type (e.g., 'momentum', 'trend_following')
        indicators: Filter by indicators (e.g., ['RSI', 'MACD'])
        min_quality: Minimum quality score

    Returns:
        Formatted examples string for prompt
    """
    loader = ExampleLoader()

    if strategy_type:
        examples = loader.get_examples_by_type(strategy_type, count)
    else:
        examples = loader.get_best_examples(count=count, min_quality=min_quality, indicators=indicators)

    return loader.format_examples_for_prompt(examples)


if __name__ == "__main__":
    # Test the example loader
    logging.basicConfig(level=logging.INFO)

    loader = ExampleLoader()

    # Show statistics
    stats = loader.get_statistics()
    print("📊 EXAMPLE STATISTICS")
    print("=" * 70)
    print(f"Total with code: {stats['total_with_code']}")
    print(f"Average quality: {stats['avg_quality']}")
    print(f"Average LOC: {stats['avg_loc']}")
    print(f"\nTop indicators: {stats['indicators_used']}")
    print(f"\nComplexity: {stats['complexity_distribution']}")
    print()

    # Get examples
    print("\n📚 EXAMPLE STRATEGIES (Top 3)")
    print("=" * 70)
    examples = loader.get_best_examples(count=3, min_quality=60)

    for example in examples:
        print(f"\n{example.name} - Quality: {example.quality_score:.1f}")
        print(f"  Indicators: {', '.join(example.indicators)}")
        print(f"  Complexity: {example.complexity}")
        print(f"  Code: {len(example.code_snippet)} chars")

    # Format for prompt
    print("\n\n📝 FORMATTED FOR LLM PROMPT")
    print("=" * 70)
    formatted = loader.format_examples_for_prompt(examples, max_lines_per_example=20)
    print(formatted[:1000], "... (truncated)")
