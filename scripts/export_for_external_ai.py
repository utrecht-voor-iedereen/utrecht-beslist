"""
Writes the council documents out as Markdown briefs to hand to another model.

Groq's free tier is 100,000 tokens a day, and re-summarizing every entry from
its actual PDF text plus translating the result into eight languages costs
roughly four times that. This exports the source text and the exact output
contract instead, so the work can be done elsewhere and imported back with
`python -m scripts.import_summaries`.

Only documents whose text could be resolved from Open Raadsinformatie
attachments are exported: with no source there is nothing to summarize, and
inventing prose is the failure mode this whole exercise is correcting.

    python -m scripts.export_for_external_ai
    python -m scripts.export_for_external_ai --per-batch 2 --max-chars 16000
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from .source_ori import fetch_utrecht_documents, filter_documents

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PROJECT_ROOT / "state" / "processed.json"
OUT_DIR = PROJECT_ROOT / "translation-tasks"

MIN_USABLE_CHARS = 500

# Written by import_summaries; entries carrying it have already been done.
EXTERNAL_MODEL_LABEL = "External model (manual hand-off)"

LANG_SUFFIXES = ["nl", "en", "es", "tr", "pt_br", "pt_pt", "fr", "de"]

# base name -> the key each language uses. The Dutch keys are irregular; they
# are what the state file already contains and must not be renamed here.
FIELD_KEYS: dict[str, dict[str, str]] = {
    "title_short": {"nl": "titel_kort_nl", "_": "title_short_{s}"},
    "summary": {"nl": "samenvatting_nl", "_": "summary_{s}"},
    "key_figure": {"nl": "cifra_clave_nl", "_": "key_figure_{s}"},
    "impact_sentence": {"nl": "frase_impacto_nl", "_": "impact_sentence_{s}"},
    "bullet_1_what": {"nl": "punt_1_wat_nl", "_": "bullet_1_what_{s}"},
    "bullet_2_who": {"nl": "punt_2_wie_nl", "_": "bullet_2_who_{s}"},
    "bullet_3_cost": {"nl": "punt_3_geld_nl", "_": "bullet_3_cost_{s}"},
    "context": {"nl": "contexto_nl", "_": "context_{s}"},
    "consequences": {"nl": "consecuencias_nl", "_": "consequences_{s}"},
    "timeline": {"nl": "plazo_nl", "_": "timeline_{s}"},
}

FIELD_BRIEF = {
    "title_short": "Short clear title, max 8 words.",
    "summary": "2-3 sentences on what the council is deciding.",
    "key_figure": 'The headline amount **exactly as the document states it**. "" if the document states no amount.',
    "impact_sentence": "One sentence on what changes for an Utrecht resident.",
    "bullet_1_what": "Prefix 📌 — one sentence: what the measure is.",
    "bullet_2_who": "Prefix 👥 — who or which area it affects.",
    "bullet_3_cost": "Prefix 💶 — the financial effect. Say so plainly if the document gives none.",
    "context": "Prefix 🎯 — why this was tabled.",
    "consequences": "Prefix 🏘️ — what concretely changes in the city.",
    "timeline": 'Prefix 📅 — start year or quarter as stated. "" if not stated.',
}

THEMES_ALLOWED = [
    "wonen", "verkeer", "groen-klimaat", "veiligheid", "bestuur-financien",
    "zorg", "jeugd-onderwijs", "cultuur-evenementen", "overig",
]
WIJKEN_ALLOWED = [
    "Binnenstad", "Oost", "Leidsche Rijn", "Overvecht", "Zuid", "Zuidwest",
    "West", "Noordwest", "Vleuten-De Meern", "Noordoost", "Overig",
]


def keys_for(base: str) -> list[str]:
    """Every state key for one logical field, in language order."""
    spec = FIELD_KEYS[base]
    out = []
    for suffix in LANG_SUFFIXES:
        out.append(spec["nl"] if suffix == "nl" else spec["_"].format(s=suffix))
    return out


def instructions() -> str:
    field_lines = "\n".join(
        f"- **`{base}`** — {FIELD_BRIEF[base]}\n  Keys: `{'`, `'.join(keys_for(base))}`"
        for base in FIELD_KEYS
    )
    return f"""## What to do

For every document below, write a plain-language summary and give it in **all
eight languages**: Dutch, English, Spanish (Spain), Turkish, Brazilian
Portuguese, European Portuguese, French, German.

The audience is Utrecht residents sorting out permits, benefits and housing —
not civil servants. Aim at CEFR **B1**: short sentences, concrete nouns, no
administrative jargon.

## Rules that matter more than style

1. **Invent nothing.** Every amount, date and number must appear literally in
   the document text below. If it is not there, return `""` for that field.
   Do not carry a figure over from another document.
2. **Never return an example from this brief as an answer.** A previous run
   copied a sample amount out of its own prompt and published it as fact on two
   unrelated decisions.
3. **Keep Dutch proper nouns**: place names, district names, and the names of
   schemes and bodies (Voorjaarsnota, Gemeenteraad, Overvecht, Huisvestings-
   verordening). Translate the words around them.
4. **Translate everything else.** Returning the Dutch or English text unchanged
   under another language is a failed answer.
5. **Say nothing about the outcome of a vote.** Whether a proposal passed is
   read from the official register separately and will overwrite anything here.
6. Keep the leading emoji shown for a field exactly as given.

## Fields

{field_lines}

Plus, per document:

- **`thema`** — array, one or more of: `{'`, `'.join(THEMES_ALLOWED)}`
- **`wijken`** — array of districts the document actually names, from:
  `{'`, `'.join(WIJKEN_ALLOWED)}`. Use `["Overig"]` when it applies city-wide.
- **`impact`** — one of `hoog`, `gemiddeld`, `laag`. Judge by how many
  residents notice it, not by the size of the budget.

## Output

Return **one JSON object, nothing else** — no commentary, no markdown fence
around it if your tool lets you avoid it. Save it as `batch-NN.json` next to
this file, matching the number in this file's name.

```json
{{
  "items": [
    {{
      "doc_id": "<copy exactly from the document heading>",
      "titel_kort_nl": "...",
      "title_short_en": "...",
      "...": "every key listed under Fields, for all eight languages",
      "thema": ["bestuur-financien"],
      "wijken": ["Overig"],
      "impact": "gemiddeld"
    }}
  ]
}}
```

`python -m scripts.import_summaries` validates the result before it touches the
site: it rejects a batch with missing keys, with an unknown `doc_id`, or with
text left identical to the Dutch or English source.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-batch", type=int, default=3, help="documents per file (default 3)")
    parser.add_argument("--max-chars", type=int, default=12000, help="source text per document")
    parser.add_argument(
        "--all",
        action="store_true",
        help="also re-export entries already summarized from their source",
    )
    args = parser.parse_args()

    state = {item["doc_id"]: item for item in json.loads(STATE_FILE.read_text(encoding="utf-8"))}

    logger.info("fetching documents and attachments from ORI...")
    docs: dict[str, dict[str, Any]] = {
        d["id"]: d for d in filter_documents(fetch_utrecht_documents(size=150))
    }

    usable, no_source, done = [], [], []
    for doc_id, entry in state.items():
        doc = docs.get(doc_id)
        if not doc or len(doc.get("text", "")) < MIN_USABLE_CHARS:
            no_source.append(doc_id)
        elif not args.all and entry.get("ai_model") == EXTERNAL_MODEL_LABEL:
            # Already written from this text; re-exporting it would spend the
            # effort again for the same result.
            done.append(doc_id)
        else:
            usable.append(doc)

    if done:
        logger.info("%d entry(ies) already summarized from source, skipped (--all to redo)", len(done))

    usable.sort(key=lambda d: d.get("date", ""), reverse=True)

    OUT_DIR.mkdir(exist_ok=True)
    for stale in OUT_DIR.glob("batch-*.md"):
        stale.unlink()

    batches = [usable[i:i + args.per_batch] for i in range(0, len(usable), args.per_batch)]
    guide = instructions()

    for number, batch in enumerate(batches, start=1):
        parts = [
            f"# Utrecht Beslist — batch {number:02d} of {len(batches):02d}",
            "",
            f"{len(batch)} document(s). Return `batch-{number:02d}.json`.",
            "",
            guide,
            "---",
            "",
            "# Documents",
        ]
        for doc in batch:
            text = doc["text"][: args.max_chars].strip()
            parts += [
                "",
                f"## doc_id: `{doc['id']}`",
                "",
                f"- **Official title:** {doc['title']}",
                f"- **Date:** {(doc.get('date') or '')[:10]}",
                f"- **Register record:** {doc.get('source_url', '')}",
            ]
            if doc.get("source_borrowed_from"):
                parts.append(
                    "- **Note:** this is the council's recorded decision on the proposal "
                    f"below (ORI publishes the papers under `{doc['source_borrowed_from']}`). "
                    "Write it as a decision that was taken, not as a proposal being tabled."
                )
            parts += [
                "",
                "### Source text",
                "",
                "```text",
                text,
                "```",
            ]
        target = OUT_DIR / f"batch-{number:02d}.md"
        target.write_text("\n".join(parts) + "\n", encoding="utf-8")
        logger.info(
            "wrote %s — %d doc(s), %d chars",
            target.relative_to(PROJECT_ROOT), len(batch), len(target.read_text(encoding="utf-8")),
        )

    readme = [
        "# Hand-off to an external model",
        "",
        f"{len(usable)} of {len(state)} entries have source text that could be resolved",
        "from Open Raadsinformatie attachments. Those are split across",
        f"`batch-01.md` … `batch-{len(batches):02d}.md`.",
        "",
        "## How to run it",
        "",
        "1. Paste one `batch-NN.md` into the model. The file carries its own",
        "   instructions, so nothing else needs saying.",
        "2. Save the JSON it returns as `translation-tasks/batch-NN.json`.",
        "3. Repeat for each batch — order does not matter, and a partial set is",
        "   fine; only the batches present get imported.",
        "4. Import and rebuild:",
        "",
        "   ```bash",
        "   python -m scripts.import_summaries --dry-run   # check first",
        "   python -m scripts.import_summaries",
        "   python -m scripts.build_site",
        "   ```",
        "",
        "The importer refuses a batch with missing keys, an unknown `doc_id`, or",
        "text left identical to the Dutch or English source, and it never",
        "overwrites the decision status, dates, links or attachments — those come",
        "from the register, not from a model.",
        "",
        "## Entries with no source text",
        "",
        "Open Raadsinformatie publishes no readable attachment for these, so they",
        "are not in any batch and keep their current text. Summarizing them would",
        "mean writing from the title alone, which is what produced the generic",
        "prose this hand-off exists to replace.",
        "",
    ]
    readme += [f"- `{doc_id}` — {state[doc_id].get('titel_kort_nl', '')}" for doc_id in no_source]
    (OUT_DIR / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")

    logger.info(
        "%d document(s) exported across %d batch(es); %d without source text",
        len(usable), len(batches), len(no_source),
    )
    logger.info("start at %s", (OUT_DIR / "README.md").relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
