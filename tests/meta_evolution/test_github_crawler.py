"""
Test GitHub Strategy Crawler

TDD Approach: Write tests first, then implement.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Direct import to avoid broken __init__.py dependencies
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "exhaustionlab"))
from app.meta_evolution.crawlers.github_crawler import GitHubStrategyCrawler


class TestGitHubCrawlerBasic:
    """Basic unit tests for GitHub crawler."""

    def test_crawler_initialization(self):
        """Test crawler can be instantiated."""
        crawler = GitHubStrategyCrawler()

        assert crawler is not None
        assert crawler.base_url == "https://api.github.com"
        assert crawler.rate_limit_remaining >= 0

    def test_crawler_with_token(self):
        """Test crawler initialization with GitHub token."""
        crawler = GitHubStrategyCrawler(github_token="test_token")

        assert crawler.github_token == "test_token"
        assert "token test_token" in crawler.session.headers.get("Authorization", "")

    def test_rate_limit_check(self):
        """Test rate limit checking logic."""
        crawler = GitHubStrategyCrawler()
        crawler.rate_limit_remaining = 100

        # Should not raise or sleep
        crawler._check_rate_limit()

        assert True  # If we get here, rate limit check passed


class TestGitHubSearchMocked:
    """Test GitHub search with mocked API responses."""

    @patch("requests.Session.get")
    def test_search_strategies_success(self, mock_get):
        """Test successful strategy search."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "name": "test-strategy",
                    "full_name": "user/test-strategy",
                    "html_url": "https://github.com/user/test-strategy",
                    "stargazers_count": 100,
                    "forks_count": 20,
                    "owner": {"login": "user"},
                    "description": "Test trading strategy",
                    "language": "Pine",
                    "created_at": "2024-01-01",
                    "updated_at": "2024-01-15",
                    "topics": ["trading", "pinescript"],
                }
            ]
        }
        mock_response.headers = {
            "X-RateLimit-Remaining": "5000",
            "X-RateLimit-Reset": "9999999999",
        }
        mock_get.return_value = mock_response

        # Test
        crawler = GitHubStrategyCrawler()
        results = crawler.search_strategies(
            query="trading strategy", min_stars=10, max_results=5
        )

        # Assertions
        assert len(results) > 0
        assert results[0]["name"] == "test-strategy"
        assert results[0]["stars"] == 100
        assert "url" in results[0]

    @patch("requests.Session.get")
    def test_search_strategies_empty_response(self, mock_get):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.headers = {
            "X-RateLimit-Remaining": "5000",
            "X-RateLimit-Reset": "9999999999",
        }
        mock_get.return_value = mock_response

        crawler = GitHubStrategyCrawler()
        results = crawler.search_strategies(max_results=5)

        assert results == []

    @patch("requests.Session.get")
    def test_extract_repo_info(self, mock_get):
        """Test repository information extraction."""
        crawler = GitHubStrategyCrawler()

        repo_data = {
            "name": "strategy",
            "full_name": "user/strategy",
            "html_url": "https://github.com/user/strategy",
            "stargazers_count": 50,
            "forks_count": 10,
            "owner": {"login": "user"},
            "description": "Test",
            "language": "Pine",
            "created_at": "2024-01-01",
            "updated_at": "2024-01-02",
            "topics": [],
        }

        info = crawler._extract_repo_info(repo_data)

        assert info is not None
        assert info["name"] == "strategy"
        assert info["stars"] == 50
        assert info["platform"] == "github"


class TestGitHubCodeExtraction:
    """Test code extraction from repositories."""

    @patch("requests.Session.get")
    def test_extract_strategy_code_success(self, mock_get):
        """Test successful code extraction."""
        # Mock search response
        search_response = Mock()
        search_response.status_code = 200
        search_response.json.return_value = {
            "items": [
                {"url": "https://api.github.com/repos/user/repo/contents/strategy.pine"}
            ]
        }
        search_response.headers = {
            "X-RateLimit-Remaining": "5000",
            "X-RateLimit-Reset": "9999999999",
        }

        # Mock file content response
        import base64

        code = "//@version=5\nindicator('Test')\nplot(close)"
        content_response = Mock()
        content_response.status_code = 200
        content_response.json.return_value = {
            "content": base64.b64encode(code.encode()).decode()
        }

        mock_get.side_effect = [search_response, content_response]

        crawler = GitHubStrategyCrawler()
        extracted_code = crawler.extract_strategy_code("user/repo")

        assert extracted_code is not None
        assert "//@version" in extracted_code
        assert "plot(close)" in extracted_code

    @patch("requests.Session.get")
    def test_extract_strategy_code_not_found(self, mock_get):
        """Test code extraction when no files found."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.headers = {
            "X-RateLimit-Remaining": "5000",
            "X-RateLimit-Reset": "9999999999",
        }
        mock_get.return_value = mock_response

        crawler = GitHubStrategyCrawler()
        code = crawler.extract_strategy_code("user/repo")

        assert code is None


@pytest.mark.integration
class TestGitHubIntegration:
    """Integration tests with real GitHub API (slow, requires network)."""

    @pytest.mark.skip(reason="Integration test - run manually")
    def test_real_search_pinescript(self):
        """Test real search for Pine Script strategies."""
        crawler = GitHubStrategyCrawler()

        results = crawler.search_strategies(
            query="pinescript trading strategy", min_stars=10, max_results=3
        )

        # Should find at least some strategies
        assert len(results) > 0

        # Check structure
        for result in results:
            assert "name" in result
            assert "url" in result
            assert "stars" in result
            assert result["stars"] >= 10

    @pytest.mark.skip(reason="Integration test - run manually")
    def test_real_code_extraction(self):
        """Test real code extraction from known repository."""
        crawler = GitHubStrategyCrawler()

        # Use a known test repository (create one if needed)
        code = crawler.extract_strategy_code("tradingview/pine-seeds")

        # Should either find code or return None gracefully
        assert code is None or isinstance(code, str)


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_updates(self):
        """Test rate limit info is updated from headers."""
        crawler = GitHubStrategyCrawler()

        headers = {"X-RateLimit-Remaining": "4500", "X-RateLimit-Reset": "1234567890"}

        crawler._update_rate_limit(headers)

        assert crawler.rate_limit_remaining == 4500
        assert crawler.rate_limit_reset == 1234567890

    @patch("time.sleep")
    def test_rate_limit_wait(self, mock_sleep):
        """Test waiting when rate limit is low."""
        import time

        crawler = GitHubStrategyCrawler()
        crawler.rate_limit_remaining = 3
        crawler.rate_limit_reset = time.time() + 60  # 60 seconds in future

        crawler._check_rate_limit()

        # Should have called sleep
        assert mock_sleep.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
