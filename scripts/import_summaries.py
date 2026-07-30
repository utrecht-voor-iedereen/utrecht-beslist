"""
Imports summaries produced by an external model back into the state file.

Reads every `translation-tasks/batch-*.json` and merges it, but only after the
batch passes validation. The checks exist because each one corresponds to
something that actually shipped: missing language variants, English text under
a Spanish heading, and an amount copied out of the prompt and presented as a
municipal figure.

Facts held by Open Raadsinformatie — decision status, dates, source links,
attachments — are never taken from these files.

    python -m scripts.import_summaries --dry-run
    python -m scripts.import_summaries
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any

from .export_for_external_ai import (
    FIELD_KEYS,
    LANG_SUFFIXES,
    OUT_DIR,
    THEMES_ALLOWED,
    WIJKEN_ALLOWED,
    keys_for,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PROJECT_ROOT / "state" / "processed.json"

IMPACT_ALLOWED = {"hoog", "gemiddeld", "laag"}

# Fields allowed to be empty: a document that names no amount and no start date
# should say nothing rather than something invented.
OPTIONAL_FIELDS = {"key_figure", "timeline"}

# A title is often the Dutch name of the scheme, so matching the Dutch source is
# correct there; matching the English is still a failure.
KEEP_DUTCH_FIELDS = {"title_short"}

PLACEHOLDER_AMOUNT = re.compile(r"^\W*(2[,.]5\s*M\s*€|€\s*2[,.]5\s*M)\W*$", re.IGNORECASE)


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def validate_item(item: dict[str, Any], known_ids: set[str]) -> list[str]:
    """Returns the reasons this entry cannot be imported; empty means it can."""
    problems: list[str] = []
    doc_id = str(item.get("doc_id", "")).strip()

    if not doc_id:
        return ["missing doc_id"]
    if doc_id not in known_ids:
        return [f"{doc_id}: not an entry in the state file"]

    for base in FIELD_KEYS:
        values: dict[str, str] = {}
        for suffix, key in zip(LANG_SUFFIXES, keys_for(base)):
            raw = item.get(key)
            if not isinstance(raw, str):
                problems.append(f"{doc_id}: {key} missing or not a string")
                continue
            values[suffix] = raw.strip()

        if len(values) != len(LANG_SUFFIXES):
            continue

        if base not in OPTIONAL_FIELDS:
            blank = [s for s, v in values.items() if not v]
            if blank:
                problems.append(f"{doc_id}: {base} empty for {', '.join(blank)}")

        if base == "key_figure":
            for suffix, value in values.items():
                if value and PLACEHOLDER_AMOUNT.match(value):
                    problems.append(f"{doc_id}: key_figure_{suffix} is the sample amount")

        # Anything long that came back byte-identical to the source is untranslated.
        english, dutch = normalize(values.get("en", "")), normalize(values.get("nl", ""))
        for suffix, value in values.items():
            if suffix in ("nl", "en") or len(value) < 25:
                continue
            echoed = normalize(value) == english
            if not echoed and base not in KEEP_DUTCH_FIELDS:
                echoed = normalize(value) == dutch
            if echoed:
                problems.append(f"{doc_id}: {base}_{suffix} is the untranslated source")

    thema = item.get("thema")
    if not isinstance(thema, list) or not thema:
        problems.append(f"{doc_id}: thema must be a non-empty array")
    elif unknown := [t for t in thema if t not in THEMES_ALLOWED]:
        problems.append(f"{doc_id}: unknown thema {unknown}")

    wijken = item.get("wijken")
    if not isinstance(wijken, list) or not wijken:
        problems.append(f"{doc_id}: wijken must be a non-empty array")
    elif unknown := [w for w in wijken if w not in WIJKEN_ALLOWED]:
        problems.append(f"{doc_id}: unknown wijk {unknown}")

    if item.get("impact") not in IMPACT_ALLOWED:
        problems.append(f"{doc_id}: impact must be one of {sorted(IMPACT_ALLOWED)}")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="validate without writing")
    args = parser.parse_args()

    batch_files = sorted(OUT_DIR.glob("batch-*.json"))
    if not batch_files:
        logger.error("no batch-*.json in %s", OUT_DIR)
        return 1

    items = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    state = {item["doc_id"]: item for item in items}

    accepted: dict[str, dict[str, Any]] = {}
    rejected: list[str] = []

    for path in batch_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rejected.append(f"{path.name}: not valid JSON ({exc})")
            continue

        batch_items = payload.get("items") if isinstance(payload, dict) else payload
        if not isinstance(batch_items, list):
            rejected.append(f"{path.name}: expected an object with an 'items' array")
            continue

        for entry in batch_items:
            if not isinstance(entry, dict):
                rejected.append(f"{path.name}: an item is not an object")
                continue
            problems = validate_item(entry, set(state))
            if problems:
                rejected.extend(f"{path.name} · {p}" for p in problems)
                continue
            accepted[str(entry["doc_id"]).strip()] = entry

        logger.info("read %s", path.name)

    for line in rejected:
        logger.warning("rejected: %s", line)

    logger.info("%d entry(ies) accepted, %d problem(s) found", len(accepted), len(rejected))

    if not accepted:
        return 1
    if args.dry_run:
        logger.info("dry run, nothing written")
        return 0

    writable = [key for base in FIELD_KEYS for key in keys_for(base)]
    for doc_id, entry in accepted.items():
        target = state[doc_id]
        for key in writable:
            target[key] = str(entry[key]).strip()
        target["thema"] = list(entry["thema"])
        target["wijken"] = list(entry["wijken"])
        target["impact"] = entry["impact"]
        target["degraded"] = False
        target["ai_model"] = str(entry.get("ai_model") or "External model (manual hand-off)")

    STATE_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("updated %d entry(ies) in %s", len(accepted), STATE_FILE.name)
    logger.info("now run: python -m scripts.build_site")
    return 0 if not rejected else 1


if __name__ == "__main__":
    raise SystemExit(main())
