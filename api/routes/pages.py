from fastapi import APIRouter, HTTPException, Query, Request

from wiki.client import PageNotFoundError
from wiki.parser import extract_infobox, html_to_clean_text, html_to_sections, section_list
from bs4 import BeautifulSoup

router = APIRouter()


@router.get(
    "/page/{title}/sections",
    summary="List sections of a wiki page",
    description=(
        "Returns all section names and their numeric indexes for a given wiki page. "
        "Use this as a lightweight preview before fetching a specific section. "
        "Titles use underscores (e.g. 'Hu_Tao'). Section index 0 is typically the introduction."
    ),
)
async def get_sections(request: Request, title: str):
    """List section names and indexes for a page."""
    client = request.app.state.wiki
    try:
        html = await client.get_page_html(title)
    except PageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Page not found: {title}")

    return {"title": title, "sections": section_list(html)}


@router.get(
    "/page/{title}/section/{index}",
    summary="Get a single section from a wiki page",
    description=(
        "Fetches the content of one section from a wiki page by its numeric index. "
        "Use /page/{title}/sections first to discover available section indexes. "
        "More efficient than fetching the full page when only one section is needed."
    ),
)
async def get_section(request: Request, title: str, index: int):
    """Fetch a single section by index."""
    client = request.app.state.wiki
    try:
        html = await client.get_page_html(title)
    except PageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Page not found: {title}")

    sections = html_to_sections(html)
    for s in sections:
        if s["index"] == index:
            return {"title": title, "section": s}

    raise HTTPException(status_code=404, detail=f"Section index {index} not found (page has {len(sections)} sections)")


@router.get(
    "/page/{title}",
    summary="Get full wiki page content",
    description=(
        "Fetches the full content of a Genshin Impact wiki page. "
        "Use format=plain (default) for clean readable text with a section index. "
        "Use format=structured for machine-readable output: infobox as key-value pairs "
        "(stats, rarity, element, etc.) and sections as a named dictionary. "
        "Titles use underscores (e.g. 'Hu_Tao', 'Raiden_Shogun'). "
        "Get the exact title from /search first."
    ),
)
async def get_page(
    request: Request,
    title: str,
    format: str = Query(
        "plain",
        pattern="^(plain|structured)$",
        description="Response format: 'plain' for clean text, 'structured' for infobox dict + named sections",
    ),
):
    """Fetch a full wiki page as clean text or structured data."""
    client = request.app.state.wiki
    try:
        html = await client.get_page_html(title)
    except PageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Page not found: {title}")

    if format == "structured":
        soup = BeautifulSoup(html, "html.parser")
        infobox = extract_infobox(soup)
        sections = html_to_sections(html)
        return {
            "title": title,
            "infobox": infobox,
            "sections": {s["title"]: s["content"] for s in sections},
        }

    return {
        "title": title,
        "content": html_to_clean_text(html),
        "sections": section_list(html),
    }
