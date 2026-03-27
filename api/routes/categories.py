from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get(
    "/category/{name:path}",
    summary="List pages in a wiki category",
    description=(
        "Returns all page titles belonging to a Genshin Impact wiki category. "
        "Useful for discovering all characters, weapons, or items of a specific type. "
        "Example category names: 'Pyro_Characters', 'Swords', 'Mondstadt', 'Version_4.0'. "
        "Category names use underscores and are case-sensitive."
    ),
)
async def get_category(
    request: Request,
    name: str,
    limit: int = Query(50, ge=1, le=500, description="Max number of pages to return (1–500, default 50)"),
):
    """List pages in a wiki category."""
    client = request.app.state.wiki
    pages = await client.get_category_members(name, limit=limit)
    return {"category": name, "count": len(pages), "pages": pages}
