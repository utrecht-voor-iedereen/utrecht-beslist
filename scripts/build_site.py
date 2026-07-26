"""
Site generator module rendering Jinja2 templates to docs/ static directory for GitHub Pages.
"""

import os
import json
import shutil
import logging
from xml.sax.saxutils import escape
from jinja2 import Environment, FileSystemLoader
from .themes import THEMES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)

def generate_rss_xml(items: list, lang: str) -> str:
    """Generates valid RSS XML feed."""
    title = "Utrecht Beslist — Raadsbesluiten" if lang == "nl" else "Utrecht Beslist — City Council Decisions"
    link = "https://zaswear.github.io/utrecht-beslist/"
    description = "Volg besluiten van de gemeenteraad van Utrecht" if lang == "nl" else "Follow Utrecht city council decisions"
    
    xml_items = []
    for item in items[:20]:
        item_title = escape(item.get("titel_kort_nl" if lang == "nl" else "title_short_en", "Besluit"))
        item_desc = escape(item.get("samenvatting_nl" if lang == "nl" else "summary_en", ""))
        pdf_url = escape(item.get("pdf_url", link))
        doc_id = item.get("doc_id", "")
        
        xml_items.append(f"""    <item>
      <title>{item_title}</title>
      <link>{pdf_url}</link>
      <description>{item_desc}</description>
      <guid isPermaLink="false">{doc_id}</guid>
    </item>""")

    return f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>{escape(title)}</title>
    <link>{link}</link>
    <description>{escape(description)}</description>
    <language>{lang}</language>
{"\n".join(xml_items)}
  </channel>
</rss>"""

def build_static_site(items: list):
    """Builds complete static web output into docs/."""
    # Ensure directories exist
    os.makedirs(os.path.join(DOCS_DIR, "nl"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "en"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "data"), exist_ok=True)

    # Copy static assets
    target_static = os.path.join(DOCS_DIR, "static")
    if os.path.exists(target_static):
        shutil.rmtree(target_static)
    shutil.copytree(STATIC_DIR, target_static)

    # Render Root Redirect index.html
    root_redirect = """<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="refresh" content="0; url=nl/index.html">
  <title>Utrecht Beslist</title>
</head>
<body>
  <p>Redirecting to <a href="nl/index.html">Utrecht Beslist (Nederlands)</a>...</p>
</body>
</html>"""
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(root_redirect)

    # Render NL Pages
    index_template = env.get_template("index.html")
    over_template = env.get_template("over.html")

    nl_index_html = index_template.render(
        lang="nl",
        items=items,
        themes=THEMES,
        root_path="../"
    )
    with open(os.path.join(DOCS_DIR, "nl", "index.html"), "w", encoding="utf-8") as f:
        f.write(nl_index_html)

    nl_over_html = over_template.render(
        lang="nl",
        themes=THEMES,
        root_path="../"
    )
    with open(os.path.join(DOCS_DIR, "nl", "over.html"), "w", encoding="utf-8") as f:
        f.write(nl_over_html)

    # Render EN Pages
    en_index_html = index_template.render(
        lang="en",
        items=items,
        themes=THEMES,
        root_path="../"
    )
    with open(os.path.join(DOCS_DIR, "en", "index.html"), "w", encoding="utf-8") as f:
        f.write(en_index_html)

    en_over_html = over_template.render(
        lang="en",
        themes=THEMES,
        root_path="../"
    )
    with open(os.path.join(DOCS_DIR, "en", "over.html"), "w", encoding="utf-8") as f:
        f.write(en_over_html)

    # Write RSS Feeds
    with open(os.path.join(DOCS_DIR, "nl", "feed.xml"), "w", encoding="utf-8") as f:
        f.write(generate_rss_xml(items, "nl"))
    with open(os.path.join(DOCS_DIR, "en", "feed.xml"), "w", encoding="utf-8") as f:
        f.write(generate_rss_xml(items, "en"))

    # Write Public Data API JSON
    with open(os.path.join(DOCS_DIR, "data", "latest.json"), "w", encoding="utf-8") as f:
        json.dump({"items": items, "count": len(items)}, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully generated static site in {DOCS_DIR} with {len(items)} items.")
