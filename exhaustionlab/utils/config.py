import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    exchange: str = os.getenv("EXCHANGE", "binance")
    symbol: str = os.getenv("SYMBOL", "ADAEUR")
    timeframe: str = os.getenv("TIMEFRAME", "1m")
    ws_enabled: bool = os.getenv("WS_ENABLED", "true").lower() in ("1", "true", "yes")


settings = Settings()
