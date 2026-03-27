from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/search")
async def search(request: Request, q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    """Search wiki pages by name."""
    client = request.app.state.wiki
    titles = await client.search(q, limit=limit)
    return {"query": q, "results": titles}
