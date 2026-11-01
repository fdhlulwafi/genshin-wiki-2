from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag


BLOCK_TAGS = [
    "p", "div", "ul", "ol", "li", "dl", "dd", "dt", "blockquote", "pre", "center",
    "section", "article", "aside", "figure", "figcaption",
    "h1", "h2", "h3", "h4", "h5", "h6",
]


def _clean_lines(text: str) -> str:
    """Drop soft hyphens, squeeze spaces and remove empty lines."""
    lines = (re.sub(r"[ \t\u00a0]+", " ", line).strip() for line in text.replace("\u00ad", "").split("\n"))
    return "\n".join(line for line in lines if line)


def _text(el: Tag) -> str:
    """Text of an element: inline links stay in their sentence, block elements get their own line."""
    for br in el.find_all("br"):
        br.replace_with("\n")
    for block in el.find_all(BLOCK_TAGS):
        block.insert_before("\n")
        block.insert_after("\n")
    return _clean_lines(el.get_text())


def _image_text(el: Tag) -> str:
    """Alt text of the images in an element, for values shown only as icons (rarity, element)."""
    alts = (re.sub(r"\.(png|jpe?g|webp|gif|svg)$", "", img.get("alt", ""), flags=re.I).strip() for img in el.find_all("img"))
    return " ".join(alt for alt in alts if alt)


def _value(el: Tag) -> str:
    """One-line value of a table cell or infobox field, falling back to its icons."""
    alt = _image_text(el)
    return " ".join(_text(el).split("\n")) or alt


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
        ".portable-infobox", ".custom-tabs",
    ]
    for sel in selectors:
        for el in soup.select(sel):
            el.decompose()


def _table_to_text(table: Tag) -> str:
    """Convert an HTML table to pipe-delimited text."""
    rows: list[str] = []
    for tr in table.find_all("tr"):
        cells = [_value(td) for td in tr.find_all(["th", "td"])]
        if any(cells):
            rows.append(" | ".join(cells))
    if len(rows) >= 2:
        rows.insert(1, " | ".join(["---"] * rows[0].count("|") + ["---"]))
    return "\n".join(rows)


def _flatten_tables(soup: BeautifulSoup) -> None:
    """Replace every table in place, innermost first, so tables inside tabs and divs keep their rows."""
    for table in reversed(soup.find_all("table")):
        table.replace_with("\n" + _table_to_text(table) + "\n")


def extract_infobox(html: str) -> dict[str, str] | None:
    """Extract the portable infobox as a flat dict.

    Character pages start with an empty placeholder infobox, so every infobox is read and merged.
    """
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, str] = {}
    for box in soup.select("aside.portable-infobox"):
        title_el = box.select_one(".pi-title")
        if title_el and "Name" not in result:
            result["Name"] = _value(title_el)

        for item in box.select(".pi-item.pi-data"):
            label_el = item.select_one(".pi-data-label")
            value_el = item.select_one(".pi-data-value")
            if label_el and value_el:
                key, val = _value(label_el), _value(value_el)
                if key and val:
                    result.setdefault(key, val)

        # Short fields (quality, weapon, element) sit side by side in small tables.
        for table in box.select("table.pi-horizontal-group"):
            labels = [_value(th) for th in table.select("th")]
            values = [_value(td) for td in table.select("td")]
            for key, val in zip(labels, values):
                if key and val:
                    result.setdefault(key, val)

    return result or None


def extract_subpages(html: str) -> list[str]:
    """Titles of the page's tabs (Hu Tao -> Hu Tao/Profile, Hu Tao/Storyline, ...), where lore usually lives."""
    soup = BeautifulSoup(html, "html.parser")
    links = soup.select(".custom-tabs a[title]")
    return list(dict.fromkeys(a["title"] for a in links))


def html_to_sections(html: str) -> list[dict]:
    """Parse page HTML into a list of sections with headings and content.

    Returns: [{"index": 0, "title": "Introduction", "content": "..."}, ...]
    """
    soup = BeautifulSoup(html, "html.parser")
    _remove_noise(soup)
    _flatten_tables(soup)

    sections: list[dict] = []
    current_title = "Introduction"
    current_parts: list[str] = []
    current_index = 0

    content_div = soup.select_one(".mw-parser-output") or soup

    for child in content_div.children:
        if not isinstance(child, Tag):
            text = _clean_lines(str(child))
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
            heading_text = _value(child)
            current_title = heading_text
            current_parts = [f"{'#' * level} {heading_text}"]
        else:
            text = _text(child)
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
