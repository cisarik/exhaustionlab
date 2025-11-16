from fastapi.testclient import TestClient
import pandas as pd

from exhaustionlab.webui.server import app


def test_chart_endpoint_with_mocked_data(monkeypatch):
    """Test /api/charts/candlestick.png without hitting Binance."""
    client = TestClient(app)

    # Provide a small deterministic dataframe
    def _fake_fetch_klines(
        symbol: str = "ADAEUR", interval: str = "1m", limit: int = 200
    ) -> pd.DataFrame:
        rows = max(50, min(limit, 200))
        ts = list(range(rows))
        base = 1.0
        opens = [base + i * 0.001 for i in range(rows)]
        highs = [o + 0.002 for o in opens]
        lows = [o - 0.002 for o in opens]
        closes = [o + (0.001 if i % 2 == 0 else -0.0005) for i, o in enumerate(opens)]
        volume = [100.0] * rows
        return pd.DataFrame(
            {
                "ts_open": ts,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volume,
            }
        )

    monkeypatch.setattr(
        "exhaustionlab.webui.chart_generator.fetch_klines_csv_like",
        _fake_fetch_klines,
    )

    r = client.get(
        "/api/charts/candlestick.png",
        params={
            "symbol": "ADAEUR",
            "timeframe": "1m",
            "limit": 120,
            "width": 800,
            "height": 600,
            "signals": True,
            "volume": True,
        },
    )
    assert r.status_code == 200
    assert r.headers.get("content-type") == "image/png"
    assert len(r.content) > 1000


def test_evolution_overview():
    client = TestClient(app)
    r = client.get("/api/evolution/overview")
    assert r.status_code == 200
    data = r.json()
    # Expect keys from EvolutionAnalytics model
    assert "metrics" in data
    assert "total_strategies" in data["metrics"]
