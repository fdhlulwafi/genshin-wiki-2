from fastapi import APIRouter, HTTPException, Query, Request

from wiki.client import PageNotFoundError
from wiki.parser import extract_infobox, html_to_clean_text, html_to_sections, section_list
from bs4 import BeautifulSoup

router = APIRouter()


@router.get("/page/{title}/sections")
async def get_sections(request: Request, title: str):
    """List section names and indexes for a page."""
    client = request.app.state.wiki
    try:
        html = await client.get_page_html(title)
    except PageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Page not found: {title}")

    return {"title": title, "sections": section_list(html)}


@router.get("/page/{title}/section/{index}")
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


@router.get("/page/{title}")
async def get_page(request: Request, title: str, format: str = Query("plain", pattern="^(plain|structured)$")):
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
