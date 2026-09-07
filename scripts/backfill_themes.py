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
import urllib.request
from pathlib import Path
from typing import Any

from .source_ori import (
    ORI_ELASTIC_ENDPOINT,
    enrich_with_attachments,
    normalize_document,
    share_text_between_siblings,
)
from .themes import detect_theme_heuristics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "processed.json"

# ORI acepta como mucho cien ids por consulta.
LOTE = 100


def fetch_by_ids(doc_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Los registros de ORI con su texto, de cien en cien.

    Mismo camino que backfill_sources.py: el texto de verdad no está en el hit,
    sino en los MediaObjects que cuelgan de él, así que hay que enriquecer antes
    de leerlo. `share_text_between_siblings` cubre el caso de que ORI archive la
    decisión y la propuesta por separado y solo una lleve el documento.
    """
    out: dict[str, dict[str, Any]] = {}
    for start in range(0, len(doc_ids), LOTE):
        chunk = doc_ids[start:start + LOTE]
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
        logger.info("leídos %d de %d", min(start + LOTE, len(doc_ids)), len(doc_ids))

    registros = list(out.values())
    enrich_with_attachments(registros)
    share_text_between_siblings(registros)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="solo las N primeras")
    args = parser.parse_args()

    items = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    objetivo = items[: args.limit] if args.limit else items

    registros = fetch_by_ids([str(i.get("doc_id")) for i in objetivo if i.get("doc_id")])
    textos: dict[str, str] = {k: (v.get("text") or "") for k, v in registros.items()}

    cambiados = 0
    sin_texto = 0
    antes: collections.Counter[str] = collections.Counter()
    despues: collections.Counter[str] = collections.Counter()

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
