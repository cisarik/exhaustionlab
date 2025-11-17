"""
Strategy Web Crawler and Knowledge Extraction

Automatically extracts example trading strategies from various sources
for LLM context enhancement and pattern recognition.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import feedparser
import requests
from bs4 import BeautifulSoup

from .meta_config import StrategyExample


@dataclass
class SourceConfig:
    """Configuration for web crawling sources."""

    name: str
    base_url: str
    content_selectors: Dict[str, str]  # CSS selectors for content extraction
    rate_limit: float  # seconds between requests
    quality_threshold: float  # minimum quality score (0-1)
    enabled: bool = True


@dataclass
class ExtractedContent:
    """Content extracted from web sources."""

    url: str
    title: str
    description: str
    code_blocks: List[str]
    indicators_used: List[str]
    strategy_type: str
    performance_metrics: Dict[str, float]
    quality_score: float
    source_confidence: float
    extraction_timestamp: float


class StrategyWebCrawler:
    """Intelligent web crawler for trading strategy examples."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".exhaustionlab" / "strategy_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # Configure web sources with quality criteria
        self.sources = self._initialize_sources()

        # Rate limiting per domain
        self.last_request_time = {}

        # Quality scoring patterns
        self.quality_indicators = self._initialize_quality_patterns()

    def _initialize_sources(self) -> List[SourceConfig]:
        """Initialize web crawling sources with quality control."""

        sources = [
            # High-quality quantitative research
            SourceConfig(
                name="quantresearch",
                base_url="https://medium.com/quantitative-research",
                content_selectors={
                    "title": "h1",
                    "content": "article p, div[data-contenteditable='true']",
                    "code": "pre code",
                    "metrics": ".metric",
                },
                rate_limit=2.0,
                quality_threshold=0.7,
            ),
            # GitHub trading strategies
            SourceConfig(
                name="github_strategies",
                base_url="https://raw.githubusercontent.com",
                content_selectors={
                    "code": "all",  # Raw code files
                    "description": "README.md",
                },
                rate_limit=1.0,
                quality_threshold=0.6,
            ),
            # Trading strategies Reddit
            SourceConfig(
                name="reddit_trading",
                base_url="https://www.reddit.com",
                content_selectors={"title": "h1", "content": "p", "code": "pre code"},
                rate_limit=1.5,
                quality_threshold=0.4,  # Lower threshold for Reddit
            ),
            # TradingView scripts
            SourceConfig(
                name="tradingview_scripts",
                base_url="https://www.tradingview.com",
                content_selectors={
                    "title": "h1",
                    "description": ".scriptDescription",
                    "code": ".scriptCode",
                },
                rate_limit=3.0,
                quality_threshold=0.6,
            ),
        ]

        return sources

    def _initialize_quality_patterns(self) -> Dict[str, Any]:
        """Initialize patterns for quality scoring."""
        return {
            # High-quality indicators
            "premium_indicators": [
                "sharpe",
                "sortino",
                "calmar",
                "win_rate",
                "profit_factor",
                "max_drawdown",
                "expectancy",
                "kelly",
                "ulcer_index",
            ],
            # Trading concepts (indicates serious content)
            "sophisticated_terms": [
                "backtest",
                "out_of_sample",
                "walk_forward",
                "monte_carlo",
                "bootstrap",
                "parameter_optimization",
                "cross_validation",
                "stationarity",
                "cointegration",
                "regression",
                "autocorrelation",
            ],
            # Risk management terms
            "risk_terms": [
                "position_sizing",
                "stop_loss",
                "portfolio_optimization",
                "var_risk",
                "drawdown",
                "risk_parity",
                "alpha_generation",
            ],
            # Code quality indicators
            "code_quality": [
                "def main",
                "@script",
                "input.",
                "plot",
                "persistent",
                "try:",
                "except:",
                "if __name__",
                "class",
                "import",
            ],
            # Low-quality warnings
            "spam_indicators": [
                "get_rich_quick",
                "guaranteed",
                "100%",
                "secret",
                "prophet",
                "scalping",
                "martingale",
                "holy_grail",
                "free_money",
            ],
        }

    def extract_strategy_examples(self, max_examples: int = 50) -> List[StrategyExample]:
        """Extract strategy examples from configured web sources."""

        extracted_examples = []

        for source in self.sources:
            if not source.enabled:
                continue

            self.logger.info(f"Extracting from {source.name}")

            try:
                source_examples = self._extract_from_source(source, max_examples // len([s for s in self.sources if s.enabled]))
                extracted_examples.extend(source_examples)

                # Rate limiting between sources
                time.sleep(source.rate_limit)

            except Exception as e:
                self.logger.error(f"Failed to extract from {source.name}: {e}")
                continue

        # Quality filtering and ranking
        filtered_examples = self._filter_by_quality(extracted_examples)
        ranked_examples = self._rank_by_relevance(filtered_examples)

        self.logger.info(f"Extracted {len(ranked_examples)} high-quality examples")

        return ranked_examples[:max_examples]

    def _extract_from_source(self, source: SourceConfig, limit: int) -> List[StrategyExample]:
        """Extract examples from specific source."""

        if source.name == "github_strategies":
            return self._extract_github_strategies(source, limit)
        elif source.name == "reddit_trading":
            return self._extract_reddit_strategies(source, limit)
        elif source.name == "tradingview_scripts":
            return self._extract_tradingview_scripts(source, limit)
        elif source.name == "quantresearch":
            return self._extract_medium_articles(source, limit)
        else:
            return []

    def _extract_github_strategies(self, source: SourceConfig, limit: int) -> List[StrategyExample]:
        """Extract strategy examples from GitHub repositories."""

        examples = []

        # Search for trending trading repositories
        search_terms = ["trading+strategy", "pine+script", "trading+bot", "backtest"]

        for term in search_terms:
            if len(examples) >= limit:
                break

            try:
                # GitHub API search (simplified for demo)
                search_url = "https://api.github.com/search/repositories"
                params = {
                    "q": f"{term} language:python stars:>100",
                    "sort": "stars",
                    "per_page": 20,
                }

                self._rate_limit_request("api.github.com", source.rate_limit)

                response = requests.get(search_url, params=params, timeout=30)
                if response.status_code != 200:
                    continue

                data = response.json()

                for repo in data.get("items", []):
                    if len(examples) >= limit:
                        break

                    # Extract strategy from README or main Python file
                    example = self._extract_github_repo_example(repo)
                    if example and self._score_quality(example) >= source.quality_threshold:
                        examples.append(example)

            except Exception as e:
                self.logger.warning(f"GitHub search failed for {term}: {e}")
                continue

        return examples

    def _extract_github_repo_example(self, repo: Dict) -> Optional[StrategyExample]:
        """Extract specific strategy example from GitHub repository."""

        try:
            repo_name = repo.get("full_name", "")
            repo_url = repo.get("html_url", "")
            description = repo.get("description", "")

            # Look for main strategy file
            api_url = f"https://api.github.com/repos/{repo_name}/contents"
            response = requests.get(api_url, timeout=10)

            if response.status_code != 200:
                return None

            files = response.json()

            # Find main strategy files
            strategy_files = [f for f in files if self._is_strategy_file(f.get("name", ""))]

            if not strategy_files:
                return None

            # Get first strategy file content
            main_file = strategy_files[0]
            file_content = self._get_github_file(repo_name, main_file.get("path"))

            if file_content:
                # Extract indicators and strategy type
                indicators_used = self._extract_indicators_from_code(file_content)
                strategy_type = self._detect_strategy_type(file_content, indicators_used)
                tags = list(indicators_used)
                if strategy_type:
                    tags.append(strategy_type)

                description_text = description or repo_name.split("/")[-1]
                if repo_url:
                    description_text = f"{description_text} ({repo_url})"

                return StrategyExample(
                    name=repo_name.split("/")[-1],
                    description=description_text,
                    source="github",
                    code=file_content,
                    performance_metrics=self._estimate_performance(file_content),
                    market_conditions="unknown",
                    risk_profile="balanced",
                    tags=tags,
                )

        except Exception as e:
            self.logger.warning(f"Failed to extract {repo_name}: {e}")

        return None

    def _extract_reddit_strategies(self, source: SourceConfig, limit: int) -> List[StrategyExample]:
        """Extract strategies from Reddit (lower quality but good for variety)."""

        examples = []

        subreddits = ["algotrading", "algo_trading", "coding_trades", "quant"]
        search_terms = ["python", "pine script", "trading strategy", "backtest"]

        for subreddit in subreddits:
            if len(examples) >= limit:
                break

            try:
                # Get RSS feed for subreddit
                rss_url = f"https://www.reddit.com/r/{subreddit}/search.rss"
                params = {
                    "q": f"({' OR '.join(search_terms)})",
                    "sort": "hot",
                    "t": "month",
                    "limit": 20,
                }

                self._rate_limit_request("reddit.com", source.rate_limit)

                feed = feedparser.parse(rss_url, params=params)

                for entry in feed.entries:
                    if len(examples) >= limit:
                        break

                    # Extract strategy from Reddit post
                    example = self._extract_reddit_post(entry)
                    if example and self._score_quality(example) >= source.quality_threshold:
                        examples.append(example)

            except Exception as e:
                self.logger.warning(f"Reddit extraction failed for {subreddit}: {e}")
                continue

        return examples

    def _extract_reddit_post(self, entry: Dict) -> Optional[StrategyExample]:
        """Extract strategy from Reddit post."""

        try:
            title = entry.get("title", "")
            description = entry.get("summary", "")
            link = entry.get("link", "")

            # Get full content
            response = requests.get(link, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")

            # Find code blocks
            code_blocks = []
            for code in soup.find_all("code"):
                code_text = code.get_text().strip()
                if self._is_strategy_code(code_text):
                    code_blocks.append(code_text)

            if not code_blocks:
                return None

            # Use the largest code block
            main_code = max(code_blocks, key=len)

            # Extract indicators and classify
            indicators_used = self._extract_indicators_from_code(main_code)
            strategy_type = self._detect_strategy_type(main_code, indicators_used)
            tags = list(indicators_used)
            if strategy_type:
                tags.append(strategy_type)

            return StrategyExample(
                name="reddit_" + title[:30].replace(" ", "_").lower(),
                description=description or title,
                source="reddit",
                code=main_code,
                performance_metrics={},
                market_conditions="unknown",
                risk_profile="high_risk",  # Reddit strategies often risky
                tags=tags,
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract Reddit post: {e}")

        return None

    def _extract_tradingview_scripts(self, source: SourceConfig, limit: int) -> List[StrategyExample]:
        """Extract Pine scripts from TradingView."""

        examples = []

        # TradingView has script libraries - would need specific search API
        # For now, return empty as this requires more complex scraping
        self.logger.info("TradingView extraction not implemented yet")

        return examples

    def _extract_medium_articles(self, source: SourceConfig, limit: int) -> List[StrategyExample]:
        """Extract from Medium quantitative research articles."""

        examples = []

        # Medium has RSS feeds for publications
        publications = ["towardsdatascience", "betterprogramming", "codeburst"]
        search_terms = ["trading", "quantitative", "backtest", "cryptocurrency"]

        for pub in publications:
            if len(examples) >= limit:
                break

            try:
                rss_url = f"https://medium.com/feed/{pub}"
                feed = feedparser.parse(rss_url)

                for entry in feed.entries:
                    if len(examples) >= limit:
                        break

                    # Check if article contains relevant terms
                    content = entry.get("summary", "") + " " + entry.get("title", "")

                    if any(term.lower() in content.lower() for term in search_terms):
                        example = self._extract_medium_article(entry)
                        if example and self._score_quality(example) >= source.quality_threshold:
                            examples.append(example)

            except Exception as e:
                self.logger.warning(f"Medium extraction failed for {pub}: {e}")
                continue

        return examples

    def _extract_medium_article(self, entry: Dict) -> Optional[StrategyExample]:
        """Extract strategy from Medium article."""

        try:
            title = entry.get("title", "")
            description = entry.get("summary", "")
            link = entry.get("link", "")

            # Get full article
            response = requests.get(link, timeout=10)
            soup = BeautifulSoup(response.content, "html.parser")

            # Find code blocks
            code_blocks = []
            for code in soup.find_all("code"):
                code_text = code.get_text().strip()
                if self._is_strategy_code(code_text):
                    code_blocks.append(code_text)

            if not code_blocks:
                return None

            # Find the largest code block
            main_code = max(code_blocks, key=len)

            # Validate it's trading strategy code
            indicators_used = self._extract_indicators_from_code(main_code)
            if not indicators_used:
                return None

            return StrategyExample(
                name="medium_" + title[:30].replace(" ", "_").lower(),
                description=description[:200],
                source="medium",
                code=main_code,
                performance_metrics={},
                market_conditions="research_environment",
                risk_profile="research_grade",
                tags=indicators_used,
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract Medium article: {e}")

        return None

    def _filter_by_quality(self, examples: List[StrategyExample]) -> List[StrategyExample]:
        """Filter examples by quality score."""
        return [e for e in examples if self._score_quality(e) >= 0.3]

    def _rank_by_relevance(self, examples: List[StrategyExample]) -> List[StrategyExample]:
        """Rank examples by relevance score."""
        return sorted(examples, key=lambda x: self._score_quality(x), reverse=True)

    def _score_quality(self, example: StrategyExample) -> float:
        """Calculate quality score for example (0-1)."""

        score = 0.5  # Base score

        code = example.code.lower()

        # Boost for sophisticated content
        for term in self.quality_indicators.sophisticated_terms:
            if term in code:
                score += 0.1

        # Boost for risk management
        for term in self.quality_indicators.risk_terms:
            if term in code:
                score += 0.05

        # Boost for code quality
        for term in self.quality_indicators.code_quality:
            if term in code:
                score += 0.05

        # Bonus for performance metrics
        if example.performance_metrics:
            score += 0.1

        # Penalty for low-quality indicators
        for term in self.quality_indicators.spam_indicators:
            if term in code:
                score -= 0.2

        # Adjust based on source
        source_scores = {
            "github": 0.2,
            "medium": 0.15,
            "tradingview": 0.1,
            "reddit": -0.1,
        }

        score += source_scores.get(example.source, 0)

        # Clamp to valid range
        return max(0.0, min(1.0, score))

    def _extract_indicators_from_code(self, code: str) -> List[str]:
        """Extract trading indicators used in code."""

        indicators = []
        code_lower = code.lower()

        # Common indicator patterns
        indicator_patterns = {
            r"\brsi\s*\(": "RSI",
            r"\bmacd\s*\(": "MACD",
            r"\bbollinger": "Bollinger Bands",
            r"\bsma\s*\(": "SMA",
            r"\bema\s*\(": "EMA",
            r"\batr\s*\(": "ATR",
            r"\bstoch\s*\(": "Stochastic",
            r"\bcci\s*\(": "CCI",
            r"\bADX": "ADX",
            r"\brate.*change": "Rate of Change",
            r"\bmomentum": "Momentum",
            r"\bstandard.*deviation": "Standard Deviation",
        }

        for pattern, indicator in indicator_patterns.items():
            if re.search(pattern, code_lower):
                indicators.append(indicator)

        return list(set(indicators))

    def _detect_strategy_type(self, code: str, indicators: List[str]) -> str:
        """Detect strategy type based on code and indicators."""

        code_lower = code.lower()

        # Type detection patterns
        type_patterns = {
            "mean_reversion": [
                r"mean.*revert",
                r"revert.*mean",
                r"bollinger",
                r"oversold",
                r"overbought",
                r"rsi.*low",
                r"bb.*bounce",
            ],
            "momentum": [
                r"momentum",
                r"rate.*change",
                r"macd.* bullish",
                r"breakout.*momentum",
                r"trend.*strength",
            ],
            "trend_following": [
                r"trend.*follow",
                r"moving.*average.*cross",
                r"crossover",
                r"crossunder",
                r"ema.*sma",
                r"trend.*continuation",
            ],
            "breakout": [
                r"breakout",
                r"consolidation",
                r"support.*resistance",
                r"range.*expand",
                r"triangle.*pattern",
            ],
            "exhaustion": [
                r"exhaustion",
                r"over.*extended",
                r"trend.*end",
                r"momentum.*exhaust",
                r"cycle.*exhaust",
            ],
        }

        for strategy_type, patterns in type_patterns.items():
            if any(re.search(pattern, code_lower) for pattern in patterns):
                return strategy_type

        # Fallback based on indicators
        if "RSI" in indicators and any(i in indicators for i in ["Bollinger Bands", "Stochastic"]):
            return "mean_reversion"
        elif "MACD" in indicators:
            return "momentum"
        elif "SMA" in indicators or "EMA" in indicators:
            return "trend_following"
        else:
            return "unknown"

    def _estimate_performance(self, code: str) -> Dict[str, float]:
        """Estimate performance based on code sophistication."""

        # This is a rough estimation based on code quality
        code_length = len(code.split("\n"))

        # Base estimation on code sophistication
        sophistication = min(1.0, code_length / 100.0)

        return {
            "estimated_sharpe": 0.5 + sophistication * 0.5,
            "estimated_max_drawdown": 0.3 - sophistication * 0.1,
            "estimated_win_rate": 0.4 + sophistication * 0.2,
        }

    def _is_strategy_file(self, filename: str) -> bool:
        """Check if file is likely a strategy file."""

        strategy_extensions = [".py", ".pin", ".pine", ".algo", ".strategy"]
        strategy_keywords = ["strategy", "indicator", "signal", "trading", "backtest"]

        filename_lower = filename.lower()

        return any(filename_lower.endswith(ext) for ext in strategy_extensions) or any(keyword in filename_lower for keyword in strategy_keywords)

    def _is_strategy_code(self, code: str) -> bool:
        """Check if code appears to be trading strategy code."""

        code_lower = code.lower()

        # Must contain some trading indicators
        has_indicators = any(ind in code_lower for ind in ["rsi(", "macd(", "sma(", "ema(", "atr(", "bb("])

        # Must contain trading logic
        has_trading_terms = any(term in code_lower for term in ["buy", "sell", "signal", "position", "trade"])

        # Must be reasonable length
        is_reasonable_length = 20 < len(code) < 5000

        return has_indicators and has_trading_terms and is_reasonable_length

    def _get_github_file(self, repo_name: str, file_path: str) -> Optional[str]:
        """Get file content from GitHub API."""

        try:
            api_url = f"https://api.github.com/repos/{repo_name}/contents/{file_path}"
            response = requests.get(api_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                content = data.get("content", "")
                import base64

                return base64.b64decode(content).decode("utf-8")

        except Exception as e:
            self.logger.warning(f"Failed to get GitHub file {repo_name}/{file_path}: {e}")

        return None

    def _rate_limit_request(self, domain: str, delay: float):
        """Handle rate limiting for domains."""

        last_time = self.last_request_time.get(domain, 0)
        current_time = time.time()

        if current_time - last_time < delay:
            sleep_time = delay - (current_time - last_time)
            time.sleep(sleep_time)

        self.last_request_time[domain] = time.time()

    def save_extracted_examples(self, examples: List[StrategyExample], filename: str = "extracted_examples.json"):
        """Save extracted examples to cache."""

        file_path = self.cache_dir / filename

        extracted_data = []
        for example in examples:
            extracted_data.append(
                {
                    "name": example.name,
                    "description": example.description,
                    "source": example.source,
                    "code": example.code,
                    "performance_metrics": example.performance_metrics,
                    "market_conditions": example.market_conditions,
                    "risk_profile": example.risk_profile,
                    "tags": example.tags,
                    "quality_score": self._score_quality(example),
                }
            )

        with open(file_path, "w") as f:
            json.dump(extracted_data, f, indent=2)

        self.logger.info(f"Saved {len(examples)} extracted examples to {file_path}")

    def load_cached_examples(self, filename: str = "extracted_examples.json") -> List[StrategyExample]:
        """Load previously extracted examples from cache."""

        file_path = self.cache_dir / filename

        if not file_path.exists():
            return []

        try:
            with open(file_path) as f:
                data = json.load(f)

            examples = []
            for item in data:
                example = StrategyExample(
                    name=item["name"],
                    description=item["description"],
                    source=item["source"],
                    code=item["code"],
                    performance_metrics=item["performance_metrics"],
                    market_conditions=item["market_conditions"],
                    risk_profile=item["risk_profile"],
                    tags=item["tags"],
                )
                examples.append(example)

            self.logger.info(f"Loaded {len(examples)} cached examples from {file_path}")
            return examples

        except Exception as e:
            self.logger.error(f"Failed to load cached examples: {e}")
            return []
