"""
Master execution pipeline for Utrecht Beslist.
Fetches documents -> filters -> summarizes via AI/fallback -> renders static site.
"""

import os
import json
import logging
from typing import Dict, Any, List

from .source_ori import fetch_utrecht_documents, filter_documents
from .ai_chain import summarize_batch
from .build_site import build_static_site

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATE_FILE = os.path.join(PROJECT_ROOT, "state", "processed.json")

def load_state() -> List[Dict[str, Any]]:
    """Loads existing processed items from state file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read state file: {e}")
    return []

def save_state(items: List[Dict[str, Any]]):
    """Saves updated items to state file."""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

def run_pipeline():
    """Runs full data fetch, processing, summarization, and site build."""
    logger.info("Starting Utrecht Beslist pipeline run...")
    
    existing_items = load_state()
    existing_ids = {item["doc_id"] for item in existing_items if "doc_id" in item}

    # Fetch recent raw documents from Open Raadsinformatie API
    raw_hits = fetch_utrecht_documents(size=30)
    filtered_docs = filter_documents(raw_hits)

    new_docs = [d for d in filtered_docs if d["id"] not in existing_ids]
    logger.info(f"Discovered {len(new_docs)} new documents to process.")

    new_summaries = []
    if new_docs:
        # Process in batches of 5
        batch_size = 5
        for i in range(0, len(new_docs), batch_size):
            batch = new_docs[i:i+batch_size]
            summarized_items = summarize_batch(batch)

            # Map back PDF URL and dates
            doc_map = {d["id"]: d for d in batch}
            for sum_item in summarized_items:
                doc_id = sum_item.get("doc_id")
                orig_doc = doc_map.get(doc_id, {})
                sum_item["pdf_url"] = orig_doc.get("pdf_url", "")
                sum_item["date"] = orig_doc.get("date", "")
                new_summaries.append(sum_item)

    all_items = new_summaries + existing_items

    # Sort items by date descending
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Save state
    save_state(all_items)

    # Build website
    build_static_site(all_items)
    logger.info("Pipeline run finished successfully.")

if __name__ == "__main__":
    run_pipeline()
