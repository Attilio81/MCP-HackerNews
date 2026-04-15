# MCP HackerNews

A [Model Context Protocol](https://modelcontextprotocol.io) server for Hacker News, built with Python + FastMCP.

Runs locally — no proxy restrictions, no API key needed.

## Tools

| Tool | Description |
|------|-------------|
| `hn_get_stories` | Fetch stories by type: `top`, `new`, `best`, `ask`, `show`, `job` |
| `hn_get_item` | Full item details + optional top-level comments |
| `hn_search` | Full-text search via Algolia (sort by relevance or date) |
| `hn_get_user` | User profile: karma, creation date, bio |

## Prerequisites

- Python 3.10+
- pip

## Installation

```bash
git clone https://github.com/Attilio81/MCP-HackerNews.git
cd MCP-HackerNews
```

**Create a virtual environment (recommended):**

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

**Test the server starts:**

```bash
python server.py
```

## Configure Claude Code

Add to your MCP settings file:

**macOS / Linux** — `~/.claude/settings.json`

**Windows** — `%APPDATA%\Claude\settings.json`

```json
{
  "mcpServers": {
    "hackernews": {
      "command": "python3",
      "args": ["/absolute/path/to/MCP-HackerNews/server.py"]
    }
  }
}
```

> **Windows example:**
> ```json
> {
>   "mcpServers": {
>     "hackernews": {
>       "command": "python",
>       "args": ["C:\\Users\\YourName\\MCP-HackerNews\\server.py"]
>     }
>   }
> }
> ```
>
> If using a virtual environment, point to the Python inside it:
> ```
> C:\Users\YourName\MCP-HackerNews\.venv\Scripts\python.exe
> ```

Restart Claude Code after saving.

## Configure Claude Desktop

Add to `claude_desktop_config.json`:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hackernews": {
      "command": "python",
      "args": ["C:\\Users\\YourName\\MCP-HackerNews\\server.py"]
    }
  }
}
```

## Examples

```
# Current front page
hn_get_stories(story_type="top", limit=30)

# Latest Show HN projects
hn_get_stories(story_type="show", limit=20)

# Search for MCP server news (most recent)
hn_search(query="MCP server", tag="story", sort="date", limit=20)

# Read an Ask HN thread with comments
hn_get_item(item_id=12345678, include_comments=True, max_comments=10)

# Check a user's karma
hn_get_user(username="pg")
```

## API Sources

- **Stories & Items**: [HN Firebase API](https://github.com/HackerNews/API) — official, no key needed
- **Search**: [Algolia HN Search](https://hn.algolia.com/api) — free, no key needed

## Scheduled Tasks & Automation

Want to run HN digests, AI reports, or alerts automatically every morning?

→ See [**guida-schedule-hackernews.md**](guida-schedule-hackernews.md) for a full guide on creating scheduled tasks with the Cowork scheduler that use this MCP server.

Examples covered:
- Daily AI digest saved as markdown
- Show HN alert filtered by score
- Weekly best-of-AI HTML report

## License

MIT
