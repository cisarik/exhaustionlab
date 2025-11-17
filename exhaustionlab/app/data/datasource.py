from typing import Dict, Iterable, Protocol


class DataSource(Protocol):
    def iter_ohlcv(self) -> Iterable[Dict]: ...
