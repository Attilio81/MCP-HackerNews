# Guida: Schedule + Server MCP HackerNews in Cowork

Come creare task automatici che leggono HackerNews e generano report, file HTML, digest o qualsiasi altro output — eseguiti in autonomia ogni mattina (o quando vuoi).

---

## Cos'è lo Scheduler

Lo scheduler di Cowork permette di definire un **task che Claude esegue automaticamente** a orari prestabiliti, senza che tu sia presente. Il task è semplicemente un prompt testuale: Claude lo legge, lo esegue usando tutti gli strumenti disponibili (MCP, web search, file, shell), e salva l'output nella tua cartella.

Ogni task ha:
- un **ID univoco** (stringa, es. `ai-github-morning-report`)
- un **prompt** (le istruzioni complete che Claude seguirà)
- una **schedule** (cron expression o data/ora unica)
- uno stato **enabled/disabled**

---

## Il Server MCP HackerNews

Il server MCP HackerNews espone tre strumenti che Claude può chiamare direttamente:

### `hn_get_stories`
Recupera le storie dalla front page o dalle sezioni speciali.

```
story_type: "top" | "new" | "best" | "ask" | "show" | "job"
limit: 1–100 (default 30)
```

Esempi pratici nel prompt:
```
hn_get_stories(story_type="top", limit=30)    → front page del momento
hn_get_stories(story_type="show", limit=20)   → Show HN recenti
hn_get_stories(story_type="ask", limit=10)    → Ask HN
```

Ogni storia restituisce: `id`, `title`, `url`, `hn_url`, `score`, `by`, `time`, `comments`.

---

### `hn_search`
Ricerca full-text su tutto HackerNews tramite Algolia. Molto più potente di `hn_get_stories` per trovare contenuti specifici.

```
query: stringa di ricerca
tag:   "story" | "comment" | "ask_hn" | "show_hn" | "job"
sort:  "relevance" | "date"
limit: 1–50
```

Esempi pratici nel prompt:
```
hn_search(query="Claude Code MCP", tag="story", sort="date", limit=15)
hn_search(query="Show HN Python agent", tag="show_hn", sort="date", limit=10)
hn_search(query="dotnet AI semantic kernel", tag="story", sort="relevance", limit=10)
```

---

### `hn_get_item`
Recupera un singolo item (storia o commento) per ID.

```
item_id: numero intero (es. 47768133)
```

Utile quando vuoi approfondire una storia specifica o leggere i commenti.

---

## Creare un Task Schedulato

Il modo più semplice è **descrivere cosa vuoi a Claude** in chat — lui userà lo strumento `create_scheduled_task` automaticamente. In alternativa, puoi strutturare la richiesta così:

> "Crea un task schedulato che ogni mattina alle 8 legge le top 20 storie di HackerNews, filtra quelle sull'AI, e salva un file markdown nella cartella outputs con titolo, link e breve sintesi."

### Campi che puoi specificare

| Campo | Descrizione | Esempio |
|---|---|---|
| `taskId` | Nome identificativo univoco | `hn-digest-mattino` |
| `description` | Etichetta breve visibile nella UI | `Digest HN mattutino` |
| `prompt` | Le istruzioni complete per Claude | vedi sotto |
| `cronExpression` | Orario ricorrente (ora locale) | `0 8 * * 1-5` |
| `fireAt` | Esecuzione una tantum | `2026-04-16T08:00:00+02:00` |
| `enabled` | Attivo o in pausa | `true` / `false` |

### Sintassi cron (ora locale, non UTC)

```
┌─ minuto  (0–59)
│ ┌─ ora   (0–23)
│ │ ┌─ giorno del mese (1–31)
│ │ │ ┌─ mese (1–12)
│ │ │ │ ┌─ giorno della settimana (0=dom, 1=lun … 6=sab)
│ │ │ │ │
0 8 * * 1-5    → ogni lunedì–venerdì alle 08:00
0 7 * * *      → ogni giorno alle 07:00
30 9 * * 1     → ogni lunedì alle 09:30
0 8 1 * *      → il primo del mese alle 08:00
```

---

## Struttura consigliata per un prompt di task HN

Un prompt ben scritto ha queste sezioni:

```markdown
## Obiettivo
[Cosa deve produrre il task — tipo di file, contenuto, destinatario]

## Fonti (esegui in parallelo)
- hn_get_stories(story_type="top", limit=30)
- hn_search(query="...", tag="story", sort="date", limit=15)
- hn_search(query="...", tag="show_hn", sort="date", limit=10)

## Criteri di selezione
[Come filtrare le storie — topic, score minimo, ultime 24h, ecc.]

## Contenuto da generare
[Formato dell'output: markdown, HTML, testo — e cosa includere per ogni storia]

## Salvataggio
Salva il file come: /sessions/[session-id]/mnt/outputs/nome_YYYY-MM-DD.ext
```

**Nota importante:** il task gira senza che tu sia presente, quindi il prompt deve essere **autosufficiente** — nessuna domanda aperta, nessuna scelta ambigua da fare a runtime. Se qualcosa non è trovabile, specifica il comportamento di fallback ("se non ci sono storie recenti, usa le top weekly").

---

## Gestire i Task Esistenti

Claude può elencare, modificare e disabilitare i task con comandi naturali:

> "Mostrami i task schedulati attivi"  
> "Modifica il prompt del task `hn-digest-mattino`"  
> "Disabilita il task del report mattutino fino a lunedì"  
> "Cambia l'orario del task a 07:30"  
> "Esegui subito il task `ai-github-morning-report`"

---

## Esempi di Task Utili con HackerNews

### Digest quotidiano AI (markdown)
```
Ogni mattina alle 7:30 nei giorni feriali:
- Prendi le top 30 storie HN + cerca "AI LLM agent" nelle ultime 24h
- Seleziona le 5 più rilevanti per uno sviluppatore .NET/C#
- Salva un file markdown con titolo, link, sintesi di 2 righe
- Nome file: hn_digest_YYYY-MM-DD.md
```

### Alert Show HN con GitHub
```
Ogni giorno alle 9:00:
- Cerca Show HN con repo GitHub nelle ultime 48h
- Filtra solo quelli con score > 50
- Salva una lista con nome repo, link, descrizione breve
```

### Weekly best of AI (venerdì)
```
Ogni venerdì alle 18:00:
- Prendi le best stories della settimana su HN
- Filtra per keyword: AI, LLM, Claude, agent, MCP, dotnet, react
- Genera un HTML con layout a righe, dark theme
- Un paragrafo di analisi per ognuna
```

---

## Note Operative

- I task in **esecuzione automatica** non possono interagire con te — se il prompt è ambiguo, Claude fa scelte autonome e le documenta nell'output.
- I file salvati in `outputs/` restano disponibili anche dopo la sessione.
- Lo scheduler usa l'**ora locale** del tuo sistema, non UTC — tienilo presente quando imposti il cron.
- Se un task usa connettori MCP (HN, web search, ecc.), la prima volta conviene eseguirlo manualmente con "Run now" per pre-approvare i permessi — così le esecuzioni automatiche successive non si bloccano in attesa di conferma.
