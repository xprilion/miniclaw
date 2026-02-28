# Cricket Scores Plugin

The Cricket Scores plugin provides a robust way to retrieve current cricket match scores using a multi-step strategy that prioritizes reliability and accuracy.

## Multi-Step Retrieval Strategy

The plugin implements a four-step approach to ensure the best possible results:

### 1. Direct API Calls
First, the plugin attempts to fetch scores from reliable cricket score services:
- **Cricbuzz API**: Tries to fetch live scores from Cricbuzz
- **ESPN Cricinfo**: Attempts to get scores from ESPN Cricinfo

### 2. Web Scraping with Proper Headers
If direct API calls fail, the plugin falls back to web scraping:
- Uses proper headers to avoid blocking
- Implements retry logic with exponential backoff
- Parses HTML content to extract score information

### 3. Smart Fallback Parsing
When standard scraping fails:
- Uses browser extraction for better content parsing
- Applies regex patterns to extract score information from text
- Handles various HTML structures and formats

### 4. Web Search as Last Resort
As a final fallback, the plugin uses web search:
- Performs a search for "live cricket scores"
- Parses search results for score information
- Extracts team names and scores from search snippets

## Features

- **Retry Logic**: Each step includes retry mechanisms with exponential backoff
- **Error Handling**: Comprehensive error handling and logging
- **Clear Reporting**: Detailed logs of all attempts and their results
- **Persistence**: Continues trying until all options are exhausted
- **Smart Parsing**: Uses multiple regex patterns to extract scores from different sources

## Usage

To use the cricket scores plugin, simply call the `get_cricket_scores` tool:

```json
{
  "tool": "get_cricket_scores",
  "arguments": {}
}
```

## Response Format

The plugin returns a structured response:

```json
{
  "success": true,
  "scores": [
    {
      "teams": "IND vs AUS",
      "score": "250/4 (45.2 Ov)",
      "status": "Live"
    }
  ],
  "attempt_log": [
    "Attempted Cricbuzz API",
    "Attempted ESPN Cricinfo"
  ],
  "total_attempts": 2,
  "message": "Successfully retrieved 1 cricket score(s)"
}
```

## Configuration

No special configuration is required. The plugin uses existing tools:
- `fetch_url` for HTTP requests
- `browser_extract` for advanced parsing
- `brave_search` for fallback search

## Error Handling

The plugin provides detailed error information:

```json
{
  "success": false,
  "scores": [],
  "attempt_log": [
    "Attempted Cricbuzz API: Connection failed",
    "Attempted ESPN Cricinfo: Timeout",
    "Web scraping failed: Parse error",
    "Used web search as fallback: No results found"
  ],
  "total_attempts": 4,
  "message": "Failed to retrieve cricket scores after all attempts",
  "error": "No scores found from any source"
}
```

## Development

To extend or modify the plugin:

1. **Adding New Sources**: Add new methods following the existing pattern (`_get_source_scores`)
2. **Improving Parsing**: Enhance the `_extract_scores_from_html` method with additional regex patterns
3. **Adjusting Retry Logic**: Modify `max_retries` and `retry_delay` constants
4. **Adding Logging**: Use the existing logger for consistent logging

## Testing

Run the test suite with:

```bash
cd miniclaw
python -m pytest tests/test_cricket_scores.py -v
```

The tests include mocks for all external services to ensure consistent testing.