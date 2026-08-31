"""
Backfill Utrecht Beslist with older council decisions.

Fetches decision documents from Open Raadsinformatie for a date range,
merges them into state/processed.json, and rebuilds the static site.
By default it creates placeholder summaries so the documents appear on the
site immediately; they can be upgraded to AI summaries later by running the
normal pipeline or a dedicated upgrade script.
"""
import json
import logging
import os
import sys
import urllib.request
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ai_chain import generate_degraded_summary
from scripts.build_site import build_static_site
from scripts.i18n import STATUS_FIELDS, status_text
from scripts.source_ori import (
    ORI_ELASTIC_ENDPOINT,
    filter_documents,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATE_FILE = os.path.join(PROJECT_ROOT, "state", "processed.json")


def load_state() -> list[dict]:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_state(items: list[dict]):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def fetch_range(start_str: str, end_str: str, page_size: int = 500) -> list[dict]:
    """Fetch every raw ORI hit in the requested date range, newest first."""
    all_hits: list[dict] = []
    search_after = None
    while True:
        payload = {
            "size": page_size,
            "query": {
                "range": {
                    "start_date": {"gte": start_str, "lt": end_str}
                }
            },
            "sort": [
                {"start_date": {"order": "desc", "unmapped_type": "keyword"}},
                {"_id": {"order": "desc"}},
            ],
        }
        if search_after:
            payload["search_after"] = search_after

        req = urllib.request.Request(
            ORI_ELASTIC_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "UtrechtBeslistBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode())
            hits = data["hits"]["hits"]

        if not hits:
            break
        all_hits.extend(hits)
        search_after = hits[-1]["sort"]
        logger.info(f"Fetched {len(hits)} hits, total {len(all_hits)}")
        if len(hits) < page_size:
            break
    return all_hits


def apply_source_facts(summary: dict, doc: dict) -> dict:
    """Copy ORI facts onto the summary, mirroring pipeline.apply_source_facts."""
    summary["pdf_url"] = doc.get("pdf_url", "")
    summary["date"] = doc.get("date", "")
    summary["state"] = doc.get("state", "agenda")
    summary["official_title"] = doc.get("title", "")
    summary["doc_type"] = doc.get("doc_type", "")
    summary["classification"] = doc.get("classification", "")
    summary["source_url"] = doc.get("source_url", "")
    summary["attachments"] = doc.get("attachments", [])
    summary["source_borrowed_from"] = doc.get("source_borrowed_from", "")

    for lang, field in STATUS_FIELDS.items():
        summary[field] = status_text(summary["state"], lang)
    return summary


def backfill(
    start_str: str,
    end_str: str,
    placeholder: bool = True,
    skip_existing: bool = True,
):
    existing_items = load_state()
    existing_ids = {item["doc_id"] for item in existing_items}
    logger.info(f"Existing state has {len(existing_items)} records ({len(existing_ids)} ids)")

    raw_hits = fetch_range(start_str, end_str)
    filtered_docs = filter_documents(raw_hits)
    logger.info(f"Filtered to {len(filtered_docs)} decision-related documents")

    # Group by official title; each group becomes one dossier/entry in the UI.
    groups: dict[str, list[dict]] = defaultdict(list)
    for doc in filtered_docs:
        groups[doc["title"].strip()].append(doc)

    new_records = 0
    new_dossiers = 0
    summaries: list[dict] = []

    for title, docs in groups.items():
        if skip_existing and any(doc["id"] in existing_ids for doc in docs):
            logger.debug(f"Skipping existing dossier: {title[:60]}")
            continue
        new_dossiers += 1
        for doc in docs:
            if placeholder:
                summary = generate_degraded_summary(doc)
                summary["degraded"] = False
                summary["ai_model"] = "Backfill placeholder"
                summary["backfilled"] = True
            else:
                raise NotImplementedError("AI backfill not implemented here")
            apply_source_facts(summary, doc)
            summaries.append(summary)
            new_records += 1

    if not summaries:
        logger.info("No new documents to backfill.")
        return

    merged = {item["doc_id"]: item for item in existing_items}
    for summary in summaries:
        merged[summary["doc_id"]] = summary

    all_items = list(merged.values())
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)
    save_state(all_items)
    logger.info(
        f"Added {new_records} records across {new_dossiers} dossiers; "
        f"state now holds {len(all_items)} records"
    )

    build_static_site(all_items)
    logger.info("Static site rebuilt.")


if __name__ == "__main__":
    # 2025-01-01 through 2026-06-18 inclusive.
    backfill("2025-01-01T00:00:00.000Z", "2026-06-19T00:00:00.000Z")
