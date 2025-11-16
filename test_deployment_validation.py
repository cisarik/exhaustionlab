"""
Test Complete Deployment Validation Pipeline

Demonstrates the full validation workflow:
1. Multi-market testing
2. Profit analysis
3. Walk-forward validation
4. Monte Carlo simulation
5. Deployment readiness assessment
"""

import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple

from exhaustionlab.app.validation import (
    EnhancedMultiMarketTester,
    ProfitAnalyzer,
    WalkForwardValidator,
    MonteCarloSimulator,
    DeploymentReadinessScorer,
    ValidationChecklist,
)


def create_sample_strategy_func():
    """Create a sample strategy function for testing."""

    def strategy_func(data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Simple momentum strategy example.

        Returns:
            trades_df: DataFrame with columns ['entry_time', 'exit_time', 'pnl']
            equity_curve: Series of equity values
        """
        # Calculate simple moving averages
        data["sma_fast"] = data["close"].rolling(window=10).mean()
        data["sma_slow"] = data["close"].rolling(window=30).mean()

        # Generate signals
        data["signal"] = 0
        data.loc[data["sma_fast"] > data["sma_slow"], "signal"] = 1  # Long
        data.loc[data["sma_fast"] < data["sma_slow"], "signal"] = -1  # Short

        # Simulate trades
        trades = []
        equity = [1.0]
        position = 0
        entry_price = 0

        for i in range(1, len(data)):
            current_signal = data["signal"].iloc[i]
            current_price = data["close"].iloc[i]

            # Entry
            if position == 0 and current_signal != 0:
                position = current_signal
                entry_price = current_price

            # Exit
            elif position != 0 and current_signal != position:
                # Calculate PnL
                if position == 1:  # Long
                    pnl = (current_price / entry_price) - 1
                else:  # Short
                    pnl = (entry_price / current_price) - 1

                trades.append(
                    {
                        "entry_time": data.index[i - 1],
                        "exit_time": data.index[i],
                        "pnl": pnl,
                        "return_pct": pnl * 100,
                    }
                )

                # Update equity
                equity.append(equity[-1] * (1 + pnl))

                # Reset position
                position = 0
                entry_price = 0
            else:
                equity.append(equity[-1])

        # Create DataFrames
        trades_df = pd.DataFrame(trades)
        equity_series = pd.Series(equity, index=data.index[: len(equity)])

        return trades_df, equity_series

    return strategy_func


async def test_multi_market():
    """Test multi-market validation."""
    print("\n" + "=" * 80)
    print("PHASE 1: MULTI-MARKET TESTING")
    print("=" * 80 + "\n")

    tester = EnhancedMultiMarketTester(max_concurrent=2)

    # Create test matrix (reduced for speed)
    test_configs = tester.create_test_matrix(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframes=["5m", "15m"],
        lookback_days=14,
    )

    print(f"Testing {len(test_configs)} market/timeframe combinations...\n")

    strategy_func = create_sample_strategy_func()

    results = await tester.test_strategy(
        strategy_func=strategy_func,
        test_configs=test_configs,
        min_quality_score=50.0,
        min_sharpe=0.5,
    )

    # Generate report
    report = tester.generate_report(results)
    print(report)

    return results


def test_profit_analysis(results):
    """Test profit analysis."""
    print("\n" + "=" * 80)
    print("PHASE 2: PROFIT ANALYSIS")
    print("=" * 80 + "\n")

    # Get first successful test result
    test_result = None
    for result in results.individual_results:
        if result.validation_passed and result.equity_curve is not None:
            test_result = result
            break

    if test_result is None:
        print("⚠️  No successful test results to analyze")
        return None

    analyzer = ProfitAnalyzer()

    profit_metrics = analyzer.analyze(
        equity_curve=test_result.equity_curve,
        trades_df=test_result.trades_df,
    )

    # Generate report
    report = analyzer.generate_report(profit_metrics)
    print(report)

    return profit_metrics


def test_walk_forward(results):
    """Test walk-forward validation."""
    print("\n" + "=" * 80)
    print("PHASE 3: WALK-FORWARD VALIDATION")
    print("=" * 80 + "\n")

    # Get test data from first result
    test_result = None
    for result in results.individual_results:
        if result.validation_passed:
            test_result = result
            break

    if test_result is None:
        print("⚠️  No successful test results for walk-forward")
        return None

    # Fetch data for walk-forward (reusing same config)
    from exhaustionlab.app.data.binance_rest import fetch_klines_csv_like

    data = fetch_klines_csv_like(
        symbol=test_result.config.symbol,
        interval=test_result.config.timeframe,
        limit=500,
    )

    # Add datetime index if not present
    if not isinstance(data.index, pd.DatetimeIndex):
        data["timestamp"] = pd.to_datetime(data["timestamp"], unit="ms")
        data = data.set_index("timestamp")

    validator = WalkForwardValidator()

    strategy_func = create_sample_strategy_func()

    wf_results = validator.validate(
        data=data,
        strategy_func=strategy_func,
        num_periods=3,  # Reduced for speed
        anchored=False,
    )

    # Generate report
    report = validator.generate_report(wf_results)
    print(report)

    return wf_results


def test_monte_carlo(results):
    """Test Monte Carlo simulation."""
    print("\n" + "=" * 80)
    print("PHASE 4: MONTE CARLO SIMULATION")
    print("=" * 80 + "\n")

    # Get test result
    test_result = None
    for result in results.individual_results:
        if result.validation_passed and result.returns_series is not None:
            test_result = result
            break

    if test_result is None:
        print("⚠️  No successful test results for Monte Carlo")
        return None

    simulator = MonteCarloSimulator(num_simulations=100)  # Reduced for speed

    # Bootstrap simulation
    print("Running bootstrap simulation...")
    mc_results = simulator.run_bootstrap_simulation(
        equity_curve=test_result.equity_curve,
        returns=test_result.returns_series,
    )

    # Generate report
    report = simulator.generate_report(mc_results)
    print(report)

    return mc_results


def test_deployment_readiness(multi_market, profit, walk_forward, monte_carlo):
    """Test deployment readiness assessment."""
    print("\n" + "=" * 80)
    print("PHASE 5: DEPLOYMENT READINESS ASSESSMENT")
    print("=" * 80 + "\n")

    # Create custom checklist (relaxed for testing)
    checklist = ValidationChecklist(
        min_markets_passed=2,
        min_pass_rate=0.5,
        min_mean_sharpe=0.5,
        max_mean_drawdown=0.40,
        min_total_return=0.05,
        min_sharpe_ratio=0.5,
        min_quality_score=50.0,
        must_be_statistically_significant=False,  # Relaxed for small sample
        min_wf_pass_rate=0.5,
        max_overfitting_score=70.0,
        min_prob_profit=0.55,
        max_prob_ruin=0.10,
        min_robustness_score=50.0,
    )

    scorer = DeploymentReadinessScorer(checklist=checklist)

    readiness = scorer.assess(
        multi_market=multi_market,
        profit=profit,
        walk_forward=walk_forward,
        monte_carlo=monte_carlo,
    )

    # Generate report
    report = scorer.generate_report(readiness)
    print(report)

    # Save to file
    output_path = Path("deployment_readiness_report.json")
    scorer.save_report(readiness, output_path)
    print(f"\n✅ Full report saved to: {output_path}")

    return readiness


async def main():
    """Run complete validation pipeline."""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "DEPLOYMENT VALIDATION PIPELINE" + " " * 27 + "║")
    print("╚" + "=" * 78 + "╝")

    try:
        # Phase 1: Multi-market testing
        multi_market_results = await test_multi_market()

        # Phase 2: Profit analysis
        profit_metrics = test_profit_analysis(multi_market_results)

        # Phase 3: Walk-forward validation
        walk_forward_results = test_walk_forward(multi_market_results)

        # Phase 4: Monte Carlo simulation
        monte_carlo_results = test_monte_carlo(multi_market_results)

        # Phase 5: Deployment readiness
        readiness = test_deployment_readiness(
            multi_market=multi_market_results,
            profit=profit_metrics,
            walk_forward=walk_forward_results,
            monte_carlo=monte_carlo_results,
        )

        # Final summary
        print("\n" + "╔" + "=" * 78 + "╗")
        print("║" + " " * 30 + "FINAL SUMMARY" + " " * 35 + "║")
        print("╚" + "=" * 78 + "╝\n")

        print(f"Status: {readiness.status.value.upper()}")
        print(f"Risk Level: {readiness.risk_level.value.upper()}")
        print(f"Readiness Score: {readiness.readiness_score:.1f}/100")
        print(f"\nCritical Failures: {len(readiness.critical_failures)}")
        print(f"Warnings: {len(readiness.warnings)}")
        print(f"\nRecommended Position Size: {readiness.recommended_position_size:.2%}")
        print(f"Recommended Max Exposure: {readiness.recommended_max_exposure:.2%}")

        if readiness.status.value == "approved":
            print("\n✅ STRATEGY APPROVED FOR DEPLOYMENT")
        elif readiness.status.value == "conditional":
            print("\n⚠️  STRATEGY CONDITIONALLY APPROVED")
        else:
            print("\n❌ STRATEGY NOT READY FOR DEPLOYMENT")

        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print(f"\n❌ Error during validation: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # Run the complete pipeline
    asyncio.run(main())
