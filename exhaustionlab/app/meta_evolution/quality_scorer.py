"""
Strategy Quality Scorer

Calculates comprehensive quality scores for trading strategies.
Combines source quality, code quality, performance, and community metrics.
"""

import logging
import re
from typing import Any, Dict

import numpy as np

logger = logging.getLogger(__name__)


class StrategyQualityScorer:
    """
    Calculate comprehensive quality score for strategies.

    Score Components:
    - Source Quality (30%): Stars, upvotes, author reputation
    - Code Quality (20%): Complexity, structure, features
    - Performance (30%): Backtest metrics if available
    - Community (20%): Usage, discussions, forks

    Final Score: 0-100
    """

    def __init__(self):
        """Initialize quality scorer."""
        self.weights = {
            "source": 0.30,
            "code": 0.20,
            "performance": 0.30,
            "community": 0.20,
        }

    def calculate_quality_score(self, strategy: Dict[str, Any]) -> float:
        """
        Calculate quality score (0-100).

        Args:
            strategy: Strategy metadata dictionary

        Returns:
            Quality score 0-100
        """
        scores = {
            "source": self._score_source(strategy),
            "code": self._score_code(strategy),
            "performance": self._score_performance(strategy),
            "community": self._score_community(strategy),
        }

        total_score = sum(scores[k] * self.weights[k] for k in scores)

        logger.debug(f"Quality scores: {scores} -> total: {total_score:.2f}")

        return round(total_score, 2)

    def _score_source(self, strategy: Dict[str, Any]) -> float:
        """Score based on source quality (0-100)."""
        platform = strategy.get("platform", "")

        # GitHub scoring
        if platform == "github":
            stars = strategy.get("stars", 0)
            forks = strategy.get("forks", 0)

            # Logarithmic scaling for stars (1000 stars = 100 points)
            star_score = min(100, (np.log1p(stars) / np.log1p(1000)) * 100)

            # Logarithmic scaling for forks (200 forks = 100 points)
            fork_score = min(100, (np.log1p(forks) / np.log1p(200)) * 100)

            return star_score * 0.7 + fork_score * 0.3

        # Reddit scoring
        elif platform == "reddit":
            upvotes = strategy.get("upvotes", 0)
            comments = strategy.get("comments", 0)
            upvote_ratio = strategy.get("upvote_ratio", 0.5)

            # Score based on upvotes (100 upvotes = 70 points)
            upvote_score = min(70, (upvotes / 100) * 70)

            # Comment engagement (20 comments = 20 points)
            comment_score = min(20, (comments / 20) * 20)

            # Upvote ratio bonus (>80% = 10 points)
            ratio_score = max(0, (upvote_ratio - 0.5) / 0.3 * 10)

            return upvote_score + comment_score + ratio_score

        # TradingView scoring
        elif platform == "tradingview":
            likes = strategy.get("likes", 0)
            uses = strategy.get("uses", 0)

            # Likes (500 likes = 60 points)
            like_score = min(60, (likes / 500) * 60)

            # Uses indicate actual usage (1000 uses = 40 points)
            use_score = min(40, (uses / 1000) * 40)

            return like_score + use_score

        # Default for unknown sources
        return 50.0

    def _score_code(self, strategy: Dict[str, Any]) -> float:
        """Score based on code quality (0-100)."""
        code = strategy.get("code") or strategy.get("pine_code") or strategy.get("python_code") or ""

        if not code:
            # No code available, use heuristics
            has_description = bool(strategy.get("description", ""))
            return 50.0 if has_description else 30.0

        score = 0.0

        # Length score (50-300 LOC is ideal)
        loc = len(code.split("\n"))
        if 50 <= loc <= 300:
            score += 30
        elif 30 <= loc < 50 or 300 < loc <= 500:
            score += 20
        else:
            score += 10

        # Complexity indicators
        complexity = self._estimate_complexity(code)
        if 0.3 <= complexity <= 0.7:
            score += 30  # Sweet spot
        elif 0.2 <= complexity < 0.3 or 0.7 < complexity <= 0.8:
            score += 20
        else:
            score += 10

        # Has proper structure
        if "//@version" in code or "@script" in code:
            score += 10

        # Has comments
        comment_ratio = len(re.findall(r"//|#", code)) / max(1, loc)
        if 0.1 <= comment_ratio <= 0.3:
            score += 10

        # Has inputs/parameters
        if "input(" in code or "input." in code:
            score += 10

        # Has plotting/visualization
        if "plot(" in code or "plotshape(" in code:
            score += 10

        return min(100, score)

    def _score_performance(self, strategy: Dict[str, Any]) -> float:
        """Score based on backtest performance (0-100)."""
        metrics = strategy.get("backtest_metrics", {})

        if not metrics:
            # No backtest data, neutral score
            return 50.0

        score = 0.0

        # Sharpe ratio (0-30 points)
        sharpe = metrics.get("sharpe_ratio", 0)
        sharpe_score = min(30, (sharpe / 3.0) * 30)
        score += sharpe_score

        # Max drawdown (0-30 points, lower is better)
        drawdown = metrics.get("max_drawdown", 0)
        dd_score = max(0, (1 - min(1, drawdown / 0.25)) * 30)
        score += dd_score

        # Win rate (0-20 points)
        win_rate = metrics.get("win_rate", 0)
        if win_rate >= 0.50:
            wr_score = 10 + ((win_rate - 0.50) / 0.20) * 10
        else:
            wr_score = (win_rate / 0.50) * 10
        score += min(20, wr_score)

        # Profit factor (0-20 points)
        pf = metrics.get("profit_factor", 1.0)
        pf_score = min(20, ((pf - 1.0) / 2.0) * 20)
        score += pf_score

        return min(100, score)

    def _score_community(self, strategy: Dict[str, Any]) -> float:
        """Score based on community engagement (0-100)."""
        platform = strategy.get("platform", "")
        score = 0.0

        # GitHub community
        if platform == "github":
            stars = strategy.get("stars", 0)
            forks = strategy.get("forks", 0)

            # Stars (0-50 points)
            star_score = min(50, (stars / 100) * 50)
            score += star_score

            # Forks indicate actual use (0-30 points)
            fork_score = min(30, (forks / 50) * 30)
            score += fork_score

            # Recent activity bonus (0-20 points)
            # (Would need update date to calculate)
            score += 10  # Default moderate activity

        # Reddit community
        elif platform == "reddit":
            upvotes = strategy.get("upvotes", 0)
            comments = strategy.get("comments", 0)

            # Upvotes (0-50 points)
            upvote_score = min(50, (upvotes / 50) * 50)
            score += upvote_score

            # Comments show engagement (0-30 points)
            comment_score = min(30, (comments / 30) * 30)
            score += comment_score

            # Upvote ratio bonus
            ratio = strategy.get("upvote_ratio", 0.5)
            ratio_bonus = max(0, (ratio - 0.5) / 0.3 * 20)
            score += ratio_bonus

        # TradingView community
        elif platform == "tradingview":
            likes = strategy.get("likes", 0)
            uses = strategy.get("uses", 0)

            # Likes (0-50 points)
            like_score = min(50, (likes / 200) * 50)
            score += like_score

            # Uses show adoption (0-50 points)
            use_score = min(50, (uses / 500) * 50)
            score += use_score

        return min(100, score)

    def _estimate_complexity(self, code: str) -> float:
        """
        Estimate code complexity (0-1).

        Based on:
        - Number of conditionals
        - Number of loops
        - Number of function calls
        - Nesting depth
        """
        if not code:
            return 0.0

        lines = code.split("\n")
        loc = len(lines)

        # Count complexity indicators
        conditionals = len(re.findall(r"\bif\b|\belse\b|\belif\b|\bswitch\b", code))
        loops = len(re.findall(r"\bfor\b|\bwhile\b", code))
        functions = len(re.findall(r"\bdef\b|\bfunction\b", code))

        # Estimate nesting (indentation levels)
        max_indent = 0
        for line in lines:
            indent = len(line) - len(line.lstrip())
            max_indent = max(max_indent, indent // 4)  # Assume 4 spaces per level

        # Complexity score (normalized)
        complexity = (conditionals / max(1, loc)) * 0.3 + (loops / max(1, loc)) * 0.2 + (functions / max(1, loc)) * 0.2 + (max_indent / 10) * 0.3

        return min(1.0, complexity)

    def get_quality_category(self, score: float) -> str:
        """Get quality category from score."""
        if score >= 80:
            return "Excellent"
        elif score >= 70:
            return "Good"
        elif score >= 60:
            return "Average"
        elif score >= 50:
            return "Below Average"
        else:
            return "Poor"
