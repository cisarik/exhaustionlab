import pandas as pd

from exhaustionlab.app.backtest.indicators import compute_squeeze_momentum


def build_dummy_df(rows: int = 60) -> pd.DataFrame:
    base = 1.0
    closes = []
    for i in range(rows):
        # oscillate to trigger both bull/bear histograms
        base += 0.003 if i % 10 < 5 else -0.002
        closes.append(base)
    data = {
        "ts_open": list(range(rows)),
        "open": closes,
        "high": [c + 0.002 for c in closes],
        "low": [c - 0.002 for c in closes],
        "close": closes,
        "volume": [100] * rows,
    }
    return pd.DataFrame(data)


def test_compute_squeeze_momentum_shapes_and_states():
    df = build_dummy_df()
    out = compute_squeeze_momentum(
        df, length_bb=10, mult_bb=2.0, length_kc=10, mult_kc=1.5
    )

    assert len(out) == len(df)
    assert set(out.columns) == {
        "value",
        "bar_color",
        "zero_color",
        "sqz_on",
        "sqz_off",
        "no_sqz",
    }
    # At least one squeeze on/off event should occur
    assert out["sqz_on"].any() or out["sqz_off"].any()
    # Histogram colors should only use expected palette
    assert set(out["bar_color"].unique()) <= {"lime", "green", "red", "maroon"}
