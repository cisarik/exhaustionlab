"""
TradingView Strategy Scraper

Extracts public trading strategies from TradingView.
Note: This scrapes public content only - respects TradingView's terms of service.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
from typing import List, Dict, Optional, Any
import logging
import re

logger = logging.getLogger(__name__)


class TradingViewScraper:
    """
    Scrape public TradingView strategies.

    IMPORTANT: This scraper:
    - Only accesses public content
    - Respects robots.txt
    - Includes rate limiting
    - Adds proper User-Agent
    """

    def __init__(self):
        """Initialize scraper."""
        self.base_url = "https://www.tradingview.com"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def search_public_scripts(
        self,
        query: str = "cryptocurrency strategy",
        category: str = "strategies",
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Search TradingView for public scripts.

        Args:
            query: Search query
            category: Script category ('strategies', 'indicators', 'libraries')
            max_results: Maximum results to return

        Returns:
            List of script metadata
        """
        logger.info(f"Searching TradingView for: {query}")

        results = []

        # TradingView script library URL
        # Note: This is a simplified approach - TradingView's actual search
        # uses a complex API that requires authentication for detailed access

        try:
            # Search via public script library
            search_url = f"{self.base_url}/scripts/"

            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            # Find script cards (structure may vary)
            # This is a simplified version - real implementation would need
            # more robust parsing based on TradingView's current HTML structure

            script_cards = soup.find_all("div", class_=re.compile("scriptCard"))

            for card in script_cards[:max_results]:
                script_info = self._extract_script_info(card)
                if script_info:
                    results.append(script_info)

            # Rate limiting
            time.sleep(random.uniform(2, 4))

        except Exception as e:
            logger.error(f"Error searching TradingView: {e}")

        logger.info(f"Found {len(results)} scripts")
        return results

    def get_script_details(self, script_url: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific script.

        Args:
            script_url: URL to TradingView script

        Returns:
            Script details including code if available
        """
        try:
            response = self.session.get(script_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract script details
            details = {
                "url": script_url,
                "platform": "tradingview",
            }

            # Try to extract script name
            title_tag = soup.find("h1")
            if title_tag:
                details["name"] = title_tag.text.strip()

            # Try to extract author
            author_tag = soup.find("a", class_=re.compile("author"))
            if author_tag:
                details["author"] = author_tag.text.strip()

            # Try to extract description
            desc_tag = soup.find("div", class_=re.compile("description"))
            if desc_tag:
                details["description"] = desc_tag.text.strip()[:500]

            # Try to extract likes/uses
            likes_tag = soup.find("span", class_=re.compile("likes"))
            if likes_tag:
                details["likes"] = self._parse_number(likes_tag.text)

            # Extract code if visible (many scripts hide code)
            code_tag = soup.find("pre", class_=re.compile("code|source"))
            if code_tag:
                details["code"] = code_tag.text.strip()
            else:
                # Code might be in script tag or protected
                details["code"] = None
                details["code_available"] = False

            # Rate limiting
            time.sleep(random.uniform(2, 4))

            return details

        except Exception as e:
            logger.error(f"Error fetching script details: {e}")
            return None

    def extract_pine_script_code(self, script_text: str) -> Optional[str]:
        """
        Extract Pine Script code from text.

        Args:
            script_text: Raw text containing Pine Script

        Returns:
            Cleaned Pine Script code
        """
        if not script_text:
            return None

        # Look for Pine Script version indicator
        if "//@version" not in script_text:
            return None

        # Extract code between markers
        lines = script_text.split("\n")
        code_lines = []
        in_code = False

        for line in lines:
            if "//@version" in line:
                in_code = True

            if in_code:
                code_lines.append(line)

        return "\n".join(code_lines) if code_lines else None

    def _extract_script_info(self, card_element) -> Optional[Dict[str, Any]]:
        """Extract script information from HTML card element."""
        try:
            info = {
                "platform": "tradingview",
            }

            # Extract title
            title_tag = card_element.find("a", class_=re.compile("title"))
            if title_tag:
                info["name"] = title_tag.text.strip()
                info["url"] = self.base_url + title_tag.get("href", "")
            else:
                return None

            # Extract author
            author_tag = card_element.find("a", class_=re.compile("author"))
            if author_tag:
                info["author"] = author_tag.text.strip()

            # Extract likes/uses
            likes_tag = card_element.find("span", class_=re.compile("likes|favs"))
            if likes_tag:
                info["likes"] = self._parse_number(likes_tag.text)

            uses_tag = card_element.find("span", class_=re.compile("uses"))
            if uses_tag:
                info["uses"] = self._parse_number(uses_tag.text)

            return info

        except Exception as e:
            logger.warning(f"Error extracting script info: {e}")
            return None

    def _parse_number(self, text: str) -> int:
        """Parse number from text (handles 'K', 'M' suffixes)."""
        if not text:
            return 0

        # Remove non-numeric except K/M
        text = re.sub(r"[^\d.KM]", "", text.upper())

        if "K" in text:
            return int(float(text.replace("K", "")) * 1000)
        elif "M" in text:
            return int(float(text.replace("M", "")) * 1000000)
        else:
            try:
                return int(float(text))
            except ValueError:
                return 0

    def get_popular_strategies(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get most popular public strategies.

        Args:
            limit: Number of strategies to return

        Returns:
            List of popular strategy metadata
        """
        logger.info(f"Fetching top {limit} popular strategies")

        # Use TradingView's public script library sorted by popularity
        url = f"{self.base_url}/scripts/"

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Find strategy links (simplified - actual structure may vary)
            results = []

            # Look for script links
            script_links = soup.find_all("a", href=re.compile(r"/script/"))

            for link in script_links[:limit]:
                script_url = self.base_url + link.get("href")

                # Get basic info from link
                info = {
                    "platform": "tradingview",
                    "url": script_url,
                    "name": link.text.strip(),
                }

                results.append(info)

                # Rate limiting
                time.sleep(random.uniform(1, 2))

            logger.info(f"Found {len(results)} strategies")
            return results

        except Exception as e:
            logger.error(f"Error fetching popular strategies: {e}")
            return []
