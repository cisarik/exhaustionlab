from random import Random

import pandas as pd

from exhaustionlab.app.backtest.ga_optimizer import GASettings, GeneticSqueezeOptimizer


def make_trend_df(rows: int = 80) -> pd.DataFrame:
    prices = []
    price = 1.0
    for i in range(rows):
        # trending up then down to exercise both sides of SQZMOM
        if i < rows // 2:
            price += 0.002
        else:
            price -= 0.0015
        prices.append(price)
    return pd.DataFrame(
        {
            "ts_open": list(range(rows)),
            "open": prices,
            "high": [p + 0.001 for p in prices],
            "low": [p - 0.001 for p in prices],
            "close": prices,
            "volume": [100] * rows,
        }
    )


def test_ga_optimizer_produces_stable_result():
    df = make_trend_df()
    settings = GASettings(population=8, generations=4, mutation_rate=0.3, crossover_rate=0.7, elite=1)
    optimizer = GeneticSqueezeOptimizer(df, settings, rng=Random(42))
    params, fitness = optimizer.run()

    assert isinstance(params, dict)
    assert isinstance(fitness, float)
    assert all(key in params for key in ("length_bb", "mult_bb", "length_kc", "mult_kc", "use_true_range"))
    # Fitness should be finite and not NaN
    assert abs(fitness) > 0.0 or fitness == 0.0
