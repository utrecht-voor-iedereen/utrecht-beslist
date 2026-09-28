"""
Backfill Utrecht Beslist with older council decisions.

Reads every council meeting of Utrecht from OpenBesluitvorming's export
snapshot, keeps the proposals of the meetings in a date range, merges them into
state/processed.json, and rebuilds the static site. By default it creates
placeholder summaries so the documents appear on the site immediately; they can
be upgraded to AI summaries later with upgrade_backfilled.py.

    python -m scripts.backfill_range 2024-01-01 2025-01-01   # [from, to)
"""
import argparse
import json
import logging
import os
import sys
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ai_chain import generate_degraded_summary
from scripts.build_site import build_static_site
from scripts.pipeline import apply_source_facts, drop_already_published
from scripts.source_obv import documents_from_meetings, snapshot_council_meetings

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


def fetch_range(start_str: str, end_str: str) -> list[dict]:
    """The proposals of every council meeting from start (inclusive) to end."""
    meetings = {
        meeting_id: meeting
        for meeting_id, meeting in snapshot_council_meetings().items()
        if start_str <= str(meeting.get("start_date") or "")[:10] < end_str
    }
    logger.info(f"{len(meetings)} council meetings between {start_str} and {end_str}")
    return documents_from_meetings(meetings)


def backfill(
    start_str: str,
    end_str: str,
    placeholder: bool = True,
    skip_existing: bool = True,
):
    existing_items = load_state()
    existing_ids = {item["doc_id"] for item in existing_items}
    logger.info(f"Existing state has {len(existing_items)} records ({len(existing_ids)} ids)")

    docs = fetch_range(start_str, end_str)
    # Items already on the site under their ORI id would come back with a new
    # id and be published twice.
    filtered_docs = drop_already_published(docs, existing_items)
    logger.info(f"{len(filtered_docs)} of {len(docs)} proposals are not on the site yet")

    # Group by official title; each group becomes one dossier/entry in the UI.
    groups: dict[str, list[dict]] = defaultdict(list)
    for doc in filtered_docs:
        groups[doc["title"].strip()].append(doc)

    new_records = 0
    new_dossiers = 0
    summaries: list[dict] = []

    for title, group in groups.items():
        if skip_existing and any(doc["id"] in existing_ids for doc in group):
            logger.debug(f"Skipping existing dossier: {title[:60]}")
            continue
        new_dossiers += 1
        for doc in group:
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("start", help="first meeting day, YYYY-MM-DD")
    parser.add_argument("end", help="day after the last meeting, YYYY-MM-DD")
    args = parser.parse_args()
    backfill(args.start, args.end)
