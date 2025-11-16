import requests, time, pandas as pd
from ...utils.timeframes import to_binance_interval

BINANCE_API = "https://api.binance.com/api/v3/klines"


def fetch_klines_csv_like(
    symbol: str = "ADAEUR", interval: str = "1m", limit: int = 500
) -> pd.DataFrame:
    params = dict(
        symbol=symbol.upper(),
        interval=to_binance_interval(interval),
        limit=max(10, min(limit, 1000)),
    )
    r = requests.get(BINANCE_API, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    cols = [
        "ts_open",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "ts_close",
        "qav",
        "trades",
        "taker_base",
        "taker_quote",
        "ignore",
    ]
    df = pd.DataFrame(data, columns=cols)
    df = df.astype(
        {
            "ts_open": "int64",
            "open": "float",
            "high": "float",
            "low": "float",
            "close": "float",
            "volume": "float",
            "ts_close": "int64",
        }
    )
    df = df[["ts_open", "open", "high", "low", "close", "volume"]]
    df["ts_open"] = df["ts_open"] / 1000.0
    return df


if __name__ == "__main__":
    import argparse, sys

    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="ADAEUR")
    p.add_argument("--interval", default="1m")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--csv", default="data/ADAEUR-1m.csv")
    args = p.parse_args()
    df = fetch_klines_csv_like(args.symbol, args.interval, args.limit)
    out = args.csv
    import pathlib

    pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows -> {out}")
