"""
Removes values the summarizer copied out of its own prompt.

The prompt used to describe the key-figure field as
`"💶 Cijfer/Kosten (bv. 2,5M € of Geen extra kosten)"`, and the model answered
with the example: two unrelated decisions were published claiming a cost of
2,5M €, and twenty-four claimed no extra cost, none of it read out of any
document. A blank field renders as nothing, which is honest; a made-up amount
on a municipal transparency site is not.

`ai_chain.py` no longer offers those examples, so this only has to clean up
what already shipped.

    python -m scripts.purge_placeholders            # apply
    python -m scripts.purge_placeholders --dry-run  # report only
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "processed.json"

KEY_FIGURE_FIELDS = [
    "cifra_clave_nl",
    "key_figure_en",
    "key_figure_es",
    "key_figure_tr",
    "key_figure_pt_br",
    "key_figure_pt_pt",
    "key_figure_fr",
    "key_figure_de",
]

# The amount the prompt used as its illustration, in the spellings the
# translation step produced.
FABRICATED_AMOUNTS = re.compile(r"^\W*(2[,.]5\s*M\s*€|€\s*2[,.]5\s*M)\W*$", re.IGNORECASE)


def is_fabricated(value: str) -> bool:
    return bool(FABRICATED_AMOUNTS.match(value.strip()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args()

    items: list[dict[str, Any]] = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    cleared = 0
    touched: list[str] = []

    for item in items:
        # The whole group goes when any language carries the example amount:
        # the other languages are translations of the same invented figure.
        if any(is_fabricated(str(item.get(field, ""))) for field in KEY_FIGURE_FIELDS):
            touched.append(f"{item.get('doc_id')} ({item.get('titel_kort_nl', '')[:40]})")
            for field in KEY_FIGURE_FIELDS:
                if item.get(field):
                    item[field] = ""
                    cleared += 1

    for line in touched:
        logger.info("cleared invented key figure: %s", line)
    logger.info("%d fields cleared across %d entries", cleared, len(touched))

    if args.dry_run:
        logger.info("dry run, nothing written")
        return 0

    STATE_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    logger.info("wrote %s", STATE_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
