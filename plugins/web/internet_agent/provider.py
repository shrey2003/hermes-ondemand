"""Web-search adapter for the Internet Agent API.

The service endpoint is deliberately a constant: it is the public API
described in ``hermes_cli/internet_plugin_schema.yaml``.  It needs no token,
and is exposed through the existing Hermes ``web_search`` tool rather than by
adding another core model tool.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from agent.web_search_provider import WebSearchProvider

logger = logging.getLogger(__name__)

_ENDPOINT = "https://serverless.on-demand.io/apps/commoditiesapi/internet-agent"
_TIMEOUT_SECONDS = 45
_MAX_QUERY_CHARS = 1_000


class InternetAgentWebSearchProvider(WebSearchProvider):
    """Use the Internet Agent API to back Hermes's existing web-search tool."""

    @property
    def name(self) -> str:
        return "internet-agent"

    @property
    def display_name(self) -> str:
        return "Internet Agent API"

    def is_available(self) -> bool:
        # The public endpoint has no credential prerequisite.  Network I/O is
        # intentionally deferred to ``search`` because this gate runs while
        # every agent tool schema is assembled.
        return True

    def supports_search(self) -> bool:
        return True

    def supports_extract(self) -> bool:
        # The endpoint returns extracted page excerpts as part of search; it is
        # not a general URL extraction API.
        return False

    def search(self, query: str, limit: int = 5) -> Dict[str, Any]:
        cleaned_query = (query or "").strip()
        if not cleaned_query:
            return {"success": False, "error": "A non-empty search query is required."}
        if len(cleaned_query) > _MAX_QUERY_CHARS:
            cleaned_query = cleaned_query[:_MAX_QUERY_CHARS]

        payload = json.dumps({"query": cleaned_query}).encode("utf-8")
        request = Request(
            _ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:  # noqa: S310 - fixed HTTPS endpoint
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            return {"success": False, "error": f"Internet Agent API returned HTTP {exc.code}."}
        except (URLError, TimeoutError, OSError) as exc:
            logger.info("Internet Agent API request failed: %s", exc)
            return {"success": False, "error": "Internet Agent API could not be reached."}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {"success": False, "error": "Internet Agent API returned invalid JSON."}

        if not isinstance(body, dict):
            return {"success": False, "error": "Internet Agent API returned an invalid response."}
        if body.get("error"):
            return {"success": False, "error": str(body.get("message") or body["error"])}

        safe_limit = max(1, min(int(limit or 5), 20))
        hits: list[dict[str, Any]] = []
        quick_answer = body.get("quickAnswer")
        if isinstance(quick_answer, dict) and quick_answer.get("answer"):
            hits.append({
                "title": str(quick_answer.get("title") or "Quick answer"),
                "url": str(quick_answer.get("sourceLink") or ""),
                "description": str(quick_answer.get("answer") or ""),
                "position": 0,
            })

        for item in body.get("searchResults") or []:
            if not isinstance(item, dict):
                continue
            description = item.get("pageExcerpt") or item.get("snippet") or ""
            hits.append({
                "title": str(item.get("title") or "Untitled result"),
                "url": str(item.get("link") or ""),
                "description": str(description),
                "position": int(item.get("position") or len(hits) + 1),
            })
            if len(hits) >= safe_limit:
                break
        return {"success": True, "data": {"web": hits[:safe_limit]}}
