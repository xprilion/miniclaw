#!/usr/bin/env python3
"""
Simple test script for Brave Search client.
"""

import json
import urllib.parse
import urllib.request
from typing import Dict, Any, List


class BraveSearchClient:
    """Brave Search API client."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    def search(self, query: str, count: int = 5, country: str = "us", 
               search_lang: str = "en", ui_lang: str = "en-US") -> Dict[str, Any]:
        """Perform a web search using Brave Search API."""
        if not query:
            raise ValueError("Search query cannot be empty")
        
        count = max(1, min(20, count))
        
        params = {
            "q": query,
            "count": count,
            "country": country,
            "search_lang": search_lang,
            "ui_lang": ui_lang,
        }
        
        query_string = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{query_string}"
        
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key,
        }
        
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
        """Format search results into a list of title/URL/snippet dictionaries."""
        formatted_results = []
        web_results = search_results.get("web", {}).get("results", [])
        
        for result in web_results:
            formatted_results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": result.get("description", ""),
            })
        
        return formatted_results


def test_brave_search():
    """Test the Brave Search client."""
    api_key = "BSAW9orqbdUdha3-8bXvUK_VPOI3r2N"
    
    client = BraveSearchClient(api_key)
    
    try:
        print("Testing Brave Search with query: 'latest AI breakthroughs 2026'")
        results = client.search("latest AI breakthroughs 2026", count=3)
        formatted = client.format_results(results)
        
        print(f"Found {len(formatted)} results:")
        for i, result in enumerate(formatted, 1):
            print(f"{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Snippet: {result['snippet'][:100]}...")
            print()
            
    except Exception as e:
        print(f"Error: {e}")
        return False
        
    return True


if __name__ == "__main__":
    success = test_brave_search()
    exit(0 if success else 1)