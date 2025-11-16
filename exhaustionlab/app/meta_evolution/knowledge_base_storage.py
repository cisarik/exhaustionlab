"""
Knowledge Base Storage System

Manages storage and retrieval of strategy knowledge.
Uses JSON files for simplicity and portability.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class KnowledgeBaseStorage:
    """
    File-based storage for strategy knowledge.

    Storage structure:
    .cache/
      strategy_examples/
        github/
          strategy_001.json
          strategy_002.json
        reddit/
          discussion_001.json
        tradingview/
          script_001.json
        index.json  # Searchable index
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize storage.

        Args:
            base_path: Base directory for storage (default: .cache/strategy_examples)
        """
        if base_path is None:
            base_path = Path.home() / "ExhaustionLab" / ".cache" / "strategy_examples"

        self.base_path = Path(base_path)
        self.index_path = self.base_path / "index.json"

        # Create directory structure
        self._init_storage()

    def _init_storage(self):
        """Initialize storage directories."""
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Create platform subdirectories
        for platform in ["github", "reddit", "tradingview"]:
            (self.base_path / platform).mkdir(exist_ok=True)

        # Create index if doesn't exist
        if not self.index_path.exists():
            self._save_index(
                {"strategies": [], "last_updated": datetime.now().isoformat()}
            )

    def save_strategy(self, strategy: Dict[str, Any]) -> str:
        """
        Save strategy to storage.

        Args:
            strategy: Strategy metadata and code

        Returns:
            Strategy ID
        """
        # Generate ID if not present
        if "id" not in strategy:
            strategy["id"] = self._generate_id(strategy)

        # Add metadata
        strategy["saved_at"] = datetime.now().isoformat()

        # Determine storage path
        platform = strategy.get("platform", "unknown")
        platform_dir = self.base_path / platform
        file_path = platform_dir / f"{strategy['id']}.json"

        # Save to file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(strategy, f, indent=2, ensure_ascii=False)

            # Update index
            self._update_index(strategy)

            logger.info(f"Saved strategy: {strategy['id']}")
            return strategy["id"]

        except Exception as e:
            logger.error(f"Failed to save strategy: {e}")
            raise

    def save_batch(self, strategies: List[Dict[str, Any]]) -> List[str]:
        """
        Save multiple strategies.

        Args:
            strategies: List of strategy dictionaries

        Returns:
            List of strategy IDs
        """
        ids = []
        for strategy in strategies:
            try:
                strategy_id = self.save_strategy(strategy)
                ids.append(strategy_id)
            except Exception as e:
                logger.error(f"Failed to save strategy: {e}")
                continue

        logger.info(f"Saved {len(ids)}/{len(strategies)} strategies")
        return ids

    def load_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """
        Load strategy by ID.

        Args:
            strategy_id: Strategy ID

        Returns:
            Strategy dictionary or None
        """
        # Search in all platform directories
        for platform in ["github", "reddit", "tradingview"]:
            file_path = self.base_path / platform / f"{strategy_id}.json"
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load strategy {strategy_id}: {e}")
                    return None

        return None

    def search(
        self,
        platform: Optional[str] = None,
        min_quality_score: Optional[float] = None,
        has_code: Optional[bool] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search strategies by criteria.

        Args:
            platform: Filter by platform
            min_quality_score: Minimum quality score
            has_code: Filter by code availability
            limit: Maximum results

        Returns:
            List of matching strategies
        """
        index = self._load_index()
        results = []

        for entry in index.get("strategies", []):
            # Apply filters
            if platform and entry.get("platform") != platform:
                continue

            if min_quality_score and entry.get("quality_score", 0) < min_quality_score:
                continue

            if has_code is not None:
                entry_has_code = bool(entry.get("has_code", False))
                if entry_has_code != has_code:
                    continue

            results.append(entry)

            if limit and len(results) >= limit:
                break

        return results

    def get_top_quality(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top quality strategies.

        Args:
            limit: Number of strategies to return

        Returns:
            List of top strategies sorted by quality score
        """
        index = self._load_index()
        strategies = index.get("strategies", [])

        # Sort by quality score
        strategies.sort(key=lambda x: x.get("quality_score", 0), reverse=True)

        return strategies[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored strategies."""
        index = self._load_index()
        strategies = index.get("strategies", [])

        if not strategies:
            return {
                "total": 0,
                "by_platform": {},
                "avg_quality_score": 0,
                "with_code": 0,
            }

        # Calculate statistics
        by_platform = {}
        total_quality = 0
        with_code = 0

        for strategy in strategies:
            platform = strategy.get("platform", "unknown")
            by_platform[platform] = by_platform.get(platform, 0) + 1

            total_quality += strategy.get("quality_score", 0)

            if strategy.get("has_code", False):
                with_code += 1

        return {
            "total": len(strategies),
            "by_platform": by_platform,
            "avg_quality_score": total_quality / len(strategies),
            "with_code": with_code,
            "last_updated": index.get("last_updated", "unknown"),
        }

    def _generate_id(self, strategy: Dict[str, Any]) -> str:
        """Generate unique ID for strategy."""
        import hashlib

        # Create ID from platform + name/title + author
        platform = strategy.get("platform", "unknown")
        name = strategy.get("name", strategy.get("title", "unnamed"))
        author = strategy.get("author", "unknown")

        # Hash to create unique ID
        id_string = f"{platform}_{name}_{author}"
        hash_obj = hashlib.md5(id_string.encode())

        return hash_obj.hexdigest()[:16]

    def _update_index(self, strategy: Dict[str, Any]):
        """Update searchable index."""
        index = self._load_index()

        # Create index entry
        entry = {
            "id": strategy["id"],
            "platform": strategy.get("platform"),
            "name": strategy.get("name", strategy.get("title")),
            "author": strategy.get("author"),
            "quality_score": strategy.get("quality_score", 0),
            "has_code": bool(strategy.get("code")),
            "saved_at": strategy.get("saved_at"),
        }

        # Check if already in index
        strategies = index.get("strategies", [])
        existing_idx = None
        for idx, s in enumerate(strategies):
            if s["id"] == entry["id"]:
                existing_idx = idx
                break

        if existing_idx is not None:
            # Update existing
            strategies[existing_idx] = entry
        else:
            # Add new
            strategies.append(entry)

        # Update index
        index["strategies"] = strategies
        index["last_updated"] = datetime.now().isoformat()

        self._save_index(index)

    def _load_index(self) -> Dict[str, Any]:
        """Load index from file."""
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"strategies": [], "last_updated": datetime.now().isoformat()}

    def _save_index(self, index: Dict[str, Any]):
        """Save index to file."""
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
