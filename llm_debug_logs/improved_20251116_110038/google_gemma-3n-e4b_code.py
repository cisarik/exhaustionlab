from pynecore import Series, color, input, plot, script
from pynecore.lib import close


@script.indicator(title="RSI Momentum Strategy", overlay=True)
def main():
    # 1. Define inputs (use ONLY input.int or input.float)
    period = input.int("Period", 14)
    sma_length = input.int("SMA Length", 20)

    # 2. Calculate indicators
    rsi = close.rsi(period)
    sma = close.sma(sma_length)

    # 3. Generate signals (use & not 'and')
    buy = (rsi < 30) & (close > sma)
    sell = (rsi > 70) & (close < sma)

    # 4. Plot (use EXACT syntax below)
    plot(buy, "Buy", color=color.green)
    plot(sell, "Sell", color=color.red)

    return {"buy": buy, "sell": sell}
