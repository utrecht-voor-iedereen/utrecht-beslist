"""
Site generator module rendering Jinja2 templates to docs/ static directory for GitHub Pages.
Generates main pages, theme/wijk RSS feeds, month archives, and individual decision detail pages.
"""

import json
import logging
import os
import shutil
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

def generate_rss_xml(items: list, lang: str, category_title: str = "") -> str:
    """Generates valid RSS XML feed."""
    base_title = "Utrecht Beslist — Raadsbesluiten" if lang == "nl" else "Utrecht Beslist — City Council Decisions"
    title = f"{base_title} ({category_title})" if category_title else base_title
    link = "https://utrecht-beslist.github.io/utrecht-beslist/"
    description = "Volg besluiten van de gemeenteraad van Utrecht" if lang == "nl" else "Follow Utrecht city council decisions"
    
    xml_items = []
    for item in items[:30]:
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
    # Ensure base directories exist
    os.makedirs(os.path.join(DOCS_DIR, "nl"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "en"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "nl", "feed"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "en", "feed"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "nl", "archief", "2026", "07"), exist_ok=True)
    os.makedirs(os.path.join(DOCS_DIR, "en", "archive", "2026", "07"), exist_ok=True)

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

    # Render Main NL & EN Pages
    index_template = env.get_template("index.html")
    over_template = env.get_template("over.html")
    detail_template = env.get_template("detail.html")

    nl_index_html = index_template.render(lang="nl", items=items, themes=THEMES, root_path="../")
    with open(os.path.join(DOCS_DIR, "nl", "index.html"), "w", encoding="utf-8") as f:
        f.write(nl_index_html)

    nl_over_html = over_template.render(lang="nl", themes=THEMES, root_path="../")
    with open(os.path.join(DOCS_DIR, "nl", "over.html"), "w", encoding="utf-8") as f:
        f.write(nl_over_html)

    en_index_html = index_template.render(lang="en", items=items, themes=THEMES, root_path="../")
    with open(os.path.join(DOCS_DIR, "en", "index.html"), "w", encoding="utf-8") as f:
        f.write(en_index_html)

    en_over_html = over_template.render(lang="en", themes=THEMES, root_path="../")
    with open(os.path.join(DOCS_DIR, "en", "over.html"), "w", encoding="utf-8") as f:
        f.write(en_over_html)

    # Render Individual Decision Detail Pages
    for item in items:
        doc_id = item.get("doc_id")
        if not doc_id:
            continue
        
        nl_detail_dir = os.path.join(DOCS_DIR, "nl", "besluit", doc_id)
        en_detail_dir = os.path.join(DOCS_DIR, "en", "decision", doc_id)
        os.makedirs(nl_detail_dir, exist_ok=True)
        os.makedirs(en_detail_dir, exist_ok=True)

        nl_detail_html = detail_template.render(lang="nl", item=item, themes=THEMES, root_path="../../../")
        with open(os.path.join(nl_detail_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(nl_detail_html)

        en_detail_html = detail_template.render(lang="en", item=item, themes=THEMES, root_path="../../../")
        with open(os.path.join(en_detail_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(en_detail_html)

    # Render Static Archives (2026/07)
    with open(os.path.join(DOCS_DIR, "nl", "archief", "2026", "07", "index.html"), "w", encoding="utf-8") as f:
        f.write(index_template.render(lang="nl", items=items, themes=THEMES, root_path="../../../../"))

    with open(os.path.join(DOCS_DIR, "en", "archive", "2026", "07", "index.html"), "w", encoding="utf-8") as f:
        f.write(index_template.render(lang="en", items=items, themes=THEMES, root_path="../../../../"))

    # Write Main & Categorized RSS Feeds
    with open(os.path.join(DOCS_DIR, "nl", "feed.xml"), "w", encoding="utf-8") as f:
        f.write(generate_rss_xml(items, "nl"))
    with open(os.path.join(DOCS_DIR, "en", "feed.xml"), "w", encoding="utf-8") as f:
        f.write(generate_rss_xml(items, "en"))

    # RSS Feeds per Theme
    for key, theme_data in THEMES.items():
        theme_items = [it for it in items if key in it.get("thema", [])]
        nl_title = str(theme_data["nl"])
        en_title = str(theme_data["en"])
        with open(os.path.join(DOCS_DIR, "nl", "feed", f"{key}.xml"), "w", encoding="utf-8") as f:
            f.write(generate_rss_xml(theme_items, "nl", nl_title))
        with open(os.path.join(DOCS_DIR, "en", "feed", f"{key}.xml"), "w", encoding="utf-8") as f:
            f.write(generate_rss_xml(theme_items, "en", en_title))

    # Write Public Data API JSON
    with open(os.path.join(DOCS_DIR, "data", "latest.json"), "w", encoding="utf-8") as f:
        json.dump({"items": items, "count": len(items)}, f, indent=2, ensure_ascii=False)

    logger.info(f"Successfully generated static site in {DOCS_DIR} with {len(items)} items, RSS feeds, month archives, and individual detail pages.")
