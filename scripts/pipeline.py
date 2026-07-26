"""
Master execution pipeline for Utrecht Beslist.
Fetches documents -> filters -> upserts -> summarizes -> renders static site.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from dateutil.parser import parse as parse_date

from .ai_chain import summarize_batch
from .build_site import build_static_site
from .source_ori import fetch_utrecht_documents, filter_documents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATE_FILE = os.path.join(PROJECT_ROOT, "state", "processed.json")
ANOMALY_THRESHOLD_DAYS = 90

def load_state() -> list[dict[str, Any]]:
    """Loads existing processed items from state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to read state file: {e}")
    return []

def save_state(items: list[dict[str, Any]]):
    """Saves updated items to state file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

def check_inactivity_anomaly(items: list[dict[str, Any]]):
    """Checks if no documents have been added or updated in > 90 days."""
    if not items:
        return
    
    latest_date_str = items[0].get("date")
    if not latest_date_str:
        return
    
    try:
        latest_dt = parse_date(latest_date_str)
        now_dt = datetime.now(timezone.utc)
        if latest_dt.tzinfo is None:
            latest_dt = latest_dt.replace(tzinfo=timezone.utc)
            
        days_diff = (now_dt - latest_dt).days
        if days_diff > ANOMALY_THRESHOLD_DAYS:
            logger.critical(f"ANOMALY DETECTED: No new documents processed for {days_diff} days (Threshold: {ANOMALY_THRESHOLD_DAYS} days). Check ORI API mapping!")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not calculate inactivity days: {e}")

def run_pipeline():
    """Runs full data fetch, processing, upserting, summarization, and site build."""
    logger.info("Starting Utrecht Beslist pipeline run...")
    
    existing_items = load_state()
    existing_map = {item["doc_id"]: item for item in existing_items if "doc_id" in item}

    # Fetch recent raw documents from Open Raadsinformatie API
    raw_hits = fetch_utrecht_documents(size=30)
    filtered_docs = filter_documents(raw_hits)

    has_ai_keys = bool(os.environ.get("GROQ_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    docs_to_process = []
    for doc in filtered_docs:
        doc_id = doc["id"]
        is_existing = doc_id in existing_map
        is_degraded = is_existing and existing_map[doc_id].get("degraded", False)
        date_changed = is_existing and existing_map[doc_id].get("date") != doc.get("date")

        # Process if new, date changed, or upgrading from degraded mode with AI keys
        if not is_existing or date_changed or (is_degraded and has_ai_keys):
            docs_to_process.append(doc)

    logger.info(f"Discovered {len(docs_to_process)} new/updated/upgradeable documents to process.")

    new_summaries = []
    if docs_to_process:
        batch_size = 5
        for i in range(0, len(docs_to_process), batch_size):
            batch = docs_to_process[i:i+batch_size]
            summarized_items = summarize_batch(batch)

            doc_map = {d["id"]: d for d in batch}
            for sum_item in summarized_items:
                doc_id = sum_item.get("doc_id")
                orig_doc = doc_map.get(doc_id, {})
                sum_item["pdf_url"] = orig_doc.get("pdf_url", "")
                sum_item["date"] = orig_doc.get("date", "")
                new_summaries.append(sum_item)

    # Upsert into state dictionary
    for item in new_summaries:
        existing_map[item["doc_id"]] = item

    all_items = list(existing_map.values())
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Check inactivity anomaly
    check_inactivity_anomaly(all_items)

    # Save state
    save_state(all_items)

    # Build website
    build_static_site(all_items)
    logger.info("Pipeline run finished successfully.")

if __name__ == "__main__":
    run_pipeline()
