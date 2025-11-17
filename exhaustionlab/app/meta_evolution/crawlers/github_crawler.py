"""
GitHub Strategy Crawler

Extracts trading strategy examples from GitHub repositories.
Focus on Pine Script and cryptocurrency trading strategies.
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class GitHubStrategyCrawler:
    """
    Crawl GitHub for trading strategies.

    Search targets:
    - Pine Script repositories
    - Trading bot repositories with strategy code
    - Backtest results and performance metrics
    """

    def __init__(self, github_token: Optional[str] = None):
        """
        Initialize crawler.

        Args:
            github_token: Optional GitHub API token for higher rate limits
                         (60 req/hour without token, 5000 req/hour with token)
        """
        self.github_token = github_token
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ExhaustionLab-Strategy-Research/1.0",
                "Accept": "application/vnd.github.v3+json",
            }
        )
        if github_token:
            self.session.headers["Authorization"] = f"token {github_token}"

        self.rate_limit_remaining = 60  # Conservative default
        self.rate_limit_reset = 0

    def search_strategies(
        self,
        query: str = "trading strategy pinescript",
        min_stars: int = 5,
        max_results: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Search GitHub repositories for trading strategies.

        Args:
            query: Search query
            min_stars: Minimum stars to filter quality
            max_results: Maximum results to return

        Returns:
            List of repository metadata
        """
        logger.info(f"Searching GitHub for: {query}")

        results = []
        page = 1
        per_page = 30

        while len(results) < max_results:
            # Check rate limit
            self._check_rate_limit()

            # Search repositories
            url = f"{self.base_url}/search/repositories"
            params = {
                "q": f"{query} stars:>={min_stars}",
                "sort": "stars",
                "order": "desc",
                "per_page": per_page,
                "page": page,
            }

            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()

                # Update rate limit info
                self._update_rate_limit(response.headers)

                data = response.json()
                repos = data.get("items", [])

                if not repos:
                    break

                # Process repositories
                for repo in repos:
                    repo_info = self._extract_repo_info(repo)
                    if repo_info:
                        results.append(repo_info)

                    if len(results) >= max_results:
                        break

                page += 1

                # Respectful rate limiting
                time.sleep(random.uniform(1, 2))

            except requests.RequestException as e:
                logger.error(f"GitHub API error: {e}")
                break

        logger.info(f"Found {len(results)} repositories")
        return results

    def extract_strategy_code(self, repo_full_name: str) -> Optional[str]:
        """
        Extract strategy code from repository.

        Args:
            repo_full_name: Repository name in format "owner/repo"

        Returns:
            Strategy code if found, None otherwise
        """
        self._check_rate_limit()

        # Search for common strategy file names
        file_patterns = [
            "strategy.pine",
            "main.pine",
            "*.pine",
            "strategy.py",
            "backtest.py",
        ]

        for pattern in file_patterns:
            url = f"{self.base_url}/search/code"
            params = {"q": f"{pattern} repo:{repo_full_name}", "per_page": 5}

            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()

                self._update_rate_limit(response.headers)

                data = response.json()
                items = data.get("items", [])

                if items:
                    # Get content of first matching file
                    file_url = items[0]["url"]
                    content = self._get_file_content(file_url)
                    if content:
                        return content

                time.sleep(random.uniform(0.5, 1))

            except requests.RequestException as e:
                logger.error(f"Error searching code: {e}")
                continue

        return None

    def _extract_repo_info(self, repo: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract relevant information from repository data."""
        try:
            return {
                "platform": "github",
                "url": repo["html_url"],
                "name": repo["name"],
                "full_name": repo["full_name"],
                "author": repo["owner"]["login"],
                "description": repo.get("description", ""),
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "language": repo.get("language", ""),
                "created_at": repo["created_at"],
                "updated_at": repo["updated_at"],
                "topics": repo.get("topics", []),
            }
        except KeyError as e:
            logger.warning(f"Missing key in repo data: {e}")
            return None

    def _get_file_content(self, file_url: str) -> Optional[str]:
        """Get file content from GitHub API."""
        try:
            response = self.session.get(file_url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Content is base64 encoded
            import base64

            content = base64.b64decode(data["content"]).decode("utf-8")

            return content

        except Exception as e:
            logger.error(f"Error getting file content: {e}")
            return None

    def _check_rate_limit(self):
        """Check if we're hitting rate limits."""
        if self.rate_limit_remaining < 5:
            # Check if reset time has passed
            current_time = time.time()
            if current_time < self.rate_limit_reset:
                wait_time = self.rate_limit_reset - current_time + 10
                logger.warning(f"Rate limit low. Waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)
                self.rate_limit_remaining = 60  # Reset

    def _update_rate_limit(self, headers: Dict[str, str]):
        """Update rate limit info from response headers."""
        try:
            self.rate_limit_remaining = int(headers.get("X-RateLimit-Remaining", 60))
            self.rate_limit_reset = int(headers.get("X-RateLimit-Reset", 0))
        except (ValueError, TypeError):
            pass
