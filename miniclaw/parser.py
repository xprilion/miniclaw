"""HTML parsing for browser_extract tool."""
from __future__ import annotations

from html.parser import HTMLParser
from typing import Dict, List, Optional


class HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self._in_title = False
        self._text_parts: List[str] = []
        self.links: List[Dict[str, str]] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: List[tuple]) -> None:
        lower = str(tag or "").lower()
        if lower in {"script", "style", "noscript"}:
            self._skip_depth += 1
            return
        if lower == "title":
            self._in_title = True
            return
        if lower == "a":
            href = ""
            for key, value in attrs:
                if str(key or "").lower() == "href":
                    href = str(value or "").strip()
                    break
            if href:
                self.links.append({"href": href})

    def handle_endtag(self, tag: str) -> None:
        lower = str(tag or "").lower()
        if lower in {"script", "style", "noscript"}:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if lower == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = str(data or "").strip()
        if not text:
            return
        if self._in_title:
            if not self.title:
                self.title = text
            return
        self._text_parts.append(text)

    def text(self, max_chars: int = 8000) -> str:
        joined = " ".join(self._text_parts)
        if len(joined) <= max_chars:
            return joined
        return joined[:max_chars]
