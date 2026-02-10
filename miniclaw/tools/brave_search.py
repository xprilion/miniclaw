import json
import urllib.parse
import urllib.request
from typing import Dict, Any, List


class BraveSearchClient:
    """Brave Search API client for MiniClaw."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    def search(self, query: str, count: int = 5, country: str = "us",
               search_lang: str = "en", ui_lang: str = "en-US") -> Dict[str, Any]:
        """
        Perform a web search using Brave Search API.

        Args:
            query: Search query string
            count: Number of results to return (1-20)
            country: Country code for region-specific results
            search_lang: Language code for search results
            ui_lang: Language code for UI elements

        Returns:
            Dictionary containing search results
        """
        # Validate inputs
        if not query:
            raise ValueError("Search query cannot be empty")

        count = max(1, min(20, count))  # Clamp between 1-20

        # Prepare query parameters
        params = {
            "q": query,
            "count": count,
            "country": country,
            "search_lang": search_lang,
            "ui_lang": ui_lang,
        }

        # Build URL with query parameters
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{query_string}"

        # Prepare headers
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }

        # Make the request
        try:
            request = urllib.request.Request(url, headers=headers)
            response = urllib.request.urlopen(request)
            data = json.loads(response.read().decode())
            return data
        except urllib.error.HTTPError as e:
            error_data = e.read().decode()
            try:
                error_json = json.loads(error_data)
                raise Exception(f"Brave Search API error: {error_json.get('message', str(e))}")
            except json.JSONDecodeError:
                raise Exception(f"Brave Search API error: {error_data}")
        except Exception as e:
            raise Exception(f"Failed to perform search: {str(e)}")

    def format_results(self, search_results: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Format search results into a list of title/URL/snippet dictionaries.

        Args:
            search_results: Raw search results from Brave API

        Returns:
            List of formatted results with title, URL, and snippet
        """
        formatted_results = []

        # Extract web results
        web_results = search_results.get("web", {}).get("results", [])

        for result in web_results:
            formatted_results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("description", ""),
            })

        return formatted_results
