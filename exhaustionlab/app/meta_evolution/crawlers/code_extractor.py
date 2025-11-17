"""
Enhanced Code Extractor

Extracts complete strategy profiles from GitHub repositories:
- Pine Script files (.pine)
- Python files (.py)
- README files
- Documentation
- Configuration files
- Test files
"""

import base64
import logging
import random
import re
import time
from typing import Any, Dict, List, Optional

import requests

from .mock_repo_data import MOCK_REPOSITORIES

logger = logging.getLogger(__name__)


class GitHubCodeExtractor:
    """
    Extract complete code and metadata from GitHub repositories.

    Gets everything:
    - All Pine Script files
    - README content
    - Documentation
    - Parameters from code
    - Indicators used
    - Test files if available
    """

    def __init__(self, github_token: Optional[str] = None):
        """Initialize extractor."""
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
        self.mock_repositories = MOCK_REPOSITORIES

    def extract_full_strategy(self, repo_full_name: str) -> Dict[str, Any]:
        """
        Extract complete strategy profile from repository.

        Args:
            repo_full_name: Repository name in format "owner/repo"

        Returns:
            Complete strategy data dictionary
        """
        logger.info(f"Extracting full strategy from: {repo_full_name}")

        strategy = {
            "repo_full_name": repo_full_name,
            "name": repo_full_name.split("/")[-1],  # Fallback name from repo
            "platform": "github",
            "extraction_status": "complete",
            "extraction_notes": [],
            "extraction_source": "github_api",
        }

        mock_data = self.mock_repositories.get(repo_full_name)

        try:
            if mock_data is not None:
                return self._extract_mock_strategy(repo_full_name, mock_data)

            # Get repository info
            repo_info = self._get_repo_info(repo_full_name)
            if repo_info:
                strategy.update(repo_info)  # Will override name if successful

            # Get README
            readme = self._get_readme(repo_full_name)
            if readme:
                strategy["readme"] = readme
                strategy["has_documentation"] = True

            # Find and extract Pine Script files
            pine_files = self._find_pine_files(repo_full_name)
            if pine_files:
                # Get first/main Pine Script file
                main_file = pine_files[0]
                code = self._get_file_content(main_file["url"])
                if code:
                    strategy["pine_code"] = code
                    strategy["has_code"] = True
                    strategy["code_language"] = "pinescript"

                    # Parse code metadata
                    code_meta = self._parse_pine_code(code)
                    strategy.update(code_meta)

            # Find Python files (if any)
            python_files = self._find_python_files(repo_full_name)
            if python_files:
                main_py = python_files[0]
                py_code = self._get_file_content(main_py["url"])
                if py_code:
                    strategy["python_code"] = py_code

            # Find test files
            test_files = self._find_test_files(repo_full_name)
            if test_files:
                strategy["has_tests"] = True

            # Extract features from README + code
            features = self._extract_features(strategy)
            strategy["features"] = features

            strategy["extraction_status"] = "complete"
            logger.info(f"✅ Successfully extracted: {repo_full_name}")

        except Exception as e:
            logger.error(f"❌ Extraction failed for {repo_full_name}: {e}")
            strategy["extraction_status"] = "failed"
            strategy["extraction_notes"].append(f"Error: {str(e)}")

        return strategy

    def _extract_mock_strategy(self, repo_full_name: str, mock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build strategy payload from local mock data."""
        if "error" in mock_data:
            raise RuntimeError(mock_data["error"])

        strategy = {
            "repo_full_name": repo_full_name,
            "name": mock_data.get("repo_info", {}).get("name", repo_full_name.split("/")[-1]),
            "platform": mock_data.get("repo_info", {}).get("platform", "github"),
            "extraction_status": "complete",
            "extraction_notes": [],
            "extraction_source": "mock_data",
        }

        repo_info = mock_data.get("repo_info")
        if repo_info:
            strategy.update(repo_info)

        readme = mock_data.get("readme")
        if readme:
            strategy["readme"] = readme
            strategy["has_documentation"] = True

        pine_code = mock_data.get("pine_code")
        if pine_code:
            strategy["pine_code"] = pine_code
            strategy["has_code"] = True
            strategy["code_language"] = "pinescript"
            strategy.update(self._parse_pine_code(pine_code))

        python_code = mock_data.get("python_code")
        if python_code:
            strategy["python_code"] = python_code

        if mock_data.get("has_tests"):
            strategy["has_tests"] = True

        for key in ("backtest_metrics", "category", "tags", "market_focus"):
            if key in mock_data:
                strategy[key] = mock_data[key]

        strategy["features"] = self._extract_features(strategy)

        return strategy

    def _get_repo_info(self, repo_full_name: str) -> Optional[Dict[str, Any]]:
        """Get repository information."""
        url = f"{self.base_url}/repos/{repo_full_name}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Get topics for tags
            topics = data.get("topics", [])

            return {
                "name": data.get("name"),
                "author": data.get("owner", {}).get("login"),
                "description": data.get("description", ""),
                "url": data.get("html_url"),
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "watchers": data.get("watchers_count", 0),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
                "tags": topics if topics else [],  # Store as tags
            }

        except Exception as e:
            logger.error(f"Failed to get repo info: {e}")
            return None

    def _get_readme(self, repo_full_name: str) -> Optional[str]:
        """Get README content."""
        url = f"{self.base_url}/repos/{repo_full_name}/readme"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")

            return content

        except Exception as e:
            logger.debug(f"No README found: {e}")
            return None

    def _find_pine_files(self, repo_full_name: str) -> List[Dict[str, str]]:
        """Find Pine Script files in repository."""
        return self._search_files(repo_full_name, extension=".pine")

    def _find_python_files(self, repo_full_name: str) -> List[Dict[str, str]]:
        """Find Python files in repository."""
        return self._search_files(
            repo_full_name,
            extension=".py",
            exclude=["test_", "setup.py", "__init__.py"],
        )

    def _find_test_files(self, repo_full_name: str) -> List[Dict[str, str]]:
        """Find test files."""
        return self._search_files(repo_full_name, path="test")

    def _search_files(
        self,
        repo_full_name: str,
        extension: Optional[str] = None,
        path: Optional[str] = None,
        exclude: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        """Search for files in repository."""
        url = f"{self.base_url}/search/code"

        # Build query
        query_parts = [f"repo:{repo_full_name}"]
        if extension:
            query_parts.append(f'extension:{extension.lstrip(".")}')
        if path:
            query_parts.append(f"path:{path}")

        query = " ".join(query_parts)

        try:
            response = self.session.get(url, params={"q": query, "per_page": 10}, timeout=10)
            response.raise_for_status()

            data = response.json()
            items = data.get("items", [])

            # Filter excluded
            if exclude:
                items = [item for item in items if not any(ex in item["name"] for ex in exclude)]

            return [{"name": item["name"], "url": item["url"]} for item in items]

        except Exception as e:
            logger.debug(f"File search failed: {e}")
            return []

    def _get_file_content(self, file_url: str) -> Optional[str]:
        """Get file content from GitHub API."""
        try:
            response = self.session.get(file_url, timeout=10)
            response.raise_for_status()

            data = response.json()
            content = base64.b64decode(data["content"]).decode("utf-8", errors="ignore")

            time.sleep(random.uniform(0.5, 1))  # Rate limiting

            return content

        except Exception as e:
            logger.error(f"Failed to get file content: {e}")
            return None

    def _parse_pine_code(self, code: str) -> Dict[str, Any]:
        """
        Parse Pine Script code to extract metadata.

        Extracts:
        - Indicators used
        - Parameters
        - Strategy name
        - Version
        - Complexity metrics
        """
        meta = {
            "indicators_used": [],
            "parameters": {},
            "lines_of_code": 0,
            "complexity_score": 0.0,
        }

        if not code:
            return meta

        lines = code.split("\n")
        meta["lines_of_code"] = len([line for line in lines if line.strip() and not line.strip().startswith("//")])

        # Extract version
        version_match = re.search(r"//@version\s*=\s*(\d+)", code)
        if version_match:
            meta["pine_version"] = int(version_match.group(1))

        # Extract title
        title_match = re.search(r'(?:indicator|strategy)\s*\(\s*(?:title\s*=\s*)?["\']([^"\']+)["\']', code)
        if title_match:
            meta["title"] = title_match.group(1)

        # Extract indicators used
        indicators = []
        indicator_patterns = [
            r"\b(rsi|macd|ema|sma|bb|stoch|cci|adx|atr|obv|mfi|willr|sar)\s*\(",
            r"ta\.(rsi|macd|ema|sma|stoch|cci|adx|atr|obv|mfi|willr|sar)\s*\(",
        ]

        for pattern in indicator_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            indicators.extend([m.upper() for m in matches])

        meta["indicators_used"] = list(set(indicators))

        # Extract input parameters (supports title argument in any position)
        input_pattern = r"input(?:\.\w+)?\s*\((.*?)\)"
        for match in re.finditer(input_pattern, code, re.DOTALL):
            arguments = match.group(1)
            title_match = re.search(r'title\s*=\s*["\']([^"\']+)["\']', arguments, re.IGNORECASE)
            if title_match:
                param_name = title_match.group(1)
            else:
                string_match = re.search(r'["\']([^"\']+)["\']', arguments)
                param_name = string_match.group(1) if string_match else None

            if param_name:
                meta["parameters"][param_name] = None  # Value not known from code

        # Estimate complexity
        conditionals = len(re.findall(r"\b(if|else|switch|case)\b", code))
        loops = len(re.findall(r"\b(for|while)\b", code))
        functions = len(re.findall(r"\b(f_\w+|func_\w+)\s*\(", code))

        meta["complexity_score"] = min(1.0, (conditionals * 0.02 + loops * 0.03 + functions * 0.05))

        return meta

    def _extract_features(self, strategy: Dict[str, Any]) -> Dict[str, bool]:
        """Extract features from code and documentation."""
        features = {
            "stop_loss": False,
            "take_profit": False,
            "trailing_stop": False,
            "position_sizing": False,
            "alerts": False,
            "multi_timeframe": False,
            "backtesting": False,
        }

        # Check code
        code = strategy.get("pine_code", "") or ""
        readme = strategy.get("readme", "") or ""

        combined_text = (code + " " + readme).lower()

        if "stop" in combined_text and "loss" in combined_text:
            features["stop_loss"] = True

        if "take" in combined_text and "profit" in combined_text:
            features["take_profit"] = True

        if "trailing" in combined_text:
            features["trailing_stop"] = True

        if "position" in combined_text and "siz" in combined_text:
            features["position_sizing"] = True

        if "alert" in combined_text:
            features["alerts"] = True

        if "timeframe" in combined_text or "mtf" in combined_text:
            features["multi_timeframe"] = True

        if "backtest" in combined_text or "strategy" in combined_text:
            features["backtesting"] = True

        return features
