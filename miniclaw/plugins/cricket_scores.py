"""Enhanced cricket scores retrieval with browser automation fallbacks."""

import json
import re
import time
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class EnhancedCricketScoreRetriever:
    """Enhanced cricket score retrieval using multiple strategies including browser automation."""
    
    def __init__(self, tool_runner):
        self.tool_runner = tool_runner
        self.max_retries = 3
        self.retry_delay = 2  # seconds
    
    def _run_tool_with_retry(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Run a tool with retry logic."""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempt {attempt + 1}/{self.max_retries} for {tool_name}")
                result = self.tool_runner.run(tool_name, arguments)
                
                if result.get("ok", False):
                    logger.info(f"Successfully executed {tool_name} on attempt {attempt + 1}")
                    return result
                else:
                    last_error = result.get("error", "Unknown error")
                    logger.warning(f"Attempt {attempt + 1} failed for {tool_name}: {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1} failed for {tool_name}: {last_error}")
            
            if attempt < self.max_retries - 1:  # Don't sleep on the last attempt
                time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
        
        # All attempts failed
        raise Exception(f"Failed to execute {tool_name} after {self.max_retries} attempts. Last error: {last_error}")
    
    def _clean_html_content(self, html_content: str) -> str:
        """Clean HTML content to improve parsing."""
        # Remove script and style tags
        html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove extra whitespace and newlines
        html_content = re.sub(r'\s+', ' ', html_content)
        
        return html_content
    
    def _extract_scores_from_text(self, text_content: str) -> List[Dict[str, Any]]:
        """Extract cricket scores from text content using comprehensive patterns."""
        scores = []
        
        # Normalize the text
        text_content = re.sub(r'\s+', ' ', text_content.strip())
        
        # Comprehensive patterns for different score formats
        patterns = [
            # Pattern 1: Team vs Team with scores
            r'([A-Z]{2,4}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+vs\s+([A-Z]{2,4}|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*).*?([0-9]+/[0-9]+).*?(?:\(([^)]+)\))?.*?([0-9]+/[0-9]+).*?(?:\(([^)]+)\))?',
            
            # Pattern 2: Team scores with overs
            r'([A-Z]{2,4})\s+([0-9]+/[0-9]+)\s*\(?([0-9.]*)\s*ov?e?r?s?\)?\s*(?:&\s*)?([A-Z]{2,4})?\s*([0-9]+/[0-9]+)?\s*\(?([0-9.]*)\s*ov?e?r?s?\)?',
            
            # Pattern 3: Simple team score format
            r'([A-Z]{2,4})\s+([0-9]+/[0-9]+).*?([A-Z]{2,4})\s+([0-9]+/[0-9]+)',
            
            # Pattern 4: Team score with overs (single team)
            r'([A-Z]{2,4}|[A-Z][a-z]+)\s+([0-9]+/[0-9]+)\s*\(([^)]+)\)',
        ]
        
        for i, pattern in enumerate(patterns):
            try:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                logger.info(f"Text pattern {i+1} found {len(matches)} matches")
                
                for match in matches:
                    try:
                        if isinstance(match, tuple) and len(match) >= 2:
                            score_info = {}
                            
                            if i == 0 and len(match) >= 5:  # Team vs Team pattern
                                team1, team2, score1, overs1, score2, overs2 = match
                                score_info = {
                                    "teams": f"{team1.strip()} vs {team2.strip()}",
                                    "score": f"{score1.strip()}{' (' + overs1.strip() + ')' if overs1 else ''} & {score2.strip()}{' (' + overs2.strip() + ')' if overs2 else ''}",
                                    "status": "Live"
                                }
                            elif i == 1 and len(match) >= 4:  # Team scores with overs pattern
                                team1, score1, overs1, team2, score2, overs2 = match[:6]
                                if team1 and score1:
                                    score_info = {
                                        "teams": f"{team1.strip()} vs {team2.strip() if team2 else 'Opponent'}",
                                        "score": f"{score1.strip()}{' (' + overs1.strip() + ' ov)' if overs1 else ''} & {score2.strip() + ' (' + overs2.strip() + ' ov)' if score2 and overs2 else (score2.strip() if score2 else '')}",
                                        "status": "Live"
                                    }
                            elif i == 2 and len(match) >= 4:  # Simple team score format
                                team1, score1, team2, score2 = match[:4]
                                if team1 and score1 and team2 and score2:
                                    score_info = {
                                        "teams": f"{team1.strip()} vs {team2.strip()}",
                                        "score": f"{score1.strip()} & {score2.strip()}",
                                        "status": "Live"
                                    }
                            elif i == 3 and len(match) >= 3:  # Team score with overs (single)
                                team1, score1, overs1 = match[:3]
                                if team1 and score1:
                                    score_info = {
                                        "teams": f"{team1.strip()}",
                                        "score": f"{score1.strip()} ({overs1.strip()})",
                                        "status": "Live"
                                    }
                            
                            if score_info and score_info.get("teams") and score_info.get("score"):
                                # Avoid duplicates
                                if not any(s["teams"] == score_info["teams"] for s in scores):
                                    scores.append(score_info)
                                    logger.info(f"Extracted score: {score_info}")
                    except Exception as e:
                        logger.debug(f"Failed to process text match: {e}")
                        continue
            except Exception as e:
                logger.debug(f"Text pattern {i+1} failed: {e}")
                continue
        
        return scores
    
    def _get_cricbuzz_scores(self) -> List[Dict[str, Any]]:
        """Try to get scores from Cricbuzz."""
        try:
            logger.info("Attempting to fetch from Cricbuzz")
            result = self._run_tool_with_retry("fetch_url", {
                "url": "https://www.cricbuzz.com/cricket-match/live-scores",
                "timeout_seconds": 15
            })
            
            if result.get("ok", False):
                html_content = result["result"].get("body", "")
                logger.info(f"Fetched Cricbuzz content length: {len(html_content)}")
                
                # Clean the HTML content
                clean_content = self._clean_html_content(html_content)
                
                # Extract text content for pattern matching
                # Remove HTML tags
                text_content = re.sub(r'<[^>]+>', ' ', clean_content)
                
                scores = self._extract_scores_from_text(text_content)
                if scores:
                    logger.info(f"Found {len(scores)} scores from Cricbuzz")
                    return scores
                else:
                    logger.warning("No scores found in Cricbuzz content")
            else:
                logger.warning(f"Failed to fetch Cricbuzz: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error fetching from Cricbuzz: {e}")
        
        return []
    
    def _get_espncricinfo_scores(self) -> List[Dict[str, Any]]:
        """Try to get scores from ESPN Cricinfo."""
        try:
            logger.info("Attempting to fetch from ESPN Cricinfo")
            result = self._run_tool_with_retry("fetch_url", {
                "url": "https://www.espncricinfo.com/live-cricket-score",
                "timeout_seconds": 15
            })
            
            if result.get("ok", False):
                html_content = result["result"].get("body", "")
                logger.info(f"Fetched ESPN content length: {len(html_content)}")
                
                # Clean the HTML content
                clean_content = self._clean_html_content(html_content)
                
                # Extract text content for pattern matching
                text_content = re.sub(r'<[^>]+>', ' ', clean_content)
                
                scores = self._extract_scores_from_text(text_content)
                if scores:
                    logger.info(f"Found {len(scores)} scores from ESPN Cricinfo")
                    return scores
                else:
                    logger.warning("No scores found in ESPN Cricinfo content")
            else:
                logger.warning(f"Failed to fetch ESPN Cricinfo: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error fetching from ESPN Cricinfo: {e}")
        
        return []
    
    def _get_google_cricket_scores(self) -> List[Dict[str, Any]]:
        """Try to get scores from Google search results."""
        try:
            logger.info("Attempting to get cricket scores via Google search")
            result = self._run_tool_with_retry("fetch_url", {
                "url": "https://www.google.com/search?q=live+cricket+scores+site:cricbuzz.com",
                "timeout_seconds": 20
            })
            
            if result.get("ok", False):
                html_content = result["result"].get("body", "")
                logger.info(f"Fetched Google search content length: {len(html_content)}")
                
                # Clean the HTML content
                clean_content = self._clean_html_content(html_content)
                
                # Extract text content for pattern matching
                text_content = re.sub(r'<[^>]+>', ' ', clean_content)
                
                scores = self._extract_scores_from_text(text_content)
                if scores:
                    logger.info(f"Found {len(scores)} scores from Google search")
                    return scores
                else:
                    logger.warning("No scores found in Google search results")
            else:
                logger.warning(f"Google search failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error getting scores from Google search: {e}")
        
        return []
    
    def _get_cricket_scores_via_search(self) -> List[Dict[str, Any]]:
        """Get cricket scores using web search as fallback."""
        try:
            logger.info("Attempting to get cricket scores via Brave search")
            search_result = self._run_tool_with_retry("brave_search", {
                "query": "live cricket scores current matches",
                "count": 10
            })
            
            if search_result.get("ok", False):
                search_results = search_result["result"].get("results", [])
                all_scores = []
                
                # Extract information from top search results
                for item in search_results:
                    title = item.get("title", "")
                    description = item.get("description", "")
                    
                    # Combine title and description for pattern matching
                    combined_text = f"{title} {description}"
                    
                    # Extract scores from the combined text
                    scores = self._extract_scores_from_text(combined_text)
                    for score in scores:
                        score["source"] = "Search result"
                        score["url"] = item.get("url", "")
                        # Avoid duplicates
                        if not any(s["teams"] == score["teams"] for s in all_scores):
                            all_scores.append(score)
                
                if all_scores:
                    logger.info(f"Found {len(all_scores)} scores via search")
                    return all_scores
                else:
                    logger.warning("No scores found in search results")
            else:
                logger.warning(f"Search failed: {search_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error getting scores via search: {e}")
        
        return []
    
    def _get_browser_based_scores(self) -> List[Dict[str, Any]]:
        """Get scores using browser automation as a last resort."""
        try:
            logger.info("Attempting browser-based score retrieval")
            
            # Since we can't easily attach a Chrome tab, we'll use a different approach
            # We'll try to get more structured data using browser_extract with specific sites
            
            sites_to_try = [
                {"url": "https://www.cricbuzz.com/cricket-match/live-scores", "name": "Cricbuzz"},
                {"url": "https://www.espncricinfo.com/live-cricket-score", "name": "ESPN Cricinfo"},
            ]
            
            for site in sites_to_try:
                try:
                    logger.info(f"Attempting browser_extract for {site['name']}")
                    result = self._run_tool_with_retry("browser_extract", {
                        "url": site["url"],
                        "timeout_seconds": 25
                    })
                    
                    if result.get("ok", False):
                        text_content = result["result"].get("text", "")
                        title = result["result"].get("title", "")
                        
                        logger.info(f"Fetched {site['name']} via browser_extract. Title: {title[:100]}...")
                        
                        # Combine title and text for better pattern matching
                        combined_content = f"{title} {text_content}"
                        
                        scores = self._extract_scores_from_text(combined_content)
                        if scores:
                            logger.info(f"Found {len(scores)} scores from {site['name']} via browser_extract")
                            # Add source information
                            for score in scores:
                                score["source"] = f"Browser extract from {site['name']}"
                            return scores
                        else:
                            logger.warning(f"No scores found in {site['name']} browser_extract content")
                    else:
                        logger.warning(f"Browser_extract failed for {site['name']}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Browser_extract attempt for {site['name']} failed: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Browser-based score retrieval failed: {e}")
        
        return []
    
    def get_cricket_scores(self) -> Dict[str, Any]:
        """Get cricket scores using enhanced multi-step strategy."""
        logger.info("Starting enhanced cricket score retrieval")
        
        scores = []
        attempt_log = []
        
        # Step 1: Try Cricbuzz
        try:
            scores = self._get_cricbuzz_scores()
            attempt_log.append("Attempted Cricbuzz API")
        except Exception as e:
            logger.error(f"Cricbuzz attempt failed: {e}")
            attempt_log.append(f"Attempted Cricbuzz API: {str(e)}")
        
        # Step 2: Try ESPN Cricinfo if Cricbuzz failed
        if not scores:
            try:
                scores = self._get_espncricinfo_scores()
                attempt_log.append("Attempted ESPN Cricinfo")
            except Exception as e:
                logger.error(f"ESPN Cricinfo attempt failed: {e}")
                attempt_log.append(f"Attempted ESPN Cricinfo: {str(e)}")
        
        # Step 3: Try Google search if previous methods failed
        if not scores:
            try:
                scores = self._get_google_cricket_scores()
                attempt_log.append("Attempted Google search")
            except Exception as e:
                logger.error(f"Google search attempt failed: {e}")
                attempt_log.append(f"Attempted Google search: {str(e)}")
        
        # Step 4: Use Brave search as another fallback
        if not scores:
            try:
                scores = self._get_cricket_scores_via_search()
                attempt_log.append("Used Brave search as fallback")
            except Exception as e:
                logger.error(f"Brave search attempt failed: {e}")
                attempt_log.append(f"Used Brave search as fallback: {str(e)}")
        
        # Step 5: Try browser-based extraction as last resort
        if not scores:
            try:
                scores = self._get_browser_based_scores()
                attempt_log.append("Used browser extract as last resort")
            except Exception as e:
                logger.error(f"Browser extract attempt failed: {e}")
                attempt_log.append(f"Used browser extract as last resort: {str(e)}")
        
        # Prepare response
        response = {
            "success": len(scores) > 0,
            "scores": scores,
            "attempt_log": attempt_log,
            "total_attempts": len(attempt_log)
        }
        
        if scores:
            response["message"] = f"Successfully retrieved {len(scores)} cricket score(s)"
        else:
            response["message"] = "Failed to retrieve cricket scores after all attempts"
            response["error"] = "No scores found from any source"
        
        logger.info(f"Enhanced cricket score retrieval completed: {response['message']}")
        return response

def get_cricket_scores(tool_runner, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Public function to get cricket scores."""
    retriever = EnhancedCricketScoreRetriever(tool_runner)
    return retriever.get_cricket_scores()