"""
Intelligent LLM Orchestrator for Meta-Evolution

Advanced strategy generation using adaptive meta-parameters,
example learning, and intelligent prompt engineering.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..backtest.strategy_genome import StrategyGenome
from ..llm import LLMRequest, LLMStrategyGenerator, LocalLLMClient
from .meta_config import EvolutionIntensity, MarketFocus, MetaEvolutionConfig, MetaParameters, MetaStrategyType


@dataclass
class EvolutionDirective:
    """High-level directive for evolution process."""

    strategy_type: MetaStrategyType
    market_focus: MarketFocus
    evolution_phase: str  # "exploration", "exploitation", "production"
    performance_targets: Dict[str, float]
    risk_tolerance: str
    time_horizon: str  # "intraday", "swing", "position"
    capital_constraints: Dict[str, float]


@dataclass
class IntelligentPrompt:
    """Sophisticated prompt generation strategy."""

    system_directive: str
    task_specification: str
    context_knowledge: str
    examples_with_weights: List[Tuple[str, float]]
    validation_requirements: List[str]
    creative_constraints: List[str]
    meta_guidance: str


class IntelligentOrchestrator:
    """Intelligent LLM orchestrator for meta-evolution."""

    def __init__(self, llm_client: LocalLLMClient, meta_config: MetaEvolutionConfig):
        self.llm_client = llm_client
        self.meta_config = meta_config
        self.generator = LLMStrategyGenerator(llm_client)

        self.logger = logging.getLogger(__name__)

        # Evolution state tracking
        self.generation_history = []
        self.performance_history = []
        self.adaptation_memory = {}

    def create_intelligent_prompt(
        self,
        directive: EvolutionDirective,
        meta_params: MetaParameters,
        performance_feedback: Optional[Dict] = None,
    ) -> LLMRequest:
        """Create sophisticated prompt for LLM strategy generation."""

        # Get comprehensive context
        context = self.meta_config.create_llm_context(meta_params)

        # Build intelligent prompt components
        system_directive = self._build_system_directive(directive, meta_params)
        task_specification = self._build_task_specification(directive, context)
        context_knowledge = self._build_context_knowledge(context, directive)
        examples_with_weights = self._prepare_weighted_examples(context, meta_params)
        validation_requirements = self._build_validation_requirements(directive, meta_params)
        creative_constraints = self._build_creative_constraints(directive, meta_params)
        meta_guidance = self._build_meta_guidance(performance_feedback)

        # Combine into prompt text
        prompt_text = f"""
{system_directive}

{task_specification}

## KNOWLEDGE CONTEXT
{context_knowledge}

## LEARNING EXAMPLES
{self._format_weighted_examples(examples_with_weights)}

## VALIDATION REQUIREMENTS
{self._format_requirements(validation_requirements)}

## CREATIVE CONSTRAINTS
{self._format_constraints(creative_constraints)}

## META-GUIDANCE
{meta_guidance}

Generate a complete, production-ready PyneCore strategy that meets all specified requirements.
"""

        system_prompt = self._build_system_prompt(meta_params)

        return LLMRequest(
            prompt=prompt_text,
            system_prompt=system_prompt,
            temperature=self._determine_temperature(meta_params, directive.evolution_phase),
            max_tokens=2000,
            context=context.get_prompt_context(),
        )

    def _build_system_directive(self, directive: EvolutionDirective, meta_params: MetaParameters) -> str:
        """Build high-level system directive."""

        directive_map = {
            "exploration": "Explore diverse innovative trading approaches with moderate risk tolerance",
            "exploitation": "Focus on proven patterns with high reliability and consistent performance",
            "production": "Create institutional-grade strategies with extreme robustness and performance",
        }

        phase_directive = directive_map.get(directive.evolution_phase, directive_map["exploration"])

        return f"""
You are an elite quantitative strategist specializing in {directive.strategy_type.value} trading systems for {directive.market_focus.value} markets.

## PRIMARY DIRECTIVE
{phase_directive}

## TRADING OBJECTIVES
- Strategy Type: {directive.strategy_type.value.upper()}
- Market Focus: {directive.market_focus.value}
- Time Horizon: {directive.time_horizon}
- Risk Tolerance: {directive.risk_tolerance}

## PERFORMANCE TARGETS
- Minimum Sharpe Ratio: {directive.performance_targets.get('min_sharpe', 1.0)}
- Maximum Drawdown: {directive.performance_targets.get('max_drawdown', 0.20):.1%}
- Win Rate Target: {directive.performance_targets.get('win_rate', 0.50):.1%}
- Daily Trade Limit: {directive.capital_constraints.get('max_trades_per_day', 50)}

Your expertise lies in creating strategies that can consistently generate profits while maintaining strict risk management. Every strategy you generate must be production-ready and capable of live deployment.
"""

    def _build_task_specification(self, directive: EvolutionDirective, context: Dict) -> str:
        """Build detailed task specification."""

        strategy_info = context.get("strategy_specification", {})
        constraints = context.get("performance_constraints", {})

        return f"""
## TASK: CREATE EXPERT TRADING STRATEGY

### STRATEGY SPECIFICATIONS
- **Type**: {strategy_info.get('type', 'hybrid')}
- **Focus**: {strategy_info.get('focus', 'spot_crypto')}
- **Core Logic**: {strategy_info.get('description', 'Adaptive trading logic')}
- **Signal Patterns**: {', '.join(strategy_info.get('signal_patterns', 'various patterns'))}

### TECHNICAL REQUIREMENTS
- **Primary Indicators**: {', '.join(strategy_info.get('key_indicators', 'RSI, MACD'))}
- **Timeframes**: {', '.join(strategy_info.get('timeframe_preference', '5m, 15m, 1h'))}
- **Risk Profile**: {strategy_info.get('risk_profile', 'balanced')}
- **Market Conditions**: {strategy_info.get('market_conditions', 'various')}

### PERFORMANCE CONSTRAINTS
- **Max Drawdown**: {constraints.get('max_drawdown_target', 0.20):.1%}
- **Min Win Rate**: {constraints.get('min_win_rate_target', 0.50):.1%}
- **Target Sharpe**: {constraints.get('expected_sharpe_target', 1.0)}
- **Daily Trades**: {'≤' + str(constraints.get('max_positions_per_day', 100))}

### CODE STRUCTURE REQUIREMENTS
1. Use @pyne decorator and proper PyneCore imports
2. All inputs defined with input() functions with appropriate ranges
3. Multi-level signal system (L1=weak, L2=medium, L3=strong)
4. Comprehensive edge case handling
5. Clean, readable code with strategic comments
6. Output visualizations using plot() and plotshape()

### INNOVATION MANDATE
Push boundaries within constraints. Consider:
- Novel indicator combinations
- Innovative signal filtering approaches
- Adaptive mechanisms for market conditions
- Robust risk management techniques
- Execution efficiency optimizations

Create a strategy that quant hedge funds would be proud to deploy in their production trading systems.
"""

    def _build_context_knowledge(self, context: Dict, directive: EvolutionDirective) -> str:
        """Build deep domain knowledge context."""

        strategy_info = context.get("strategy_specification", {})

        return f"""
## DOMAIN EXPERTISE KNOWLEDGE

### {directive.strategy_type.value.upper()} STRATEGY FRAMEWORK
Expert understanding of {strategy_info.get('description', 'strategy domain')} with proven track record in cryptocurrency markets.

### ADVANCED TECHNICAL ANALYSIS
Mastery of technical indicators and their limitations in crypto environments:
- **Volume Dynamics**: Critical in 24/7 crypto markets with manipulation susceptibility
- **Volatility Management**: Essential for risk control in high-volatility assets
- **Timeframe Synergy**: Multi-timeframe analysis for signal confirmation
- **Market Microstructure**: Understanding of order flow and liquidity dynamics

### PSYCHOLOGICAL TRADING FACTORS
Expert knowledge of market psychology effects in crypto:
- **Fear & Greed Cycles**: Behavioral finance patterns in retail-dominated markets
- **News & Sentiment Impact**: Rapid price reactions to breaking crypto news
- **Whale Manipulation**: Large order flow manipulation patterns
- **Regulatory Shocks**: Policy change impact on trading patterns

### QUANTITATIVE RESEARCH BACKGROUND
Deep understanding of modern quantitative methods:
- **Statistical Arbitrage**: Mean reversion and cointegration-based strategies
- **Machine Learning**: Pattern recognition and adaptive optimization
- **Risk Management**: Value-at-Risk, drawdown control, position sizing
- **Backtesting Methodology**: avoiding overfitting and ensuring robustness

### INSTITUTIONAL TRADING STANDARDS
Production-grade code quality and operational excellence:
- **Execution Optimization**: Minimizing slippage and transaction costs
- **Error Handling**: Graceful degradation under extreme market conditions
- **Scalability**: Performance with increasing computational requirements
- **Monitoring**: Comprehensive logging and performance tracking

### CRYPTO-SPECIFIC EXPERTISE
Specialized knowledge for cryptocurrency trading:
- **Exchange Variations**: Different order book dynamics across exchanges
- **Network Effects**: Blockchain events and protocol changes
- **Cross-Correlations**: Inter-asset relationships and arbitrage opportunities
- **Regulatory Landscape**: Compliance requirements and platform differences

Apply this comprehensive expertise to create a truly exceptional trading strategy.
"""

    def _prepare_weighted_examples(self, context: Dict, meta_params: MetaParameters) -> List[Tuple[str, float]]:
        """Prepare weighted examples based on performance and relevance."""

        examples = context.get("examples", [])
        weighted_examples = []

        for example in examples:
            # Calculate weight based on performance metrics
            performance = example.get("performance", {})

            weight = 0.5  # Base weight

            # Performance-based weighting
            if performance:
                sharpe = performance.get("sharpe_ratio", 0)
                if sharpe > 2.0:
                    weight += 0.3
                elif sharpe > 1.0:
                    weight += 0.15

                win_rate = performance.get("win_rate", 0.4)
                if win_rate > 0.70:
                    weight += 0.2
                elif win_rate > 0.55:
                    weight += 0.1

                drawdown = performance.get("max_drawdown", 0.2)
                if drawdown < 0.05:
                    weight += 0.15
                elif drawdown < 0.10:
                    weight += 0.05

            # Relevance weighting
            tags = example.get("tags", [])
            strategy_tags = [
                meta_params.strategy_type.value.lower(),
                meta_params.market_focus.value.lower(),
            ]

            for strategy_tag in strategy_tags:
                found_similar = False
                for tag in tags:
                    if strategy_tag in tag.lower() or tag.lower() in strategy_tag:
                        weight += 0.2
                        found_similar = True
                        break

                if found_similar:
                    break

            # Normalize weights
            weight = min(1.0, max(0.1, weight))

            weighted_examples.append((example["code"], weight))

        # Sort by weight and take top examples
        weighted_examples.sort(key=lambda x: x[1], reverse=True)
        max_examples = context.get("learning_parameters", {}).get("context_examples", 3)

        return weighted_examples[:max_examples]

    def _build_validation_requirements(self, directive: EvolutionDirective, meta_params: MetaParameters) -> List[str]:
        """Build validation requirements based on production standards."""

        requirements = [
            "Syntactically valid PyneCore code with proper imports and decorators",
            "All signal logic must be testable and avoid forward-looking bias",
            "Input parameters must have sensible ranges and default values",
            "Multi-level signal system with clear progression (L1→L2→L3)",
            "Comprehensive error handling for edge cases and extreme market conditions",
            "Clean code structure with strategic comments explaining key decisions",
            "Backtest-ready logic without look-ahead or survivorship bias",
            "Live-trading feasible with realistic execution assumptions",
        ]

        # Add directive-specific requirements
        if directive.evolution_phase == "production":
            requirements.extend(
                [
                    "Extensive edge case testing with simulation of market disruptions",
                    "Computational efficiency for real-time execution (< 50ms per signal)",
                    "Comprehensive logging and monitoring capabilities",
                    "Graceful degradation under load and market stress",
                    "Institutional-grade documentation and maintainability",
                ]
            )

        # Add performance-centric requirements
        if meta_params.domain_knowledge_depth == "advanced":
            requirements.extend(
                [
                    "Advanced mathematical justification for all parameter choices",
                    "Statistical significance testing of all signal components",
                    "Multiple timeframe analysis and consistency",
                    "Risk-adjusted performance optimization",
                ]
            )

        return requirements

    def _build_creative_constraints(self, directive: EvolutionDirective, meta_params: MetaParameters) -> List[str]:
        """Build creative constraints to guide LLM innovation."""

        base_constraints = [
            "Must use only available PyneCore API functions - no Pine Script ta.* functions",
            "Maximum 200 lines of code for maintainability and debugging capability",
            "No circular dependencies or complex state management patterns",
            "Signal frequency should be appropriate for {meta_params.timeframes[0]} timeframe",
            "Risk management integrated directly into signal logic (not just a filter)",
        ]

        # Intensity-based constraints
        if meta_params.evolution_intensity == EvolutionIntensity.EXPLORATORY:
            base_constraints.extend(
                [
                    "Encourage novel indicator combinations and mathematical transformations",
                    "Consider non-obvious correlations between multiple signals",
                    "May explore creative signal strength weightings and thresholding approaches",
                ]
            )
        elif meta_params.evolution_intensity == EvolutionIntensity.EXPLOITATIVE:
            base_constraints.extend(
                [
                    "Focus on proven patterns with conservative risk management",
                    "Use standard indicators with minor innovative modifications",
                    "Maintain clear, explainable logic suitable for institutional review",
                ]
            )

        # Strategy-type specific constraints
        if directive.strategy_type == MetaStrategyType.MEAN_REVERSION:
            base_constraints.extend(
                [
                    "Mean reversion signals must consider volatility regime and statistical significance",
                    "Implement timeout mechanisms for failed reversion scenarios",
                ]
            )
        elif directive.strategy_type == MetaStrategyType.MOMENTUM:
            base_constraints.extend(
                [
                    "Momentum signals must include volume or volatility confirmation",
                    "Consider momentum strength and acceleration for signal filtering",
                ]
            )

        return base_constraints

    def _build_meta_guidance(self, performance_feedback: Optional[Dict] = None) -> str:
        """Build meta-level guidance based on learning and performance."""

        base_guidance = """
## META-LEVEL GUIDANCE

### DESIGN PHILOSOPHY
Create strategies that are both innovative and practical. Balance:
- **Cutting-edge innovation** with proven quantitative principles
- **Mathematical elegance** with practical code maintainability
- **Performance optimization** with robust risk management
- **Sophistication** with operational simplicity

### TRADING EXCELLENCE STANDARDS
Target strategies that elite quant funds would deploy:
- **Consistent Performance**: Generate alpha across different market regimes
- **Risk Excellence**: Maintain discipline during extreme market stress
- **Execution Strength**: Real-world trading without slippage disasters
- **Scalability**: Handle position sizes from small beginnings to institutional scale

### INNOVATION MANDATE
Push beyond standard retail trading strategies:
- **Multi-signal integration**: Combine complementary approaches intelligently
- **Adaptive mechanisms**: Adjust to changing market conditions automatically
- **Microstructure awareness**: Understand and exploit order flow dynamics
- **Cross-asset insights**: Incorporate relationships between correlated assets

Focus on creating strategies that can consistently generate alpha while maintaining the highest standards of risk management and operational excellence.
"""

        if performance_feedback:
            guidance = (
                base_guidance
                + f"""

### PERFORMANCE FEEDBACK
Recent performance provides these insights:
- **Current Sharpe Ratio**: {performance_feedback.get('sharpe_ratio', 'N/A')}
- **Realized Drawdown**: {performance_feedback.get('max_drawdown', 'N/A')}
- **Win Rate Achievement**: {performance_feedback.get('win_rate', 'N/A')}

**Adaptive Guidance**:
Based on this performance, {
self._generate_adaptive_guidance(performance_feedback)
}
"""
            )
            return guidance

        return base_guidance

    def _generate_adaptive_guidance(self, performance: Dict) -> str:
        """Generate adaptive guidance based on performance history."""

        sharpe = performance.get("sharpe_ratio", 0)
        drawdown = performance.get("max_drawdown", 0.5)
        win_rate = performance.get("win_rate", 0.3)

        guidance_parts = []

        if sharpe < 0.5:
            guidance_parts.append("increase signal quality and reduce noise trading")

        if drawdown > 0.2:
            guidance_parts.append("implement stronger risk management and position sizing")

        if win_rate < 0.4:
            guidance_parts.append("improve signal confirmation and edge detection")

        if sharpe > 1.5 and drawdown < 0.08:
            guidance_parts.append("consider scaling up position sizes while monitoring capacity")
            guidance_parts.append("focus on execution optimization and speed improvements")

        if not guidance_parts:
            return "current approach is strong - continue with similar quality improvements"

        return f"{'; '.join(guidance_parts)}. Also consider diversifying signal approaches to improve stability."

    def _determine_temperature(self, meta_params: MetaParameters, evolution_phase: str) -> float:
        """Determine LLM temperature based on evolution phase and intensity."""

        base_temps = {
            EvolutionIntensity.EXPLORATORY: 0.8,
            EvolutionIntensity.BALANCED: 0.6,
            EvolutionIntensity.EXPLOITATIVE: 0.4,
            EvolutionIntensity.AGGRESSIVE: 0.9,
        }

        temp = base_temps.get(meta_params.evolution_intensity, 0.6)

        # Adjust for evolution phase
        if evolution_phase == "production":
            temp *= 0.7  # Lower temperature for production
        elif evolution_phase == "exploration":
            temp *= 1.2  # Higher temperature for exploration

        return min(1.0, max(0.2, temp))

    def _build_system_prompt(self, meta_params: MetaParameters) -> str:
        """Build comprehensive system prompt."""

        return f"""You are an elite quantitative strategist with deep expertise in cryptocurrency trading systems, advanced mathematics, and institutional-grade code development.

Your specialization focuses on {meta_params.strategy_type.value} strategies for {meta_params.market_focus.value} markets with {meta_params.domain_knowledge_depth} level knowledge.

CRITICAL REQUIREMENTS:
1. Generate syntactically valid, testable PyneCore code that can be deployed immediately
2. Use only available PyneCore API - no Pine Script ta.* functions
3. Create production-quality strategies with comprehensive error handling
4. Implement intelligent multi-level signal systems
5. Quantitative justification for all parameter choices and signal logic
6. Code must be clear, documented, and maintainable by institutional dev teams

VALIDATION STANDARDS:
- All generated strategies must pass comprehensive validation testing
- Code must be immediately executable in PyneCore environment
- Implement robust edge case handling for extreme market conditions
- Focus on risk-adjusted returns rather than raw returns alone
- Consider execution costs, slippage, and market impact

EXPERTISE DELIVERY:
Demonstrate deep understanding of:
- Technical analysis mathematics and statistical significance
- Market microstructure and execution optimization
- Risk management and position sizing algorithms
- Multi-timeframe signal correlation and confirmation
- Behavioral finance patterns in cryptocurrency markets

Generate strategies that elite hedge funds would be proud to add to their trading lineup.
"""

    def _format_weighted_examples(self, examples: List[Tuple[str, float]]) -> str:
        """Format weighted examples for LLM."""
        if not examples:
            return "No specific examples available."

        formatted_text = ""
        for i, (code, weight) in enumerate(examples, 1):
            relevance = "HIGH" if weight > 0.8 else "MEDIUM" if weight > 0.5 else "LOW"
            formatted_text += f"""
### Example {i} (Relevance: {relevance})
```python
{code[:300]}...
```
"""

        return formatted_text

    def _format_requirements(self, requirements: List[str]) -> str:
        """Format requirements list."""
        return "1. " + "\n1. ".join(requirements)

    def _format_constraints(self, constraints: List[str]) -> str:
        """Format constraints list."""
        return "- " + "\n- ".join(constraints)

    def generate_intelligent_strategy(self, strategy_directive: EvolutionDirective) -> StrategyGenome:
        """Generate strategy using intelligent orchestration."""

        # Determine evolution approach
        if strategy_directive.evolution_phase == "production":
            meta_config = self.meta_config.create_evolution_config(
                strategy_directive.strategy_type,
                strategy_directive.market_focus,
                EvolutionIntensity.EXPLOITATIVE,
            )
        elif strategy_directive.evolution_phase == "exploration":
            meta_config = self.meta_config.create_evolution_config(
                strategy_directive.strategy_type,
                strategy_directive.market_focus,
                EvolutionIntensity.EXPLORATORY,
            )
        else:
            meta_config = self.meta_config.create_evolution_config(
                strategy_directive.strategy_type,
                strategy_directive.market_focus,
                EvolutionIntensity.BALANCED,
            )

        # Create intelligent prompt
        prompt_request = self.create_intelligent_prompt(strategy_directive, meta_config)

        # Generate strategy
        gen_request = self.generator.create_signal_strategy(
            meta_config.strategy_type.value,
            meta_config.risk_levels[0] if meta_config.risk_levels else "balanced",
            meta_config.get_prompt_context(),
        )

        # Override with intelligent prompt
        gen_request.prompt = prompt_request.prompt
        gen_request.system_prompt = prompt_request.system_prompt
        gen_request.temperature = prompt_request.temperature

        # Execute generation
        result = self.generator.generate_strategy(gen_request)

        # Convert to genome
        if result.success:
            genome = self.generator.convert_to_strategy_genome(
                result,
                f"intelligent_{strategy_directive.strategy_type.value}_strategy",
                f"Intelligently generated {strategy_directive.strategy_type.value} strategy",
            )

            if genome:
                # Add meta-information
                genome.parameters.update(
                    {
                        "meta_strategy_type": strategy_directive.strategy_type.value,
                        "market_focus": strategy_directive.market_focus.value,
                        "evolution_phase": strategy_directive.evolution_phase,
                        "generation_method": "intelligent_orchestrator",
                    }
                )

                # Record in evolution history
                self.generation_history.append(
                    {
                        "directive": strategy_directive,
                        "meta_params": meta_config,
                        "result": result,
                        "success": True,
                    }
                )

                return genome

        self.logger.error(f"Intelligent strategy generation failed: {result.error_message}")
        return None
