# LLM Generation Analysis Report
**Model**: google/gemma-3n-e4b  
**Date**: 2025-11-16  
**Session**: session_20251116_105821

## Summary
The model **generated syntactically correct Python code**, but contains **several hallucinations** where it invented API features that don't exist in PyneCore.

## ✅ What The Model Got RIGHT

1. **Overall Structure** - Perfect
   - ✅ Correct `@script.indicator()` decorator
   - ✅ Proper `main()` function definition
   - ✅ Correct `input.int()` usage
   - ✅ Valid return statement with dict

2. **Indicator Calls** - Correct
   - ✅ `close.rsi(period)` - Valid API
   - ✅ `close.sma(period)` - Valid API

3. **Code Organization** - Good
   - Clear comments
   - Logical sections (inputs → calculations → signals → plots)
   - Clean formatting

## ❌ HALLUCINATIONS Detected

### 1. **Invalid `plot()` Parameters**

**Generated Code**:
```python
plot(rsi_value, "RSI", color=color.purple, title="RSI")
plot(buy_signal, "Buy", color=color.green, style=plot.Style.POINT)
```

**Problems**:
- ❌ `title="RSI"` parameter **doesn't exist** in PyneCore plot()
- ❌ `style=plot.Style.POINT` **doesn't exist** - hallucinated enum

**Correct PyneCore API** (from actual code):
```python
plot(rsi_value, "RSI", color=color.purple)  # No 'title' parameter
plot(buy_signal, "Buy", color=color.green)   # No 'style' parameter
```

### 2. **Potentially Invalid Colors**

**Generated**:
```python
color.purple
color.orange
```

**Status**: Need to verify if these exist. Standard colors in examples are:
- ✅ `color.green`
- ✅ `color.red`
- ✅ `color.blue`
- ❓ `color.purple` (not seen in examples)
- ❓ `color.orange` (not seen in examples)

### 3. **Missing Import**

**Generated**:
```python
from pynecore import script, input, plot, color, Series
```

**Problem**: ❌ `close` is not imported!

**Correct Import** (from actual PyneCore code):
```python
from pynecore import Series, Persistent
from pynecore.lib import script, close, plot, color, input
```

OR:

```python
from pynecore import Series, input, plot, color, script
# close is implicitly available
```

### 4. **Boolean Operator Issue**

**Generated**:
```python
buy_signal = rsi_value < 30 and close > sma_value
sell_signal = rsi_value > 70 and close < sma_value
```

**Problem**: ❌ Using Python's `and` operator instead of pandas-like `&`

**Correct PyneCore Syntax** (from examples):
```python
# Should likely be:
buy_signal = (rsi_value < 30) & (close > sma_value)
sell_signal = (rsi_value > 70) & (close < sma_value)
```

## Why These Hallucinations Occur

### Root Cause Analysis:

1. **Generic Programming Knowledge**
   - Model knows Python has `style` parameters (from matplotlib, etc.)
   - Model knows about `title` parameters (common in plotting libraries)
   - Model generalizes from other APIs it's seen

2. **Incomplete System Prompt**
   - System prompt shows basic structure but doesn't explicitly list ALL plot() parameters
   - Doesn't show what parameters are FORBIDDEN
   - Doesn't provide negative examples ("DON'T use...")

3. **Small Model Size**
   - gemma-3n-e4b is a 4B parameter model (small)
   - May not have enough capacity to remember exact API details
   - Falls back to "reasonable assumptions" that are wrong

4. **No Real PyneCore Training Data**
   - PyneCore is a custom/niche library
   - Model likely never saw real PyneCore code during training
   - Makes up what "seems reasonable" based on similar libraries

## Impact Assessment

### Severity: **MEDIUM-HIGH**

- **Syntax**: Code will NOT run due to invalid parameters
- **Logic**: Even if parameters fixed, `and` operator may cause issues
- **Imports**: Missing `close` import will cause NameError
- **Fix Effort**: Manual correction required for each issue

### Would This Pass Validation?

**Current validation** (from debug output):
- ✅ Syntax check: PASS (Python syntax is valid)
- ✅ Structure check: PASS (has decorator, main, inputs, return)
- ❌ **API validation**: Would need to check parameter validity
- ❌ **Runtime validation**: Would fail with NameError or TypeError

## Recommendations

### 1. **Improve System Prompt** (CRITICAL)

Add explicit API constraints:

```python
# CORRECT PLOT SYNTAX:
plot(value, "Name", color=color.green)

# INVALID - DO NOT USE:
# ❌ plot(..., title="x")        # No 'title' parameter!
# ❌ plot(..., style=X)           # No 'style' parameter!
# ❌ plot(..., linewidth=X)       # No 'linewidth' parameter!

# AVAILABLE COLORS ONLY:
color.green, color.red, color.blue, color.yellow, color.white, color.black
# ❌ color.purple, color.orange - DO NOT USE!
```

### 2. **Add Negative Examples**

Show what NOT to do:

```python
# ❌ WRONG:
buy_signal = rsi < 30 and price > sma  # Don't use 'and'

# ✅ CORRECT:
buy_signal = (rsi < 30) & (price > sma)  # Use '&' for Series
```

### 3. **Explicit Import Template**

```python
# REQUIRED IMPORTS (copy exactly):
from pynecore import Series, input, plot, color, script
from pynecore.lib import close

# OR simplified:
from pynecore import *
```

### 4. **Add API Reference Card**

```
PLOT API:
  plot(series, label, color=color.XXX)
  
  Parameters:
    - series: The data to plot
    - label: String name (required)
    - color: ONLY use color.green/red/blue/yellow/white/black
  
  NO OTHER PARAMETERS SUPPORTED!
```

### 5. **Try Different Models**

Test with:
- ✅ `deepseek/deepseek-r1-0528-qwen3-8b` (8B, reasoning model)
- ✅ `google/gemma-3-12b` (12B, larger version)
- Consider: Larger models may remember exact APIs better

### 6. **Add Few-Shot Examples**

Include 2-3 complete, working examples in the prompt:

```python
# EXAMPLE 1: Simple RSI Strategy
from pynecore import Series, input, plot, color, script
from pynecore.lib import close

@script.indicator(title="RSI Strategy", overlay=True)
def main():
    period = input.int("Period", 14)
    rsi = close.rsi(period)
    buy = rsi < 30
    sell = rsi > 70
    plot(buy, "Buy", color=color.green)
    plot(sell, "Sell", color=color.red)
    return {"buy": buy, "sell": sell}
```

## Next Steps

1. **Enhance Prompt** with negative examples and explicit constraints
2. **Test with deepseek-r1** (reasoning model may catch its own errors)
3. **Add validator** that checks for forbidden parameters
4. **Iterate**: Run 5-10 generations, analyze patterns
5. **Consider hybrid approach**: LLM generates skeleton → rule-based validator fixes API calls

## Conclusion

The **experiment makes sense**, but requires **significant prompt engineering**:

- ✅ Model CAN understand the task
- ✅ Model CAN generate reasonable code structure
- ❌ Model HALLUCINATES API details without explicit guidance
- ⚠️ Small models (4B) may be too limited
- 💡 **Solution**: Better prompts + larger models + validation pipeline

**Recommendation**: Continue with enhanced prompts and try deepseek-r1-0528-qwen3-8b (reasoning model).
