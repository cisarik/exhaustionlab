"""
Strategy Database - SQLite Backend

Stores complete strategy profiles including:
- Code (Pine Script, Python, etc.)
- Metadata (name, author, description, README)
- Performance metrics
- Source information
- Quality scores
- Parameters and configuration
"""

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    Boolean,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)

Base = declarative_base()


class Strategy(Base):
    """
    Complete strategy profile.

    Stores everything we know about a strategy:
    - Source code (Pine Script, Python, etc.)
    - Documentation (README, description, comments)
    - Metadata (author, dates, repo info)
    - Metrics (performance, quality, community)
    """

    __tablename__ = "strategies"

    # Primary key
    id = Column(String(32), primary_key=True)

    # Basic info
    name = Column(String(255), nullable=False, index=True)
    title = Column(String(255))
    author = Column(String(255), index=True)
    platform = Column(
        String(50), nullable=False, index=True
    )  # github, reddit, tradingview

    # Source information
    url = Column(String(500), unique=True)
    repo_full_name = Column(String(255))  # e.g., "user/repo" for GitHub

    # Code
    pine_code = Column(Text)  # Pine Script source
    python_code = Column(Text)  # Python implementation if available
    code_language = Column(String(50))  # "pinescript", "python", "javascript"
    pine_version = Column(Integer)  # Pine Script version if known

    # Documentation
    description = Column(Text)  # Short description
    readme = Column(Text)  # Full README content
    documentation = Column(Text)  # Additional docs
    comments = Column(Text)  # Code comments extracted

    # Parameters & Configuration
    parameters = Column(JSON)  # Strategy parameters as JSON
    config = Column(JSON)  # Configuration options

    # Indicators & Features
    indicators_used = Column(JSON)  # List of indicators: ["RSI", "MACD", ...]
    features = Column(JSON)  # Features: {"stop_loss": true, "take_profit": true}
    timeframes = Column(JSON)  # Supported timeframes: ["1m", "5m", "1h"]

    # Performance Metrics (if available)
    backtest_metrics = Column(JSON)  # Full backtest results
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    profit_factor = Column(Float)
    total_trades = Column(Integer)

    # Community Metrics
    stars = Column(Integer, default=0, index=True)
    forks = Column(Integer, default=0)
    watchers = Column(Integer, default=0)
    upvotes = Column(Integer, default=0)  # Reddit/TradingView
    comments_count = Column(Integer, default=0)
    uses = Column(Integer, default=0)  # TradingView uses

    # Quality Assessment
    quality_score = Column(Float, default=0.0, index=True)
    quality_category = Column(String(50))  # "Excellent", "Good", "Average", etc.
    has_code = Column(Boolean, default=False, index=True)
    has_documentation = Column(Boolean, default=False)
    has_tests = Column(Boolean, default=False)

    # Code Quality Metrics
    lines_of_code = Column(Integer)
    complexity_score = Column(Float)

    # Dates
    created_at = Column(DateTime)  # When strategy was created (on platform)
    updated_at = Column(DateTime)  # Last update on platform
    extracted_at = Column(
        DateTime, default=datetime.now, index=True
    )  # When we extracted it

    # Tags & Categories
    tags = Column(JSON)  # ["momentum", "trend_following", "crypto"]
    category = Column(String(100), index=True)  # "momentum", "mean_reversion", etc.
    market_focus = Column(JSON)  # ["crypto", "forex", "stocks"]

    # Extraction metadata
    extraction_source = Column(String(100))  # "github_api", "reddit_scrape", etc.
    extraction_status = Column(String(50))  # "complete", "partial", "failed"
    extraction_notes = Column(Text)  # Any issues during extraction

    def __repr__(self):
        return f"<Strategy(id={self.id}, name={self.name}, platform={self.platform}, score={self.quality_score})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "author": self.author,
            "platform": self.platform,
            "url": self.url,
            "description": self.description,
            "has_code": self.has_code,
            "quality_score": self.quality_score,
            "quality_category": self.quality_category,
            "stars": self.stars,
            "forks": self.forks,
            "indicators_used": self.indicators_used,
            "category": self.category,
            "extracted_at": (
                self.extracted_at.isoformat() if self.extracted_at else None
            ),
        }


class StrategyDatabase:
    """
    Database manager for strategy storage and retrieval.

    Uses SQLite for local storage with full SQL capabilities.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize database.

        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            db_path = Path.home() / "ExhaustionLab" / ".cache" / "strategies.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)

        # Create tables
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)

        logger.info(f"Database initialized: {self.db_path}")

    def get_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()

    def save_strategy(self, strategy_data: Dict[str, Any]) -> Strategy:
        """
        Save or update strategy.

        Args:
            strategy_data: Strategy information dictionary

        Returns:
            Saved Strategy object
        """
        session = self.get_session()

        try:
            # Serialize lists to JSON strings for SQLite compatibility
            if "extraction_notes" in strategy_data and isinstance(
                strategy_data["extraction_notes"], list
            ):
                strategy_data["extraction_notes"] = json.dumps(
                    strategy_data["extraction_notes"]
                )

            # Check if exists
            strategy_id = strategy_data.get("id")
            if strategy_id:
                strategy = session.query(Strategy).filter_by(id=strategy_id).first()
                if strategy:
                    # Update existing
                    for key, value in strategy_data.items():
                        if hasattr(strategy, key):
                            setattr(strategy, key, value)
                    logger.info(f"Updated strategy: {strategy_id}")
                else:
                    # Create new
                    strategy = Strategy(**strategy_data)
                    session.add(strategy)
                    logger.info(f"Created strategy: {strategy_id}")
            else:
                # Generate ID and create
                import hashlib

                id_string = f"{strategy_data.get('platform')}_{strategy_data.get('name')}_{strategy_data.get('author')}"
                strategy_data["id"] = hashlib.md5(id_string.encode()).hexdigest()[:16]

                strategy = Strategy(**strategy_data)
                session.add(strategy)
                logger.info(f"Created strategy: {strategy_data['id']}")

            session.commit()
            session.refresh(strategy)

            return strategy

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save strategy: {e}")
            raise
        finally:
            session.close()

    def save_batch(self, strategies: List[Dict[str, Any]]) -> int:
        """Save multiple strategies."""
        saved = 0
        for strategy_data in strategies:
            try:
                self.save_strategy(strategy_data)
                saved += 1
            except Exception as e:
                logger.error(f"Failed to save strategy: {e}")
                continue

        return saved

    def get_strategy(self, strategy_id: str) -> Optional[Strategy]:
        """Get strategy by ID."""
        session = self.get_session()
        try:
            return session.query(Strategy).filter_by(id=strategy_id).first()
        finally:
            session.close()

    def search(
        self,
        platform: Optional[str] = None,
        category: Optional[str] = None,
        min_quality_score: Optional[float] = None,
        has_code: Optional[bool] = None,
        min_stars: Optional[int] = None,
        indicators: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Strategy]:
        """
        Search strategies with filters.

        Args:
            platform: Filter by platform
            category: Filter by category
            min_quality_score: Minimum quality score
            has_code: Filter by code availability
            min_stars: Minimum stars/upvotes
            indicators: Filter by indicators used
            limit: Maximum results

        Returns:
            List of matching strategies
        """
        session = self.get_session()

        try:
            query = session.query(Strategy)

            # Apply filters
            if platform:
                query = query.filter(Strategy.platform == platform)

            if category:
                query = query.filter(Strategy.category == category)

            if min_quality_score is not None:
                query = query.filter(Strategy.quality_score >= min_quality_score)

            if has_code is not None:
                query = query.filter(Strategy.has_code == has_code)

            if min_stars is not None:
                query = query.filter(Strategy.stars >= min_stars)

            # Order by quality score
            query = query.order_by(Strategy.quality_score.desc())

            # Limit
            query = query.limit(limit)

            return query.all()

        finally:
            session.close()

    def get_top_quality(self, limit: int = 10) -> List[Strategy]:
        """Get top quality strategies."""
        return self.search(min_quality_score=0, limit=limit)

    def get_with_code(self, limit: int = 100) -> List[Strategy]:
        """Get strategies that have code."""
        return self.search(has_code=True, limit=limit)

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        session = self.get_session()

        try:
            total = session.query(Strategy).count()

            if total == 0:
                return {
                    "total": 0,
                    "with_code": 0,
                    "avg_quality_score": 0,
                    "by_platform": {},
                    "by_category": {},
                }

            with_code = (
                session.query(Strategy).filter(Strategy.has_code == True).count()
            )

            # Average quality
            from sqlalchemy import func

            avg_quality = session.query(func.avg(Strategy.quality_score)).scalar() or 0

            # By platform
            from sqlalchemy import func

            by_platform = dict(
                session.query(Strategy.platform, func.count(Strategy.id))
                .group_by(Strategy.platform)
                .all()
            )

            # By category
            by_category = dict(
                session.query(Strategy.category, func.count(Strategy.id))
                .filter(Strategy.category != None)
                .group_by(Strategy.category)
                .all()
            )

            return {
                "total": total,
                "with_code": with_code,
                "avg_quality_score": round(avg_quality, 2),
                "by_platform": by_platform,
                "by_category": by_category,
            }

        finally:
            session.close()

    def delete_strategy(self, strategy_id: str):
        """Delete strategy by ID."""
        session = self.get_session()
        try:
            strategy = session.query(Strategy).filter_by(id=strategy_id).first()
            if strategy:
                session.delete(strategy)
                session.commit()
                logger.info(f"Deleted strategy: {strategy_id}")
        finally:
            session.close()

    def clear_all(self):
        """Clear all strategies (use with caution!)."""
        session = self.get_session()
        try:
            session.query(Strategy).delete()
            session.commit()
            logger.warning("Cleared all strategies from database")
        finally:
            session.close()
