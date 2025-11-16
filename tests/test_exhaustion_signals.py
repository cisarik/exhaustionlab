import pandas as pd

from exhaustionlab.app.backtest.engine import compute_exhaustion_signals


def test_compute_exhaustion_signals_basic_sequence():
    # Construct a deterministic OHLC series: rising close for 12 bars then falling
    closes = [1 + i * 0.01 for i in range(15)] + [1.14 - i * 0.02 for i in range(15)]
    data = {
        "ts_open": list(range(len(closes))),
        "open": closes,
        "high": [c + 0.005 for c in closes],
        "low": [c - 0.005 for c in closes],
        "close": closes,
        "volume": [100] * len(closes),
    }
    df = pd.DataFrame(data)

    sig = compute_exhaustion_signals(df, level1=3, level2=4, level3=5)

    # Expect at least one bull_l1 trigger while price is rising
    assert sig["bull_l1"].any()
    # Once price starts falling, bear sequences should appear
    assert sig["bear_l1"].any()
