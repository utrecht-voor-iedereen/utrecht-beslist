"""
Master execution pipeline for Utrecht Beslist.
Fetches documents -> filters -> upserts -> summarizes -> renders static site.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from dateutil.parser import parse as parse_date

from .ai_chain import run_ai_chain
from .build_site import build_static_site
from .i18n import STATUS_FIELDS, status_text
from .source_ori import fetch_utrecht_documents, filter_documents
from .translate_missing import FIELDS as TRANSLATABLE_FIELDS
from .translate_missing import TARGETS as TRANSLATION_TARGETS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATE_FILE = os.path.join(PROJECT_ROOT, "state", "processed.json")
# Days without a newer document before the run says something is wrong. It was
# 90, which is long enough for the upstream harvester to stop and the site to
# sit frozen for a quarter without anyone being told. Dutch councils take a
# summer recess of roughly six weeks, so the message has to allow for that
# rather than claim a fault it cannot prove.
ANOMALY_THRESHOLD_DAYS = int(os.environ.get("ANOMALY_THRESHOLD_DAYS", "21"))

# Seconds to wait between summarization batches, to stay inside the provider's
# per-minute token budget. Overridable for local runs on a paid key.
BATCH_PAUSE_SECONDS = float(os.environ.get("BATCH_PAUSE_SECONDS", "45"))

# How many previously unseen documents one run may summarize. ORI's window
# holds far more than a day's allowance: 46 unprocessed documents were waiting
# at roughly 159,000 tokens, against a free-tier limit of 100,000 a day. Left
# uncapped, the run burns its budget, the rest fall through to degraded mode,
# and the backlog is published as filler. Capped, it drains over a few days
# with every entry written from its actual source.
MAX_NEW_PER_RUN = int(os.environ.get("MAX_NEW_PER_RUN", "12"))

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
            logger.critical(
                "STALE: the newest document is %d days old (threshold %d). Either the "
                "council is in recess or Open Raadsinformatie has stopped harvesting "
                "Utrecht. Check the newest start_date in ori_utrecht* against the "
                "council's own agenda before assuming the pipeline is at fault.",
                days_diff, ANOMALY_THRESHOLD_DAYS,
            )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Could not calculate inactivity days: {e}")

def report_untranslated(items: list[dict[str, Any]]):
    """
    Warns about entries with no text in a language the site publishes.

    The summarization prompt asks for eight languages but the model has
    returned only Dutch and English, and get_item_lang_field() quietly falls
    back to English, so six of the eight language versions of the site were
    shipping English text with nobody noticing. This makes that visible in the
    run log; `python -m scripts.translate_missing` fills the gaps.
    """
    gaps: dict[str, int] = {}
    for item in items:
        for suffix in TRANSLATION_TARGETS:
            for base, _nl, _en in TRANSLATABLE_FIELDS:
                value = item.get(f"{base}_{suffix}")
                if not (isinstance(value, str) and value.strip()):
                    gaps[suffix] = gaps.get(suffix, 0) + 1
                    break

    if not gaps:
        logger.info("All %d entries carry text in every published language.", len(items))
        return

    summary = ", ".join(f"{lang}: {count}" for lang, count in sorted(gaps.items()))
    logger.warning(
        "Entries falling back to English (%s). These pages show English text. "
        "Run: python -m scripts.translate_missing",
        summary,
    )


def apply_source_facts(summary: dict[str, Any], doc: dict[str, Any]) -> dict[str, Any]:
    """
    Overwrites everything the register knows for certain onto the summary.

    Dates, links, and the decision state are facts held by Open
    Raadsinformatie; letting the model supply them is how six documents that
    ORI records as passed ended up displayed as still under review, and how
    twenty entries ended up with a status of nothing but an hourglass.
    """
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


def run_pipeline():
    """Runs full data fetch, processing, upserting, summarization, and site build."""
    logger.info("Starting Utrecht Beslist pipeline run...")
    
    existing_items = load_state()
    existing_map = {item["doc_id"]: item for item in existing_items if "doc_id" in item}

    # Fetch up to 150 recent raw documents from Open Raadsinformatie API
    raw_hits = fetch_utrecht_documents(size=150)
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

    # Newest first, so the backlog drains from the most recent decisions.
    docs_to_process.sort(key=lambda d: d.get("date") or "", reverse=True)
    if len(docs_to_process) > MAX_NEW_PER_RUN:
        logger.warning(
            "Summarizing the %d most recent of %d; the rest wait for the next run "
            "so this one stays inside the provider's daily token budget.",
            MAX_NEW_PER_RUN, len(docs_to_process),
        )
        docs_to_process = docs_to_process[:MAX_NEW_PER_RUN]

    new_summaries: list[dict[str, Any]] = []
    skipped_degraded: list[str] = []
    if docs_to_process:
        # Two documents per call, paced to the minute. Batches of five were fine
        # while every document was an empty title, but now that attachment text
        # is included a batch of five exceeds Groq's 12,000 tokens per minute
        # and the whole run falls through to degraded mode.
        batch_size = 2
        for i in range(0, len(docs_to_process), batch_size):
            batch = docs_to_process[i:i+batch_size]
            if i:
                time.sleep(BATCH_PAUSE_SECONDS)
            summarized_items = run_ai_chain(batch)

            doc_map = {d["id"]: d for d in batch}
            for sum_item in summarized_items:
                doc_id = sum_item.get("doc_id")
                orig_doc = doc_map.get(doc_id, {})
                apply_source_facts(sum_item, orig_doc)

                # A degraded summary says nothing the title does not. Publishing
                # it is how thirty entries came to read "this proposal concerns
                # X"; leaving it out means the document simply waits for a run
                # that can summarize it properly.
                if sum_item.get("degraded"):
                    skipped_degraded.append(doc_id)
                    continue

                new_summaries.append(sum_item)

    # Upsert into state dictionary. Merging rather than replacing: a plain
    # assignment threw away every field translate_missing had added, so any
    # document that came round again reverted to English on six of the eight
    # language editions.
    for item in new_summaries:
        doc_id = item["doc_id"]
        if doc_id in existing_map:
            merged = dict(existing_map[doc_id])
            merged.update({k: v for k, v in item.items() if v not in ("", None, [])})
            existing_map[doc_id] = merged
        else:
            existing_map[doc_id] = item

    if skipped_degraded:
        logger.warning(
            "%d document(s) left unpublished because no AI provider answered: %s. "
            "They are retried on the next run.",
            len(skipped_degraded), ", ".join(skipped_degraded[:10]),
        )

    all_items = list(existing_map.values())
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)

    # Check inactivity anomaly
    check_inactivity_anomaly(all_items)

    report_untranslated(all_items)

    # Save state
    save_state(all_items)

    # Build website
    build_static_site(all_items)
    logger.info("Pipeline run finished successfully.")

if __name__ == "__main__":
    run_pipeline()
