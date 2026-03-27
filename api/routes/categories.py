from fastapi import APIRouter, Query, Request

router = APIRouter()


@router.get("/category/{name:path}")
async def get_category(request: Request, name: str, limit: int = Query(50, ge=1, le=500)):
    """List pages in a wiki category."""
    client = request.app.state.wiki
    pages = await client.get_category_members(name, limit=limit)
    return {"category": name, "count": len(pages), "pages": pages}
