"""
Site generator module rendering Jinja2 templates to docs/ static directory for GitHub Pages.
Generates main pages, theme/wijk RSS feeds, month archives, and individual decision detail pages.
Supports 8 languages: NL, EN, ES, TR, PT-BR, PT-PT, FR, DE.
"""

import json
import logging
import os
import shutil
import sys
from xml.sax.saxutils import escape

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from jinja2 import Environment, FileSystemLoader

from scripts.i18n import LANGUAGES, get_item_lang_field, t
from scripts.themes import THEMES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "templates")
STATIC_DIR = os.path.join(PROJECT_ROOT, "static")
DOCS_DIR = os.path.join(PROJECT_ROOT, "docs")

SUPPORTED_LANGUAGES = ["nl", "en", "es", "tr", "pt-br", "pt-pt", "fr", "de"]

env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)
env.globals["t"] = t
env.globals["get_item_lang_field"] = get_item_lang_field
env.globals["LANGUAGES"] = LANGUAGES


def generate_rss_xml(items: list, lang: str, category_title: str = "") -> str:
    """Generates valid RSS XML feed."""
    base_title = t("site_title", lang)
    title = f"{base_title} ({category_title})" if category_title else base_title
    link = "https://utrecht-voor-iedereen.github.io/utrecht-beslist/"
    description = t("meta_description", lang)

    xml_items = []
    for item in items[:30]:
        item_title = escape(get_item_lang_field(item, "title_short", lang) or "Besluit")
        item_desc = escape(get_item_lang_field(item, "summary", lang) or "")
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
    """Builds complete static web output into docs/ for all 8 supported languages."""
    # Ensure data directory exists
    os.makedirs(os.path.join(DOCS_DIR, "data"), exist_ok=True)

    # Prepare directories for all languages
    for lang in SUPPORTED_LANGUAGES:
        os.makedirs(os.path.join(DOCS_DIR, lang), exist_ok=True)
        os.makedirs(os.path.join(DOCS_DIR, lang, "feed"), exist_ok=True)
        os.makedirs(os.path.join(DOCS_DIR, lang, "archief", "2026", "07"), exist_ok=True)

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

    # Templates
    index_template = env.get_template("index.html")
    over_template = env.get_template("over.html")
    detail_template = env.get_template("detail.html")

    # Render main index and over pages for all 8 languages
    for lang in SUPPORTED_LANGUAGES:
        index_html = index_template.render(lang=lang, items=items, themes=THEMES, root_path="../")
        with open(os.path.join(DOCS_DIR, lang, "index.html"), "w", encoding="utf-8") as f:
            f.write(index_html)

        over_html = over_template.render(lang=lang, themes=THEMES, root_path="../")
        with open(os.path.join(DOCS_DIR, lang, "over.html"), "w", encoding="utf-8") as f:
            f.write(over_html)

        # Render month archive
        archive_html = index_template.render(lang=lang, items=items, themes=THEMES, root_path="../../../../")
        with open(os.path.join(DOCS_DIR, lang, "archief", "2026", "07", "index.html"), "w", encoding="utf-8") as f:
            f.write(archive_html)

        # Write main RSS feed
        with open(os.path.join(DOCS_DIR, lang, "feed.xml"), "w", encoding="utf-8") as f:
            f.write(generate_rss_xml(items, lang))

        # Write theme RSS feeds
        for key, theme_data in THEMES.items():
            theme_items = [it for it in items if key in it.get("thema", [])]
            t_title = str(theme_data.get(lang, theme_data.get("nl", key)))
            with open(os.path.join(DOCS_DIR, lang, "feed", f"{key}.xml"), "w", encoding="utf-8") as f:
                f.write(generate_rss_xml(theme_items, lang, t_title))

    # Render Individual Decision Detail Pages for all 8 languages
    for item in items:
        doc_id = item.get("doc_id")
        if not doc_id:
            continue

        for lang in SUPPORTED_LANGUAGES:
            detail_dir = os.path.join(DOCS_DIR, lang, "besluit", doc_id)
            os.makedirs(detail_dir, exist_ok=True)

            detail_html = detail_template.render(lang=lang, item=item, themes=THEMES, root_path="../../../")
            with open(os.path.join(detail_dir, "index.html"), "w", encoding="utf-8") as f:
                f.write(detail_html)

    # Write Public Data API JSON
    with open(os.path.join(DOCS_DIR, "data", "latest.json"), "w", encoding="utf-8") as f:
        json.dump({"items": items, "count": len(items)}, f, indent=2, ensure_ascii=False)

    logger.info(
        f"Successfully generated static site in {DOCS_DIR} for {len(SUPPORTED_LANGUAGES)} languages "
        f"with {len(items)} items, RSS feeds, month archives, and individual detail pages."
    )


if __name__ == "__main__":
    state_file = os.path.join(PROJECT_ROOT, "state", "processed.json")
    if os.path.exists(state_file):
        with open(state_file, "r", encoding="utf-8") as f:
            state_data = json.load(f)
            if isinstance(state_data, dict):
                items = state_data.get("items", [])
            elif isinstance(state_data, list):
                items = state_data
            else:
                items = []
            build_static_site(items)
