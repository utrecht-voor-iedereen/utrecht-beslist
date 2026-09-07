"""
Re-derives the theme tags of the entries already in the state file from the full
document text in Open Raadsinformatie, instead of trusting what the summarizer
put there.

Same doctrine as backfill_sources.py and backfill_wijken.py: the facts come from
the register, not from the model. Measured over the 983 entries, the summarizer
tagged 97% of them "bestuur-financien" and 89% "verkeer", with 3,9 themes each.
A filter where almost everything carries the same label does not filter.

Classifying from the stored summary does not work either: it is ~330 characters
of generic prose and leaves 70% of the archive with no theme at all. The real
text is in ORI — up to 6.000 characters per stuk — and that is what this reads.

Entries whose document carries no text (agenda items with no attachment) keep
the tags they had: a worse guess is still better than none.

    python -m scripts.backfill_themes            # apply
    python -m scripts.backfill_themes --dry-run  # report only
    python -m scripts.backfill_themes --limit 50 # probar con unos pocos
"""
from __future__ import annotations

import argparse
import collections
import json
import logging
from pathlib import Path

from .source_ori import fetch_documents_by_ids
from .themes import detect_theme_heuristics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "processed.json"

# ORI se pide de cien en cien; fetch_documents_by_ids ya trocea, pero pedir los
# mil de golpe deja la memoria llena de adjuntos que no hacen falta a la vez.
LOTE = 200


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="solo las N primeras")
    args = parser.parse_args()

    items = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    objetivo = items[: args.limit] if args.limit else items

    textos: dict[str, str] = {}
    for inicio in range(0, len(objetivo), LOTE):
        lote = [str(i.get("doc_id")) for i in objetivo[inicio : inicio + LOTE]]
        for doc in fetch_documents_by_ids(lote):
            textos[str(doc.get("id"))] = doc.get("text") or ""
        logger.info("leídos %d de %d", min(inicio + LOTE, len(objetivo)), len(objetivo))

    cambiados = 0
    sin_texto = 0
    antes = collections.Counter()
    despues = collections.Counter()

    for item in objetivo:
        previos = [t for t in (item.get("thema") or []) if t]
        for t in previos:
            antes[t] += 1

        texto = textos.get(str(item.get("doc_id")), "")
        if not texto:
            sin_texto += 1
            for t in previos:
                despues[t] += 1
            continue

        nuevos = detect_theme_heuristics(str(item.get("official_title") or ""), texto)
        # "overig" es el comodín de "no se pudo clasificar". Si el texto no da
        # ninguna pista, la etiqueta del modelo es mejor que ninguna.
        if nuevos == ["overig"]:
            for t in previos:
                despues[t] += 1
            continue

        for t in nuevos:
            despues[t] += 1
        if sorted(nuevos) != sorted(previos):
            cambiados += 1
        item["thema"] = nuevos

    n = len(objetivo)
    logger.info("%d entradas reclasificadas, %d sin texto en ORI, de %d", cambiados, sin_texto, n)
    logger.info("%-22s %8s %8s", "tema", "antes", "después")
    for tema in sorted(set(antes) | set(despues)):
        logger.info("%-22s %7d%% %7d%%", tema, antes[tema] * 100 // n, despues[tema] * 100 // n)
    media_antes = sum(antes.values()) / n
    media_despues = sum(despues.values()) / n
    logger.info("temas por ficha: %.2f -> %.2f", media_antes, media_despues)

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
