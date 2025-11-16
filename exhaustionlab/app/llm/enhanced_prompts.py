"""
Enhanced Prompt Builder with Real Strategy Examples

Extends PromptEngine with database-backed examples for improved
LLM generation quality.
"""

from __future__ import annotations

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

try:
    from .prompts import PromptEngine, PromptContext
    from .example_loader import ExampleLoader, load_examples_for_prompt
except ImportError:
    # Standalone execution
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from prompts import PromptEngine, PromptContext
    from example_loader import ExampleLoader, load_examples_for_prompt


class EnhancedPromptBuilder:
    """
    Enhanced prompt builder with real strategy examples.

    Combines base PromptEngine with database examples for:
    - Better code structure understanding
    - Real indicator usage patterns
    - Production-quality code examples
    - Domain-specific best practices
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize enhanced prompt builder."""
        self.base_engine = PromptEngine()
        self.example_loader = ExampleLoader(db_path)
        self.logger = logging.getLogger(__name__)

        # Cache examples by type
        self._example_cache = {}

    def build_indicator_prompt(
        self,
        context: PromptContext,
        include_examples: bool = True,
        num_examples: int = 2,
    ) -> str:
        """
        Build indicator generation prompt with examples.

        Args:
            context: Prompt context with requirements
            include_examples: Whether to include real examples
            num_examples: Number of examples to include

        Returns:
            Complete prompt string
        """
        # Build base prompt
        base_prompt = self._build_base_indicator_prompt(context)

        if not include_examples:
            return base_prompt

        # Get relevant examples
        examples = self._get_relevant_examples(
            strategy_type="indicator",
            indicators=context.indicators_to_include,
            count=num_examples,
        )

        if not examples:
            self.logger.warning("No examples found, using base prompt only")
            return base_prompt

        # Format examples
        examples_section = self.example_loader.format_examples_for_prompt(
            examples, max_lines_per_example=40
        )

        # Combine
        enhanced_prompt = f"""
{base_prompt}

{examples_section}

## IMPORTANT NOTES
- Learn from the examples above but CREATE YOUR OWN UNIQUE LOGIC
- Use similar code structure and patterns
- Follow PyneCore API conventions shown in examples
- Include proper error handling like the examples
- Make your strategy DIFFERENT and BETTER than examples

Now create your indicator following the requirements above.
"""

        return enhanced_prompt

    def build_strategy_prompt(
        self,
        context: PromptContext,
        include_examples: bool = True,
        num_examples: int = 3,
    ) -> str:
        """
        Build full strategy generation prompt with examples.

        Args:
            context: Prompt context
            include_examples: Include real examples
            num_examples: Number of examples

        Returns:
            Complete prompt
        """
        base_prompt = self._build_base_strategy_prompt(context)

        if not include_examples:
            return base_prompt

        # Get strategy type examples
        if context.signal_logic:
            examples = self.example_loader.get_examples_by_type(
                context.signal_logic, count=num_examples
            )
        else:
            examples = self.example_loader.get_best_examples(
                count=num_examples,
                indicators=context.indicators_to_include,
                min_quality=60,
            )

        if not examples:
            return base_prompt

        examples_section = self.example_loader.format_examples_for_prompt(
            examples, max_lines_per_example=50
        )

        enhanced_prompt = f"""
{base_prompt}

{examples_section}

## STRATEGY REQUIREMENTS
Based on the examples above, create a NEW strategy that:
1. Uses PyneCore API correctly (see examples)
2. Implements {context.signal_logic} logic
3. Includes {', '.join(context.indicators_to_include)} indicators
4. Has clear entry and exit conditions
5. Includes risk management (stop loss, take profit)
6. Is optimized for {context.timeframe} timeframe
7. Follows {context.risk_profile} risk profile

Make your strategy UNIQUE - don't just copy the examples!
"""

        return enhanced_prompt

    def build_mutation_prompt(
        self, base_strategy_code: str, mutation_type: str, context: PromptContext
    ) -> str:
        """
        Build mutation prompt with example patterns.

        Args:
            base_strategy_code: Existing strategy to mutate
            mutation_type: Type of mutation ('parameter', 'logic', 'hybrid')
            context: Context for mutation

        Returns:
            Mutation prompt
        """
        # Get one high-quality example for reference
        example = self.example_loader.get_simple_example()

        prompt = f"""
## TASK: Mutate Existing Strategy

You are mutating an existing trading strategy to improve performance.

## BASE STRATEGY
```python
{base_strategy_code}
```

## MUTATION TYPE: {mutation_type.upper()}

"""

        if mutation_type == "parameter":
            prompt += """
### Parameter Mutation
Modify numerical parameters:
- Adjust indicator periods (e.g., RSI 14 → 20)
- Change thresholds (e.g., oversold < 30 → < 25)
- Modify timeframes
- Adjust risk management values

Keep the core logic unchanged, only tweak parameters.
"""
        elif mutation_type == "logic":
            prompt += """
### Logic Mutation
Modify the core logic:
- Add new conditions to entry/exit
- Combine indicators differently
- Add trend filters
- Implement new signal logic

Keep similar structure but change the decision-making logic.
"""
        else:  # hybrid
            prompt += """
### Hybrid Mutation
Combine parameter AND logic mutations:
- Adjust parameters
- Modify logic
- Add new indicators
- Change risk management approach

Create a significantly different variant.
"""

        if example:
            prompt += f"""

## REFERENCE EXAMPLE
Here's a high-quality strategy for inspiration:

{example.to_prompt_format(max_lines=30)}

Use similar code patterns and quality standards.
"""

        prompt += """

## OUTPUT
Provide the complete mutated strategy code with:
1. All necessary imports
2. Modified parameters/logic
3. Clear comments explaining changes
4. Valid PyneCore syntax
5. Improved functionality

Create a BETTER version of the base strategy!
"""

        return prompt

    def _build_base_indicator_prompt(self, context: PromptContext) -> str:
        """Build base indicator prompt without examples."""
        return f"""
# Create Technical Indicator

## Requirements
- Type: Custom {', '.join(context.indicators_to_include)} indicator
- Timeframe: {context.timeframe}
- Market: {', '.join(context.market_focus)}
- Risk: {context.risk_profile}

## Technical Specs
- Use PyneCore API
- Include @pyne decorator
- Define all inputs
- Plot signals clearly
- Add proper comments

## Code Structure
```python
from pynecore import Series, input, plot, color, script

@script.indicator(title="Custom Indicator", overlay=False)
def main():
    # Your code here
    pass
```

Create a professional, production-ready indicator.
"""

    def _build_base_strategy_prompt(self, context: PromptContext) -> str:
        """Build base strategy prompt without examples."""
        return f"""
# Create Trading Strategy

## Strategy Specifications
- Type: {context.signal_logic.replace('_', ' ').title()}
- Indicators: {', '.join(context.indicators_to_include)}
- Timeframe: {context.timeframe}
- Market: {', '.join(context.market_focus)}
- Risk Profile: {context.risk_profile}

## Requirements
1. Clear entry/exit signals
2. Risk management (SL/TP)
3. Position sizing logic
4. Indicator calculations
5. Signal validation

## Code must include:
- @pyne decorator
- Input parameters
- Indicator logic
- Entry conditions
- Exit conditions
- Risk management
- Plot statements

Create a complete, testable trading strategy.
"""

    def _get_relevant_examples(
        self, strategy_type: str, indicators: Optional[List[str]], count: int
    ) -> List[Any]:
        """Get relevant examples from cache or database."""
        cache_key = f"{strategy_type}_{indicators}_{count}"

        if cache_key in self._example_cache:
            return self._example_cache[cache_key]

        if strategy_type in [
            "momentum",
            "mean_reversion",
            "trend_following",
            "breakout",
        ]:
            examples = self.example_loader.get_examples_by_type(strategy_type, count)
        else:
            examples = self.example_loader.get_best_examples(
                count=count, indicators=indicators, min_quality=60
            )

        self._example_cache[cache_key] = examples
        return examples

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about available examples."""
        return self.example_loader.get_statistics()

    def clear_cache(self):
        """Clear example cache."""
        self._example_cache.clear()


# Convenience functions


def create_enhanced_indicator_prompt(
    indicators: List[str],
    timeframe: str = "1h",
    risk_profile: str = "balanced",
    signal_logic: str = "trend_following",
    include_examples: bool = True,
) -> str:
    """
    Quick function to create indicator prompt with examples.

    Args:
        indicators: List of indicators to include
        timeframe: Trading timeframe
        risk_profile: Risk level
        signal_logic: Strategy type
        include_examples: Include real examples

    Returns:
        Complete prompt string
    """
    builder = EnhancedPromptBuilder()

    context = PromptContext(
        strategy_type="indicator",
        market_focus=["spot", "futures"],
        timeframe=timeframe,
        indicators_to_include=indicators,
        signal_logic=signal_logic,
        risk_profile=risk_profile,
    )

    return builder.build_indicator_prompt(context, include_examples=include_examples)


def create_enhanced_strategy_prompt(
    signal_logic: str,
    indicators: List[str],
    timeframe: str = "1h",
    risk_profile: str = "balanced",
    include_examples: bool = True,
) -> str:
    """
    Quick function to create strategy prompt with examples.

    Args:
        signal_logic: Strategy type (momentum, mean_reversion, etc.)
        indicators: List of indicators
        timeframe: Trading timeframe
        risk_profile: Risk level
        include_examples: Include real examples

    Returns:
        Complete prompt string
    """
    builder = EnhancedPromptBuilder()

    context = PromptContext(
        strategy_type="strategy",
        market_focus=["spot", "futures"],
        timeframe=timeframe,
        indicators_to_include=indicators,
        signal_logic=signal_logic,
        risk_profile=risk_profile,
    )

    return builder.build_strategy_prompt(context, include_examples=include_examples)


if __name__ == "__main__":
    # Test enhanced prompts
    logging.basicConfig(level=logging.INFO)

    print("🚀 ENHANCED PROMPT BUILDER TEST\n")
    print("=" * 70)

    # Test indicator prompt
    print("\n📊 INDICATOR PROMPT WITH EXAMPLES:")
    print("=" * 70)

    prompt = create_enhanced_indicator_prompt(
        indicators=["RSI", "MACD"],
        timeframe="15m",
        signal_logic="momentum",
        include_examples=True,
    )

    print(prompt[:1500])
    print("\n... (truncated)")
    print(f"\nTotal prompt length: {len(prompt)} chars")

    # Test strategy prompt
    print("\n\n📈 STRATEGY PROMPT WITH EXAMPLES:")
    print("=" * 70)

    prompt = create_enhanced_strategy_prompt(
        signal_logic="trend_following",
        indicators=["EMA", "ATR"],
        timeframe="1h",
        include_examples=True,
    )

    print(prompt[:1500])
    print("\n... (truncated)")
    print(f"\nTotal prompt length: {len(prompt)} chars")

    # Show statistics
    builder = EnhancedPromptBuilder()
    stats = builder.get_statistics()

    print("\n\n📊 EXAMPLE DATABASE STATISTICS:")
    print("=" * 70)
    print(f"Total strategies with code: {stats['total_with_code']}")
    print(f"Average quality: {stats['avg_quality']}")
    print(f"Average LOC: {stats['avg_loc']}")
    print(f"\nTop indicators used:")
    for indicator, count in list(stats["indicators_used"].items())[:5]:
        print(f"  - {indicator}: {count} strategies")
