# Integration Guide: Deployment Validation → ExhaustionLab

## Overview

This guide shows how to integrate the new deployment validation system with existing ExhaustionLab components.

## Architecture Integration

```
┌─────────────────────────────────────────────────────────────┐
│                  ExhaustionLab System                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │ Strategy         │         │  LLM Strategy    │         │
│  │ Evolution        │────────▶│  Generator       │         │
│  └──────────────────┘         └──────────────────┘         │
│           │                            │                    │
│           ▼                            ▼                    │
│  ┌──────────────────────────────────────────────┐          │
│  │      Unified Evolution Engine                │          │
│  │  • GA Optimization                           │          │
│  │  • LLM Mutations                             │          │
│  │  • Hybrid Approach                           │          │
│  └──────────────────────────────────────────────┘          │
│           │                                                 │
│           │ Generated Strategies                            │
│           ▼                                                 │
│  ┌──────────────────────────────────────────────┐          │
│  │  ⭐ NEW: Deployment Validation Pipeline      │          │
│  │                                              │          │
│  │  1. Multi-Market Testing                     │          │
│  │  2. Profit Analysis                          │          │
│  │  3. Walk-Forward Validation                  │          │
│  │  4. Monte Carlo Simulation                   │          │
│  │  5. Deployment Readiness                     │          │
│  └──────────────────────────────────────────────┘          │
│           │                                                 │
│           │ Validation Results                              │
│           ▼                                                 │
│  ┌──────────────────────────────────────────────┐          │
│  │      Strategy Registry                       │          │
│  │  • Store validated strategies                │          │
│  │  • Track deployment status                   │          │
│  │  • Version control                           │          │
│  └──────────────────────────────────────────────┘          │
│           │                                                 │
│           │ Approved Strategies                             │
│           ▼                                                 │
│  ┌──────────────────────────────────────────────┐          │
│  │      Live Trading Engine                     │          │
│  │  • Execute approved strategies               │          │
│  │  • Monitor performance                       │          │
│  │  • Risk management                           │          │
│  └──────────────────────────────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Integration Point 1: UnifiedEvolutionEngine

### Current Code
```python
# exhaustionlab/app/backtest/unified_evolution.py
class UnifiedEvolutionEngine:
    def evolve_strategy(self, ...):
        # ... evolution logic ...
        
        # Currently just returns best strategy
        return EvolutionResult(
            best_strategy=best,
            best_fitness=fitness,
            ...
        )
```

### Enhanced Code
```python
# exhaustionlab/app/backtest/unified_evolution.py
from ..validation import (
    EnhancedMultiMarketTester,
    DeploymentReadinessScorer,
)

class UnifiedEvolutionEngine:
    def __init__(self, ..., enable_validation: bool = True):
        self.enable_validation = enable_validation
        if enable_validation:
            self.validator = EnhancedMultiMarketTester()
            self.scorer = DeploymentReadinessScorer()
    
    async def evolve_strategy(self, ..., validate_before_accept: bool = True):
        # ... evolution logic ...
        
        # NEW: Validate before accepting
        if self.enable_validation and validate_before_accept:
            logger.info("Validating evolved strategy...")
            
            validation_results = await self.validator.test_strategy(
                strategy_func=best_strategy,
                min_quality_score=60.0,
                min_sharpe=1.0,
            )
            
            readiness = self.scorer.assess(multi_market=validation_results)
            
            # Only accept if approved or conditional
            if readiness.status.value in ["approved", "conditional"]:
                logger.info(f"Strategy ACCEPTED: {readiness.status.value}")
                return EvolutionResult(
                    best_strategy=best,
                    best_fitness=fitness,
                    validation_result=readiness,  # NEW
                    deployment_ready=True,  # NEW
                )
            else:
                logger.warning(f"Strategy REJECTED: {readiness.status.value}")
                # Continue evolution or try next candidate
                return self._evolve_next_candidate(...)
        
        return EvolutionResult(...)
```

## Integration Point 2: StrategyRegistry

### Current Schema
```python
# exhaustionlab/app/backtest/strategy_registry.py
@dataclass
class StrategyMetrics:
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    # ... existing fields ...
```

### Enhanced Schema
```python
# exhaustionlab/app/backtest/strategy_registry.py
from ..validation import ReadinessReport

@dataclass
class StrategyMetrics:
    # Existing fields
    total_pnl: float
    sharpe_ratio: float
    max_drawdown: float
    # ... existing fields ...
    
    # NEW: Validation results
    validation_status: Optional[str] = None  # approved/conditional/rejected
    readiness_score: Optional[float] = None  # 0-100
    risk_level: Optional[str] = None  # low/medium/high/extreme
    deployment_ready: bool = False
    validation_timestamp: Optional[datetime] = None
    validation_report_path: Optional[str] = None  # Path to detailed report

class StrategyRegistry:
    def record_validation_result(
        self,
        strategy_id: str,
        version_id: str,
        readiness: ReadinessReport,
    ):
        """Store validation results."""
        conn = sqlite3.connect(self.db_path)
        
        # Update strategy_metrics table
        conn.execute("""
            UPDATE strategy_metrics
            SET validation_status = ?,
                readiness_score = ?,
                risk_level = ?,
                deployment_ready = ?,
                validation_timestamp = ?
            WHERE strategy_id = ? AND version_id = ?
        """, (
            readiness.status.value,
            readiness.readiness_score,
            readiness.risk_level.value,
            readiness.status.value in ["approved", "conditional"],
            datetime.now().isoformat(),
            strategy_id,
            version_id,
        ))
        
        conn.commit()
        conn.close()
        
        # Save detailed report
        report_path = self.reports_dir / f"{strategy_id}_{version_id}_validation.json"
        with open(report_path, 'w') as f:
            json.dump(readiness.to_dict(), f, indent=2)
    
    def get_deployable_strategies(
        self,
        min_readiness_score: float = 70.0,
        allowed_risk_levels: List[str] = ["low", "medium"],
    ) -> List[Tuple[str, str]]:
        """Get strategies approved for deployment."""
        conn = sqlite3.connect(self.db_path)
        
        results = conn.execute("""
            SELECT strategy_id, version_id, readiness_score, risk_level
            FROM strategy_metrics
            WHERE deployment_ready = 1
              AND readiness_score >= ?
              AND risk_level IN ({})
            ORDER BY readiness_score DESC
        """.format(','.join('?' * len(allowed_risk_levels))),
            [min_readiness_score] + allowed_risk_levels
        ).fetchall()
        
        conn.close()
        
        return [(row[0], row[1]) for row in results]
```

## Integration Point 3: Adaptive Parameter Optimization

### Current Code
```python
# exhaustionlab/app/meta_evolution/adaptive_parameters.py
class AdaptiveParameterOptimizer:
    def update_from_result(self, config: Dict, quality_score: float, success: bool):
        # Update based on quality score
        pass
```

### Enhanced Code
```python
# exhaustionlab/app/meta_evolution/adaptive_parameters.py
from ..validation import ReadinessReport

class AdaptiveParameterOptimizer:
    def update_from_validation(
        self,
        config: Dict,
        readiness: ReadinessReport,
    ):
        """Update optimizer based on deployment validation results."""
        
        # Use deployment readiness as quality signal
        quality_score = readiness.readiness_score
        success = readiness.status.value in ["approved", "conditional"]
        
        # Weight by component scores
        weights = {
            'temperature': readiness.profit_quality_score / 100,
            'max_indicators': readiness.multi_market_score / 100,
            'complexity_preference': (100 - readiness.walk_forward_score) / 100,  # Less complexity if overfitting
        }
        
        # Update parameters with weighted scores
        for param, weight in weights.items():
            if param in config:
                self.update_from_result(
                    {param: config[param]},
                    quality_score * weight,
                    success
                )
        
        # Learn from validation patterns
        if readiness.status.value == "rejected":
            # Penalize configurations that lead to rejection
            for param, value in config.items():
                self._penalize_configuration(param, value)
        
        elif readiness.status.value == "approved":
            # Reinforce successful configurations
            for param, value in config.items():
                self._reinforce_configuration(param, value)
```

## Integration Point 4: WebUI Integration

### Add Validation Tab

```python
# exhaustionlab/webui/routes/validation.py
from fastapi import APIRouter, HTTPException
from ..validation import (
    EnhancedMultiMarketTester,
    ProfitAnalyzer,
    WalkForwardValidator,
    MonteCarloSimulator,
    DeploymentReadinessScorer,
)

router = APIRouter()

@router.post("/api/validate-strategy/{strategy_id}")
async def validate_strategy(strategy_id: str, version_id: str):
    """
    Run complete validation pipeline on a strategy.
    
    Returns:
        Deployment readiness report
    """
    # Get strategy from registry
    registry = get_strategy_registry()
    strategy = registry.get_strategy(strategy_id, version_id)
    
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    # Phase 1: Multi-market
    tester = EnhancedMultiMarketTester()
    multi_market = await tester.test_strategy(strategy.func)
    
    # Phase 2: Profit analysis
    analyzer = ProfitAnalyzer()
    best_result = multi_market.individual_results[0]
    profit = analyzer.analyze(
        equity_curve=best_result.equity_curve,
        trades_df=best_result.trades_df,
    )
    
    # Phase 3: Walk-forward
    validator = WalkForwardValidator()
    walk_forward = validator.validate(data, strategy.func)
    
    # Phase 4: Monte Carlo
    simulator = MonteCarloSimulator()
    monte_carlo = simulator.run_bootstrap_simulation(
        best_result.equity_curve,
        best_result.returns_series,
    )
    
    # Phase 5: Deployment readiness
    scorer = DeploymentReadinessScorer()
    readiness = scorer.assess(
        multi_market=multi_market,
        profit=profit,
        walk_forward=walk_forward,
        monte_carlo=monte_carlo,
    )
    
    # Store results
    registry.record_validation_result(strategy_id, version_id, readiness)
    
    return readiness.to_dict()

@router.get("/api/strategies/deployable")
async def get_deployable_strategies():
    """Get all strategies approved for deployment."""
    registry = get_strategy_registry()
    return registry.get_deployable_strategies()
```

### Add Frontend Component

```vue
<!-- exhaustionlab/webui/static/components/ValidationReport.vue -->
<template>
  <div class="validation-report">
    <h2>Deployment Validation</h2>
    
    <div class="status-badge" :class="statusClass">
      {{ readiness.status.toUpperCase() }}
    </div>
    
    <div class="score">
      <h3>Readiness Score</h3>
      <div class="score-bar">
        <div class="score-fill" :style="{ width: readiness.readiness_score + '%' }"></div>
      </div>
      <p>{{ readiness.readiness_score.toFixed(1) }}/100</p>
    </div>
    
    <div class="components">
      <h3>Component Scores</h3>
      <ul>
        <li>Multi-Market: {{ readiness.multi_market_score.toFixed(1) }}/100</li>
        <li>Profit Quality: {{ readiness.profit_quality_score.toFixed(1) }}/100</li>
        <li>Walk-Forward: {{ readiness.walk_forward_score.toFixed(1) }}/100</li>
        <li>Monte Carlo: {{ readiness.monte_carlo_score.toFixed(1) }}/100</li>
      </ul>
    </div>
    
    <div v-if="readiness.critical_failures.length > 0" class="failures">
      <h3>❌ Critical Failures</h3>
      <ul>
        <li v-for="failure in readiness.critical_failures">{{ failure }}</li>
      </ul>
    </div>
    
    <div class="recommendations">
      <h3>Recommendations</h3>
      <ul>
        <li v-for="rec in readiness.recommendations">{{ rec }}</li>
      </ul>
    </div>
    
    <div class="parameters">
      <h3>Recommended Parameters</h3>
      <table>
        <tr>
          <td>Position Size:</td>
          <td>{{ (readiness.recommended_position_size * 100).toFixed(2) }}%</td>
        </tr>
        <tr>
          <td>Max Exposure:</td>
          <td>{{ (readiness.recommended_max_exposure * 100).toFixed(2) }}%</td>
        </tr>
        <tr>
          <td>Daily Loss Limit:</td>
          <td>{{ (readiness.recommended_daily_loss_limit * 100).toFixed(2) }}%</td>
        </tr>
      </table>
    </div>
    
    <button v-if="readiness.status === 'approved'" @click="deployStrategy" class="deploy-btn">
      Deploy Strategy
    </button>
  </div>
</template>

<script>
export default {
  props: ['readiness'],
  computed: {
    statusClass() {
      return {
        'approved': this.readiness.status === 'approved',
        'conditional': this.readiness.status === 'conditional',
        'rejected': this.readiness.status === 'rejected',
      };
    }
  },
  methods: {
    async deployStrategy() {
      // Deploy to live trading
      await this.$axios.post('/api/deploy-strategy', {
        strategy_id: this.strategy_id,
        position_size: this.readiness.recommended_position_size,
        max_exposure: this.readiness.recommended_max_exposure,
      });
    }
  }
}
</script>
```

## Complete Integration Example

```python
# exhaustionlab/app/deployment_pipeline.py
"""
Complete deployment pipeline integrating all components.
"""

import asyncio
from pathlib import Path
from typing import Optional

from .backtest.unified_evolution import UnifiedEvolutionEngine
from .backtest.strategy_registry import StrategyRegistry
from .validation import (
    EnhancedMultiMarketTester,
    ProfitAnalyzer,
    WalkForwardValidator,
    MonteCarloSimulator,
    DeploymentReadinessScorer,
)
from .meta_evolution.adaptive_parameters import AdaptiveParameterOptimizer


class DeploymentPipeline:
    """
    End-to-end pipeline for strategy evolution, validation, and deployment.
    """
    
    def __init__(
        self,
        registry: StrategyRegistry,
        optimizer: Optional[AdaptiveParameterOptimizer] = None,
    ):
        self.registry = registry
        self.optimizer = optimizer or AdaptiveParameterOptimizer()
        
        # Initialize components
        self.evolution_engine = UnifiedEvolutionEngine(use_adaptive_params=True)
        self.validator = EnhancedMultiMarketTester()
        self.profit_analyzer = ProfitAnalyzer()
        self.walk_forward_validator = WalkForwardValidator()
        self.monte_carlo_simulator = MonteCarloSimulator(num_simulations=1000)
        self.readiness_scorer = DeploymentReadinessScorer()
    
    async def evolve_and_validate(
        self,
        initial_strategy,
        max_generations: int = 20,
        target_readiness_score: float = 80.0,
    ):
        """
        Evolve strategies until one meets deployment standards.
        
        Returns:
            Approved strategy with validation results
        """
        for generation in range(max_generations):
            print(f"\n{'='*80}")
            print(f"GENERATION {generation + 1}/{max_generations}")
            print('='*80)
            
            # Evolve strategy
            print("\n1. Evolving strategy...")
            evolution_result = self.evolution_engine.evolve_strategy(
                initial_strategy=initial_strategy,
                config=self.optimizer.suggest_configuration(),
                max_generations=1,
            )
            
            candidate_strategy = evolution_result.best_strategy
            
            # Validate strategy
            print("\n2. Running validation pipeline...")
            validation_result = await self._run_validation_pipeline(candidate_strategy)
            
            # Check if meets standards
            if validation_result.readiness_score >= target_readiness_score:
                print(f"\n✅ APPROVED! Score: {validation_result.readiness_score:.1f}/100")
                
                # Store in registry
                strategy_id = self.registry.register_strategy(
                    strategy=candidate_strategy,
                    metrics=evolution_result.best_fitness,
                )
                
                self.registry.record_validation_result(
                    strategy_id=strategy_id,
                    version_id=evolution_result.version_id,
                    readiness=validation_result,
                )
                
                return {
                    'strategy': candidate_strategy,
                    'strategy_id': strategy_id,
                    'validation': validation_result,
                    'generation': generation + 1,
                }
            
            else:
                print(f"\n⚠️  Score: {validation_result.readiness_score:.1f}/100 (need {target_readiness_score})")
                
                # Update optimizer with validation results
                self.optimizer.update_from_validation(
                    config=evolution_result.config,
                    readiness=validation_result,
                )
        
        raise RuntimeError(f"Failed to evolve deployable strategy in {max_generations} generations")
    
    async def _run_validation_pipeline(self, strategy):
        """Run complete 5-phase validation."""
        
        # Phase 1: Multi-market
        print("  Phase 1/5: Multi-market testing...")
        multi_market = await self.validator.test_strategy(strategy)
        print(f"    Pass rate: {multi_market.pass_rate:.1%}")
        
        # Phase 2: Profit analysis
        print("  Phase 2/5: Profit analysis...")
        best_result = multi_market.individual_results[0]
        profit = self.profit_analyzer.analyze(
            equity_curve=best_result.equity_curve,
            trades_df=best_result.trades_df,
        )
        print(f"    Quality score: {profit.quality_score:.1f}/100")
        
        # Phase 3: Walk-forward
        print("  Phase 3/5: Walk-forward validation...")
        # Fetch data for validation
        from .data.binance_rest import fetch_klines_csv_like
        data = fetch_klines_csv_like("BTCUSDT", "5m", limit=500)
        
        walk_forward = self.walk_forward_validator.validate(data, strategy)
        print(f"    Overfitting score: {walk_forward.overfitting_score:.1f}/100")
        
        # Phase 4: Monte Carlo
        print("  Phase 4/5: Monte Carlo simulation...")
        monte_carlo = self.monte_carlo_simulator.run_bootstrap_simulation(
            best_result.equity_curve,
            best_result.returns_series,
        )
        print(f"    Robustness: {monte_carlo.robustness_score:.1f}/100")
        
        # Phase 5: Deployment readiness
        print("  Phase 5/5: Deployment assessment...")
        readiness = self.readiness_scorer.assess(
            multi_market=multi_market,
            profit=profit,
            walk_forward=walk_forward,
            monte_carlo=monte_carlo,
        )
        print(f"    Status: {readiness.status.value.upper()}")
        
        return readiness


# Usage
async def main():
    registry = StrategyRegistry()
    pipeline = DeploymentPipeline(registry)
    
    # Define initial strategy
    initial_strategy = load_initial_strategy()
    
    # Evolve and validate
    result = await pipeline.evolve_and_validate(
        initial_strategy=initial_strategy,
        max_generations=20,
        target_readiness_score=75.0,
    )
    
    print(f"\n{'='*80}")
    print("DEPLOYMENT READY!")
    print(f"Strategy ID: {result['strategy_id']}")
    print(f"Readiness Score: {result['validation'].readiness_score:.1f}/100")
    print(f"Risk Level: {result['validation'].risk_level.value}")
    print(f"Position Size: {result['validation'].recommended_position_size:.2%}")
    print('='*80)

if __name__ == "__main__":
    asyncio.run(main())
```

## Database Migration

Add new columns to strategy_metrics table:

```sql
-- exhaustionlab/app/backtest/migrations/002_add_validation_fields.sql

ALTER TABLE strategy_metrics
ADD COLUMN validation_status TEXT DEFAULT NULL,
ADD COLUMN readiness_score REAL DEFAULT NULL,
ADD COLUMN risk_level TEXT DEFAULT NULL,
ADD COLUMN deployment_ready INTEGER DEFAULT 0,
ADD COLUMN validation_timestamp TEXT DEFAULT NULL,
ADD COLUMN validation_report_path TEXT DEFAULT NULL;

CREATE INDEX idx_deployment_ready ON strategy_metrics(deployment_ready, readiness_score);
CREATE INDEX idx_validation_status ON strategy_metrics(validation_status);
```

## Testing Integration

```python
# tests/test_deployment_integration.py

import asyncio
import pytest
from exhaustionlab.app.deployment_pipeline import DeploymentPipeline
from exhaustionlab.app.backtest.strategy_registry import StrategyRegistry


@pytest.mark.asyncio
async def test_complete_pipeline():
    """Test complete evolution → validation → deployment pipeline."""
    
    # Setup
    registry = StrategyRegistry(db_path=":memory:")
    pipeline = DeploymentPipeline(registry)
    
    # Create sample strategy
    def sample_strategy(data):
        # Simple moving average crossover
        pass
    
    # Run pipeline
    result = await pipeline.evolve_and_validate(
        initial_strategy=sample_strategy,
        max_generations=5,
        target_readiness_score=60.0,  # Relaxed for testing
    )
    
    # Verify
    assert result['validation'].readiness_score >= 60.0
    assert result['validation'].status.value in ["approved", "conditional"]
    assert result['strategy_id'] is not None
    
    # Check registry
    deployable = registry.get_deployable_strategies()
    assert len(deployable) > 0
```

## Configuration

```toml
# config/validation.toml

[multi_market]
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT", "DOGEUSDT"]
timeframes = ["1m", "5m", "15m", "1h", "4h"]
lookback_days = 30
min_quality_score = 60.0
min_sharpe = 1.0

[profit_analysis]
risk_free_rate = 0.02
confidence_level = 0.95
min_total_return = 0.10
min_sharpe_ratio = 1.0

[walk_forward]
in_sample_ratio = 0.7
out_sample_ratio = 0.3
num_periods = 5
max_overfitting_score = 60.0

[monte_carlo]
num_simulations = 1000
confidence_level = 0.95
min_prob_profit = 0.65
max_prob_ruin = 0.05

[deployment]
min_readiness_score = 70.0
allowed_risk_levels = ["low", "medium"]
auto_deploy = false
```

## Next Steps

1. **Implement database migration** - Add validation fields to schema
2. **Update UnifiedEvolutionEngine** - Add validation hooks
3. **Enhance StrategyRegistry** - Store validation results
4. **Create WebUI components** - Add validation tab
5. **Test integration** - Run complete pipeline test
6. **Deploy to production** - Enable validation in live system

---

**Status**: Ready for integration

All components designed and documented. Follow this guide to integrate validation into ExhaustionLab.
