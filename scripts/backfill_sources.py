"""
Re-reads Open Raadsinformatie for the documents already in the state file and
writes back the facts the register holds: decision state, publication date,
source links and attachments.

The summaries themselves are left alone — this only replaces the fields the
summarizer should never have been asked to invent. Running it is idempotent.

    python -m scripts.backfill_sources            # apply
    python -m scripts.backfill_sources --dry-run  # report only
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from .i18n import STATUS_FIELDS, status_text
from .source_ori import (
    ORI_ELASTIC_ENDPOINT,
    ORI_PERMALINK,
    enrich_with_attachments,
    normalize_document,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "processed.json"

# Types that are containers rather than decisions. A Meeting shipped as an
# article titled "Raadsvoorstellen weekoverzicht" with no content behind it.
DROP_DOC_TYPES = {"Meeting"}


def fetch_by_ids(doc_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Fetches the ORI records for a list of ids, in chunks of 100."""
    import urllib.request

    out: dict[str, dict[str, Any]] = {}
    for start in range(0, len(doc_ids), 100):
        chunk = doc_ids[start:start + 100]
        payload = {"size": len(chunk), "query": {"ids": {"values": chunk}}}
        req = urllib.request.Request(
            ORI_ELASTIC_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "UtrechtBeslistBot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=40) as response:
            data = json.loads(response.read().decode("utf-8"))
        for hit in data.get("hits", {}).get("hits", []):
            out[hit.get("_id", "")] = normalize_document(hit)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report changes without writing")
    args = parser.parse_args()

    items = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    doc_ids = [item["doc_id"] for item in items if item.get("doc_id")]

    records = fetch_by_ids(doc_ids)
    logger.info("resolved %d of %d documents at ORI", len(records), len(doc_ids))

    missing = [d for d in doc_ids if d not in records]
    if missing:
        logger.warning("not found at ORI, left untouched: %s", ", ".join(missing))

    enrich_with_attachments([r for r in records.values()])

    kept: list[dict[str, Any]] = []
    changes: list[str] = []
    dropped: list[str] = []

    for item in items:
        doc_id = item.get("doc_id", "")
        doc = records.get(doc_id)
        if not doc:
            kept.append(item)
            continue

        if doc["doc_type"] in DROP_DOC_TYPES:
            dropped.append(f"{doc_id} ({doc['doc_type']}: {doc['title'][:40]})")
            continue

        before_state = item.get("state")
        before_status = item.get("estado_besluit", "")
        before_pdf = item.get("pdf_url", "")

        item["state"] = doc["state"]
        item["doc_type"] = doc["doc_type"]
        item["classification"] = doc["classification"]
        item["source_url"] = doc["source_url"] or ORI_PERMALINK.format(doc_id=doc_id)
        item["attachments"] = doc["attachments"]
        if doc["date"]:
            item["date"] = doc["date"]
        if doc["pdf_url"]:
            item["pdf_url"] = doc["pdf_url"]

        for lang, field in STATUS_FIELDS.items():
            item[field] = status_text(item["state"], lang)

        if before_state != item["state"] or before_status != item["estado_besluit"]:
            changes.append(f"{doc_id}: status {before_status!r} -> {item['estado_besluit']!r}")
        if not before_pdf and item["pdf_url"]:
            changes.append(f"{doc_id}: pdf_url filled ({len(item['attachments'])} attachments)")

        kept.append(item)

    for line in changes:
        logger.info(line)
    for line in dropped:
        logger.info("dropped %s", line)

    logger.info("%d changes, %d entries dropped, %d kept", len(changes), len(dropped), len(kept))

    if args.dry_run:
        logger.info("dry run, nothing written")
        return 0

    STATE_FILE.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("wrote %s", STATE_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
