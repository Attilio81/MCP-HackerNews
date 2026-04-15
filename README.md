# MCP HackerNews

Un server [Model Context Protocol](https://modelcontextprotocol.io) per Hacker News, costruito con Python + FastMCP.

Gira in locale — nessuna restrizione di proxy, nessuna API key necessaria.

## Strumenti

| Strumento | Descrizione |
|-----------|-------------|
| `hn_get_stories` | Recupera storie per tipo: `top`, `new`, `best`, `ask`, `show`, `job` |
| `hn_get_item` | Dettagli completi di un item + commenti di primo livello (opzionale) |
| `hn_search` | Ricerca full-text tramite Algolia (ordina per rilevanza o data) |
| `hn_get_user` | Profilo utente: karma, data di iscrizione, bio |

## Requisiti

- Python 3.10+
- pip

## Installazione

```bash
git clone https://github.com/Attilio81/MCP-HackerNews.git
cd MCP-HackerNews
```

**Crea un ambiente virtuale (consigliato):**

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

**Installa le dipendenze:**

```bash
pip install -r requirements.txt
```

**Verifica che il server parta:**

```bash
python server.py
```

## Configurazione Claude Code

Aggiungi al file di impostazioni MCP:

**macOS / Linux** — `~/.claude/settings.json`

**Windows** — `%APPDATA%\Claude\settings.json`

```json
{
  "mcpServers": {
    "hackernews": {
      "command": "python3",
      "args": ["/percorso/assoluto/MCP-HackerNews/server.py"]
    }
  }
}
```

> **Esempio Windows:**
> ```json
> {
>   "mcpServers": {
>     "hackernews": {
>       "command": "python",
>       "args": ["C:\\Users\\TuoNome\\MCP-HackerNews\\server.py"]
>     }
>   }
> }
> ```
>
> Se usi un ambiente virtuale, punta al Python al suo interno:
> ```
> C:\Users\TuoNome\MCP-HackerNews\.venv\Scripts\python.exe
> ```

Riavvia Claude Code dopo aver salvato.

## Configurazione Claude Desktop

Aggiungi a `claude_desktop_config.json`:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hackernews": {
      "command": "python",
      "args": ["C:\\Users\\TuoNome\\MCP-HackerNews\\server.py"]
    }
  }
}
```

## Esempi

```
# Front page attuale
hn_get_stories(story_type="top", limit=30)

# Ultimi progetti Show HN
hn_get_stories(story_type="show", limit=20)

# Cerca notizie sui server MCP (più recenti)
hn_search(query="MCP server", tag="story", sort="date", limit=20)

# Leggi un thread Ask HN con commenti
hn_get_item(item_id=12345678, include_comments=True, max_comments=10)

# Controlla il karma di un utente
hn_get_user(username="pg")
```

## Sorgenti API

- **Storie & Item**: [HN Firebase API](https://github.com/HackerNews/API) — ufficiale, senza chiave
- **Ricerca**: [Algolia HN Search](https://hn.algolia.com/api) — gratuita, senza chiave

## Task Schedulati & Automazione

Vuoi ricevere digest HN, report sull'AI o alert automatici ogni mattina?

→ Leggi [**guida-schedule-hackernews.md**](guida-schedule-hackernews.md) per una guida completa su come creare task schedulati con il Cowork scheduler che usano questo server MCP.

Esempi inclusi:
- Digest AI giornaliero salvato in markdown
- Alert Show HN filtrato per score
- Report settimanale "best of AI" in HTML

## Licenza

MIT
