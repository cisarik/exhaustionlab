from __future__ import annotations

import numpy as np
import pandas as pd


def compute_squeeze_momentum(
    df: pd.DataFrame,
    length_bb: int = 20,
    mult_bb: float = 2.0,
    length_kc: int = 20,
    mult_kc: float = 1.5,
    use_true_range: bool = True,
) -> pd.DataFrame:
    """Python port of the SQZMOM_LB Pine script.

    Returns DataFrame with:
      - value: histogram value (float)
      - bar_color: string key for the histogram color
      - zero_color: string key for squeeze state color (zero-line markers)
      - sqz_on / sqz_off / no_sqz: boolean state flags
    """
    if df.empty:
        return pd.DataFrame(columns=["value", "bar_color", "zero_color", "sqz_on", "sqz_off", "no_sqz"])

    close = df["close"]
    high = df["high"]
    low = df["low"]

    basis = close.rolling(length_bb).mean()
    dev = close.rolling(length_bb).std(ddof=0) * mult_bb
    upper_bb = basis + dev
    lower_bb = basis - dev

    ma = close.rolling(length_kc).mean()
    if use_true_range:
        prev_close = close.shift(1)
        tr = pd.concat(
            [
                (high - low).abs(),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)
    else:
        tr = (high - low).abs()
    range_ma = tr.rolling(length_kc).mean()
    upper_kc = ma + range_ma * mult_kc
    lower_kc = ma - range_ma * mult_kc

    sqz_on = (lower_bb > lower_kc) & (upper_bb < upper_kc)
    sqz_off = (lower_bb < lower_kc) & (upper_bb > upper_kc)
    no_sqz = ~(sqz_on | sqz_off)

    highest_high = high.rolling(length_kc).max()
    lowest_low = low.rolling(length_kc).min()
    avg_hilo = (highest_high + lowest_low) / 2.0
    avg_close = close.rolling(length_kc).mean()
    avg_all = (avg_hilo + avg_close) / 2.0
    linreg_input = close - avg_all
    value = _rolling_linreg(linreg_input, length_kc)
    value = value.fillna(0.0)

    prev_value = value.shift(1).fillna(0.0)
    bar_color = np.where(
        value > 0,
        np.where(value > prev_value, "lime", "green"),
        np.where(value < prev_value, "red", "maroon"),
    )
    zero_color = np.where(no_sqz, "blue", np.where(sqz_on, "black", "gray"))

    out = pd.DataFrame(
        {
            "value": value,
            "bar_color": bar_color,
            "zero_color": zero_color,
            "sqz_on": sqz_on,
            "sqz_off": sqz_off,
            "no_sqz": no_sqz,
        }
    )
    return out


def _rolling_linreg(series: pd.Series, length: int) -> pd.Series:
    if length <= 1:
        return series.copy()

    x = np.arange(length, dtype=float)
    x_mean = x.mean()
    x_denom = np.sum((x - x_mean) ** 2)

    def linreg(y: np.ndarray) -> float:
        if np.isnan(y).any():
            return np.nan
        y_mean = y.mean()
        slope = np.sum((x - x_mean) * (y - y_mean)) / x_denom
        intercept = y_mean - slope * x_mean
        return slope * (length - 1) + intercept

    return series.rolling(length).apply(linreg, raw=True)
