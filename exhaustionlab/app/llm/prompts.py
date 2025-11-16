"""
Advanced Prompt Engineering Framework for PyneCore Strategy Generation

Provides Pine Script context, PyneCore API knowledge, and structured
prompt templates for generating trading strategies and indicators.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .llm_client import LLMRequest

# Completion token budgets tuned for DeepSeek thinking responses
INDICATOR_COMPLETION_TOKENS = 3200
SIGNAL_COMPLETION_TOKENS = 4200
MUTATION_COMPLETION_TOKENS = 3600

# IMPROVED SYSTEM PROMPT - Prevents API hallucinations
IMPROVED_PYNECORE_API_REFERENCE = """
═══════════════════════════════════════════════════════════════════════════════
📦 REQUIRED IMPORTS (copy exactly):
═══════════════════════════════════════════════════════════════════════════════

from pynecore import Series, input, plot, color, script
from pynecore.lib import close

# OR alternative (if close is implicitly available):
from pynecore import Series, input, plot, color, script

═══════════════════════════════════════════════════════════════════════════════
✅ ALLOWED plot() SYNTAX (ONLY THIS FORM):
═══════════════════════════════════════════════════════════════════════════════

plot(value, "Label", color=color.XXX)

Where color.XXX can ONLY be:
  • color.green
  • color.red
  • color.blue
  • color.yellow
  • color.white
  • color.black

═══════════════════════════════════════════════════════════════════════════════
❌ FORBIDDEN - DO NOT USE:
═══════════════════════════════════════════════════════════════════════════════

# ❌ NO style parameter
plot(x, "Label", style=plot.Style.POINT)  # WRONG!
plot(x, "Label", style=anything)          # WRONG!

# ❌ NO title parameter in plot() calls
plot(x, "Label", title="X")  # WRONG!

# ❌ NO linewidth, linestyle, marker, etc.
plot(x, "Label", linewidth=2)  # WRONG!

# ❌ NO custom/invalid colors
color.purple   # WRONG!
color.orange   # WRONG!
color.pink     # WRONG!

# ❌ NO 'and'/'or' operators for Series boolean operations
buy = rsi < 30 and close > sma  # WRONG!

# ✅ USE '&' and '|' instead
buy = (rsi < 30) & (close > sma)  # CORRECT!

═══════════════════════════════════════════════════════════════════════════════
📊 AVAILABLE INDICATORS (use only these):
═══════════════════════════════════════════════════════════════════════════════

close.sma(length)              # Simple Moving Average
close.ema(length)              # Exponential Moving Average
close.rsi(length)              # Relative Strength Index
close.atr(length)              # Average True Range
close.std(length)              # Standard Deviation
close.max(length)              # Maximum over periods
close.min(length)              # Minimum over periods

# For series comparison and historical access:
close[1]                       # Previous bar
close[2]                       # 2 bars ago

═══════════════════════════════════════════════════════════════════════════════
🔍 WORKING EXAMPLE - COPY THIS PATTERN:
═══════════════════════════════════════════════════════════════════════════════

from pynecore import Series, input, plot, color, script
from pynecore.lib import close

@script.indicator(title="Example Strategy", overlay=True)
def main():
    # 1. Inputs
    period = input.int("Period", 14)
    threshold = input.float("Threshold", 30.0)
    
    # 2. Calculate indicators
    rsi = close.rsi(period)
    sma = close.sma(20)
    
    # 3. Generate signals (NOTE: Use & not 'and')
    buy = (rsi < threshold) & (close > sma)
    sell = (rsi > (100 - threshold)) & (close < sma)
    
    # 4. Plot (NOTE: Only 3 parameters allowed!)
    plot(buy, "Buy Signal", color=color.green)
    plot(sell, "Sell Signal", color=color.red)
    
    return {"buy": buy, "sell": sell}

═══════════════════════════════════════════════════════════════════════════════

CRITICAL: Follow these rules EXACTLY. Do NOT improvise on the API!
"""


def _make_llm_request(**kwargs):
    from .llm_client import LLMRequest

    return LLMRequest(**kwargs)


@dataclass
class PromptContext:
    """Context information to provide to LLM for generation."""

    strategy_type: str  # 'indicator', 'signal', 'strategy'
    market_focus: List[str]  # ['spot', 'futures', 'options']
    timeframe: str  # '1m', '5m', '15m', '1h', '1d'
    indicators_to_include: List[str]  # ['SMA', 'RSI', 'MACD', 'BB', 'ATR']
    signal_logic: str  # 'trend_following', 'mean_reversion', 'breakout', 'exhaustion'
    risk_profile: str  # 'conservative', 'balanced', 'aggressive'
    base_strategy: Optional[str] = None  # Starting point for mutations
    examples: List[str] = field(default_factory=list)
    constraints: Dict[str, Any] = field(default_factory=dict)


class PromptEngine:
    """Advanced prompt engineering with Pine Script to PyneCore translation."""

    def __init__(self):
        # Load Pine Script documentation and examples
        self.pine_docs = self._load_pine_documentation()
        self.pynecore_api = self._load_pynecore_api_docs()
        self.trading_templates = self._load_trading_templates()

        # System prompts for different purposes
        self.system_prompts = {
            "indicator": self._build_indicator_system_prompt(),
            "signal": self._build_signal_system_prompt(),
            "strategy": self._build_strategy_system_prompt(),
            "mutation": self._build_mutation_system_prompt(),
        }

    def generate_indicator_prompt(self, context: PromptContext) -> "LLMRequest":
        """Generate prompt for indicator creation."""

        base_prompt = f"""
You are an expert quantitative analyst and Pine Script developer specializing in creating robust technical indicators for cryptocurrency markets.

## TASK
Create a complete PyneCore indicator implementing {', '.join(context.indicators_to_include)} with the following specifications:

## REQUIREMENTS
- Market: {', '.join(context.market_focus)} cryptocurrency trading
- Timeframe: {context.timeframe} multi-timeframe compatibility  
- Risk Profile: {context.risk_profile}
- Strategy Type: {context.signal_logic}
- Signal Logic: {self._get_signal_logic_description(context.signal_logic)}

## INDICATORS TO IMPLEMENT
{self._format_indicators_list(context.indicators_to_include)}

## TECHNICAL REQUIREMENTS
1. Use only PyneCore API functions and syntax
2. Follow @pyne decorator pattern exactly
3. All inputs must be defined with input() function
4. Signals must be plotted using plot() function
5. Include proper error handling and edge cases
6. Code must be syntactically valid and executable
7. Include type hints where appropriate

## OUTPUT FORMAT
Provide complete PyneCore code with:
1. Proper imports (@pyne decorator)
2. All required inputs with sensible defaults
3. Indicator calculations
4. Signal generation logic
5. Output plots for visualization
6. Brief code comments explaining key logic
7. Entire response wrapped in a single ```python fenced code block with no prose before or after.  
   Absolutely no `<think>` sections or narrative text outside the code block.

## CONTEXT
You are translating Pine Script concepts to PyneCore. Important differences:
- Pine Script `ta.sma()` → `Series.sma()` or custom implementation
- Pine Script `request.security()` → Not available in PyneCore
- Pine Script `strategy.*` functions → Use direct plots and calculations
- Pine Script `varip int` → Use `Persistent[int]` or just direct vars
- Pine Script `math.*` functions → Use Python math library

## EXAMPLE CODE STRUCTURE
```python
# @pyne decorator at top of file
from pynecore import Series, input, plot, color, script

@script.indicator(title="Custom Indicator", overlay=False)
def main():
    # Inputs
    length = input.int("Length", 14)
    source = input.source("Source", close)
    
    # Calculations
    indicator_value = source.sma(length)
    
    # Output
    plot(indicator_value, "Indicator", color=color.blue)
```

Focus on creating robust, production-quality indicators that work reliably in live trading environments.
"""

        return _make_llm_request(
            prompt=base_prompt,
            system_prompt=self.system_prompts["indicator"],
            temperature=0.7,
            max_tokens=INDICATOR_COMPLETION_TOKENS,
            context=context,
        )

    def generate_signal_strategy_prompt(self, context: PromptContext) -> "LLMRequest":
        """Generate prompt for signal strategy creation."""

        if context.base_strategy:
            base_code = self._load_strategy_code(context.base_strategy)
            base_instruction = f"""
## CURRENT STRATEGY CODE TO IMPROVE:
```python
{base_code}
```
Your task is to enhance this strategy by {context.signal_logic} mutations.
"""
        else:
            base_instruction = "Create a new strategy from scratch."

        prompt = f"""
You are an expert quantitative strategy developer specializing in automated cryptocurrency trading systems.

## TASK
Create a complete PyneCore trading strategy focused on {context.signal_logic} with {context.risk_profile} risk management.

## SPECIFICATIONS
- Market: {', '.join(context.market_focus)}
- Timeframe: {context.timeframe}
- Signal Logic: {context.signal_logic}
- Risk Profile: {context.risk_profile}
- Indicators: {', '.join(context.indicators_to_include)}

## TRADING LOGIC REQUIREMENTS
Focus on {self._get_signal_logic_description(context.signal_logic)}:
{self._get_signal_requirements(context.signal_logic)}
{base_instruction}

## VALIDATION CRITERIA
1. Generate meaningful signals on {', '.join(context.indicators_to_include)} indicators
2. Implement proper signal filtering to avoid noise
3. Include level-based signal strength (L1, L2, L3)
4. Handle edge cases and abnormal market conditions
5. Ensure backtest-able logical consistency
6. Code must be syntactically valid PyneCore

## CODE STRUCTURE
Follow this proven signal strategy pattern:
1. Define indicator inputs with sensible ranges
2. Calculate required technical indicators  
3. Implement signal detection logic
4. Add signal strength levels (L1=weak, L2=medium, L3=strong)
5. Plot signals for visualization
6. Include signal state management

## KEY PINE SCRIPT → PYNECORE TRANSLATIONS
- Pine `ta.rsi(close, 14)` → `close.rsi(14)` 
- Pine `ta.bb(close, 20, 2)` → Custom Bollinger Bands implementation
- Pine `ta.atr(14)` → `Range.atr(14)` with custom Range class
- Pine `strategy.entry()` → Use `plot()` with boolean signals
- Pine `strategy.risk.max_drawdown_percent()` → Manual drawdown tracking

## OUTPUT
Provide complete, valid PyneCore code with:
- Proper @pyne decorator
- All necessary inputs and calculations
- Clear signal generation logic
- Multiple signal levels
- Error handling and edge cases
- Brief explanatory comments
- Wrap the entire response in one ```python fenced block and do not include natural language outside it.
- Do **not** emit `<think>` or chain-of-thought text; only the final code block is permitted.

The strategy must be robust enough for consideration in automated trading portfolios.
"""

        return _make_llm_request(
            prompt=prompt,
            system_prompt=self.system_prompts["signal"],
            temperature=0.8,
            max_tokens=SIGNAL_COMPLETION_TOKENS,
            context=context,
        )

    def generate_mutation_prompt(
        self, base_code: str, mutation_type: str, context: PromptContext
    ) -> "LLMRequest":
        """Generate prompt for mutating existing strategy."""

        mutation_instructions = {
            "parameter": "Modify only the input parameters and their default values. Keep all logic and calculations identical.",
            "logic": "Modify the signal generation logic and calculations. Keep parameter structure identical.",
            "indicator": "Replace one key indicator with a similar type (SMA→EMA, RSI→Stoch, etc). Keep signal logic similar.",
            "timeframe": "Adjust timeframe sensitivity and lookback periods. Make strategy更适合 for {context.timeframe} timeframe.",
            "risk": "Adjust risk management and signal filtering. Add stop-loss, take-profit, or position sizing logic.",
        }

        instruction = mutation_instructions.get(
            mutation_type,
            "Apply intelligent mutation while preserving overall strategy structure.",
        )

        prompt = f"""
You are performing LLM-driven genetic algorithm mutation on PyneCore trading strategies.

## MUTATION TASK
Apply {mutation_type.upper()} mutation to the following PyneCore strategy:

## CURRENT STRATEGY CODE:
```python
{base_code}
```

## MUTATION INSTRUCTIONS
{instruction}

## MUTATION REQUIREMENTS
1. Maintain valid PyneCore syntax and imports
2. Preserve overall strategy structure and function naming
3. Keep signal strength levels (L1, L2, L3) if present
4. Ensure mutation is meaningful but not destructive
5. Keep strategy in same risk category ({context.risk_profile})
6. Include brief comment on what was mutated

## CONTEXT
- Strategy Type: {context.strategy_type}
- Market Focus: {', '.join(context.market_focus)}
- Timeframe: {context.timeframe}
- Current Indicators: {', '.join(context.indicators_to_include)}

## VALIDATION
Mutated strategy must:
- Be syntactically valid PyneCore
- Generate meaningful signals on the same indicators
- Maintain backtest compatibility
- Show measurable difference from original

## OUTPUT FORMAT (MANDATORY)
Return exactly one ```python code block containing the full mutated strategy.
Do not include commentary, justification, `<think>` traces, or text outside the block.

Provide the complete mutated PyneCore code ready for backtesting comparison.
"""

        return _make_llm_request(
            prompt=prompt,
            system_prompt=self.system_prompts["mutation"],
            temperature=0.9,  # Higher temperature for creativity
            max_tokens=MUTATION_COMPLETION_TOKENS,
            context=context,
        )

    def build_context_prompt(self, context: PromptContext) -> str:
        """Build system prompt with comprehensive context."""
        return f"""
## PYNECORE API REFERENCE
Key functions and patterns for PyneCore indicator development:

### Available Functions
- `Series.sma(length)` - Simple Moving Average
- `Series.ema(length)` - Exponential Moving Average  
- `Series.rsi(length)` - Relative Strength Index
- `Series.stoch(length, smoothK, smoothD)` - Stochastic Oscillator
- `Series.macd(fast, slow, signal)` - MACD
- `Series.bollinger_bands(length, mult)` - Bollinger Bands (custom)
- `Series.atr(length)` - Average True Range (custom)

### Input Functions
- `input.int(name, default, minval, maxval)` - Integer input
- `input.float(name, default, minval, maxval)` - Float input
- `input.bool(name, default)` - Boolean input
- `input.source(name, default)` - Source (OHLCV data)

### Plotting Functions
- `plot(series, title, color)` - Plot line
- `plotshape(condition, style, color, location)` - Plot shapes
- `plotarrow(condition, colorup, colordown)` - Plot arrows

### Data Access
- `close`, `open`, `high`, `low`, `volume` - Price data
- `close[1]`, `close[2]` - Historical data with offset

### State Management
- `Persistent[T]` for state preservation across bars
- Simple variables if state not needed

## PINE SCRIPT EQUIVALENTS
Use these translations when thinking in Pine Script terms:
- `ta.sma()` → `Series.sma()`
- `ta.rsi()` → `CurrentSeries.rsi()`
- `crossunder()` → `a < b and a.shift() >= b.shift()`
- `crossover()` → `a > b and a.shift() <= b.shift()`
- `barssince()` → Loop with counter variable

## STRATEGY PATTERNS

### Exhaustion Signal Pattern
```python
# Persistent state
cycle: Persistent[int] = 0
bull: Persistent[int] = 0
bear: Persistent[int] = 0

# Cycle management
if condition:
    bull += 1; bear = 0; cycle = bull
elif condition:
    bear += 1; bull = 0; cycle = bear

# Signal levels
level1_bull = bull == 9
level2_bull = bull == 12  
level3_bull = bull == 14

# Output signals
plot(level1_bull, "Bull L1", color=color.green)
```

### Mean Reversion Pattern
```python
# Calculate deviation from mean
mean = close.sma(20)
deviation = (close - mean) / mean

# Generate reversion signals
oversold = deviation < -0.02  # 2% below mean
overbought = deviation > 0.02  # 2% above mean

# Confirmation with RSI
rsi = close.rsi(14)
rsi_confirm = rsi < 30 if oversold else rsi > 70

# Combined signals
buy_signal = oversold and rsi_confirm
sell_signal = overbought and rsi_confirm
```

### Breakout Pattern
```python
# Price bands
upper_band = close.sma(20) + (close.std(20) * 2)
lower_band = close.sma(20) - (close.std(20) * 2)

# Volume confirmation  
vol_ma = volume.sma(20)
vol_spike = volume > vol_ma * 1.5

# Breakout signals
buy_breakout = close[1] <= upper_band[1] and close > upper_band and vol_spike
sell_breakout = close[1] >= lower_band[1] and close < lower_band and vol_spike
```

Focus on creating robust, production-grade indicators that can handle edge cases and provide reliable signals.
"""

    def _load_pine_documentation(self) -> Dict[str, str]:
        """Load Pine Script documentation for context."""
        return {
            "ta_functions": """
Pine Script Technical Analysis Functions:
- ta.sma(source, length) - Simple Moving Average
- ta.ema(source, length) - Exponential Moving Average
- ta.rsi(source, length) - Relative Strength Index  
- ta.macd(source, fast, slow, signal) - MACD
- ta.bb(source, length, mult) - Bollinger Bands
- ta.stoch(source, length, smoothK, smoothD) - Stochastic
- ta.atr(length) - Average True Range
- ta.crossover(a, b) - Cross over
- ta.crossunder(a, b) - Cross under
""",
            "strategy_functions": """
Pine Script Strategy Functions:
- strategy.entry() - Enter position
- strategy.close() - Close position  
- strategy.exit() - Exit position
- strategy.risk.max_drawdown_percent() - Drawdown limit
- strategy.order() - Advanced order management
""",
        }

    def _load_pynecore_api_docs(self) -> Dict[str, str]:
        """Load PyneCore API documentation."""
        return {
            "series_methods": """
PyneCore Series Methods:
- close.sma(length) - Simple Moving Average
- close.ema(length) - Exponential Moving Average
- close.rsi(length) - Relative Strength Index
- close.std(length) - Standard Deviation
- close.max(length) - Maximum over periods
- close.min(length) - Minimum over periods
""",
            "inputs": """
PyneCore Input Functions:
- input.int(name, default, minval, maxval) - Integer parameter
- input.float(name, default, minval, maxval) - Float parameter  
- input.bool(name, default) - Boolean parameter
- input.source(name, default) - Data source selector (close, open, high, low)
""",
        }

    def _load_trading_templates(self) -> Dict[str, str]:
        """Load trading strategy templates."""
        return {
            "exhaustion": """
Exhaustion Signal Template:
- Track consecutive directional movements
- Multi-level signal strength (L1=weak, L2=medium, L3=strong)
- Reset cycles after strong signals
- Works well for range-bound markets
""",
            "trend_following": """
Trend Following Template:
- Use moving averages for trend direction
- Volume confirmation for breakouts
- Trailing stop-loss logic
- Best for trending markets
""",
            "mean_reversion": """
Mean Reversion Template:
- Calculate deviation from moving average
- Use oscillators (RSI, Stoch) for confirmation
- Fade extreme price movements  
- Best for range-bound markets
""",
        }

    def _build_indicator_system_prompt(self) -> str:
        """Build system prompt for indicator generation."""
        return f"""You are an expert quantitative developer specializing in PyneCore indicator creation. You translate advanced Pine Script concepts to robust PyneCore implementations.

{IMPROVED_PYNECORE_API_REFERENCE}

CRITICAL REQUIREMENTS:
1. Generate syntactically valid PyneCore code
2. Use ONLY the API functions listed above (no improvisation!)
3. Include proper imports exactly as shown
4. All inputs must be defined with input() functions
5. Use plot() with ONLY 3 parameters: plot(value, "label", color=color.xxx)
6. Use & and | operators for boolean operations on Series (NOT 'and'/'or')
7. Include error handling for edge cases
8. Add explanatory comments for key logic

Your responses must be executable PyneCore code without syntax errors or API hallucinations."""

    def _build_signal_system_prompt(self) -> str:
        """Build system prompt for signal strategy generation."""
        return f"""You are an expert quantitative strategy developer creating PyneCore trading systems. You focus on robust signal generation with multiple strength levels.

{IMPROVED_PYNECORE_API_REFERENCE}

STRATEGY REQUIREMENTS:
1. Multi-level signal system (L1=weak, L2=medium, L3=strong)
2. Noise filtering and confirmation logic
3. Edge case handling and robust calculations
4. Clear signal visualization with plots (using ONLY the allowed plot() syntax above!)
5. Backtest-friendly logical structure
6. Production-ready error handling

SIGNAL PATTERNS:
- L1 signals: Standard conditions (fast response)
- L2 signals: Stronger confirmation (medium response)  
- L3 signals: Maximum confirmation (strong response)
- CRITICAL: Use & for boolean operations: level1_bull = (condition1 & condition2)
- Plot each level with ONLY allowed colors (green, red, blue, yellow, white, black)

VALIDATION FOCUS:
- Signal frequency optimization (not too sparse, not too noisy)
- Market condition adaptation
- Risk-adjusted signal strength
- Real-world trading considerations

Generate complete, backtestable PyneCore strategies with NO API hallucinations.
"""

    def _build_strategy_system_prompt(self) -> str:
        """Build system prompt for full strategy generation."""
        return """You are an expert quantitative system architect designing complete PyneCore trading strategies ready for automated trading.

PORTFOLIO-READY REQUIREMENTS:
1. Comprehensive signal generation with noise filtering
2. Multi-timeframe compatibility
3. Variable market condition handling
4. Robust error handling and edge cases
5. Efficient calculations for live trading
6. Clear performance metric integration

RISK MANAGEMENT INTEGRATION:
- Position sizing considerations
- Stop-loss take-profit logic triggers
- Maximum drawdown monitoring signals
- Market volatility adaptation
- Correlation awareness (when applicable)

PRODUCTION CODE STANDARDS:
- Efficient calculations (minimize redundant computations)
- State management with persistence where needed
- Clear separation of calculation, signal generation, and output
- Comprehensive commenting for strategy maintenance
- Modular structure for easy parameter tuning

Create strategies that could pass institutional validation.
"""

    def _build_mutation_system_prompt(self) -> str:
        """Build system prompt for strategy mutation."""
        return f"""You are facilitating genetic algorithm evolution of PyneCore trading strategies through intelligent mutations.

{IMPROVED_PYNECORE_API_REFERENCE}

MUTATION PRINCIPLES:
1. Preserve overall strategy structure and logic flow
2. Apply meaningful changes that create measurable difference
3. Maintain syntactic validity and backtest compatibility
4. Keep signal strength levels if present
5. Adapt mutations to strategy type and market focus
6. Balance innovation (new logic) with similarity (proven structure)
7. CRITICAL: Do NOT add invalid parameters to plot() or use invalid colors!

MUTATION VALIDATION:
- Code must parse and execute without errors
- Strategy should generate different signals from original
- Changes should be meaningful but not destructive
- Preserve essential strategy character
- Ensure backtest comparability
- No API hallucinations (no style=, title= in plot, no invalid colors)

Apply mutations that evolution algorithms would deem valuable, following API constraints exactly.
"""

    def _format_indicators_list(self, indicators: List[str]) -> str:
        """Format indicators list with descriptions."""
        indicator_descriptions = {
            "SMA": "Simple Moving Average - trend following",
            "EMA": "Exponential Moving Average - responsive trend",
            "RSI": "Relative Strength Index - momentum oscillator",
            "MACD": "MACD - trend change detection",
            "BB": "Bollinger Bands - volatility mean reversion",
            "ATR": "Average True Range - volatility measurement",
            "Stoch": "Stochastic Oscillator - momentum reversal",
        }

        formatted = []
        for ind in indicators:
            desc = indicator_descriptions.get(ind, "Custom indicator")
            formatted.append(f"- {ind}: {desc}")

        return "\n".join(formatted)

    def _get_signal_logic_description(self, logic_type: str) -> str:
        """Get description for signal logic type."""
        descriptions = {
            "trend_following": "Follow and ride established market trends with momentum confirmation",
            "mean_reversion": "Identify overextended moves and trade price return to average",
            "breakout": "Trade momentum breaks from established price ranges with volume confirmation",
            "exhaustion": "Identify end of directional moves using multi-level signal strength",
        }
        return descriptions.get(logic_type, "Custom hybrid signal logic")

    def _get_signal_requirements(self, logic_type: str) -> str:
        """Get specific requirements for signal logic type."""
        requirements = {
            "trend_following": """
1. Use moving averages (SMA/EMA) for trend definition
2. Add momentum confirmation (RSI, MACD)
3. Include volume filtering for quality signals
4. Implement trend strength measurement
5. Consider multi-timeframe trend alignment""",
            "mean_reversion": """
1. Calculate deviation from mean (moving average)
2. Use oscillators (RSI, Stochastic) for extreme reading detection
3. Add Bollinger Bands for overbought/oversold levels
4. Include volume spikes for confirmation
5. Implement time-based exit logic""",
            "breakout": """
1. Define clear support/resistance levels
2. Use Bollinger Bands and moving averages for dynamic levels
3. Require volume confirmation (1.5x average or more)
4. Add momentum oscillator confirmation
5. Include volatility filtering""",
            "exhaustion": """
1. Track consecutive directional movements
2. Implement multiple signal strength levels (L1, L2, L3)
3. Use multi-timeframe price relationships
4. Add divergence detection with momentum indicators
5. Include cycle-reset logic after major signals""",
        }

        return requirements.get(logic_type, "")

    def _load_strategy_code(self, strategy_name: str) -> str:
        """Load existing strategy code for mutation."""
        # This would load from storage - placeholder for now
        return "# Existing strategy code placeholder"

    def build_comprehensive_prompt(self, context: PromptContext) -> "LLMRequest":
        """Build comprehensive prompt for strategy generation."""
        if context.strategy_type == "indicator":
            return self.generate_indicator_prompt(context)
        elif context.strategy_type == "signal":
            return self.generate_signal_strategy_prompt(context)
        else:
            return self.generate_signal_strategy_prompt(context)  # Default to signal
