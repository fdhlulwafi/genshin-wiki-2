from __future__ import annotations

import asyncio
import logging

import httpx

from config import (
    ART_CACHE_SIZE,
    ART_WIDTH,
    CACHE_MAX_SIZE,
    CACHE_TTL,
    IMAGE_PROXY_URL,
    MAX_RETRIES,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    WIKI_API_URL,
)
from wiki.cache import TTLCache

log = logging.getLogger(__name__)


ART_MIME = {"image/png", "image/jpeg", "image/webp"}
MIN_ART_SIDE = 200  # leaves out icons


class WikiClientError(Exception):
    pass


class PageNotFoundError(WikiClientError):
    pass


class WikiClient:
    """Async MediaWiki API client with rate limiting, retry, and caching."""

    def __init__(self) -> None:
        self._http: httpx.AsyncClient | None = None
        self._semaphore = asyncio.Semaphore(1)
        self._cache = TTLCache(ttl=CACHE_TTL, max_size=CACHE_MAX_SIZE)
        self._pictures = TTLCache(ttl=CACHE_TTL, max_size=ART_CACHE_SIZE)

    async def start(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "GenshinWikiAPI/2.0 (FastAPI)"},
        )

    async def close(self) -> None:
        if self._http:
            await self._http.aclose()
            self._http = None

    async def _get(self, params: dict) -> dict:
        """Rate-limited GET with retry and backoff."""
        cache_key = str(sorted(params.items()))
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        assert self._http is not None, "WikiClient not started"
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES):
            async with self._semaphore:
                try:
                    resp = await self._http.get(WIKI_API_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    self._cache.set(cache_key, data)
                    await asyncio.sleep(REQUEST_DELAY)
                    return data
                except (httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                    last_exc = exc
            wait = 2 ** attempt
            log.warning("Wiki API attempt %d failed: %s — retrying in %ds", attempt + 1, last_exc, wait)
            await asyncio.sleep(wait)

        raise WikiClientError(f"Wiki API request failed after {MAX_RETRIES} retries") from last_exc

    # ── Public API ──────────────────────────────────────────────

    async def search(self, query: str, limit: int = 10) -> list[str]:
        """Search wiki page titles via opensearch."""
        data = await self._get({
            "action": "opensearch",
            "search": query,
            "limit": str(limit),
            "namespace": "0",
        })
        # opensearch returns [query, [titles], [descriptions], [urls]]
        if isinstance(data, list) and len(data) >= 2:
            return data[1]
        return []

    async def fulltext(self, query: str, limit: int = 10) -> list[str]:
        """Search inside page text. Returns matching titles."""
        data = await self._get({
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": str(limit),
            "srnamespace": "0",
            "format": "json",
        })
        hits = data.get("query", {}).get("search", [])
        return [h["title"] for h in hits]

    async def canonical_name(self, name: str) -> str | None:
        """Where the wiki redirects a name: Scaramouche -> Wanderer, Morax -> Zhongli. None if it does not."""
        data = await self._get({"action": "query", "titles": name, "redirects": "1", "format": "json"})
        redirects = data.get("query", {}).get("redirects")
        return redirects[-1]["to"].split("/")[0] if redirects else None

    async def find_files(self, query: str, limit: int = 20) -> list[dict]:
        """Wiki picture files whose name starts with the query ('Hu Tao Birthday'), else files matching it."""
        data = await self._get({
            "action": "query", "list": "allimages", "aiprefix": query.strip().replace(" ", "_"),
            "ailimit": "50", "aiprop": "size|mime", "format": "json",
        })
        files = data.get("query", {}).get("allimages", [])
        if not files:
            data = await self._get({
                "action": "query", "generator": "search", "gsrsearch": query, "gsrnamespace": "6", "gsrlimit": "50",
                "prop": "imageinfo", "iiprop": "size|mime", "format": "json",
            })
            files = [{"title": p["title"].removeprefix("File:"), **p["imageinfo"][0]}
                     for p in data.get("query", {}).get("pages", {}).values() if p.get("imageinfo")]
        out = [{"name": (f.get("title") or f["name"].replace("_", " ")).removeprefix("File:"), "width": f.get("width"), "height": f.get("height")}
               for f in files if f.get("mime") in ART_MIME and (f.get("width") or 0) >= MIN_ART_SIDE]
        return sorted(out, key=lambda f: f["name"])[:limit]

    async def picture(self, name: str) -> bytes:
        """A wiki picture, scaled and re-encoded as JPEG, fetched through the image proxy."""
        cached = self._pictures.get(name)
        if cached is not None:
            return cached
        data = await self._get({
            "action": "query", "titles": f"File:{name}", "prop": "imageinfo", "iiprop": "url|mime", "format": "json",
        })
        info = next(iter(data.get("query", {}).get("pages", {}).values()), {}).get("imageinfo")
        if not info or info[0].get("mime") not in ART_MIME:
            raise PageNotFoundError(f"Picture not found: {name}")
        source = info[0]["url"].split("?")[0].removeprefix("https://")
        assert self._http is not None, "WikiClient not started"
        try:
            resp = await self._http.get(
                IMAGE_PROXY_URL, params={"url": source, "w": ART_WIDTH, "we": "1", "output": "jpg", "q": "85"}, timeout=40,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise WikiClientError(f"Image proxy failed for {name}") from exc
        self._pictures.set(name, resp.content)
        return resp.content

    async def get_page_html(self, title: str) -> str:
        """Fetch rendered HTML for a page."""
        data = await self._get({
            "action": "parse",
            "page": title,
            "prop": "text",
            "format": "json",
            "redirects": "1",
        })
        parse = data.get("parse")
        if not parse:
            error = data.get("error", {})
            if error.get("code") in ("missingtitle", "invalidtitle"):
                raise PageNotFoundError(f"Page not found: {title}")
            raise WikiClientError(f"Wiki API error for {title}: {error.get('code', 'no parse result')}")
        return parse["text"]["*"]

    async def get_category_members(self, category: str, limit: int = 50, subpages: bool = False) -> list[str]:
        """List page titles in a category, leaving out subpages like 'Hu Tao/Storyline' unless asked."""
        results: list[str] = []
        params: dict = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": str(min(limit, 50)),
            "cmtype": "page",
            "format": "json",
        }

        while len(results) < limit:
            data = await self._get(params)
            members = data.get("query", {}).get("categorymembers", [])
            results.extend(m["title"] for m in members if subpages or "/" not in m["title"])

            cont = data.get("continue", {}).get("cmcontinue")
            if not cont or len(results) >= limit:
                break
            params["cmcontinue"] = cont

        return results[:limit]
