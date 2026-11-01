import httpx
from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()


@router.get(
    "/search",
    summary="Search wiki page titles",
    description=(
        "Search the Genshin Impact wiki for page titles matching the query. "
        "Returns a list of matching page titles. Use this FIRST to find the exact page title "
        "before calling /page/{title}. Titles use underscores (e.g. 'Hu_Tao', 'Raiden_Shogun')."
    ),
)
async def search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search keyword, e.g. 'Hu Tao', 'sword', 'Mondstadt'"),
    limit: int = Query(10, ge=1, le=50, description="Max number of results to return (1–50, default 10)"),
):
    """Search wiki pages by name."""
    client = request.app.state.wiki
    titles = await client.search(q, limit=limit)
    if not titles:  # title search needs a prefix match; fall back to the page text
        titles = await client.fulltext(q, limit=limit)
    return {"query": q, "results": titles}


@router.get(
    "/fulltext",
    summary="Search inside wiki page text",
    description=(
        "Searches the text of every page and returns the matching titles. "
        "Use it when the answer is a fact rather than a page name, e.g. 'who runs the Wangsheng Funeral Parlor'."
    ),
)
async def fulltext(
    request: Request,
    q: str = Query(..., min_length=1, description="Words to look for in page text"),
    limit: int = Query(10, ge=1, le=50, description="Max number of results to return (1–50, default 10)"),
):
    """Search page text."""
    client = request.app.state.wiki
    return {"query": q, "results": await client.fulltext(q, limit=limit)}


@router.get(
    "/images",
    summary="Find official game art",
    description="Returns image URLs for a character, weapon, artifact set or enemy, matched by name.",
)
async def images(
    request: Request,
    q: str = Query(..., min_length=1, description="Name, e.g. 'Hu Tao', 'Staff of Homa', 'Dvalin'"),
    limit: int = Query(3, ge=1, le=10, description="Max number of results to return (1–10, default 3)"),
):
    """Find artwork by name."""
    try:
        return {"query": q, "results": await request.app.state.images.find(q, limit=limit)}
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Image catalog unavailable")
