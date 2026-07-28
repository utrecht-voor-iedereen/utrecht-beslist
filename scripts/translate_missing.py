"""
Fills in the language variants the summarization step never produced.

The AI chain asks for eight languages in one response, but the model returns
only the Dutch and English fields and nothing checks, so every page in ES, TR,
PT-BR, PT-PT, FR and DE falls back to English through get_item_lang_field().
This translates the existing Dutch and English text into the missing languages
and, unlike the summarization step, refuses to accept a partial answer.

    python -m scripts.translate_missing              # only what is missing
    python -m scripts.translate_missing --force      # redo every language
    python -m scripts.translate_missing --limit 2    # try a couple first
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "processed.json"

# Target languages keyed by the suffix used in the item dict.
TARGETS = {
    "es": "Spanish (Spain)",
    "tr": "Turkish",
    "pt_br": "Portuguese (Brazil)",
    "pt_pt": "Portuguese (Portugal)",
    "fr": "French",
    "de": "German",
}

# The eleven translatable fields, with the Dutch and English keys they come
# from. The Dutch names are irregular — several use Spanish words — so they are
# listed explicitly rather than derived.
FIELDS = [
    ("title_short", "titel_kort_nl", "title_short_en"),
    ("summary", "samenvatting_nl", "summary_en"),
    ("status", "estado_besluit", "status_en"),
    ("key_figure", "cifra_clave_nl", "key_figure_en"),
    ("impact_sentence", "frase_impacto_nl", "impact_sentence_en"),
    ("bullet_1_what", "punt_1_wat_nl", "bullet_1_what_en"),
    ("bullet_2_who", "punt_2_wie_nl", "bullet_2_who_en"),
    ("bullet_3_cost", "punt_3_geld_nl", "bullet_3_cost_en"),
    ("context", "contexto_nl", "context_en"),
    ("consequences", "consecuencias_nl", "consequences_en"),
    ("timeline", "plazo_nl", "timeline_en"),
]

SYSTEM_PROMPT = """You translate Dutch municipal council summaries for residents of Utrecht who do not read Dutch.

Rules:
- Translate into the requested language only. Never leave English or Dutch text in the output.
- Keep the leading emoji of a field exactly as it appears in the source.
- Keep it plain and concrete, at roughly CEFR B1. These are read by people sorting out benefits and permits, not by civil servants.
- Keep Dutch proper nouns as they are: place names, district names, and the names of schemes and bodies (Voorjaarsnota, Gemeenteraad, Overvecht). Translate the words around them.
- Keep numbers, dates, amounts and document identifiers unchanged.
- Return only a JSON object with exactly the requested keys. No commentary.
"""


def load_state() -> list[dict[str, Any]]:
    with STATE_FILE.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, list) else list(data.values())


def save_state(items: list[dict[str, Any]]) -> None:
    with STATE_FILE.open("w", encoding="utf-8") as fh:
        json.dump(items, fh, ensure_ascii=False, indent=2)


def missing_langs(item: dict[str, Any], force: bool) -> list[str]:
    """Languages for which at least one field is absent or blank."""
    if force:
        return list(TARGETS)
    out = []
    for suffix in TARGETS:
        for base, _nl, _en in FIELDS:
            value = item.get(f"{base}_{suffix}")
            if not (isinstance(value, str) and value.strip()):
                out.append(suffix)
                break
    return out


def call_groq(payload: dict[str, Any], api_key: str) -> str:
    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


def translate(item: dict[str, Any], suffix: str, api_key: str, model: str) -> dict[str, str]:
    """Asks for one language at a time: a short answer is far likelier to arrive whole."""
    source = {}
    for base, nl_key, en_key in FIELDS:
        source[base] = {
            "nl": item.get(nl_key, ""),
            "en": item.get(en_key, ""),
        }

    user = {
        "target_language": TARGETS[suffix],
        "required_keys": [base for base, _n, _e in FIELDS],
        "source": source,
    }

    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
        ],
    }

    raw = call_groq(payload, api_key)
    data = json.loads(raw)

    # The model sometimes nests the answer under the language name.
    if not any(base in data for base, _n, _e in FIELDS):
        for value in data.values():
            if isinstance(value, dict) and any(base in value for base, _n, _e in FIELDS):
                data = value
                break

    result = {}
    for base, _nl, _en in FIELDS:
        value = data.get(base)
        if isinstance(value, str) and value.strip():
            result[base] = value.strip()
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="retranslate even where text exists")
    parser.add_argument("--limit", type=int, default=0, help="stop after N items")
    parser.add_argument("--dry-run", action="store_true", help="report what is missing and exit")
    args = parser.parse_args()

    items = load_state()
    pending = [(i, missing_langs(item, args.force)) for i, item in enumerate(items)]
    pending = [(i, langs) for i, langs in pending if langs]

    if args.limit:
        pending = pending[: args.limit]

    total = sum(len(langs) for _i, langs in pending)
    logger.info("%d of %d entries need translating (%d language passes)", len(pending), len(items), total)

    if args.dry_run or not pending:
        return 0

    api_key = (os.environ.get("GROQ_API_KEY") or "").strip().strip('"').strip("'")
    if not api_key:
        logger.error("GROQ_API_KEY is not set. Run with: python -m dotenv or export it first.")
        return 1
    model = os.environ.get("AI_MODEL", "llama-3.3-70b-versatile")

    done = 0
    incomplete: list[str] = []

    for index, langs in pending:
        item = items[index]
        label = item.get("titel_kort_nl") or item.get("doc_id", "?")

        for suffix in langs:
            filled: dict[str, str] = {}
            # One retry: a truncated or malformed answer is usually fine second time.
            for attempt in (1, 2):
                try:
                    filled = translate(item, suffix, api_key, model)
                except urllib.error.HTTPError as exc:
                    wait = 20 if exc.code == 429 else 3
                    logger.warning("%s/%s HTTP %s, waiting %ss", label[:40], suffix, exc.code, wait)
                    time.sleep(wait)
                    continue
                except Exception as exc:  # noqa: BLE001
                    logger.warning("%s/%s failed: %s", label[:40], suffix, exc)
                    time.sleep(3)
                    continue

                if len(filled) == len(FIELDS):
                    break
                logger.warning(
                    "%s/%s returned %d of %d fields on attempt %d",
                    label[:40], suffix, len(filled), len(FIELDS), attempt,
                )

            # Write whatever came back, but never overwrite good text with nothing.
            for base, value in filled.items():
                item[f"{base}_{suffix}"] = value

            if len(filled) < len(FIELDS):
                incomplete.append(f"{item.get('doc_id')}/{suffix} ({len(filled)}/{len(FIELDS)})")
            else:
                done += 1

            # Groq's free tier is rate limited; a short pause is cheaper than a 429.
            time.sleep(1.5)

        save_state(items)
        logger.info("saved after %s", label[:50])

    logger.info("completed %d of %d language passes", done, total)
    if incomplete:
        logger.warning("still incomplete (%d): %s", len(incomplete), ", ".join(incomplete[:20]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
