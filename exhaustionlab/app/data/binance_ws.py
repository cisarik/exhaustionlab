import asyncio
import json
import time

import websockets
from ...utils.timeframes import to_binance_interval


class BinanceWS:
    def __init__(self, symbol="ADAEUR", interval="1m", on_kline=None):
        self.symbol = symbol.lower()
        self.interval = to_binance_interval(interval)
        self.on_kline = on_kline
        self._task = None
        self._stop = asyncio.Event()

    async def start(self):
        stream = f"{self.symbol}@kline_{self.interval}"
        url = f"wss://stream.binance.com:9443/ws/{stream}"
        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    url, ping_interval=20, ping_timeout=20, close_timeout=5
                ) as ws:
                    async for msg in ws:
                        if self._stop.is_set():
                            break
                        data = json.loads(msg)
                        if "k" in data:
                            k = data["k"]
                            payload = {
                                "t": k["t"],
                                "o": k["o"],
                                "h": k["h"],
                                "l": k["l"],
                                "c": k["c"],
                                "v": k["v"],
                                "x": k["x"],
                            }
                            if self.on_kline:
                                self.on_kline(payload)
            except Exception as e:
                await asyncio.sleep(1.0)  # basic backoff

    async def stop(self):
        self._stop.set()


class BinanceBookTickerWS:
    """Streams best bid/ask via Binance `bookTicker` channel."""

    def __init__(self, symbol="ADAEUR", on_quote=None):
        self.symbol = symbol.lower()
        self.on_quote = on_quote
        self._stop = asyncio.Event()

    async def start(self):
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@bookTicker"
        while not self._stop.is_set():
            try:
                async with websockets.connect(
                    url, ping_interval=20, ping_timeout=20, close_timeout=5
                ) as ws:
                    async for msg in ws:
                        if self._stop.is_set():
                            break
                        data = json.loads(msg)
                        payload = {
                            "bid": float(data["b"]),
                            "ask": float(data["a"]),
                            "bid_qty": float(data.get("B", 0.0)),
                            "ask_qty": float(data.get("A", 0.0)),
                            "ts": data.get("T", time.time() * 1000) / 1000.0,
                        }
                        if self.on_quote:
                            self.on_quote(payload)
            except Exception:
                await asyncio.sleep(1.0)

    async def stop(self):
        self._stop.set()
