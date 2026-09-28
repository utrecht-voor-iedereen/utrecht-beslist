"""
Re-derives the theme tags of the entries already in the state file from the full
document text in OpenBesluitvorming, instead of trusting what the summarizer
put there.

Same doctrine as pipeline.apply_source_facts and backfill_wijken.py: the facts come from
the register, not from the model. Measured over the 983 entries, the summarizer
tagged 97% of them "bestuur-financien" and 89% "verkeer", with 3,9 themes each.
A filter where almost everything carries the same label does not filter.

Classifying from the stored summary does not work either: it is ~330 characters
of generic prose and leaves 70% of the archive with no theme at all. The real
text is in the register — up to 6.000 characters per stuk — and that is what
this reads, one dossier at a time.

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
from typing import Any

from .source_obv import papers_of, text_of
from .themes import detect_theme_heuristics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "processed.json"

def texts_by_dossier(items: list[dict[str, Any]]) -> dict[str, str]:
    """El texto de cada expediente, por título oficial.

    Se lee por expediente y no por ficha: ORI archivaba la decisión aparte de la
    propuesta y solo la propuesta llevaba los PDF, así que la decisión toma el
    texto de sus hermanas. Los PDF se buscan en OpenBesluitvorming por su id de
    iBabs, el único que ambos registros comparten.
    """
    expedientes: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for item in items:
        expedientes[str(item.get("official_title") or "").strip()].append(item)

    out: dict[str, str] = {}
    for n, (titulo, fichas) in enumerate(expedientes.items(), start=1):
        papeles = papers_of(fichas)
        out[titulo] = text_of([p["id"] for p in papeles]) if papeles else ""
        if n % 25 == 0:
            logger.info("leídos %d de %d expedientes", n, len(expedientes))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="solo las N primeras")
    args = parser.parse_args()

    items = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    objetivo = items[: args.limit] if args.limit else items

    textos = texts_by_dossier(objetivo)

    cambiados = 0
    sin_texto = 0
    antes: collections.Counter[str] = collections.Counter()
    despues: collections.Counter[str] = collections.Counter()

    for item in objetivo:
        previos = [t for t in (item.get("thema") or []) if t]
        for t in previos:
            antes[t] += 1

        texto = textos.get(str(item.get("official_title") or "").strip(), "")
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
    logger.info("%d entradas reclasificadas, %d sin texto en el registro, de %d", cambiados, sin_texto, n)
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
