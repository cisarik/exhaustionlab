from pynecore import Series, color, input, plot, script


@script.indicator(title="RSI & SMA Momentum Strategy", overlay=True)
def main():
    # 1. Define inputs
    rsi_period = input.int("RSI Period", 14)
    sma_period = input.int("SMA Period", 20)

    # 2. Calculate indicators
    rsi_value = close.rsi(rsi_period)
    sma_value = close.sma(sma_period)

    # 3. Generate signals
    buy_signal = rsi_value < 30 and close > sma_value
    sell_signal = rsi_value > 70 and close < sma_value

    # 4. Plot results
    plot(rsi_value, "RSI", color=color.purple, title="RSI")
    plot(sma_value, "SMA", color=color.orange, title="SMA")
    plot(buy_signal, "Buy", color=color.green, style=plot.Style.POINT)
    plot(sell_signal, "Sell", color=color.red, style=plot.Style.POINT)

    return {"buy": buy_signal, "sell": sell_signal}
