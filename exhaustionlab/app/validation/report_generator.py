"""
Strategy Report Generator

Generates comprehensive HTML/PDF reports with:
- Equity curve visualization
- Drawdown analysis charts
- Trade journal table
- Component score breakdown
- Performance metrics
- Actionable recommendations
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from .backtest_parser import BacktestResult
from .comprehensive_scorer import ComponentScores, ComprehensiveScorer

logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    include_charts: bool = True
    include_trade_journal: bool = True
    include_recommendations: bool = True
    chart_width: int = 1200
    chart_height: int = 400
    chart_dpi: int = 100
    max_trades_in_journal: int = 100
    output_format: str = "html"  # "html" or "pdf"


class ReportGenerator:
    """
    Generate comprehensive strategy validation reports.

    Creates professional HTML reports with:
    - Executive summary
    - Performance metrics
    - Visual analytics (equity curve, drawdown, returns distribution)
    - Trade journal
    - Score breakdown
    - Recommendations
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize report generator.

        Args:
            config: Report configuration
        """
        self.config = config or ReportConfig()
        self.scorer = ComprehensiveScorer()

    def generate_html_report(
        self,
        backtest: BacktestResult,
        scores: ComponentScores,
        symbol: str,
        output_path: Path | str,
        costs: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
    ) -> Path:
        """
        Generate complete HTML report.

        Args:
            backtest: Parsed backtest result
            scores: Comprehensive scores
            symbol: Trading symbol
            output_path: Path to save HTML report
            costs: Trading costs dictionary (optional)
            metadata: Additional metadata (optional)

        Returns:
            Path to generated report
        """
        output_path = Path(output_path)

        logger.info(f"Generating HTML report: {output_path}")

        # Generate all sections
        html = self._build_html_structure(
            backtest=backtest,
            scores=scores,
            symbol=symbol,
            costs=costs,
            metadata=metadata,
        )

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")

        logger.info(f"Report generated: {output_path}")

        return output_path

    def _build_html_structure(
        self,
        backtest: BacktestResult,
        scores: ComponentScores,
        symbol: str,
        costs: Optional[Dict],
        metadata: Optional[Dict],
    ) -> str:
        """Build complete HTML structure."""

        # Generate all sections
        header = self._generate_header(backtest, symbol)
        summary = self._generate_executive_summary(backtest, scores, costs)
        metrics = self._generate_metrics_table(backtest, scores)
        charts = self._generate_charts(backtest) if self.config.include_charts else ""
        score_breakdown = self._generate_score_breakdown(scores)
        trade_journal = self._generate_trade_journal(backtest) if self.config.include_trade_journal else ""
        recommendations = self._generate_recommendations(backtest, scores) if self.config.include_recommendations else ""
        footer = self._generate_footer()

        # Combine all sections
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strategy Validation Report - {backtest.strategy_name}</title>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        {header}
        {summary}
        {metrics}
        {score_breakdown}
        {charts}
        {trade_journal}
        {recommendations}
        {footer}
    </div>
</body>
</html>"""

        return html

    def _generate_header(self, backtest: BacktestResult, symbol: str) -> str:
        """Generate report header."""
        return f"""
        <div class="header">
            <h1>Strategy Validation Report</h1>
            <div class="header-info">
                <div><strong>Strategy:</strong> {backtest.strategy_name}</div>
                <div><strong>Symbol:</strong> {symbol}</div>
                <div><strong>Timeframe:</strong> {backtest.timeframe}</div>
                <div><strong>Period:</strong> {backtest.start_date.strftime('%Y-%m-%d')} to {backtest.end_date.strftime('%Y-%m-%d')}</div>
                <div><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            </div>
        </div>
        """

    def _generate_executive_summary(
        self,
        backtest: BacktestResult,
        scores: ComponentScores,
        costs: Optional[Dict],
    ) -> str:
        """Generate executive summary section."""

        # Determine grade and status
        grade = self._get_grade(scores.total_score)
        status_class = "approved" if scores.total_score >= 75 else "warning" if scores.total_score >= 65 else "rejected"
        status_text = "APPROVED" if scores.total_score >= 75 else "CONDITIONAL" if scores.total_score >= 65 else "NOT APPROVED"

        # Calculate net return if costs available
        net_return_section = ""
        if costs:
            net_return = backtest.annualized_return - (costs["total_costs"]["total_annual_drag_pct"] / 100)
            net_return_section = f"""
                <div class="metric">
                    <div class="metric-label">Net Return (After Costs)</div>
                    <div class="metric-value">{net_return:.2%}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Trading Costs</div>
                    <div class="metric-value">{costs['total_costs']['total_annual_drag_pct']:.2f}%</div>
                </div>
            """

        return f"""
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="summary-grid">
                <div class="summary-card {status_class}">
                    <div class="summary-title">Deployment Status</div>
                    <div class="summary-value">{status_text}</div>
                    <div class="summary-subtitle">Overall Score: {scores.total_score:.1f}/100 ({grade})</div>
                </div>

                <div class="metrics-grid">
                    <div class="metric">
                        <div class="metric-label">Total Return</div>
                        <div class="metric-value">{backtest.annualized_return:.2%}</div>
                    </div>
                    {net_return_section}
                    <div class="metric">
                        <div class="metric-label">Sharpe Ratio</div>
                        <div class="metric-value">{backtest.sharpe_ratio:.2f}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Max Drawdown</div>
                        <div class="metric-value {self._get_drawdown_class(backtest.max_drawdown)}">{backtest.max_drawdown:.2%}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Win Rate</div>
                        <div class="metric-value">{backtest.win_rate:.2%}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Total Trades</div>
                        <div class="metric-value">{backtest.total_trades}</div>
                    </div>
                </div>
            </div>
        </div>
        """

    def _generate_metrics_table(self, backtest: BacktestResult, scores: ComponentScores) -> str:
        """Generate detailed metrics table."""

        return f"""
        <div class="section">
            <h2>Performance Metrics</h2>
            <table class="metrics-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Value</th>
                        <th>Target</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Total Return</td>
                        <td>{backtest.total_return:.2%}</td>
                        <td>-</td>
                        <td>{self._get_status_badge(backtest.total_return > 0)}</td>
                    </tr>
                    <tr>
                        <td>Annualized Return</td>
                        <td>{backtest.annualized_return:.2%}</td>
                        <td>&gt; 30%</td>
                        <td>{self._get_status_badge(backtest.annualized_return > 0.30)}</td>
                    </tr>
                    <tr>
                        <td>Sharpe Ratio</td>
                        <td>{backtest.sharpe_ratio:.2f}</td>
                        <td>&gt; 1.5</td>
                        <td>{self._get_status_badge(backtest.sharpe_ratio > 1.5)}</td>
                    </tr>
                    <tr>
                        <td>Sortino Ratio</td>
                        <td>{backtest.sortino_ratio:.2f}</td>
                        <td>&gt; 1.5</td>
                        <td>{self._get_status_badge(backtest.sortino_ratio > 1.5)}</td>
                    </tr>
                    <tr>
                        <td>Max Drawdown</td>
                        <td class="{self._get_drawdown_class(backtest.max_drawdown)}">{backtest.max_drawdown:.2%}</td>
                        <td>&lt; 25%</td>
                        <td>{self._get_status_badge(backtest.max_drawdown < 0.25)}</td>
                    </tr>
                    <tr>
                        <td>Drawdown Duration</td>
                        <td>{backtest.max_drawdown_duration} periods</td>
                        <td>&lt; 30</td>
                        <td>{self._get_status_badge(backtest.max_drawdown_duration < 30)}</td>
                    </tr>
                    <tr>
                        <td>Win Rate</td>
                        <td>{backtest.win_rate:.2%}</td>
                        <td>&gt; 55%</td>
                        <td>{self._get_status_badge(backtest.win_rate > 0.55)}</td>
                    </tr>
                    <tr>
                        <td>Profit Factor</td>
                        <td>{backtest.profit_factor:.2f}</td>
                        <td>&gt; 1.5</td>
                        <td>{self._get_status_badge(backtest.profit_factor > 1.5)}</td>
                    </tr>
                    <tr>
                        <td>Average Win</td>
                        <td>${backtest.avg_win:.2f}</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td>Average Loss</td>
                        <td>${backtest.avg_loss:.2f}</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td>Largest Win</td>
                        <td>${backtest.largest_win:.2f}</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>
                    <tr>
                        <td>Largest Loss</td>
                        <td>${backtest.largest_loss:.2f}</td>
                        <td>-</td>
                        <td>-</td>
                    </tr>
                </tbody>
            </table>
        </div>
        """

    def _generate_score_breakdown(self, scores: ComponentScores) -> str:
        """Generate score breakdown section."""

        grade = self._get_grade(scores.total_score)

        return f"""
        <div class="section">
            <h2>Score Breakdown</h2>
            <div class="score-summary">
                <div class="total-score">
                    <div class="score-label">Total Score</div>
                    <div class="score-value">{scores.total_score:.1f}/100</div>
                    <div class="score-grade">{grade}</div>
                </div>
            </div>

            <div class="score-components">
                <div class="component">
                    <div class="component-header">
                        <h3>Performance</h3>
                        <span class="component-score">{scores.performance_total:.1f}/35</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {(scores.performance_total / 35) * 100}%"></div>
                    </div>
                    <div class="sub-metrics">
                        <div>Sharpe Ratio: {scores.sharpe_score:.1f}/15</div>
                        <div>Total Return: {scores.return_score:.1f}/10</div>
                        <div>Win Rate: {scores.win_rate_score:.1f}/10</div>
                    </div>
                </div>

                <div class="component">
                    <div class="component-header">
                        <h3>Risk Management</h3>
                        <span class="component-score">{scores.risk_total:.1f}/30</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {(scores.risk_total / 30) * 100}%"></div>
                    </div>
                    <div class="sub-metrics">
                        <div>Max Drawdown: {scores.drawdown_score:.1f}/15</div>
                        <div>Consistency: {scores.consistency_score:.1f}/10</div>
                        <div>Recovery: {scores.recovery_score:.1f}/5</div>
                    </div>
                </div>

                <div class="component">
                    <div class="component-header">
                        <h3>Execution Quality</h3>
                        <span class="component-score">{scores.execution_total:.1f}/20</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {(scores.execution_total / 20) * 100}%"></div>
                    </div>
                    <div class="sub-metrics">
                        <div>Frequency: {scores.frequency_score:.1f}/10</div>
                        <div>Latency: {scores.latency_score:.1f}/5</div>
                        <div>Slippage: {scores.slippage_score:.1f}/5</div>
                    </div>
                </div>

                <div class="component">
                    <div class="component-header">
                        <h3>Robustness</h3>
                        <span class="component-score">{scores.robustness_total:.1f}/15</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {(scores.robustness_total / 15) * 100}%"></div>
                    </div>
                    <div class="sub-metrics">
                        <div>Out-of-Sample: {scores.out_of_sample_score:.1f}/7</div>
                        <div>Cross-Market: {scores.cross_market_score:.1f}/8</div>
                    </div>
                </div>
            </div>
        </div>
        """

    def _generate_charts(self, backtest: BacktestResult) -> str:
        """Generate all charts as embedded base64 images."""

        charts_html = '<div class="section"><h2>Visual Analytics</h2>'

        # Equity curve
        equity_chart = self._create_equity_curve_chart(backtest)
        charts_html += f'<div class="chart-container"><h3>Equity Curve</h3><img src="data:image/png;base64,{equity_chart}" /></div>'

        # Drawdown chart
        drawdown_chart = self._create_drawdown_chart(backtest)
        charts_html += f'<div class="chart-container"><h3>Drawdown Analysis</h3><img src="data:image/png;base64,{drawdown_chart}" /></div>'

        # Returns distribution
        returns_chart = self._create_returns_distribution_chart(backtest)
        charts_html += f'<div class="chart-container"><h3>Returns Distribution</h3><img src="data:image/png;base64,{returns_chart}" /></div>'

        # Monthly returns heatmap
        if len(backtest.returns) > 30:
            monthly_chart = self._create_monthly_returns_chart(backtest)
            charts_html += f'<div class="chart-container"><h3>Monthly Returns</h3><img src="data:image/png;base64,{monthly_chart}" /></div>'

        charts_html += "</div>"

        return charts_html

    def _create_equity_curve_chart(self, backtest: BacktestResult) -> str:
        """Create equity curve chart."""
        fig, ax = plt.subplots(
            figsize=(self.config.chart_width / 100, self.config.chart_height / 100),
            dpi=self.config.chart_dpi,
        )

        equity = backtest.equity_curve
        ax.plot(equity.index, equity.values, linewidth=2, color="#2E86DE")
        ax.fill_between(equity.index, 1.0, equity.values, alpha=0.1, color="#2E86DE")

        ax.set_title("Equity Curve", fontsize=14, fontweight="bold")
        ax.set_xlabel("Date")
        ax.set_ylabel("Equity")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.xticks(rotation=45)

        # Add horizontal line at starting equity
        ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.5, linewidth=1)

        plt.tight_layout()

        return self._fig_to_base64(fig)

    def _create_drawdown_chart(self, backtest: BacktestResult) -> str:
        """Create drawdown chart."""
        fig, ax = plt.subplots(
            figsize=(self.config.chart_width / 100, self.config.chart_height / 100),
            dpi=self.config.chart_dpi,
        )

        equity = backtest.equity_curve
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max

        ax.fill_between(drawdown.index, 0, drawdown.values * 100, color="#EE5A6F", alpha=0.3)
        ax.plot(drawdown.index, drawdown.values * 100, linewidth=2, color="#EE5A6F")

        ax.set_title("Drawdown Analysis", fontsize=14, fontweight="bold")
        ax.set_xlabel("Date")
        ax.set_ylabel("Drawdown (%)")
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        plt.xticks(rotation=45)

        # Add max drawdown line
        max_dd = drawdown.min() * 100
        ax.axhline(
            y=max_dd,
            color="red",
            linestyle="--",
            alpha=0.7,
            linewidth=1,
            label=f"Max DD: {max_dd:.2f}%",
        )
        ax.legend()

        plt.tight_layout()

        return self._fig_to_base64(fig)

    def _create_returns_distribution_chart(self, backtest: BacktestResult) -> str:
        """Create returns distribution histogram."""
        fig, ax = plt.subplots(
            figsize=(self.config.chart_width / 100, self.config.chart_height / 100),
            dpi=self.config.chart_dpi,
        )

        returns = backtest.returns * 100  # Convert to percentage

        ax.hist(returns, bins=50, color="#26DE81", alpha=0.7, edgecolor="black")

        # Add vertical lines for mean and median
        ax.axvline(
            returns.mean(),
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Mean: {returns.mean():.2f}%",
        )
        ax.axvline(
            returns.median(),
            color="blue",
            linestyle="--",
            linewidth=2,
            label=f"Median: {returns.median():.2f}%",
        )
        ax.axvline(0, color="gray", linestyle="-", linewidth=1, alpha=0.5)

        ax.set_title("Returns Distribution", fontsize=14, fontweight="bold")
        ax.set_xlabel("Return (%)")
        ax.set_ylabel("Frequency")
        ax.grid(True, alpha=0.3, axis="y")
        ax.legend()

        plt.tight_layout()

        return self._fig_to_base64(fig)

    def _create_monthly_returns_chart(self, backtest: BacktestResult) -> str:
        """Create monthly returns bar chart."""
        fig, ax = plt.subplots(
            figsize=(self.config.chart_width / 100, self.config.chart_height / 100),
            dpi=self.config.chart_dpi,
        )

        monthly_returns = backtest.returns.resample("M").sum() * 100

        colors = ["#26DE81" if r > 0 else "#EE5A6F" for r in monthly_returns]
        ax.bar(range(len(monthly_returns)), monthly_returns.values, color=colors, alpha=0.7)

        ax.set_title("Monthly Returns", fontsize=14, fontweight="bold")
        ax.set_xlabel("Month")
        ax.set_ylabel("Return (%)")
        ax.grid(True, alpha=0.3, axis="y")
        ax.axhline(y=0, color="gray", linestyle="-", linewidth=1)

        # Set x-tick labels to month names
        ax.set_xticks(range(len(monthly_returns)))
        ax.set_xticklabels([d.strftime("%Y-%m") for d in monthly_returns.index], rotation=45)

        plt.tight_layout()

        return self._fig_to_base64(fig)

    def _generate_trade_journal(self, backtest: BacktestResult) -> str:
        """Generate trade journal table."""

        trades = backtest.trades[: self.config.max_trades_in_journal]

        if not trades:
            return ""

        rows = ""
        for trade in trades:
            pnl_class = "positive" if trade.pnl > 0 else "negative"
            rows += f"""
                <tr>
                    <td>{trade.trade_id}</td>
                    <td>{trade.entry_time.strftime('%Y-%m-%d %H:%M')}</td>
                    <td>{trade.exit_time.strftime('%Y-%m-%d %H:%M')}</td>
                    <td>{trade.side.upper()}</td>
                    <td>${trade.entry_price:.2f}</td>
                    <td>${trade.exit_price:.2f}</td>
                    <td class="{pnl_class}">${trade.pnl:.2f}</td>
                    <td class="{pnl_class}">{trade.pnl_pct:.2%}</td>
                    <td>{trade.reason}</td>
                </tr>
            """

        total_shown = len(trades)
        total_trades = len(backtest.trades)
        note = f"<p><em>Showing {total_shown} of {total_trades} trades</em></p>" if total_trades > total_shown else ""

        return f"""
        <div class="section">
            <h2>Trade Journal</h2>
            {note}
            <div class="table-container">
                <table class="trade-journal">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Entry Time</th>
                            <th>Exit Time</th>
                            <th>Side</th>
                            <th>Entry Price</th>
                            <th>Exit Price</th>
                            <th>P&L ($)</th>
                            <th>P&L (%)</th>
                            <th>Exit Reason</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>
        </div>
        """

    def _generate_recommendations(self, backtest: BacktestResult, scores: ComponentScores) -> str:
        """Generate actionable recommendations."""

        recommendations = []

        # Performance recommendations
        if scores.sharpe_score < 10:
            recommendations.append(
                {
                    "type": "warning",
                    "title": "Low Sharpe Ratio",
                    "message": (f"Current Sharpe ratio ({backtest.sharpe_ratio:.2f}) is below " "target (1.5). Consider improving risk-adjusted returns by " "reducing volatility or increasing average returns."),
                }
            )

        if scores.return_score < 7:
            recommendations.append(
                {
                    "type": "warning",
                    "title": "Low Returns",
                    "message": f"Annual return ({backtest.annualized_return:.2%}) is below target (30%). Consider optimizing entry/exit timing or increasing position sizes.",
                }
            )

        if scores.win_rate_score < 7:
            recommendations.append(
                {
                    "type": "warning",
                    "title": "Low Win Rate",
                    "message": f"Win rate ({backtest.win_rate:.2%}) is below target (55%). Consider tightening entry criteria or improving exit logic.",
                }
            )

        # Risk recommendations
        if scores.drawdown_score < 10:
            recommendations.append(
                {
                    "type": "error",
                    "title": "High Drawdown",
                    "message": f"Max drawdown ({backtest.max_drawdown:.2%}) exceeds target (25%). Reduce position sizes or add stop-loss protections.",
                }
            )

        if scores.consistency_score < 7:
            recommendations.append(
                {
                    "type": "warning",
                    "title": "Inconsistent Performance",
                    "message": "Strategy shows inconsistent monthly returns. Consider testing across different market conditions.",
                }
            )

        # Execution recommendations
        if scores.frequency_score < 7:
            recommendations.append(
                {
                    "type": "info",
                    "title": "Trading Frequency",
                    "message": "Trading frequency may not be optimal for market liquidity. Consider adjusting signal generation frequency.",
                }
            )

        if scores.slippage_score < 3:
            recommendations.append(
                {
                    "type": "warning",
                    "title": "High Slippage",
                    "message": "Estimated slippage is high. Consider using limit orders, reducing position sizes, or trading more liquid markets.",
                }
            )

        # Robustness recommendations
        if scores.out_of_sample_score < 5:
            recommendations.append(
                {
                    "type": "warning",
                    "title": "Overfitting Risk",
                    "message": "Out-of-sample performance is significantly lower than in-sample. Strategy may be overfitted. Simplify logic or use regularization.",
                }
            )

        if scores.cross_market_score < 5:
            recommendations.append(
                {
                    "type": "warning",
                    "title": "Poor Cross-Market Performance",
                    "message": "Strategy doesn't generalize well across markets. Test on more symbols or add market regime detection.",
                }
            )

        # Overall recommendation
        if scores.total_score >= 75:
            recommendations.insert(
                0,
                {
                    "type": "success",
                    "title": "Approved for Deployment",
                    "message": (f"Strategy passed validation with score " f"{scores.total_score:.1f}/100. Ready for live trading with " f"recommended position size of {2.0 * (scores.total_score / 100):.2%}."),
                },
            )
        elif scores.total_score >= 65:
            recommendations.insert(
                0,
                {
                    "type": "warning",
                    "title": "Conditional Approval",
                    "message": (f"Strategy conditionally approved with score " f"{scores.total_score:.1f}/100. Start with reduced position " "size " f"({1.0 * (scores.total_score / 100):.2%}) and monitor " "closely for 30 days."),
                },
            )
        else:
            recommendations.insert(
                0,
                {
                    "type": "error",
                    "title": "Not Approved",
                    "message": f"Strategy score ({scores.total_score:.1f}/100) is below minimum threshold (65). Address critical issues before deployment.",
                },
            )

        # Build HTML
        if not recommendations:
            return ""

        rec_html = ""
        for rec in recommendations:
            rec_html += f"""
                <div class="recommendation {rec['type']}">
                    <div class="rec-title">{rec['title']}</div>
                    <div class="rec-message">{rec['message']}</div>
                </div>
            """

        return f"""
        <div class="section">
            <h2>Recommendations</h2>
            <div class="recommendations">
                {rec_html}
            </div>
        </div>
        """

    def _generate_footer(self) -> str:
        """Generate report footer."""
        return """
        <div class="footer">
            <p>Generated by ExhaustionLab Validation Framework v2.0</p>
            <p><em>This report is for informational purposes only and does not constitute investment advice.</em></p>
        </div>
        """

    def _fig_to_base64(self, fig: Figure) -> str:
        """Convert matplotlib figure to base64 string."""
        buffer = BytesIO()
        fig.savefig(buffer, format="png", bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        return image_base64

    def _get_grade(self, score: float) -> str:
        """Get letter grade from score."""
        if score >= 85:
            return "A (EXCELLENT)"
        elif score >= 75:
            return "B (GOOD)"
        elif score >= 65:
            return "C (ACCEPTABLE)"
        elif score >= 50:
            return "D (MARGINAL)"
        else:
            return "F (FAIL)"

    def _get_status_badge(self, passed: bool) -> str:
        """Get status badge HTML."""
        if passed:
            return '<span class="badge success">✓</span>'
        else:
            return '<span class="badge warning">⚠</span>'

    def _get_drawdown_class(self, drawdown: float) -> str:
        """Get CSS class for drawdown severity."""
        if drawdown < 0.15:
            return "positive"
        elif drawdown < 0.25:
            return ""
        else:
            return "negative"

    def _get_css(self) -> str:
        """Get CSS styles for report."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }

        .header h1 {
            font-size: 32px;
            margin-bottom: 15px;
        }

        .header-info {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            font-size: 14px;
        }

        .section {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .section h2 {
            font-size: 24px;
            margin-bottom: 20px;
            color: #2c3e50;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }

        .section h3 {
            font-size: 18px;
            margin: 15px 0 10px 0;
            color: #34495e;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }

        .summary-card {
            padding: 30px;
            border-radius: 10px;
            text-align: center;
        }

        .summary-card.approved {
            background: linear-gradient(135deg, #26DE81 0%, #20BF6B 100%);
            color: white;
        }

        .summary-card.warning {
            background: linear-gradient(135deg, #FED330 0%, #F7B731 100%);
            color: #333;
        }

        .summary-card.rejected {
            background: linear-gradient(135deg, #EE5A6F 0%, #FC5C65 100%);
            color: white;
        }

        .summary-title {
            font-size: 14px;
            text-transform: uppercase;
            margin-bottom: 10px;
            opacity: 0.9;
        }

        .summary-value {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .summary-subtitle {
            font-size: 16px;
            opacity: 0.9;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
        }

        .metric {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }

        .metric-label {
            font-size: 12px;
            color: #6c757d;
            text-transform: uppercase;
            margin-bottom: 8px;
        }

        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }

        .metric-value.positive {
            color: #26DE81;
        }

        .metric-value.negative {
            color: #EE5A6F;
        }

        .metrics-table {
            width: 100%;
            border-collapse: collapse;
        }

        .metrics-table th,
        .metrics-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }

        .metrics-table th {
            background: #f8f9fa;
            font-weight: 600;
            color: #495057;
        }

        .metrics-table tr:hover {
            background: #f8f9fa;
        }

        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }

        .badge.success {
            background: #26DE81;
            color: white;
        }

        .badge.warning {
            background: #FED330;
            color: #333;
        }

        .score-summary {
            text-align: center;
            margin-bottom: 30px;
        }

        .total-score {
            display: inline-block;
            padding: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
        }

        .score-label {
            font-size: 14px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }

        .score-value {
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .score-grade {
            font-size: 20px;
        }

        .score-components {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }

        .component {
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        .component-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .component-score {
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
        }

        .progress-bar {
            height: 8px;
            background: #dee2e6;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 15px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }

        .sub-metrics {
            font-size: 14px;
            color: #6c757d;
        }

        .sub-metrics div {
            padding: 5px 0;
        }

        .chart-container {
            margin: 30px 0;
        }

        .chart-container img {
            width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .table-container {
            overflow-x: auto;
        }

        .trade-journal {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        .trade-journal th,
        .trade-journal td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }

        .trade-journal th {
            background: #f8f9fa;
            font-weight: 600;
            position: sticky;
            top: 0;
        }

        .trade-journal tr:hover {
            background: #f8f9fa;
        }

        .trade-journal td.positive {
            color: #26DE81;
            font-weight: 600;
        }

        .trade-journal td.negative {
            color: #EE5A6F;
            font-weight: 600;
        }

        .recommendations {
            display: grid;
            gap: 15px;
        }

        .recommendation {
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid;
        }

        .recommendation.success {
            background: #d4edda;
            border-color: #26DE81;
        }

        .recommendation.warning {
            background: #fff3cd;
            border-color: #FED330;
        }

        .recommendation.error {
            background: #f8d7da;
            border-color: #EE5A6F;
        }

        .recommendation.info {
            background: #d1ecf1;
            border-color: #2E86DE;
        }

        .rec-title {
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 8px;
        }

        .rec-message {
            font-size: 14px;
            line-height: 1.6;
        }

        .footer {
            text-align: center;
            padding: 20px;
            color: #6c757d;
            font-size: 14px;
        }

        @media print {
            .container {
                max-width: 100%;
            }

            .section {
                page-break-inside: avoid;
            }
        }
        """


def generate_validation_report(
    backtest: BacktestResult,
    scores: ComponentScores,
    symbol: str,
    output_path: Path | str,
    costs: Optional[Dict] = None,
    config: Optional[ReportConfig] = None,
) -> Path:
    """
    Convenience function to generate validation report.

    Args:
        backtest: Parsed backtest result
        scores: Comprehensive scores
        symbol: Trading symbol
        output_path: Path to save report
        costs: Trading costs (optional)
        config: Report configuration (optional)

    Returns:
        Path to generated report
    """
    generator = ReportGenerator(config)
    return generator.generate_html_report(
        backtest=backtest,
        scores=scores,
        symbol=symbol,
        output_path=output_path,
        costs=costs,
    )
