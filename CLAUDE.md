# Genshin Wiki API v2

## Overview
Live-scraping REST API for the Genshin Impact Fandom Wiki. No local storage — every request fetches from `https://genshin-impact.fandom.com/api.php` with a short in-memory TTL cache. Designed for LLM consumption.

## Tech Stack
- **Python 3.12** / **FastAPI** / **uvicorn**
- **httpx** — async HTTP client
- **beautifulsoup4** — HTML parsing (rendered HTML via MediaWiki `action=parse`)

## Project Structure
```
genshin-wiki-2/
├── main.py              # Entry point — runs uvicorn with factory
├── config.py            # All constants & env vars (no .env file, uses os.getenv)
├── requirements.txt
├── Dockerfile
├── wiki/
│   ├── cache.py         # TTLCache — OrderedDict-based, LRU eviction, per-entry timestamps
│   ├── client.py        # WikiClient — single shared instance, rate-limited (Semaphore(1)), retry with backoff
│   └── parser.py        # HTML→clean text, infobox extraction, table→pipe-delimited, section splitting
└── api/
    ├── app.py           # FastAPI app factory with lifespan (creates/closes WikiClient on app.state.wiki)
    └── routes/
        ├── search.py    # GET /search
        ├── pages.py     # GET /page/{title}, /page/{title}/sections, /page/{title}/section/{index}
        └── categories.py # GET /category/{name}
```

## Key Architecture Decisions
- **App factory pattern**: `api/app.py:create_app()` — uvicorn calls it via `factory=True`
- **WikiClient lifecycle**: created in `lifespan` context manager, stored on `app.state.wiki`, accessed via `request.app.state.wiki` in route handlers
- **Route ordering in pages.py**: `/page/{title}/sections` and `/page/{title}/section/{index}` are registered BEFORE `/page/{title}` to avoid the catch-all matching sub-paths
- **No `:path` converter on page routes**: wiki titles use underscores (e.g. `Hu_Tao`), not slashes
- **Cache key**: `str(sorted(params.items()))` — deterministic string from query params
- **HTML parsing uses `action=parse&prop=text`** (rendered HTML), not raw wikitext — MediaWiki expands all templates

## Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL` | `300` | Cache entry lifetime in seconds |
| `CACHE_MAX_SIZE` | `500` | Max cached entries before LRU eviction |
| `REQUEST_DELAY` | `0.15` | Seconds between wiki API requests |
| `MAX_RETRIES` | `3` | Retry attempts on failed requests |
| `REQUEST_TIMEOUT` | `15` | HTTP request timeout in seconds |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |

## Running
```bash
pip install -r requirements.txt
python main.py
# or: docker build -t genshin-wiki . && docker run -p 8000:8000 genshin-wiki
```

## API Endpoints
| Endpoint | Purpose |
|----------|---------|
| `GET /` | Service info + endpoint list (LLM discovery) |
| `GET /health` | Health check |
| `GET /search?q=term&limit=10` | Search wiki page titles (MediaWiki opensearch) |
| `GET /page/{title}` | Full page as clean text + section index. `?format=structured` for infobox dict + keyed sections |
| `GET /page/{title}/sections` | Section names & indexes only (lightweight) |
| `GET /page/{title}/section/{index}` | Single section by index |
| `GET /category/{name}?limit=50` | List pages in a wiki category |

## Conventions
- All config lives in `config.py` — no scattered env reads
- Route handlers access WikiClient via `request.app.state.wiki`
- Errors from wiki: `PageNotFoundError` → HTTP 404, `WikiClientError` → HTTP 500
- Parser functions are pure (take HTML string, return data) — no side effects
- No persistent storage, no database, no files written at runtime
