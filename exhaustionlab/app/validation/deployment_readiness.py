"""
Deployment Readiness Assessment

Final go/no-go decision for strategy deployment based on:
- Multi-market performance
- Profit quality
- Walk-forward validation
- Monte Carlo robustness
- Risk management compliance
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from .monte_carlo_simulator import SimulationResult
from .multi_market_tester import AggregatedResults as MultiMarketResults
from .profit_analyzer import ProfitMetrics
from .walk_forward_validator import WalkForwardResult

logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """Deployment readiness status."""

    APPROVED = "approved"  # Ready for live trading
    CONDITIONAL = "conditional"  # Approved with conditions
    NEEDS_IMPROVEMENT = "needs_improvement"  # Not ready yet
    REJECTED = "rejected"  # Failed critical checks


class RiskLevel(Enum):
    """Strategy risk classification."""

    LOW = "low"  # Conservative, low drawdown
    MEDIUM = "medium"  # Balanced risk/reward
    HIGH = "high"  # Aggressive, higher drawdown
    EXTREME = "extreme"  # Very high risk, not recommended


@dataclass
class ValidationChecklist:
    """Checklist of validation requirements."""

    # Multi-market requirements
    min_markets_passed: int = 4
    min_pass_rate: float = 0.6  # 60%
    min_mean_sharpe: float = 1.0
    max_mean_drawdown: float = 0.30  # 30%

    # Profit requirements
    min_total_return: float = 0.10  # 10%
    min_sharpe_ratio: float = 1.0
    min_quality_score: float = 60.0
    must_be_statistically_significant: bool = True

    # Walk-forward requirements
    min_wf_pass_rate: float = 0.6
    max_overfitting_score: float = 60.0
    max_degradation: float = 0.40  # 40%

    # Monte Carlo requirements
    min_prob_profit: float = 0.65  # 65%
    max_prob_ruin: float = 0.05  # 5%
    min_robustness_score: float = 60.0

    # Risk management
    max_position_size: float = 0.05  # 5% per trade
    max_portfolio_exposure: float = 0.20  # 20% total
    max_daily_loss_limit: float = 0.02  # 2% per day


@dataclass
class CheckResult:
    """Result of a single validation check."""

    check_name: str
    passed: bool
    value: float
    threshold: float
    critical: bool  # If True, failure rejects deployment
    message: str


@dataclass
class ReadinessReport:
    """Complete deployment readiness report."""

    # Overall assessment
    status: DeploymentStatus
    risk_level: RiskLevel
    readiness_score: float  # 0-100

    # Component scores
    multi_market_score: float
    profit_quality_score: float
    walk_forward_score: float
    monte_carlo_score: float
    risk_management_score: float

    # Validation checks
    checks: List[CheckResult] = field(default_factory=list)
    critical_failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    # Deployment parameters
    recommended_position_size: float = 0.0
    recommended_max_exposure: float = 0.0
    recommended_daily_loss_limit: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "risk_level": self.risk_level.value,
            "readiness_score": self.readiness_score,
            "multi_market_score": self.multi_market_score,
            "profit_quality_score": self.profit_quality_score,
            "walk_forward_score": self.walk_forward_score,
            "monte_carlo_score": self.monte_carlo_score,
            "risk_management_score": self.risk_management_score,
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "recommended_position_size": self.recommended_position_size,
            "recommended_max_exposure": self.recommended_max_exposure,
        }


class DeploymentReadinessScorer:
    """
    Comprehensive deployment readiness assessment.

    Combines all validation results to make final go/no-go decision.
    """

    def __init__(self, checklist: Optional[ValidationChecklist] = None):
        """
        Initialize scorer.

        Args:
            checklist: Validation requirements (uses defaults if None)
        """
        self.checklist = checklist or ValidationChecklist()

    def assess(
        self,
        multi_market: Optional[MultiMarketResults] = None,
        profit: Optional[ProfitMetrics] = None,
        walk_forward: Optional[WalkForwardResult] = None,
        monte_carlo: Optional[SimulationResult] = None,
    ) -> ReadinessReport:
        """
        Assess deployment readiness.

        Args:
            multi_market: Multi-market test results
            profit: Profit analysis results
            walk_forward: Walk-forward validation results
            monte_carlo: Monte Carlo simulation results

        Returns:
            Complete readiness report
        """
        checks = []
        critical_failures = []
        warnings = []
        recommendations = []

        # Multi-market validation
        mm_score = 0.0
        if multi_market:
            mm_checks, mm_score = self._check_multi_market(multi_market)
            checks.extend(mm_checks)

            for check in mm_checks:
                if not check.passed:
                    if check.critical:
                        critical_failures.append(f"{check.check_name}: {check.message}")
                    else:
                        warnings.append(f"{check.check_name}: {check.message}")
        else:
            warnings.append("Multi-market validation not performed")

        # Profit analysis
        profit_score = 0.0
        if profit:
            profit_checks, profit_score = self._check_profit_quality(profit)
            checks.extend(profit_checks)

            for check in profit_checks:
                if not check.passed:
                    if check.critical:
                        critical_failures.append(f"{check.check_name}: {check.message}")
                    else:
                        warnings.append(f"{check.check_name}: {check.message}")
        else:
            warnings.append("Profit analysis not performed")

        # Walk-forward validation
        wf_score = 0.0
        if walk_forward:
            wf_checks, wf_score = self._check_walk_forward(walk_forward)
            checks.extend(wf_checks)

            for check in wf_checks:
                if not check.passed:
                    if check.critical:
                        critical_failures.append(f"{check.check_name}: {check.message}")
                    else:
                        warnings.append(f"{check.check_name}: {check.message}")
        else:
            warnings.append("Walk-forward validation not performed")

        # Monte Carlo validation
        mc_score = 0.0
        if monte_carlo:
            mc_checks, mc_score = self._check_monte_carlo(monte_carlo)
            checks.extend(mc_checks)

            for check in mc_checks:
                if not check.passed:
                    if check.critical:
                        critical_failures.append(f"{check.check_name}: {check.message}")
                    else:
                        warnings.append(f"{check.check_name}: {check.message}")
        else:
            warnings.append("Monte Carlo validation not performed")

        # Risk management
        risk_score = self._check_risk_management(multi_market, profit, walk_forward)

        # Calculate overall score
        component_scores = [mm_score, profit_score, wf_score, mc_score, risk_score]
        valid_scores = [s for s in component_scores if s > 0]

        if valid_scores:
            readiness_score = sum(valid_scores) / len(valid_scores)
        else:
            readiness_score = 0.0

        # Determine status
        status = self._determine_status(readiness_score, critical_failures, warnings)

        # Classify risk level
        risk_level = self._classify_risk_level(multi_market, profit)

        # Generate recommendations
        recommendations = self._generate_recommendations(status, multi_market, profit, walk_forward, monte_carlo)

        # Calculate recommended parameters
        rec_position_size, rec_exposure, rec_loss_limit = self._calculate_recommended_parameters(risk_level, profit, multi_market)

        return ReadinessReport(
            status=status,
            risk_level=risk_level,
            readiness_score=readiness_score,
            multi_market_score=mm_score,
            profit_quality_score=profit_score,
            walk_forward_score=wf_score,
            monte_carlo_score=mc_score,
            risk_management_score=risk_score,
            checks=checks,
            critical_failures=critical_failures,
            warnings=warnings,
            recommendations=recommendations,
            recommended_position_size=rec_position_size,
            recommended_max_exposure=rec_exposure,
            recommended_daily_loss_limit=rec_loss_limit,
        )

    def _check_multi_market(self, results: MultiMarketResults) -> tuple[List[CheckResult], float]:
        """Check multi-market validation."""
        checks = []

        # Markets passed
        checks.append(
            CheckResult(
                check_name="Multi-Market Pass Rate",
                passed=results.markets_passed >= self.checklist.min_markets_passed,
                value=results.markets_passed,
                threshold=self.checklist.min_markets_passed,
                critical=True,
                message=f"{results.markets_passed} markets passed (need {self.checklist.min_markets_passed})",
            )
        )

        # Pass rate
        checks.append(
            CheckResult(
                check_name="Overall Pass Rate",
                passed=results.pass_rate >= self.checklist.min_pass_rate,
                value=results.pass_rate,
                threshold=self.checklist.min_pass_rate,
                critical=True,
                message=f"Pass rate: {results.pass_rate:.1%}",
            )
        )

        # Mean Sharpe
        checks.append(
            CheckResult(
                check_name="Mean Sharpe Ratio",
                passed=results.mean_sharpe >= self.checklist.min_mean_sharpe,
                value=results.mean_sharpe,
                threshold=self.checklist.min_mean_sharpe,
                critical=False,
                message=f"Mean Sharpe: {results.mean_sharpe:.2f}",
            )
        )

        # Max drawdown
        checks.append(
            CheckResult(
                check_name="Mean Drawdown",
                passed=results.mean_drawdown <= self.checklist.max_mean_drawdown,
                value=results.mean_drawdown,
                threshold=self.checklist.max_mean_drawdown,
                critical=True,
                message=f"Mean drawdown: {results.mean_drawdown:.1%}",
            )
        )

        # Performance consistency
        checks.append(
            CheckResult(
                check_name="Performance Consistency",
                passed=results.performance_consistent,
                value=1.0 if results.performance_consistent else 0.0,
                threshold=1.0,
                critical=False,
                message=("Performance is statistically consistent" if results.performance_consistent else "Performance inconsistent"),
            )
        )

        # Calculate score
        passed = sum(1 for c in checks if c.passed)
        score = (passed / len(checks)) * 100

        return checks, score

    def _check_profit_quality(self, profit: ProfitMetrics) -> tuple[List[CheckResult], float]:
        """Check profit quality."""
        checks = []

        # Total return
        checks.append(
            CheckResult(
                check_name="Total Return",
                passed=profit.total_return >= self.checklist.min_total_return,
                value=profit.total_return,
                threshold=self.checklist.min_total_return,
                critical=True,
                message=f"Total return: {profit.total_return:.1%}",
            )
        )

        # Sharpe ratio
        checks.append(
            CheckResult(
                check_name="Sharpe Ratio",
                passed=profit.sharpe_ratio >= self.checklist.min_sharpe_ratio,
                value=profit.sharpe_ratio,
                threshold=self.checklist.min_sharpe_ratio,
                critical=True,
                message=f"Sharpe: {profit.sharpe_ratio:.2f}",
            )
        )

        # Quality score
        checks.append(
            CheckResult(
                check_name="Profit Quality Score",
                passed=profit.quality_score >= self.checklist.min_quality_score,
                value=profit.quality_score,
                threshold=self.checklist.min_quality_score,
                critical=False,
                message=f"Quality: {profit.quality_score:.1f}/100",
            )
        )

        # Statistical significance
        checks.append(
            CheckResult(
                check_name="Statistical Significance",
                passed=profit.statistically_significant or not self.checklist.must_be_statistically_significant,
                value=1.0 if profit.statistically_significant else 0.0,
                threshold=1.0,
                critical=self.checklist.must_be_statistically_significant,
                message=f"P-value: {profit.p_value:.4f}",
            )
        )

        # Calculate score
        passed = sum(1 for c in checks if c.passed)
        score = (passed / len(checks)) * 100

        return checks, score

    def _check_walk_forward(self, wf: WalkForwardResult) -> tuple[List[CheckResult], float]:
        """Check walk-forward validation."""
        checks = []

        # Pass rate
        checks.append(
            CheckResult(
                check_name="Walk-Forward Pass Rate",
                passed=wf.pass_rate >= self.checklist.min_wf_pass_rate,
                value=wf.pass_rate,
                threshold=self.checklist.min_wf_pass_rate,
                critical=True,
                message=f"WF pass rate: {wf.pass_rate:.1%}",
            )
        )

        # Overfitting
        checks.append(
            CheckResult(
                check_name="Overfitting Score",
                passed=wf.overfitting_score <= self.checklist.max_overfitting_score,
                value=wf.overfitting_score,
                threshold=self.checklist.max_overfitting_score,
                critical=True,
                message=f"Overfitting: {wf.overfitting_score:.1f}/100",
            )
        )

        # Degradation
        checks.append(
            CheckResult(
                check_name="Performance Degradation",
                passed=wf.mean_performance_degradation <= self.checklist.max_degradation,
                value=wf.mean_performance_degradation,
                threshold=self.checklist.max_degradation,
                critical=False,
                message=f"Degradation: {wf.mean_performance_degradation:.1%}",
            )
        )

        # Stability
        checks.append(
            CheckResult(
                check_name="Performance Stability",
                passed=wf.performance_stable,
                value=1.0 if wf.performance_stable else 0.0,
                threshold=1.0,
                critical=False,
                message=("Performance is stable" if wf.performance_stable else "Performance unstable"),
            )
        )

        # Calculate score
        passed = sum(1 for c in checks if c.passed)
        score = (passed / len(checks)) * 100

        return checks, score

    def _check_monte_carlo(self, mc: SimulationResult) -> tuple[List[CheckResult], float]:
        """Check Monte Carlo simulation."""
        checks = []

        # Probability of profit
        checks.append(
            CheckResult(
                check_name="Probability of Profit",
                passed=mc.probability_of_profit >= self.checklist.min_prob_profit,
                value=mc.probability_of_profit,
                threshold=self.checklist.min_prob_profit,
                critical=True,
                message=f"P(profit): {mc.probability_of_profit:.1%}",
            )
        )

        # Probability of ruin
        checks.append(
            CheckResult(
                check_name="Probability of Ruin",
                passed=mc.probability_of_ruin <= self.checklist.max_prob_ruin,
                value=mc.probability_of_ruin,
                threshold=self.checklist.max_prob_ruin,
                critical=True,
                message=f"P(ruin): {mc.probability_of_ruin:.1%}",
            )
        )

        # Robustness score
        checks.append(
            CheckResult(
                check_name="Robustness Score",
                passed=mc.robustness_score >= self.checklist.min_robustness_score,
                value=mc.robustness_score,
                threshold=self.checklist.min_robustness_score,
                critical=False,
                message=f"Robustness: {mc.robustness_score:.1f}/100",
            )
        )

        # Calculate score
        passed = sum(1 for c in checks if c.passed)
        score = (passed / len(checks)) * 100

        return checks, score

    def _check_risk_management(
        self,
        multi_market: Optional[MultiMarketResults],
        profit: Optional[ProfitMetrics],
        walk_forward: Optional[WalkForwardResult],
    ) -> float:
        """Check risk management compliance."""
        # Risk management is mostly about setting limits
        # Score based on available data quality
        score = 100.0

        # Penalize if key validations are missing
        if multi_market is None:
            score -= 20
        if profit is None:
            score -= 20
        if walk_forward is None:
            score -= 20

        return max(0, score)

    def _determine_status(self, score: float, critical_failures: List[str], warnings: List[str]) -> DeploymentStatus:
        """Determine deployment status."""
        if critical_failures:
            return DeploymentStatus.REJECTED
        elif score >= 85 and not warnings:
            return DeploymentStatus.APPROVED
        elif score >= 70:
            return DeploymentStatus.CONDITIONAL
        else:
            return DeploymentStatus.NEEDS_IMPROVEMENT

    def _classify_risk_level(
        self,
        multi_market: Optional[MultiMarketResults],
        profit: Optional[ProfitMetrics],
    ) -> RiskLevel:
        """Classify strategy risk level."""
        if multi_market is None or profit is None:
            return RiskLevel.MEDIUM

        # Use drawdown and volatility to classify
        max_dd = multi_market.max_drawdown

        if max_dd < 0.15:  # < 15%
            return RiskLevel.LOW
        elif max_dd < 0.30:  # < 30%
            return RiskLevel.MEDIUM
        elif max_dd < 0.50:  # < 50%
            return RiskLevel.HIGH
        else:
            return RiskLevel.EXTREME

    def _generate_recommendations(
        self,
        status: DeploymentStatus,
        multi_market: Optional[MultiMarketResults],
        profit: Optional[ProfitMetrics],
        walk_forward: Optional[WalkForwardResult],
        monte_carlo: Optional[SimulationResult],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recs = []

        if status == DeploymentStatus.APPROVED:
            recs.append("Strategy approved for live deployment")
            recs.append("Start with minimum position size and scale up gradually")
            recs.append("Monitor performance closely for first 30 days")

        elif status == DeploymentStatus.CONDITIONAL:
            recs.append("Strategy may be deployed with additional monitoring")
            recs.append("Use reduced position sizes (50% of calculated)")
            recs.append("Implement stricter stop-losses initially")

            if walk_forward and walk_forward.overfitting_score > 40:
                recs.append("High overfitting detected - consider parameter simplification")

        elif status == DeploymentStatus.NEEDS_IMPROVEMENT:
            recs.append("Strategy needs improvement before deployment")

            if multi_market and multi_market.pass_rate < 0.6:
                recs.append("Improve multi-market consistency")

            if profit and profit.sharpe_ratio < 1.0:
                recs.append("Improve risk-adjusted returns")

            if walk_forward and walk_forward.overfitting_detected:
                recs.append("Reduce overfitting through simpler logic or different parameters")

        else:  # REJECTED
            recs.append("Strategy rejected - critical failures detected")
            recs.append("DO NOT deploy to live trading")
            recs.append("Review and address all critical issues")

        return recs

    def _calculate_recommended_parameters(
        self,
        risk_level: RiskLevel,
        profit: Optional[ProfitMetrics],
        multi_market: Optional[MultiMarketResults],
    ) -> tuple[float, float, float]:
        """Calculate recommended trading parameters."""
        # Base parameters by risk level
        base_params = {
            RiskLevel.LOW: (0.03, 0.15, 0.015),  # 3%, 15%, 1.5%
            RiskLevel.MEDIUM: (0.02, 0.10, 0.010),  # 2%, 10%, 1%
            RiskLevel.HIGH: (0.01, 0.05, 0.005),  # 1%, 5%, 0.5%
            RiskLevel.EXTREME: (0.005, 0.025, 0.002),  # 0.5%, 2.5%, 0.2%
        }

        position_size, max_exposure, daily_loss = base_params.get(risk_level, (0.02, 0.10, 0.010))

        # Adjust based on Kelly criterion if available
        if profit and profit.trade_analysis and profit.trade_analysis.kelly_criterion > 0:
            # Use fraction of Kelly (typically 25-50%)
            kelly_fraction = 0.25
            kelly_size = profit.trade_analysis.kelly_criterion * kelly_fraction
            position_size = min(position_size, kelly_size)

        return position_size, max_exposure, daily_loss

    def generate_report(self, report: ReadinessReport) -> str:
        """Generate human-readable deployment report."""
        lines = [
            "=" * 80,
            "DEPLOYMENT READINESS REPORT",
            "=" * 80,
            "",
            "OVERALL ASSESSMENT:",
            f"  Status: {report.status.value.upper()}",
            f"  Risk Level: {report.risk_level.value.upper()}",
            f"  Readiness Score: {report.readiness_score:.1f}/100",
            "",
            "COMPONENT SCORES:",
            f"  Multi-Market: {report.multi_market_score:.1f}/100",
            f"  Profit Quality: {report.profit_quality_score:.1f}/100",
            f"  Walk-Forward: {report.walk_forward_score:.1f}/100",
            f"  Monte Carlo: {report.monte_carlo_score:.1f}/100",
            f"  Risk Management: {report.risk_management_score:.1f}/100",
            "",
        ]

        if report.critical_failures:
            lines.extend(
                [
                    "CRITICAL FAILURES:",
                    *[f"  ❌ {failure}" for failure in report.critical_failures],
                    "",
                ]
            )

        if report.warnings:
            lines.extend(
                [
                    "WARNINGS:",
                    *[f"  ⚠️  {warning}" for warning in report.warnings],
                    "",
                ]
            )

        lines.extend(
            [
                "RECOMMENDED PARAMETERS:",
                f"  Position Size: {report.recommended_position_size:.1%} per trade",
                f"  Max Exposure: {report.recommended_max_exposure:.1%} total",
                f"  Daily Loss Limit: {report.recommended_daily_loss_limit:.1%}",
                "",
                "RECOMMENDATIONS:",
                *[f"  • {rec}" for rec in report.recommendations],
            ]
        )

        lines.append("=" * 80)

        return "\n".join(lines)

    def save_report(self, report: ReadinessReport, filepath: Path):
        """Save report to JSON file."""
        with open(filepath, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info(f"Report saved to {filepath}")
