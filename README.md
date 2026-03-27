# Genshin Wiki API v2

Live-scraping REST API for the [Genshin Impact Fandom Wiki](https://genshin-impact.fandom.com/wiki/). Fetches and parses wiki content on every request with in-memory caching. Designed for LLM consumption — search, browse sections, and drill into specific data.

## Features

- **Live scraping** — no local data storage, always up-to-date
- **Clean text output** — HTML stripped, tables converted to pipe-delimited format, headings as markdown
- **Structured format** — optional infobox extraction + keyed sections dict
- **Section-level access** — fetch just the section you need instead of entire pages
- **In-memory TTL cache** — 5-minute default, avoids hammering the wiki
- **Rate limiting** — semaphore-based request throttling with exponential backoff retry

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

The API runs on `http://localhost:8000` by default.

### Docker

```bash
docker build -t genshin-wiki .
docker run -p 8000:8000 genshin-wiki
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Service info and endpoint list |
| `GET /health` | Health check |
| `GET /search?q=term&limit=10` | Search wiki pages by name |
| `GET /page/{title}` | Full page as clean text + section index |
| `GET /page/{title}?format=structured` | Full page with infobox dict + keyed sections |
| `GET /page/{title}/sections` | List section names and indexes (lightweight) |
| `GET /page/{title}/section/{index}` | Fetch a single section by index |
| `GET /category/{name}?limit=50` | List pages in a wiki category |

## Usage Example

**1. Search for a character:**

```
GET /search?q=raiden shogun
```
```json
{
  "query": "raiden shogun",
  "results": ["Raiden Shogun", "Raiden Shogun/Voice-Overs", "Raiden Shogun/Lore", ...]
}
```

**2. List available sections:**

```
GET /page/Raiden_Shogun/sections
```
```json
{
  "title": "Raiden_Shogun",
  "sections": [
    {"index": 0, "title": "Introduction"},
    {"index": 1, "title": "Gameplay Info"},
    {"index": 2, "title": "Ascensions and Stats"},
    {"index": 3, "title": "Talents"},
    ...
  ]
}
```

**3. Fetch a specific section:**

```
GET /page/Raiden_Shogun/section/3
```
```json
{
  "title": "Raiden_Shogun",
  "section": {
    "index": 3,
    "title": "Talents",
    "content": "### Talents\nNormal Attack\nElemental Skill\n..."
  }
}
```

**4. Get structured data with infobox:**

```
GET /page/Raiden_Shogun?format=structured
```
```json
{
  "title": "Raiden_Shogun",
  "infobox": {"Weapon": "Polearm", "Element": "Electro", "Region": "Inazuma", ...},
  "sections": {"Introduction": "...", "Talents": "...", ...}
}
```

**5. Browse a category:**

```
GET /category/Playable_Characters?limit=10
```
```json
{
  "category": "Playable_Characters",
  "count": 10,
  "pages": ["Aether", "Aino", "Albedo", "Alhaitham", "Aloy", "Amber", ...]
}
```

## Configuration

All settings are configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_TTL` | `300` | Cache lifetime in seconds |
| `CACHE_MAX_SIZE` | `500` | Max cached entries |
| `REQUEST_DELAY` | `0.15` | Delay between wiki API requests (seconds) |
| `MAX_RETRIES` | `3` | Retry attempts on failure |
| `REQUEST_TIMEOUT` | `15` | HTTP timeout in seconds |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |

## Project Structure

```
genshin-wiki-2/
├── main.py                  # Entry point
├── config.py                # Constants & env vars
├── requirements.txt
├── Dockerfile
├── wiki/
│   ├── cache.py             # In-memory TTL cache (OrderedDict + LRU eviction)
│   ├── client.py            # Async MediaWiki API client (rate limit, retry, cache)
│   └── parser.py            # HTML → clean text, infobox extraction, table formatting
└── api/
    ├── app.py               # FastAPI app factory with lifespan
    └── routes/
        ├── search.py        # /search endpoint
        ├── pages.py         # /page/* endpoints
        └── categories.py    # /category/* endpoint
```

## How It Works

1. **WikiClient** (`wiki/client.py`) sends requests to the MediaWiki API at `genshin-impact.fandom.com/api.php`
2. Uses `action=parse&prop=text` to get fully rendered HTML (all templates expanded by MediaWiki)
3. **Parser** (`wiki/parser.py`) strips noise (navboxes, TOC, edit links, scripts), converts tables to pipe-delimited text, splits content into indexed sections
4. Results are cached in-memory for 5 minutes with LRU eviction at 500 entries
5. Rate limiting via `asyncio.Semaphore(1)` ensures only one wiki request at a time

## License

This project scrapes publicly available data from the [Genshin Impact Fandom Wiki](https://genshin-impact.fandom.com/wiki/). All game content belongs to HoYoverse / miHoYo. Wiki content is available under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/).
