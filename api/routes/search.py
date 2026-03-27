from fastapi import APIRouter, Query, Request

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
    return {"query": q, "results": titles}
