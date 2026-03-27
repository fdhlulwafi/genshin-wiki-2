from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag


def _remove_noise(soup: BeautifulSoup) -> None:
    """Remove non-content elements from parsed HTML."""
    selectors = [
        "script", "style", "noscript",
        ".navbox", ".navbox-container",
        "#toc", ".toc",
        ".mw-editsection",
        ".gallery", ".wikia-gallery",
        ".reference", "sup.reference",
        ".mbox-image", ".ambox", ".tmbox",
        ".noprint", ".mw-empty-elt",
    ]
    for sel in selectors:
        for el in soup.select(sel):
            el.decompose()


def _table_to_text(table: Tag) -> str:
    """Convert an HTML table to pipe-delimited text."""
    rows: list[str] = []
    for tr in table.find_all("tr"):
        cells = []
        for td in tr.find_all(["th", "td"]):
            text = td.get_text(" ", strip=True)
            cells.append(text)
        if cells:
            rows.append(" | ".join(cells))
    if len(rows) >= 2:
        rows.insert(1, " | ".join(["---"] * rows[0].count("|") + ["---"]))
    return "\n".join(rows)


def extract_infobox(soup: BeautifulSoup) -> dict[str, str] | None:
    """Extract the portable infobox as a flat dict."""
    infobox = soup.select_one(".portable-infobox, .pi-item")
    if not infobox:
        infobox_div = soup.select_one(".infobox, .infoboxtable")
        if not infobox_div:
            return None
        result: dict[str, str] = {}
        for row in infobox_div.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                key = th.get_text(" ", strip=True)
                val = td.get_text(" ", strip=True)
                if key and val:
                    result[key] = val
        return result if result else None

    parent = infobox
    if not infobox.select(".pi-item"):
        parent_box = infobox.find_parent(class_="portable-infobox")
        if parent_box:
            parent = parent_box

    result = {}
    title_el = parent.select_one(".pi-title")
    if title_el:
        result["Name"] = title_el.get_text(" ", strip=True)

    for item in parent.select(".pi-item.pi-data"):
        label_el = item.select_one(".pi-data-label")
        value_el = item.select_one(".pi-data-value")
        if label_el and value_el:
            key = label_el.get_text(" ", strip=True)
            val = value_el.get_text(" ", strip=True)
            if key and val:
                result[key] = val

    return result if result else None


def html_to_sections(html: str) -> list[dict]:
    """Parse page HTML into a list of sections with headings and content.

    Returns: [{"index": 0, "title": "Introduction", "content": "..."}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    _remove_noise(soup)

    sections: list[dict] = []
    current_title = "Introduction"
    current_parts: list[str] = []
    current_index = 0

    content_div = soup.select_one(".mw-parser-output") or soup

    for child in content_div.children:
        if not isinstance(child, Tag):
            text = str(child).strip()
            if text:
                current_parts.append(text)
            continue

        if child.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            sections.append({
                "index": current_index,
                "title": current_title,
                "content": "\n".join(current_parts).strip(),
            })
            current_index += 1
            level = int(child.name[1])
            heading_text = child.get_text(" ", strip=True)
            current_title = heading_text
            current_parts = [f"{'#' * level} {heading_text}"]
        elif child.name == "table":
            current_parts.append(_table_to_text(child))
        else:
            text = child.get_text("\n", strip=True)
            if text:
                current_parts.append(text)

    if current_parts:
        sections.append({
            "index": current_index,
            "title": current_title,
            "content": "\n".join(current_parts).strip(),
        })

    return sections


def html_to_clean_text(html: str) -> str:
    """Convert page HTML to clean markdown-like text."""
    sections = html_to_sections(html)
    return "\n\n".join(s["content"] for s in sections if s["content"])


def section_list(html: str) -> list[dict]:
    """Return lightweight section index: [{"index": 0, "title": "Introduction"}, ...]"""
    return [{"index": s["index"], "title": s["title"]} for s in html_to_sections(html)]
