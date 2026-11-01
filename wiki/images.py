from __future__ import annotations

import re
import time

import httpx

from config import IMAGE_API_URL, IMAGE_ASSET_URL, IMAGE_CATALOG_TTL, REQUEST_TIMEOUT

# Fandom's image host answers servers with a bot check, so artwork comes from Project Yatta's game asset mirror.


def _character(icon: str) -> str:
    return f"{IMAGE_ASSET_URL}/{icon.replace('UI_AvatarIcon_', 'UI_Gacha_AvatarImg_')}.png"


def _weapon(icon: str) -> str:
    return f"{IMAGE_ASSET_URL}/{icon.replace('UI_EquipIcon_', 'UI_Gacha_EquipIcon_')}.png"


def _artifact(icon: str) -> str:
    return f"{IMAGE_ASSET_URL}/reliquary/{icon}.png"


def _enemy(icon: str) -> str:
    return f"{IMAGE_ASSET_URL}/monster/{icon}.png"


KINDS = {"avatar": ("character", _character), "weapon": ("weapon", _weapon),
         "reliquary": ("artifact", _artifact), "monster": ("enemy", _enemy)}


# Names with their own wiki page, so no redirect leads to the playable character.
ALIASES = {"ei": "Raiden Shogun", "childe": "Tartaglia", "ajax": "Tartaglia"}


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


class ImageCatalog:
    """Name -> artwork URL for characters, weapons, artifact sets and enemies, refreshed a few times a day."""

    def __init__(self) -> None:
        self._items: list[dict] = []
        self._loaded = 0.0

    async def _load(self) -> None:
        if self._items and time.monotonic() - self._loaded < IMAGE_CATALOG_TTL:
            return
        items: dict[str, dict] = {}
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as http:
            for endpoint, (kind, url) in KINDS.items():
                resp = await http.get(f"{IMAGE_API_URL}/{endpoint}")
                resp.raise_for_status()
                for item in resp.json()["data"]["items"].values():
                    items.setdefault(item["name"], {"name": item["name"], "type": kind, "url": url(item["icon"])})
        self._items = list(items.values())
        self._loaded = time.monotonic()

    def _match(self, query: str) -> list[dict]:
        """Exact name first, then names containing the query as whole words (so 'Ei' is not Beidou)."""
        q = _norm(query)
        exact = [i for i in self._items if _norm(i["name"]) == q]
        partial = [i for i in self._items if f" {q} " in f" {_norm(i['name'])} " and i not in exact]
        return exact + partial

    async def find(self, query: str, canonical: str | None = None, limit: int = 3) -> list[dict]:
        """Art for a name. canonical is the wiki's own name for it, e.g. Wanderer for Scaramouche."""
        await self._load()
        for name in (canonical, query):
            found = self._match(ALIASES.get(_norm(name), name)) if name else []
            if found:
                return found[:limit]
        return []
