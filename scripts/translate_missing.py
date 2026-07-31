"""
Fills in the language variants the summarization step never produced.

The AI chain asks for eight languages in one response, but the model returns
only the Dutch and English fields and nothing checks, so every page in ES, TR,
PT-BR, PT-PT, FR and DE falls back to English through get_item_lang_field().
This translates the existing Dutch and English text into the missing languages
and, unlike the summarization step, refuses to accept a partial answer.

    python -m scripts.translate_missing              # only what is missing
    python -m scripts.translate_missing --recheck    # also redo English leftovers
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

# The ten translatable fields, with the Dutch and English keys they come from.
# The Dutch names are irregular — several use Spanish words — so they are
# listed explicitly rather than derived.
#
# `status` is deliberately absent: it comes from a fixed table in i18n.py keyed
# on what Open Raadsinformatie records, so translating it here would let a
# paraphrase drift away from the register.
FIELDS = [
    ("title_short", "titel_kort_nl", "title_short_en"),
    ("summary", "samenvatting_nl", "summary_en"),
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


def missing_langs(item: dict[str, Any], force: bool, recheck: bool = False) -> list[str]:
    """
    Languages for which at least one field is absent, blank, or still English.

    With `recheck`, text the model returned verbatim from the source counts as
    missing too, so an entry that slipped through before this check existed is
    picked up on the next run.
    """
    if force:
        return list(TARGETS)
    out = []
    for suffix in TARGETS:
        for base, nl_key, en_key in FIELDS:
            value = item.get(f"{base}_{suffix}")
            if not (isinstance(value, str) and value.strip()):
                out.append(suffix)
                break
            if recheck and is_untranslated(
                value.strip(), item.get(en_key, ""), item.get(nl_key, ""), base
            ):
                out.append(suffix)
                break
    return out


# A title is often the Dutch name of the scheme itself ("Meerjaren Perspectief
# Ruimte 2026"), which the prompt asks to keep, so matching the Dutch source is
# correct there and only an English echo counts as a failure.
KEEP_DUTCH_FIELDS = {"title_short"}


def is_untranslated(value: str, english: str, dutch: str, base: str = "") -> bool:
    """
    True when the model handed the source text back unchanged.

    Short values are exempt: a year, an amount, or a street name is supposed to
    come through identical, and rejecting those would loop forever.
    """
    if len(value) < 25:
        return False
    normalized = " ".join(value.lower().split())
    sources = [" ".join(english.lower().split())]
    if base not in KEEP_DUTCH_FIELDS:
        sources.append(" ".join(dutch.lower().split()))
    return normalized in sources


def call_groq(payload: dict[str, Any], api_key: str) -> str:
    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            # Groq answers 403 to urllib's default agent; ai_chain.py sends this one.
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UtrechtBeslist/1.0",
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

    # The target language goes in the system message as well as the payload:
    # with it only in the JSON body the model sometimes locked onto the "en"
    # key it saw in every source object and echoed the English straight back.
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\nEvery value you return must be written in "
                           f"{TARGETS[suffix]}. Returning the English or Dutch source "
                           f"unchanged is a failed answer.",
            },
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
    for base, _nl, en_key in FIELDS:
        value = data.get(base)
        if not (isinstance(value, str) and value.strip()):
            continue
        value = value.strip()
        if is_untranslated(value, item.get(en_key, ""), item.get(_nl, ""), base):
            # Dropping it here means the attempt counts as incomplete and gets
            # retried. Accepting it is how four entries shipped English prose
            # under a Spanish, Turkish, French and German heading.
            continue
        result[base] = value
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="retranslate even where text exists")
    parser.add_argument("--limit", type=int, default=0, help="stop after N items")
    parser.add_argument("--dry-run", action="store_true", help="report what is missing and exit")
    parser.add_argument(
        "--max-seconds",
        type=float,
        default=float(os.environ.get("TRANSLATE_MAX_SECONDS", "0")),
        help="stop cleanly after this long, keeping what is already saved",
    )
    parser.add_argument(
        "--recheck",
        action="store_true",
        help="also redo fields the model returned verbatim in English or Dutch",
    )
    args = parser.parse_args()

    items = load_state()
    pending = [(i, missing_langs(item, args.force, args.recheck)) for i, item in enumerate(items)]
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
    deadline = time.monotonic() + args.max_seconds if args.max_seconds > 0 else None
    ran_out = False

    for index, langs in pending:
        # A GitHub job that is cancelled mid-step skips the commit, so a run
        # that overruns throws away the summarizing it already paid for. This
        # stops while there is still time to save and push.
        if deadline and time.monotonic() > deadline:
            ran_out = True
            logger.warning(
                "out of time after %.0fs; the rest is picked up on the next run",
                args.max_seconds,
            )
            break

        item = items[index]
        label = item.get("titel_kort_nl") or item.get("doc_id", "?")

        for suffix in langs:
            filled: dict[str, str] = {}
            # Groq's free tier throttles hard, and giving up after two tries is
            # what left 70 of 174 passes empty on the first run.
            for attempt in (1, 2, 3, 4):
                try:
                    filled = translate(item, suffix, api_key, model)
                except urllib.error.HTTPError as exc:
                    if exc.code == 429:
                        # Groq tells you exactly how long to wait; guessing wastes
                        # the retry budget on a window that has not reopened yet.
                        header = exc.headers.get("retry-after") if exc.headers else None
                        try:
                            wait = min(float(header), 120) if header else 30 * attempt
                        except (TypeError, ValueError):
                            wait = 30 * attempt
                    else:
                        wait = 5
                    logger.warning(
                        "%s/%s HTTP %s, waiting %.0fs (attempt %d)",
                        label[:40], suffix, exc.code, wait, attempt,
                    )
                    time.sleep(wait)
                    continue
                except Exception as exc:  # noqa: BLE001
                    logger.warning("%s/%s failed: %s", label[:40], suffix, exc)
                    time.sleep(5)
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

            # Pacing below the free-tier limit costs less time overall than
            # burning retries on 429s.
            time.sleep(float(os.environ.get("TRANSLATE_DELAY", "4")))

        save_state(items)
        logger.info("saved after %s", label[:50])

    logger.info("completed %d of %d language passes", done, total)
    if ran_out:
        return 0
    if incomplete:
        logger.warning("still incomplete (%d): %s", len(incomplete), ", ".join(incomplete[:20]))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
