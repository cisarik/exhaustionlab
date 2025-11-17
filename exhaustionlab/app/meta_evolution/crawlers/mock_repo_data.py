"""
Local mock data for GitHub repositories used by BDD tests.

These fixtures allow the GitHub extractor to run without performing
external network requests, ensuring deterministic behaviour.
"""

from __future__ import annotations

from typing import Any, Dict

BASE_PINE_CODE = """\
//@version=5
indicator("Mock Exhaustion Strategy", overlay=true)
length = input.int(14, "Length")
source = input.source(close, "Source")
threshold = input.float(70.0, "Threshold")
fast = ta.ema(source, 12)
slow = ta.ema(source, 26)
macd_val = ta.macd(close, 12, 26, 9)
rsi_val = ta.rsi(source, length)
plot(rsi_val, color=color.blue)
plot(macd_val, color=color.orange)
alertcondition(rsi_val > threshold, "Sell Signal", "RSI exhaustion")
"""


def _make_repo_info(name: str, author: str, stars: int) -> Dict[str, Any]:
    """Helper to create repo metadata."""
    return {
        "name": name,
        "author": author,
        "description": f"Mock repository for {name}.",
        "url": f"https://github.com/{author}/{name}",
        "stars": stars,
        "forks": max(1, stars // 5),
        "watchers": max(1, stars // 6),
        "platform": "github",
        "tags": ["mock", "test"],
        "category": "momentum",
        "market_focus": ["crypto"],
    }


MOCK_REPOSITORIES: Dict[str, Dict[str, Any]] = {
    "user/trading-strategy": {
        "repo_info": _make_repo_info("trading-strategy", "user", 150),
        "readme": ("# Mock Trading Strategy\n\n" "Includes stop loss, take profit, and position sizing guidance."),
        "pine_code": BASE_PINE_CODE + 'strategy.exit("TP", from_entry="Long", limit=take_profit)\n',
        "python_code": "def run_backtest():\n    return True\n",
        "backtest_metrics": {
            "sharpe_ratio": 1.85,
            "max_drawdown": 0.18,
            "win_rate": 0.56,
            "profit_factor": 1.7,
        },
        "has_tests": True,
    },
    "tradingview/pine-seeds": {
        "repo_info": _make_repo_info("pine-seeds", "tradingview", 90),
        "pine_code": """\
//@version=5
indicator("Pine Seeds Example")
plot(close)
""",
    },
    "f13end/tradingview-pinescript-indicators": {
        "repo_info": _make_repo_info("tradingview-pinescript-indicators", "f13end", 60),
        "readme": ("# Indicator Collection\n\n" "This mock README demonstrates documentation extraction."),
        "pine_code": BASE_PINE_CODE,
    },
    "nonexistent/fake-repo-12345": {"error": "Repository not found on GitHub"},
}


for idx in range(5):
    repo_name = f"user/repo{idx}"
    MOCK_REPOSITORIES[repo_name] = {
        "repo_info": _make_repo_info(f"repo{idx}", "user", 20 + idx * 5),
        "readme": f"# Repo {idx}\n\nBatch extraction demo repository {idx}.",
        "pine_code": BASE_PINE_CODE + f"plot(close * {idx + 1})\n",
    }
