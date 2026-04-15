#!/usr/bin/env python3
"""
MCP Server for Hacker News.

Provides tools to fetch stories, search content, and retrieve user profiles
from Hacker News using the official Firebase API and Algolia search API.
"""

import json
import asyncio
from typing import Optional, List
from enum import Enum

import httpx
from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP

# ─── Server ──────────────────────────────────────────────────────────────────

mcp = FastMCP("hackernews_mcp")

# ─── Constants ───────────────────────────────────────────────────────────────

HN_BASE_URL = "https://hacker-news.firebaseio.com/v0"
ALGOLIA_BASE_URL = "https://hn.algolia.com/api/v1"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"
HN_USER_URL = "https://news.ycombinator.com/user?id={id}"

STORY_TYPE_ENDPOINTS = {
    "top": "topstories",
    "new": "newstories",
    "best": "beststories",
    "ask": "askstories",
    "show": "showstories",
    "job": "jobstories",
}

# ─── Enums ───────────────────────────────────────────────────────────────────

class StoryType(str, Enum):
    TOP = "top"
    NEW = "new"
    BEST = "best"
    ASK = "ask"
    SHOW = "show"
    JOB = "job"

class SearchSort(str, Enum):
    RELEVANCE = "relevance"
    DATE = "date"

class SearchTag(str, Enum):
    STORY = "story"
    COMMENT = "comment"
    ASK_HN = "ask_hn"
    SHOW_HN = "show_hn"
    JOB = "job"

# ─── Input Models ────────────────────────────────────────────────────────────

class GetStoriesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    story_type: StoryType = Field(
        default=StoryType.TOP,
        description="Type of stories: 'top' (front page), 'new' (latest), 'best' (all-time best), 'ask' (Ask HN), 'show' (Show HN), 'job'"
    )
    limit: int = Field(
        default=30,
        description="Number of stories to return (1-100)",
        ge=1,
        le=100
    )

class GetItemInput(BaseModel):
    model_config = ConfigDict(validate_assignment=True, extra="forbid")

    item_id: int = Field(
        ...,
        description="HN item ID (story, comment, job, poll). E.g. 12345678",
        gt=0
    )
    include_comments: bool = Field(
        default=False,
        description="Whether to include top-level comments"
    )
    max_comments: int = Field(
        default=5,
        description="Max number of top-level comments to fetch (1-20)",
        ge=1,
        le=20
    )

class SearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    query: str = Field(
        ...,
        description="Search query (e.g. 'Claude Code', 'MCP server', 'React Vite')",
        min_length=1,
        max_length=300
    )
    tag: SearchTag = Field(
        default=SearchTag.STORY,
        description="Content type filter: 'story', 'comment', 'ask_hn', 'show_hn', 'job'"
    )
    sort: SearchSort = Field(
        default=SearchSort.RELEVANCE,
        description="Sort order: 'relevance' or 'date' (most recent first)"
    )
    limit: int = Field(
        default=20,
        description="Number of results to return (1-50)",
        ge=1,
        le=50
    )

class GetUserInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    username: str = Field(
        ...,
        description="HN username (e.g. 'pg', 'dang', 'tptacek')",
        min_length=1,
        max_length=100
    )

# ─── Shared HTTP helpers ─────────────────────────────────────────────────────

async def _hn_get(path: str) -> dict | list | None:
    """Fetch a single HN Firebase endpoint."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{HN_BASE_URL}/{path}")
        resp.raise_for_status()
        return resp.json()

async def _fetch_items_parallel(ids: List[int], limit: int) -> List[dict]:
    """Fetch up to `limit` HN items in parallel."""
    ids = ids[:limit]
    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [
            client.get(f"{HN_BASE_URL}/item/{item_id}.json")
            for item_id in ids
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    items = []
    for r in responses:
        if isinstance(r, Exception):
            continue
        try:
            data = r.json()
            if data:
                items.append(data)
        except Exception:
            continue
    return items

def _handle_error(e: Exception) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 404:
            return "Error: Item not found."
        if code == 429:
            return "Error: Rate limit exceeded. Wait a moment and retry."
        return f"Error: HN API returned status {code}."
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. HN API may be slow — retry."
    return f"Error: {type(e).__name__}: {e}"

def _format_unix(ts: Optional[int]) -> str:
    if not ts:
        return "unknown"
    from datetime import datetime, timezone
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def _story_to_dict(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "title": item.get("title", "(no title)"),
        "url": item.get("url", f"https://news.ycombinator.com/item?id={item.get('id')}"),
        "hn_url": HN_ITEM_URL.format(id=item.get("id")),
        "score": item.get("score", 0),
        "by": item.get("by", "unknown"),
        "time": _format_unix(item.get("time")),
        "comments": item.get("descendants", 0),
        "type": item.get("type", "story"),
        "text": item.get("text"),  # for Ask HN
    }

# ─── Tools ───────────────────────────────────────────────────────────────────

@mcp.tool(
    name="hn_get_stories",
    annotations={
        "title": "Get HN Stories",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def hn_get_stories(params: GetStoriesInput) -> str:
    """
    Fetch stories from Hacker News by type (top, new, best, ask, show, job).

    Returns a ranked list with title, URL, score, author, date, and comment count.
    Use story_type='top' for the current front page (default).
    Use story_type='ask' for Ask HN threads, 'show' for Show HN projects.

    Args:
        params (GetStoriesInput):
            - story_type: 'top' | 'new' | 'best' | 'ask' | 'show' | 'job'
            - limit: number of stories (1-100, default 30)

    Returns:
        str: JSON list of stories with id, title, url, hn_url, score, by, time, comments.

    Examples:
        - "Get top 30 HN stories" → story_type='top', limit=30
        - "Latest Show HN projects" → story_type='show', limit=20
        - "Best Ask HN threads" → story_type='ask', limit=10
    """
    try:
        endpoint = STORY_TYPE_ENDPOINTS[params.story_type.value]
        ids: List[int] = await _hn_get(f"{endpoint}.json")
        if not ids:
            return json.dumps({"stories": [], "total_available": 0})

        items = await _fetch_items_parallel(ids, params.limit)
        stories = [_story_to_dict(item) for item in items if item.get("type") in ("story", "job", "poll")]

        return json.dumps({
            "story_type": params.story_type.value,
            "count": len(stories),
            "total_available": len(ids),
            "stories": stories
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="hn_get_item",
    annotations={
        "title": "Get HN Item Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def hn_get_item(params: GetItemInput) -> str:
    """
    Fetch full details of a Hacker News item (story, comment, job, poll).

    Optionally includes top-level comments. Use this to read an Ask HN thread
    body, get comment context, or fetch full story metadata.

    Args:
        params (GetItemInput):
            - item_id (int): HN item ID (e.g. 12345678)
            - include_comments (bool): fetch top-level comments (default False)
            - max_comments (int): max comments to fetch (1-20, default 5)

    Returns:
        str: JSON with full item data and optional comments array.

    Examples:
        - "Get story 12345678" → item_id=12345678
        - "Read Ask HN thread with comments" → item_id=..., include_comments=True
    """
    try:
        item = await _hn_get(f"item/{params.item_id}.json")
        if not item:
            return f"Error: Item {params.item_id} not found."

        result = _story_to_dict(item)
        result["kids"] = item.get("kids", [])

        if params.include_comments and item.get("kids"):
            comment_ids = item["kids"][:params.max_comments]
            comments_raw = await _fetch_items_parallel(comment_ids, params.max_comments)
            result["top_comments"] = [
                {
                    "id": c.get("id"),
                    "by": c.get("by", "unknown"),
                    "time": _format_unix(c.get("time")),
                    "text": c.get("text", ""),
                    "reply_count": len(c.get("kids", [])),
                }
                for c in comments_raw
                if not c.get("deleted") and not c.get("dead")
            ]

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="hn_search",
    annotations={
        "title": "Search Hacker News",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def hn_search(params: SearchInput) -> str:
    """
    Search Hacker News content via Algolia API.

    Supports full-text search across stories, comments, Ask HN, Show HN, and jobs.
    Sort by relevance (default) or by date (most recent first).

    Args:
        params (SearchInput):
            - query (str): search terms (e.g. 'Claude Code', 'MCP server React')
            - tag: 'story' | 'comment' | 'ask_hn' | 'show_hn' | 'job'
            - sort: 'relevance' | 'date'
            - limit: results count (1-50, default 20)

    Returns:
        str: JSON with matched items including title, url, score, author, date.

    Examples:
        - "Search HN for MCP server" → query='MCP server', tag='story'
        - "Latest comments about Claude" → query='Claude', tag='comment', sort='date'
        - "Recent Show HN AI projects" → query='AI agent', tag='show_hn', sort='date'
    """
    try:
        endpoint = "search_by_date" if params.sort == SearchSort.DATE else "search"
        tag_map = {
            "story": "story",
            "comment": "comment",
            "ask_hn": "ask_hn",
            "show_hn": "show_hn",
            "job": "job",
        }
        tag_value = tag_map[params.tag.value]

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{ALGOLIA_BASE_URL}/{endpoint}",
                params={
                    "query": params.query,
                    "tags": tag_value,
                    "hitsPerPage": params.limit,
                }
            )
            resp.raise_for_status()
            data = resp.json()

        hits = data.get("hits", [])
        if not hits:
            return json.dumps({"query": params.query, "count": 0, "results": []})

        results = []
        for h in hits:
            obj_id = h.get("objectID") or h.get("story_id")
            results.append({
                "id": obj_id,
                "title": h.get("title") or h.get("story_title") or "(comment)",
                "url": h.get("url") or (HN_ITEM_URL.format(id=obj_id) if obj_id else None),
                "hn_url": HN_ITEM_URL.format(id=obj_id) if obj_id else None,
                "score": h.get("points") or h.get("score", 0),
                "by": h.get("author", "unknown"),
                "time": h.get("created_at", "unknown"),
                "comments": h.get("num_comments", 0),
                "text_snippet": (h.get("comment_text") or h.get("story_text") or "")[:300] or None,
            })

        return json.dumps({
            "query": params.query,
            "tag": params.tag.value,
            "sort": params.sort.value,
            "count": len(results),
            "total_found": data.get("nbHits", len(results)),
            "results": results,
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="hn_get_user",
    annotations={
        "title": "Get HN User Profile",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)
async def hn_get_user(params: GetUserInput) -> str:
    """
    Fetch a Hacker News user's public profile.

    Returns karma score, account age, bio, and list of recent submission IDs.

    Args:
        params (GetUserInput):
            - username (str): HN username (e.g. 'pg', 'dang', 'tptacek')

    Returns:
        str: JSON with id, karma, created, about, submitted_count, recent_submissions.

    Examples:
        - "HN profile of pg" → username='pg'
        - "How much karma does tptacek have?" → username='tptacek'
    """
    try:
        user = await _hn_get(f"user/{params.username}.json")
        if not user:
            return f"Error: User '{params.username}' not found."

        return json.dumps({
            "id": user.get("id"),
            "karma": user.get("karma", 0),
            "created": _format_unix(user.get("created")),
            "about": user.get("about"),
            "hn_url": HN_USER_URL.format(id=user.get("id")),
            "submitted_count": len(user.get("submitted", [])),
            "recent_submission_ids": user.get("submitted", [])[:20],
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        return _handle_error(e)


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
