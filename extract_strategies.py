#!/usr/bin/env python3
"""
Strategy Extraction Master Script

Extracts trading strategies from multiple sources:
- GitHub (Pine Script repositories)
- Reddit (trading discussions)
- TradingView (public scripts)

Scores quality and stores in knowledge base.
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add to path
sys.path.insert(0, os.path.dirname(__file__))

# Import crawlers
from exhaustionlab.app.meta_evolution.crawlers.github_crawler import (
    GitHubStrategyCrawler,
)
from exhaustionlab.app.meta_evolution.crawlers.reddit_crawler import (
    RedditStrategyCrawler,
)
from exhaustionlab.app.meta_evolution.crawlers.tradingview_scraper import (
    TradingViewScraper,
)
from exhaustionlab.app.meta_evolution.quality_scorer import StrategyQualityScorer
from exhaustionlab.app.meta_evolution.knowledge_base_storage import KnowledgeBaseStorage


class StrategyExtractor:
    """Master class for extracting strategies from all sources."""

    def __init__(self):
        """Initialize extractors."""
        self.github_crawler = GitHubStrategyCrawler()
        self.reddit_crawler = RedditStrategyCrawler()
        self.tradingview_scraper = TradingViewScraper()
        self.quality_scorer = StrategyQualityScorer()
        self.storage = KnowledgeBaseStorage()

    def extract_from_github(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Extract strategies from GitHub."""
        logger.info(f"🔍 Extracting from GitHub (limit: {limit})...")

        try:
            # Search for Pine Script strategies with better query
            results = self.github_crawler.search_strategies(
                query="pinescript",  # Simple query works best
                min_stars=10,
                max_results=limit,
            )

            logger.info(f"   Found {len(results)} GitHub repositories")

            # Score quality
            for strategy in results:
                strategy["quality_score"] = self.quality_scorer.calculate_quality_score(
                    strategy
                )

            return results

        except Exception as e:
            logger.error(f"❌ GitHub extraction failed: {e}")
            return []

    def extract_from_reddit(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Extract strategies from Reddit."""
        logger.info(f"🔍 Extracting from Reddit (limit: {limit})...")

        try:
            # Search trading subreddits
            results = self.reddit_crawler.search_strategies(
                query="pinescript strategy cryptocurrency bitcoin",
                min_upvotes=10,
                max_results=limit,
            )

            logger.info(f"   Found {len(results)} Reddit posts")

            # Score quality
            for strategy in results:
                strategy["quality_score"] = self.quality_scorer.calculate_quality_score(
                    strategy
                )

            return results

        except Exception as e:
            logger.error(f"❌ Reddit extraction failed: {e}")
            return []

    def extract_from_tradingview(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Extract strategies from TradingView."""
        logger.info(f"🔍 Extracting from TradingView (limit: {limit})...")

        try:
            # Get popular strategies
            results = self.tradingview_scraper.get_popular_strategies(limit=limit)

            logger.info(f"   Found {len(results)} TradingView scripts")

            # Score quality
            for strategy in results:
                strategy["quality_score"] = self.quality_scorer.calculate_quality_score(
                    strategy
                )

            return results

        except Exception as e:
            logger.error(f"❌ TradingView extraction failed: {e}")
            return []

    def extract_all(
        self,
        github_limit: int = 50,
        reddit_limit: int = 30,
        tradingview_limit: int = 20,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract from all sources.

        Args:
            github_limit: Max GitHub results
            reddit_limit: Max Reddit results
            tradingview_limit: Max TradingView results

        Returns:
            Dictionary with results from each source
        """
        results = {"github": [], "reddit": [], "tradingview": []}

        # Extract from each source
        results["github"] = self.extract_from_github(github_limit)
        results["reddit"] = self.extract_from_reddit(reddit_limit)
        results["tradingview"] = self.extract_from_tradingview(tradingview_limit)

        return results

    def save_to_knowledge_base(
        self, results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, int]:
        """
        Save extracted strategies to knowledge base.

        Args:
            results: Dictionary with strategies from each source

        Returns:
            Dictionary with count saved from each source
        """
        logger.info("💾 Saving to knowledge base...")

        saved = {"github": 0, "reddit": 0, "tradingview": 0}

        for source, strategies in results.items():
            if strategies:
                try:
                    ids = self.storage.save_batch(strategies)
                    saved[source] = len(ids)
                    logger.info(f"   {source}: {len(ids)} strategies saved")
                except Exception as e:
                    logger.error(f"   {source}: Failed to save - {e}")

        return saved

    def get_top_strategies(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top quality strategies from knowledge base."""
        logger.info(f"📊 Getting top {limit} strategies...")

        top = self.storage.get_top_quality(limit=limit)

        for idx, strategy in enumerate(top, 1):
            quality = strategy.get("quality_score", 0)
            category = self.quality_scorer.get_quality_category(quality)
            logger.info(
                f"   {idx}. {strategy.get('name', 'Unknown')[:50]} - {quality:.1f} ({category})"
            )

        return top

    def print_statistics(self):
        """Print statistics about knowledge base."""
        stats = self.storage.get_statistics()

        print("\n" + "=" * 60)
        print("📊 KNOWLEDGE BASE STATISTICS")
        print("=" * 60)
        print(f"Total Strategies: {stats['total']}")
        print(f"Average Quality Score: {stats['avg_quality_score']:.1f}")
        print(f"Strategies with Code: {stats['with_code']}")
        print("\nBy Platform:")
        for platform, count in stats["by_platform"].items():
            print(f"  - {platform.title()}: {count}")
        print(f"\nLast Updated: {stats['last_updated']}")
        print("=" * 60)


def main():
    """Main extraction flow."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract trading strategies from multiple sources"
    )
    parser.add_argument(
        "--github", type=int, default=50, help="GitHub limit (default: 50)"
    )
    parser.add_argument(
        "--reddit", type=int, default=30, help="Reddit limit (default: 30)"
    )
    parser.add_argument(
        "--tradingview", type=int, default=20, help="TradingView limit (default: 20)"
    )
    parser.add_argument(
        "--quick", action="store_true", help="Quick extraction (20 total)"
    )
    parser.add_argument(
        "--full", action="store_true", help="Full extraction (100 total)"
    )
    parser.add_argument(
        "--stats-only", action="store_true", help="Show statistics only"
    )

    args = parser.parse_args()

    # Initialize extractor
    extractor = StrategyExtractor()

    # Show stats only
    if args.stats_only:
        extractor.print_statistics()
        return 0

    # Adjust limits for quick/full modes
    if args.quick:
        github_limit = 10
        reddit_limit = 5
        tradingview_limit = 5
        total = 20
    elif args.full:
        github_limit = 50
        reddit_limit = 30
        tradingview_limit = 20
        total = 100
    else:
        github_limit = args.github
        reddit_limit = args.reddit
        tradingview_limit = args.tradingview
        total = github_limit + reddit_limit + tradingview_limit

    print("\n" + "=" * 60)
    print("🚀 STRATEGY EXTRACTION PIPELINE")
    print("=" * 60)
    print(f"Target: {total} strategies")
    print(f"  - GitHub: {github_limit}")
    print(f"  - Reddit: {reddit_limit}")
    print(f"  - TradingView: {tradingview_limit}")
    print("=" * 60)
    print()

    # Extract from all sources
    results = extractor.extract_all(
        github_limit=github_limit,
        reddit_limit=reddit_limit,
        tradingview_limit=tradingview_limit,
    )

    # Count total extracted
    total_extracted = sum(len(strategies) for strategies in results.values())

    print("\n" + "=" * 60)
    print("📦 EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Total extracted: {total_extracted} strategies")
    for source, strategies in results.items():
        print(f"  - {source.title()}: {len(strategies)}")
    print()

    # Save to knowledge base
    saved = extractor.save_to_knowledge_base(results)
    total_saved = sum(saved.values())

    print("\n" + "=" * 60)
    print("💾 SAVED TO KNOWLEDGE BASE")
    print("=" * 60)
    print(f"Total saved: {total_saved} strategies")
    for source, count in saved.items():
        print(f"  - {source.title()}: {count}")
    print()

    # Show top strategies
    if total_saved > 0:
        print("\n" + "=" * 60)
        print("🏆 TOP 10 QUALITY STRATEGIES")
        print("=" * 60)
        extractor.get_top_strategies(limit=10)
        print()

    # Show statistics
    extractor.print_statistics()

    print("\n✅ Extraction pipeline complete!")
    print(f"📊 {total_saved} strategies ready for LLM training")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
