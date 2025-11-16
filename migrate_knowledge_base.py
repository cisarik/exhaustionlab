#!/usr/bin/env python3
"""
Migrate existing knowledge base to SQLite database.

We already have 70 strategies extracted to JSON files.
This script migrates them to the new SQLite database.
"""

import sys
import os
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from exhaustionlab.app.meta_evolution.knowledge_base_storage import KnowledgeBaseStorage
from exhaustionlab.app.meta_evolution.strategy_database import StrategyDatabase
from exhaustionlab.app.meta_evolution.quality_scorer import StrategyQualityScorer


def migrate():
    """Migrate knowledge base to database."""

    # Initialize
    kb = KnowledgeBaseStorage()
    db = StrategyDatabase()
    scorer = StrategyQualityScorer()

    logger.info("Loading strategies from knowledge base...")

    # Get all strategies
    all_strategies = []

    # Load from GitHub
    github_dir = kb.base_path / "github"
    if github_dir.exists():
        for strategy_file in github_dir.glob("*.json"):
            strategy = kb.load_strategy(strategy_file.stem)
            if strategy:
                all_strategies.append(strategy)

    # Load from TradingView
    tv_dir = kb.base_path / "tradingview"
    if tv_dir.exists():
        for strategy_file in tv_dir.glob("*.json"):
            strategy = kb.load_strategy(strategy_file.stem)
            if strategy:
                all_strategies.append(strategy)

    logger.info(f"Found {len(all_strategies)} strategies in knowledge base")

    # Migrate each strategy
    migrated = 0
    skipped = 0

    for idx, strategy in enumerate(all_strategies, 1):
        try:
            logger.info(
                f"[{idx}/{len(all_strategies)}] Migrating: {strategy.get('name', 'Unknown')}"
            )

            # Prepare for database
            db_strategy = {
                "name": strategy.get("name"),
                "platform": strategy.get("platform", "github"),
                "url": strategy.get("url"),
                "repo_full_name": strategy.get("full_name"),
                "description": strategy.get("description"),
                "stars": strategy.get("stars", 0),
                "forks": strategy.get("forks", 0),
                "watchers": strategy.get("watchers", 0),
                "quality_score": strategy.get("quality_score", 0),
                "quality_category": scorer.get_quality_category(
                    strategy.get("quality_score", 0)
                ),
                "has_code": False,  # Will update if we find code
                "has_documentation": False,
                "tags": strategy.get("topics", []) if strategy.get("topics") else [],
            }

            # Save to database
            saved = db.save_strategy(db_strategy)
            migrated += 1

            logger.info(
                f"  ✅ Migrated: {saved.name} (score: {saved.quality_score:.1f})"
            )

        except Exception as e:
            logger.error(f"  ❌ Failed to migrate: {e}")
            skipped += 1
            continue

    logger.info(f"\n{'='*70}")
    logger.info(f"MIGRATION COMPLETE")
    logger.info(f"{'='*70}")
    logger.info(f"Total: {len(all_strategies)}")
    logger.info(f"Migrated: {migrated}")
    logger.info(f"Skipped: {skipped}")
    logger.info(f"{'='*70}")

    # Show statistics
    stats = db.get_statistics()
    logger.info(f"\nDatabase now has {stats['total']} strategies")
    logger.info(f"Average quality: {stats['avg_quality_score']:.1f}/100")

    # Show top 10
    logger.info(f"\n{'='*70}")
    logger.info(f"TOP 10 STRATEGIES")
    logger.info(f"{'='*70}")

    top = db.get_top_quality(limit=10)
    for idx, s in enumerate(top, 1):
        logger.info(
            f"{idx}. {s.name} - {s.quality_score:.1f} ({s.quality_category}) - ⭐ {s.stars}"
        )

    logger.info(f"{'='*70}")


if __name__ == "__main__":
    migrate()
