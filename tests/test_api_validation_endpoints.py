import json
from pathlib import Path
from fastapi.testclient import TestClient

from exhaustionlab.webui.server import app


def _write_sample_backtest(tmp_path: Path) -> Path:
    out = tmp_path / "backtest_out"
    out.mkdir(parents=True, exist_ok=True)

    # Minimal trades.json (2 trades, simple PnL)
    trades = {
        "trades": [
            {
                "id": 1,
                "entry_time": "2024-01-01T00:00:00Z",
                "exit_time": "2024-01-01T01:00:00Z",
                "entry_price": 100.0,
                "exit_price": 102.0,
                "quantity": 1.0,
                "side": "long",
                "pnl": 2.0,
                "pnl_pct": 0.02,
                "commission": 0.0,
                "slippage": 0.0,
                "reason": "signal",
                "duration": 3600,
            },
            {
                "id": 2,
                "entry_time": "2024-01-01T02:00:00Z",
                "exit_time": "2024-01-01T04:00:00Z",
                "entry_price": 104.0,
                "exit_price": 103.0,
                "quantity": 1.0,
                "side": "long",
                "pnl": -1.0,
                "pnl_pct": -0.009615,
                "commission": 0.0,
                "slippage": 0.0,
                "reason": "signal",
                "duration": 7200,
            },
        ]
    }
    (out / "trades.json").write_text(json.dumps(trades))

    # Minimal equity.json (not used deeply by parser currently)
    equity = {
        "equity": [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 10000},
            {"timestamp": "2024-01-01T01:00:00Z", "value": 10200},
            {"timestamp": "2024-01-01T04:00:00Z", "value": 10100},
        ]
    }
    (out / "equity.json").write_text(json.dumps(equity))

    # summary.json with metadata
    summary = {
        "strategy_name": "sample_strategy",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "start_date": "2024-01-01T00:00:00Z",
        "end_date": "2024-01-01T04:00:00Z",
    }
    (out / "summary.json").write_text(json.dumps(summary))

    return out


def test_validation_api_pipeline(tmp_path: Path):
    client = TestClient(app)
    output_dir = _write_sample_backtest(tmp_path)

    # 1) Parse backtest
    r = client.post(
        "/api/validation/parse-backtest",
        json={"output_dir": str(output_dir), "symbol": "BTCUSDT"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "success"
    assert data["backtest"]["total_trades"] == 2
    assert "equity_curve" in data["backtest"]

    # 2) Calculate score
    r = client.post(
        "/api/validation/calculate-score",
        json={
            "backtest_output_dir": str(output_dir),
            "symbol": "BTCUSDT",
            "portfolio_size_usd": 100000,
            "out_of_sample_ratio": 0.7,
            "cross_market_pass_rate": 0.6,
        },
    )
    assert r.status_code == 200, r.text
    score_payload = r.json()
    assert score_payload["status"] == "success"
    assert "scores" in score_payload
    assert 0 <= score_payload["scores"]["total"] <= 100

    # 3) Generate report (writes to reports/)
    r = client.post(
        "/api/validation/generate-report",
        json={
            "backtest_output_dir": str(output_dir),
            "symbol": "BTCUSDT",
            "portfolio_size_usd": 100000,
            "output_filename": "test_validation_report.html",
            "include_costs": True,
            "fee_bps": 10.0,
        },
    )
    assert r.status_code == 200, r.text
    report_payload = r.json()
    assert report_payload["status"] == "success"
    report_path = Path(report_payload["report_path"]).resolve()
    assert report_path.exists(), f"Report not found at {report_path}"

    # 4) Estimate slippage
    r = client.post(
        "/api/validation/estimate-slippage",
        json={
            "symbol": "BTCUSDT",
            "order_size_usd": 10000,
            "signal_frequency": 5.0,
            "volatility": 0.8,
        },
    )
    assert r.status_code == 200, r.text
    slippage_payload = r.json()
    assert slippage_payload["status"] == "success"
    assert "estimate" in slippage_payload
    assert slippage_payload["estimate"]["total_slippage_bps"] >= 0

    # 5) Calculate trading costs for parsed backtest
    r = client.post(
        "/api/validation/calculate-costs",
        json={
            "backtest_output_dir": str(output_dir),
            "symbol": "BTCUSDT",
            "portfolio_size_usd": 100000,
            "include_fees": True,
            "fee_bps": 10.0,
        },
    )
    assert r.status_code == 200, r.text
    costs_payload = r.json()
    assert costs_payload["status"] == "success"
    assert "costs" in costs_payload
    assert "slippage" in costs_payload["costs"]

    # 6) Liquidity info
    r = client.get("/api/validation/liquidity-info/BTCUSDT")
    assert r.status_code == 200, r.text
    lq = r.json()
    assert lq["status"] == "success"
    assert lq["liquidity_info"]["liquidity_class"] in {
        "very_high",
        "high",
        "medium",
        "low",
        "very_low",
    }
