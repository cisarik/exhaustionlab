from fastapi.testclient import TestClient

from exhaustionlab.webui.server import app


def test_live_trading_deploy_and_stop():
    client = TestClient(app)

    # Deploy a dummy strategy
    deploy_req = {
        "strategy_id": "demo-001",
        "strategy_name": "Demo Strategy",
        "mode": "paper",
        "symbols": ["ADAEUR"],
        "timeframe": "1m",
        "max_position_size": 0.02,
        "max_daily_loss": 0.01,
        "max_drawdown": 0.05,
        "max_open_positions": 1,
        "enable_stop_loss": True,
        "stop_loss_pct": 0.02,
        "enable_take_profit": True,
        "take_profit_pct": 0.05,
        "exchange": "binance",
        "testnet": True,
    }

    r = client.post("/api/trading/deploy", json=deploy_req)
    assert r.status_code == 200, r.text
    payload = r.json()
    deployment_id = payload["deployment_id"]
    assert payload["status"] == "deployed"
    assert deployment_id

    # List deployments
    r = client.get("/api/trading/deployments")
    assert r.status_code == 200
    deployments = r.json()
    assert any(d["deployment_id"] == deployment_id for d in deployments)

    # Get single deployment status
    r = client.get(f"/api/trading/deployment/{deployment_id}")
    assert r.status_code == 200
    status = r.json()
    assert status["deployment_id"] == deployment_id
    assert status["status"] in {"active", "paused", "stopped", "error"}

    # Stop deployment to cleanup background task
    r = client.post(f"/api/trading/stop/{deployment_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "stopped"
