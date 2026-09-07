"""
Upgrade placeholder summaries created by backfill_range.py to real AI summaries.

The script is resumable: it keeps a progress file in state/upgrade_progress.json
and only processes dossiers that have not been upgraded yet. It respects the
daily token budget of the configured AI provider by stopping as soon as the
provider returns degraded summaries.
"""
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ai_chain import run_ai_chain
from scripts.build_site import build_static_site
from scripts.i18n import STATUS_FIELDS, status_text
from scripts.source_ori import fetch_documents_by_ids

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATE_FILE = os.path.join(PROJECT_ROOT, "state", "processed.json")
PROGRESS_FILE = os.path.join(PROJECT_ROOT, "state", "upgrade_progress.json")

# Fields that describe the record itself and must not be copied from the lead
# summary to sibling records.
RECORD_IDENTITY_FIELDS = {
    "doc_id",
    "date",
    "state",
    "official_title",
    "doc_type",
    "classification",
    "source_url",
    "attachments",
    "source_borrowed_from",
    "pdf_url",
}


def load_state() -> list[dict[str, Any]]:
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(items: list[dict[str, Any]]):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


def load_progress() -> dict[str, Any]:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"upgraded": []}


def save_progress(progress: dict[str, Any]):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def apply_source_facts(summary: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
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


def select_lead_doc(docs: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the document with the most usable text for summarization."""
    if not docs:
        return None
    scored = [
        (
            len(d.get("text", "").strip()),
            len(d.get("attachments", [])),
            d.get("date", ""),
            d,
        )
        for d in docs
    ]
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return scored[0][3]


def upgrade_backfilled(
    batch_size: int = 2,
    save_every: int = 5,
    pause_seconds: float = 45.0,
):
    """Upgrade backfilled placeholder summaries to real AI summaries."""
    items = load_state()
    progress = load_progress()
    upgraded = set(progress.get("upgraded", []))

    # Group backfilled items by dossier title.
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        if item.get("backfilled"):
            key = (item.get("official_title") or "").strip() or item["doc_id"]
            groups[key].append(item)

    if not groups:
        logger.info("No backfilled dossiers left to upgrade.")
        return

    # Process newest dossiers first, so the public site keeps improving recent
    # decisions before the oldest ones.
    ordered = sorted(
        groups.items(),
        key=lambda kv: max((i.get("date") or "") for i in kv[1]),
        reverse=True,
    )

    pending = [(title, docs) for title, docs in ordered if title not in upgraded]
    logger.info(
        f"Found {len(groups)} backfilled dossiers; {len(pending)} still need upgrading."
    )

    processed_this_run = 0

    for title, group_items in pending:
        doc_ids = [item["doc_id"] for item in group_items]
        logger.info(f"Upgrading dossier: {title[:80]} ({len(doc_ids)} records)")

        try:
            ori_docs = fetch_documents_by_ids(doc_ids)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Could not fetch ORI documents for {title}: {e}")
            continue

        if not ori_docs:
            logger.warning(f"No ORI documents returned for {title}; skipping.")
            continue

        lead_doc = select_lead_doc(ori_docs)
        if not lead_doc or not lead_doc.get("text", "").strip():
            logger.warning(f"No usable text for {title}; skipping.")
            continue

        summaries = run_ai_chain([lead_doc])
        if not summaries or summaries[0].get("degraded"):
            logger.warning(
                "AI provider returned a degraded/empty summary. Stopping to respect "
                "the daily budget; re-run later."
            )
            break

        lead_summary = summaries[0]
        ori_doc_map = {d["id"]: d for d in ori_docs}

        for item in group_items:
            doc_id = item["doc_id"]
            doc = ori_doc_map.get(doc_id, lead_doc)

            # Copy AI-generated fields from the lead summary, but keep record
            # identity fields tied to this specific ORI record.
            for key, value in lead_summary.items():
                if key in RECORD_IDENTITY_FIELDS:
                    continue
                if value is not None:
                    item[key] = value

            apply_source_facts(item, doc)
            item["backfilled"] = False
            processed_this_run += 1

        upgraded.add(title)
        progress["upgraded"] = sorted(upgraded)
        progress["last_upgraded"] = title
        progress["last_run"] = datetime.now(timezone.utc).isoformat()

        if len(upgraded) % save_every == 0:
            save_progress(progress)
            save_state(items)
            logger.info(f"Saved progress after {len(upgraded)} dossiers.")

        if processed_this_run % batch_size == 0 and processed_this_run > 0:
            logger.info(f"Pausing {pause_seconds}s between batches...")
            time.sleep(pause_seconds)

    save_progress(progress)
    save_state(items)
    logger.info(f"Upgraded {processed_this_run} records this run.")

    build_static_site(items)
    logger.info("Static site rebuilt.")


if __name__ == "__main__":
    upgrade_backfilled()
