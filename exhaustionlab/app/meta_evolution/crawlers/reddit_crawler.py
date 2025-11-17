"""
Reddit Strategy Crawler

Extracts trading strategy discussions from Reddit.
Target subreddits: r/algotrading, r/TradingView, r/CryptoCurrency
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

import praw

logger = logging.getLogger(__name__)


class RedditStrategyCrawler:
    """
    Crawl Reddit for trading strategy discussions.

    Target subreddits:
    - r/algotrading
    - r/TradingView
    - r/CryptoCurrency
    - r/Daytrading
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: str = "ExhaustionLab-Research/1.0",
    ):
        """
        Initialize Reddit crawler.

        Args:
            client_id: Reddit API client ID
            client_secret: Reddit API client secret
            user_agent: User agent string

        Note: If credentials not provided, will use read-only mode
        """
        try:
            if client_id and client_secret:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent,
                )
            else:
                # Read-only mode (limited but no authentication needed)
                self.reddit = praw.Reddit(
                    client_id="_",  # Dummy values for read-only
                    client_secret="_",
                    user_agent=user_agent,
                    check_for_async=False,
                )

            self.target_subreddits = [
                "algotrading",
                "TradingView",
                "CryptoCurrency",
                "Daytrading",
                "algorithmictrading",
            ]
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            self.reddit = None

    def search_strategies(
        self,
        query: str = "strategy pinescript",
        min_upvotes: int = 10,
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search Reddit for strategy discussions.

        Args:
            query: Search query
            min_upvotes: Minimum upvotes to filter quality
            max_results: Maximum results to return

        Returns:
            List of post metadata
        """
        if not self.reddit:
            logger.error("Reddit client not initialized")
            return []

        logger.info(f"Searching Reddit for: {query}")

        results = []

        for subreddit_name in self.target_subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)

                # Search posts
                posts = subreddit.search(query, sort="relevance", time_filter="all", limit=max_results)

                for post in posts:
                    if post.score >= min_upvotes:
                        post_info = self._extract_post_info(post)
                        if post_info:
                            results.append(post_info)

                    if len(results) >= max_results:
                        break

                # Respectful rate limiting
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error searching r/{subreddit_name}: {e}")
                continue

        logger.info(f"Found {len(results)} relevant posts")
        return results

    def extract_code_from_post(self, post_id: str) -> Optional[str]:
        """
        Extract strategy code from Reddit post.

        Args:
            post_id: Reddit post ID

        Returns:
            Extracted code if found
        """
        if not self.reddit:
            return None

        try:
            submission = self.reddit.submission(id=post_id)

            # Check post body
            code = self._extract_code_blocks(submission.selftext)
            if code:
                return code

            # Check comments for code
            submission.comments.replace_more(limit=5)
            for comment in submission.comments.list():
                code = self._extract_code_blocks(comment.body)
                if code:
                    return code

            return None

        except Exception as e:
            logger.error(f"Error extracting code from post: {e}")
            return None

    def _extract_post_info(self, post) -> Optional[Dict[str, Any]]:
        """Extract relevant information from Reddit post."""
        try:
            return {
                "platform": "reddit",
                "url": f"https://reddit.com{post.permalink}",
                "id": post.id,
                "title": post.title,
                "author": str(post.author) if post.author else "[deleted]",
                "subreddit": str(post.subreddit),
                "description": (post.selftext[:500] if post.selftext else ""),  # First 500 chars
                "upvotes": post.score,
                "upvote_ratio": post.upvote_ratio,
                "comments": post.num_comments,
                "created_date": post.created_utc,
                "has_code": bool(re.search(r"```|//@version|study\(|strategy\(", post.selftext or "")),
            }
        except Exception as e:
            logger.warning(f"Error extracting post info: {e}")
            return None

    def _extract_code_blocks(self, text: str) -> Optional[str]:
        """Extract code blocks from markdown text."""
        if not text:
            return None

        # Look for code blocks (```...```)
        code_block_pattern = r"```(?:pine|python)?\n(.*?)```"
        matches = re.findall(code_block_pattern, text, re.DOTALL)

        if matches:
            return matches[0]

        # Look for Pine Script indicators
        if "//@version" in text or "study(" in text or "strategy(" in text:
            # Likely Pine Script code without markdown formatting
            return text

        return None
