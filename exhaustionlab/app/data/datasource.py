from typing import Protocol, Iterable, Dict


class DataSource(Protocol):
    def iter_ohlcv(self) -> Iterable[Dict]: ...
