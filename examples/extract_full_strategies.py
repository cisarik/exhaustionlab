#!/usr/bin/env python3
"""
Full Strategy Extraction Pipeline with Database

Extracts COMPLETE strategy profiles including:
- Source code (Pine Script, Python)
- Documentation (README, descriptions)
- Metadata (author, dates, parameters)
- Performance metrics
- Quality scores

Stores everything in SQLite database.
"""

import argparse
import logging
import os
import sys
from typing import Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Add to path
sys.path.insert(0, os.path.dirname(__file__))

# Import modules
from exhaustionlab.app.meta_evolution.crawlers.code_extractor import GitHubCodeExtractor
from exhaustionlab.app.meta_evolution.crawlers.github_crawler import GitHubStrategyCrawler
from exhaustionlab.app.meta_evolution.quality_scorer import StrategyQualityScorer
from exhaustionlab.app.meta_evolution.strategy_database import StrategyDatabase


class FullStrategyExtractor:
    """
    Complete strategy extraction pipeline.

    Extracts:
    1. Repository metadata from GitHub
    2. All source code files
    3. Documentation (README, etc.)
    4. Parameters and configuration
    5. Quality assessment
    6. Stores in SQLite database
    """

    def __init__(self):
        """Initialize extractors."""
        self.crawler = GitHubStrategyCrawler()
        self.code_extractor = GitHubCodeExtractor()
        self.scorer = StrategyQualityScorer()
        self.database = StrategyDatabase()

        logger.info("Initialized full extraction pipeline")

    def extract_and_store(self, repo_full_name: str) -> bool:
        """
        Extract full strategy and store in database.

        Args:
            repo_full_name: Repository name "owner/repo"

        Returns:
            True if successful
        """
        try:
            logger.info(f"📦 Extracting: {repo_full_name}")

            # Extract full profile
            strategy = self.code_extractor.extract_full_strategy(repo_full_name)

            # Add platform
            strategy["platform"] = "github"

            # Calculate quality score
            quality = self.scorer.calculate_quality_score(strategy)
            strategy["quality_score"] = quality
            strategy["quality_category"] = self.scorer.get_quality_category(quality)

            # Save to database
            saved = self.database.save_strategy(strategy)

            logger.info(f"✅ Saved: {saved.name} (score: {quality:.1f})")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to extract {repo_full_name}: {e}")
            return False

    def extract_batch(self, repo_list: List[str]) -> Dict[str, int]:
        """
        Extract multiple repositories.

        Args:
            repo_list: List of repository names

        Returns:
            Statistics dictionary
        """
        stats = {"total": len(repo_list), "success": 0, "failed": 0, "with_code": 0}

        for idx, repo in enumerate(repo_list, 1):
            logger.info(f"\n[{idx}/{stats['total']}] Processing: {repo}")

            success = self.extract_and_store(repo)

            if success:
                stats["success"] += 1
            else:
                stats["failed"] += 1

        # Count strategies with code
        stats["with_code"] = self.database.get_statistics()["with_code"]

        return stats

    def find_and_extract_top_repos(self, limit: int = 20) -> Dict[str, int]:
        """
        Find top GitHub repos and extract them.

        Args:
            limit: Number of repositories to extract

        Returns:
            Statistics dictionary
        """
        logger.info(f"🔍 Finding top {limit} Pine Script repositories...")

        # Search for top repos
        repos = self.crawler.search_strategies(query="pinescript", min_stars=10, max_results=limit)

        logger.info(f"Found {len(repos)} repositories")

        # Extract full names
        repo_names = [r["full_name"] for r in repos]

        # Extract all
        return self.extract_batch(repo_names)

    def show_statistics(self):
        """Display database statistics."""
        stats = self.database.get_statistics()

        print("\n" + "=" * 70)
        print("📊 DATABASE STATISTICS")
        print("=" * 70)
        print(f"Total Strategies: {stats['total']}")
        print(f"With Code: {stats['with_code']}")
        print(f"Average Quality: {stats['avg_quality_score']:.1f}/100")

        print("\nBy Platform:")
        for platform, count in stats.get("by_platform", {}).items():
            print(f"  • {platform.title()}: {count}")

        print("\nBy Category:")
        for category, count in stats.get("by_category", {}).items():
            if category:
                print(f"  • {category.title()}: {count}")

        print("=" * 70)

    def show_top_strategies(self, limit: int = 10):
        """Display top quality strategies."""
        strategies = self.database.get_top_quality(limit=limit)

        print("\n" + "=" * 70)
        print(f"🏆 TOP {limit} QUALITY STRATEGIES")
        print("=" * 70)

        for idx, strategy in enumerate(strategies, 1):
            print(f"\n{idx}. {strategy.name}")
            print(f"   Author: {strategy.author}")
            print(f"   Platform: {strategy.platform}")
            print(f"   Quality: {strategy.quality_score:.1f} ({strategy.quality_category})")
            print(f"   Stars: {strategy.stars or 0}")
            if strategy.has_code:
                print(f"   Code: ✅ {strategy.lines_of_code or '?'} LOC")
            if strategy.indicators_used:
                indicators = strategy.indicators_used[:5]  # First 5
                print(f"   Indicators: {', '.join(indicators)}")
            if strategy.url:
                print(f"   URL: {strategy.url}")

        print("=" * 70)

    def show_with_code(self, limit: int = 10):
        """Display strategies that have code."""
        strategies = self.database.get_with_code(limit=limit)

        print("\n" + "=" * 70)
        print(f"💻 STRATEGIES WITH CODE (showing {limit})")
        print("=" * 70)

        for idx, strategy in enumerate(strategies, 1):
            print(f"\n{idx}. {strategy.name}")
            print(f"   Quality: {strategy.quality_score:.1f}")

            if strategy.pine_code:
                lines = len(strategy.pine_code.split("\n"))
                print(f"   Pine Script: {lines} lines")

            if strategy.python_code:
                lines = len(strategy.python_code.split("\n"))
                print(f"   Python: {lines} lines")

            if strategy.readme:
                print("   README: ✅")

        print("=" * 70)


def main():
    """Main extraction flow."""
    parser = argparse.ArgumentParser(description="Extract complete strategy profiles to database")
    parser.add_argument(
        "--repos",
        nargs="+",
        help="Specific repositories to extract (owner/repo format)",
    )
    parser.add_argument("--top", type=int, help="Extract top N repositories from GitHub")
    parser.add_argument("--quick", action="store_true", help="Quick extraction (10 repos)")
    parser.add_argument("--full", action="store_true", help="Full extraction (50 repos)")
    parser.add_argument("--stats", action="store_true", help="Show statistics only")
    parser.add_argument("--show-top", type=int, metavar="N", help="Show top N strategies")
    parser.add_argument("--show-code", type=int, metavar="N", help="Show N strategies with code")

    args = parser.parse_args()

    # Initialize extractor
    extractor = FullStrategyExtractor()

    # Show stats only
    if args.stats:
        extractor.show_statistics()
        return 0

    # Show top strategies
    if args.show_top:
        extractor.show_top_strategies(limit=args.show_top)
        return 0

    # Show strategies with code
    if args.show_code:
        extractor.show_with_code(limit=args.show_code)
        return 0

    # Determine what to extract
    if args.repos:
        # Extract specific repos
        repos_to_extract = args.repos
    elif args.top:
        # Extract top N
        stats = extractor.find_and_extract_top_repos(limit=args.top)
        extractor.show_statistics()
        extractor.show_top_strategies(limit=10)
        return 0
    elif args.quick:
        # Quick extraction
        stats = extractor.find_and_extract_top_repos(limit=10)
        extractor.show_statistics()
        return 0
    elif args.full:
        # Full extraction
        stats = extractor.find_and_extract_top_repos(limit=50)
        extractor.show_statistics()
        extractor.show_top_strategies(limit=20)
        return 0
    else:
        parser.print_help()
        return 1

    # Extract specific repos
    print("\n" + "=" * 70)
    print("🚀 FULL STRATEGY EXTRACTION")
    print("=" * 70)
    print(f"Extracting {len(repos_to_extract)} repositories...")
    print()

    stats = extractor.extract_batch(repos_to_extract)

    print("\n" + "=" * 70)
    print("📊 EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Total: {stats['total']}")
    print(f"Success: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print()

    extractor.show_statistics()
    extractor.show_top_strategies(limit=5)

    return 0


if __name__ == "__main__":
    sys.exit(main())
