# Globálny Fitness Configuration Guide

## Jednoduché použitie

### **Preset konfigurácie**
```python
from .config.fitness_config import get_fitness_config

# Pre rýchle demo testovanie
config = get_fitness_config("AGGRESSIVE_DEMO")

# Pre výskum a vývoj
config = get_fitness_config("BALANCED_RESEARCH") 

# Pre paper trading
config = get_fitness_config("CONSERVATIVE_PRODUCTION")

# Pre live trading
config = get_fitness_config("LIVE_TRADING_PRODUCTION")
```

### **Vlastné váhy (Quick Update)**
```python
from .config.fitness_config import quick_update_weights

# Zvýšiť dôraz na zisk
config = quick_update_weights({"pnl": 0.4, "sharpe_ratio": 0.15})

# Zamerať sa na Sharpe ratio
config = quick_update_weights({"sharpe_ratio": 0.35})

# Redukovať risk
config = quick_update_weights({"max_drawdown": 0.3, "consistency": 0.2})
```

## Komponenty váženia (0-1)

### **Základné metriky**
- `pnl` (0.25) - Celkový zisk
- `sharpe_ratio` (0.20) - Risk-adjusted returns
- `max_drawdown` (0.20) - Max. drawdown (lower je lepší)
- `win_rate` (0.15) - Percento výherných obchodov

### **Kvalita obchodovania**
- `consistency` (0.10) - Konzistencia (downside deviation)
- `trade_frequency` (0.05) - Frekvencia obchodov

### **Real-world faktory**
- `slippage_resistance` (0.03) - Odpornosť na slippage
- `execution_speed` (0.02) - Rýchlosť vykonania
- `market_diversity` (0.05) - Diverzita trhov

## Použitie v GA

```bash
# S agresívnym fitness (demo)
python -m exhaustionlab.app.backtest.ga_optimizer \
  --llm-evolution \
  --fitness-preset AGGRESSIVE_DEMO \
  --population-size 8 \
  --generations 10

# S konzervatívnym fitness (production)
python -m exhaustionlab.app.backtest.ga_optimizer \
  --llm-evolution \
  --fitness-preset CONSERVATIVE_PRODUCTION \
  --population-size 6 \
  --generations 15
```

## Validácia pre Deployment

Každá stratégia musí prejsť validáciou podľa threshold hodnôt:

- Minimálny fitness skóre: 0.3-0.5
- Minimálny Sharpe ratio: 0.3-1.0  
- Maximálny drawdown: 15-35%
- Win rate: 40-55%
- Minimálne trhy: 2-6
- Minimálne obchody/trh: 5-20
- Slippage < 0.8-2.0%
- Execution < 300-1000ms

## Rýchle príklady

```python
# Výskumná fáza - hľadanie nových stratégií
research_config = get_fitness_config("AGGRESSIVE_DEMO")

# Optimalizačná fáza - doladenie najlepšej stratégie  
optimization_config = get_fitness_config("BALANCED_RESEARCH")

# Validácia pre live trading
validation_config = get_fitness_config("CONSERVATIVE_PRODUCTION")
```

Config je navrhnutý ako "lightweight" - jednoduchý na použitie, ale silný vo výsledkoch!
