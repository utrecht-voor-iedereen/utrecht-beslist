"""
Client module for Open Raadsinformatie (ORI) ElasticSearch API for Utrecht municipal documents.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORI_ELASTIC_ENDPOINT = "https://api.openraadsinformatie.nl/v1/elastic/ori_utrecht*/_search"

EXCLUDE_TITLE_KEYWORDS = [
    "presentielijst",
    "besluitenlijst ter vaststelling",
    "actielijst",
    "incomende stukken",
    "opening en mededelingen",
    "sluiting",
    "vaststelling agenda"
]

def fetch_utrecht_documents(size: int = 150) -> list[dict[str, Any]]:
    """
    Fetch latest documents from Open Raadsinformatie for Utrecht.
    """
    query_payload = {
        "size": size,
        "sort": [
            {
                "start_date": {
                    "order": "desc",
                    "unmapped_type": "keyword"
                }
            }
        ]
    }

    req = urllib.request.Request(
        ORI_ELASTIC_ENDPOINT,
        data=json.dumps(query_payload).encode('utf-8'),
        headers={"Content-Type": "application/json", "User-Agent": "UtrechtBeslistBot/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
            hits = data.get("hits", {}).get("hits", [])
            logger.info(f"Fetched {len(hits)} raw documents from Open Raadsinformatie.")
            return hits
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error fetching from Open Raadsinformatie: {e}")
        return []

def normalize_document(raw_hit: dict[str, Any]) -> dict[str, Any]:
    """
    Normalizes Elastic raw hit into standard document dict.
    """
    doc_id = raw_hit.get("_id", "")
    source = raw_hit.get("_source", {})

    title = source.get("name") or source.get("title") or "Gemeentestuk Utrecht"
    date_str = source.get("start_date") or source.get("last_discussed_at") or ""
    pdf_url = source.get("original_url") or source.get("url") or ""

    text_content = ""
    md_text = source.get("md_text")
    if isinstance(md_text, list):
        text_content = "\n".join([str(t) for t in md_text if t and str(t).strip() != "\f"])
    elif isinstance(md_text, str):
        text_content = md_text

    if not text_content:
        raw_text = source.get("text")
        if isinstance(raw_text, list):
            text_content = "\n".join([str(t) for t in raw_text if t and str(t).strip() != "\f"])
        elif isinstance(raw_text, str):
            text_content = raw_text

    return {
        "id": doc_id,
        "title": title.strip(),
        "date": date_str,
        "pdf_url": pdf_url,
        "text": text_content.strip()
    }

def filter_documents(raw_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filters raw document hits to keep relevant, non-trivial documents.
    """
    filtered = []
    for hit in raw_hits:
        doc = normalize_document(hit)
        title_lower = doc["title"].lower()

        # Check keyword exclusions
        if any(kw in title_lower for kw in EXCLUDE_TITLE_KEYWORDS):
            continue

        # Reject empty or very short text documents unless title is strong
        if len(doc["text"]) < 100 and not ("raadsvoorstel" in title_lower or "nota" in title_lower):
            continue

        filtered.append(doc)
    return filtered
