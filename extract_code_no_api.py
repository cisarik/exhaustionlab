#!/usr/bin/env python3
"""
Extract Pine Script Code WITHOUT GitHub API

Uses direct GitHub raw URLs to bypass rate limits:
https://raw.githubusercontent.com/owner/repo/master/file.pine

Also searches common file patterns:
- *.pine
- *.txt (some repos use .txt for Pine Script)
- strategy.pine, indicator.pine, etc.
"""

import sys
import os
import requests
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(__file__))

from exhaustionlab.app.meta_evolution.strategy_database import StrategyDatabase
from exhaustionlab.app.meta_evolution.crawlers.code_extractor import GitHubCodeExtractor


class DirectCodeExtractor:
    """
    Extract code directly from GitHub without API.

    Bypasses rate limits by:
    1. Using raw.githubusercontent.com URLs
    2. Scraping repository file listings
    3. Smart filename guessing
    """

    def __init__(self):
        """Initialize extractor."""
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        self.extractor = GitHubCodeExtractor()

    def extract_pine_files(self, repo_full_name: str) -> List[Dict[str, str]]:
        """
        Find Pine Script files by scraping repository.

        Args:
            repo_full_name: Repository "owner/repo"

        Returns:
            List of {filename, url, content} dicts
        """
        owner, repo = repo_full_name.split("/")

        logger.info(f"🔍 Searching for Pine files in: {repo_full_name}")

        files = []

        # Common branches
        branches = ["master", "main", "develop"]

        # Common Pine Script filenames
        common_names = [
            "strategy.pine",
            "indicator.pine",
            "script.pine",
            "main.pine",
            "index.pine",
        ]

        # Try common filenames first
        for branch in branches:
            for filename in common_names:
                url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
                content = self._fetch_raw(url)

                if content and self._is_pinescript(content):
                    files.append(
                        {
                            "filename": filename,
                            "url": url,
                            "content": content,
                            "branch": branch,
                        }
                    )
                    logger.info(f"  ✅ Found: {filename}")

        # Try scraping repository file tree
        if not files:
            files.extend(self._scrape_repo_files(repo_full_name))

        return files

    def _fetch_raw(self, url: str) -> Optional[str]:
        """Fetch raw file content."""
        try:
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                return response.text

            return None

        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None

    def _is_pinescript(self, content: str) -> bool:
        """Check if content is Pine Script."""
        # Look for Pine Script signatures
        signatures = [
            "//@version",
            "indicator(",
            "strategy(",
            "ta.rsi",
            "ta.ema",
            "ta.sma",
            "plot(",
            "plotshape(",
        ]

        content_lower = content.lower()

        # Must have version declaration or at least 2 signatures
        has_version = "//@version" in content
        signature_count = sum(1 for sig in signatures if sig.lower() in content_lower)

        return has_version or signature_count >= 2

    def _scrape_repo_files(self, repo_full_name: str) -> List[Dict[str, str]]:
        """
        Scrape repository main page for Pine files.

        Uses GitHub's HTML interface to find files.
        """
        owner, repo = repo_full_name.split("/")

        # Try to get file listing from GitHub
        url = f"https://github.com/{owner}/{repo}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            html = response.text

            # Find .pine files in HTML
            # Pattern: href="/owner/repo/blob/branch/path/file.pine"
            pattern = (
                r'href="/'
                + re.escape(owner)
                + r"/"
                + re.escape(repo)
                + r'/blob/([^/]+)/([^"]+\.(?:pine|txt))"'
            )

            matches = re.findall(pattern, html)

            files = []

            for branch, filepath in matches[:10]:  # Limit to 10 files
                # Convert to raw URL
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filepath}"

                content = self._fetch_raw(raw_url)

                if content and self._is_pinescript(content):
                    filename = filepath.split("/")[-1]
                    files.append(
                        {
                            "filename": filename,
                            "url": raw_url,
                            "content": content,
                            "branch": branch,
                            "path": filepath,
                        }
                    )
                    logger.info(f"  ✅ Found: {filename}")

                time.sleep(0.5)  # Rate limiting

            return files

        except Exception as e:
            logger.debug(f"Failed to scrape repo: {e}")
            return []

    def update_strategy_with_code(self, strategy_id: str, db: StrategyDatabase) -> bool:
        """
        Extract code for strategy and update database.

        Args:
            strategy_id: Strategy ID
            db: Database instance

        Returns:
            True if code found and saved
        """
        session = db.get_session()

        try:
            # Get strategy from database using Strategy model
            from exhaustionlab.app.meta_evolution.strategy_database import Strategy

            strategy = session.query(Strategy).filter_by(id=strategy_id).first()

            if not strategy:
                logger.error(f"Strategy not found: {strategy_id}")
                return False

            if not strategy.repo_full_name:
                logger.warning(f"No repo name for: {strategy.name}")
                return False

            logger.info(f"📦 Extracting code for: {strategy.name}")

            # Extract Pine files
            pine_files = self.extract_pine_files(strategy.repo_full_name)

            if not pine_files:
                logger.warning(f"  ⚠️ No Pine files found")
                return False

            # Use first file as main code
            main_file = pine_files[0]
            code = main_file["content"]

            # Parse code metadata
            code_meta = self.extractor._parse_pine_code(code)

            # Update strategy object
            strategy.pine_code = code
            strategy.has_code = True
            strategy.code_language = "pinescript"

            # Update metadata from code
            if code_meta.get("title"):
                strategy.title = code_meta["title"]

            if code_meta.get("indicators_used"):
                strategy.indicators_used = code_meta["indicators_used"]

            if code_meta.get("parameters"):
                strategy.parameters = code_meta["parameters"]

            if code_meta.get("lines_of_code"):
                strategy.lines_of_code = code_meta["lines_of_code"]

            if code_meta.get("complexity_score"):
                strategy.complexity_score = code_meta["complexity_score"]

            # Commit changes
            session.commit()

            logger.info(
                f"  ✅ Saved code: {len(code)} chars, {strategy.lines_of_code} LOC"
            )

            return True

        except Exception as e:
            session.rollback()
            logger.error(f"  ❌ Failed to save: {e}")
            import traceback

            traceback.print_exc()
            return False

        finally:
            session.close()


def main():
    """Extract code for all strategies in database."""

    logger.info("=" * 70)
    logger.info("🚀 DIRECT CODE EXTRACTION (No API)")
    logger.info("=" * 70)

    # Initialize
    db = StrategyDatabase()
    extractor = DirectCodeExtractor()

    # Get strategies without code
    all_strategies = db.search(platform="github", has_code=False, limit=100)

    logger.info(f"Found {len(all_strategies)} GitHub strategies without code")

    if not all_strategies:
        logger.info("✅ All strategies already have code!")
        return 0

    # Extract code for each
    stats = {"total": len(all_strategies), "success": 0, "failed": 0}

    for idx, strategy in enumerate(all_strategies, 1):
        logger.info(f"\n[{idx}/{stats['total']}] {strategy.name}")

        success = extractor.update_strategy_with_code(strategy.id, db)

        if success:
            stats["success"] += 1
        else:
            stats["failed"] += 1

        # Rate limiting
        time.sleep(1)

    # Results
    logger.info("\n" + "=" * 70)
    logger.info("📊 EXTRACTION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total: {stats['total']}")
    logger.info(f"Success: {stats['success']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Success Rate: {stats['success']/stats['total']*100:.1f}%")
    logger.info("=" * 70)

    # Show updated statistics
    db_stats = db.get_statistics()
    logger.info(f"\nDatabase now has {db_stats['with_code']} strategies with code")

    # Show some examples
    logger.info("\n" + "=" * 70)
    logger.info("💻 STRATEGIES WITH CODE (Top 10)")
    logger.info("=" * 70)

    with_code = db.get_with_code(limit=10)

    for idx, s in enumerate(with_code, 1):
        logger.info(f"\n{idx}. {s.name}")
        logger.info(f"   Quality: {s.quality_score:.1f}")
        logger.info(f"   LOC: {s.lines_of_code or '?'}")
        if s.indicators_used:
            logger.info(f"   Indicators: {', '.join(s.indicators_used[:5])}")

    logger.info("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
