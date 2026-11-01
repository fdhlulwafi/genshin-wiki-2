from fastapi import APIRouter, HTTPException, Query, Request, Response
from urllib.parse import quote

from config import PUBLIC_URL
from wiki.client import PageNotFoundError

router = APIRouter()


@router.get(
    "/art",
    summary="Find wiki artwork by file name",
    description=(
        "Lists picture files on the wiki whose name starts with the query, each with a URL that serves the picture as a JPEG. "
        "Useful prefixes: '<Character> Birthday' (yearly birthday art, '- Shorts' files are vertical), '<Character> Card', "
        "'<Character> Full Wish', '<Weapon> Wish'. Icons are left out."
    ),
)
async def art(
    request: Request,
    q: str = Query(..., min_length=2, description="File name prefix, e.g. 'Hu Tao Birthday'"),
    limit: int = Query(20, ge=1, le=50, description="Max number of results to return (1–50, default 20)"),
):
    """Find artwork files."""
    files = await request.app.state.wiki.find_files(q, limit=limit)
    for f in files:
        f["url"] = f"{PUBLIC_URL}/art/file/{quote(f['name'], safe='')}"
    return {"query": q, "results": files}


@router.get(
    "/art/file/{name}",
    summary="Serve one wiki picture",
    description="The picture as a JPEG up to 1280 px wide. Names come from /art.",
    response_class=Response,
    responses={200: {"content": {"image/jpeg": {}}}},
)
async def art_file(request: Request, name: str):
    """Serve a wiki picture."""
    try:
        data = await request.app.state.wiki.picture(name)
    except PageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Picture not found: {name}")
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
