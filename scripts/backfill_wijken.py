"""
Re-derives the neighbourhood tags of the entries already in the state file from
their own text, instead of trusting what the summarizer put there.

Same doctrine the project already applies to the decision state, dates and
source links: the facts come from the document, not from the model. The
summarizer left 85% of the archive on the catch-all "Overig", and it was right
more often than not — most council business really is city-wide — but it missed
every stuk that names the neighbourhood without naming the district, which is
how the documents are actually written.

Only ever ADDS districts. A tag the model got right from context the text does
not spell out is not thrown away, because there is no way to tell it apart from
one it invented.

    python -m scripts.backfill_wijken            # apply
    python -m scripts.backfill_wijken --dry-run  # report only
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

from .i18n import wijk_label
from .themes import detect_wijken_heuristics

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "processed.json"

# Los campos en neerlandés son los que escribe el modelo primero; los demás
# idiomas son traducciones suyas y no aportan topónimos nuevos.
CAMPOS_TEXTO = (
    "official_title",
    "titel_kort_nl",
    "samenvatting_nl",
    "contexto_nl",
    "consecuencias_nl",
    "punt_2_wie_nl",
)


def texto_de(item: dict) -> str:
    return " ".join(str(item.get(c) or "") for c in CAMPOS_TEXTO)


# La línea visible de "a quién y dónde afecta", por idioma. Se pegaba la lista
# de barrios en crudo, así que el comodín interno "Overig" salía tal cual en los
# ocho idiomas: 813 fichas respondían "Afecta a Overig".
BULLET_WIE = {
    "punt_2_wie_nl": ("nl", "👥 Wie & Waar: Betreft {}"),
    "bullet_2_who_en": ("en", "👥 Who & Where: Concerns {}"),
    "bullet_2_who_es": ("es", "👥 Quién y dónde: Afecta a {}"),
    "bullet_2_who_tr": ("tr", "👥 Kim ve Nerede: {} bölgesini ilgilendiriyor"),
    "bullet_2_who_pt_br": ("pt-br", "👥 Quem e Onde: Refere-se a {}"),
    "bullet_2_who_pt_pt": ("pt-pt", "👥 Quem e Onde: Refere-se a {}"),
    "bullet_2_who_fr": ("fr", "👥 Qui & Où : Concerne {}"),
    "bullet_2_who_de": ("de", "👥 Wer & Wo: Betrifft {}"),
}

# Solo se reescriben las líneas que siguen exactamente esa plantilla. Si alguien
# escribió a mano una explicación mejor, se respeta.
PLANTILLAS = {
    campo: re.compile("^" + re.escape(patron.split("{}")[0]) + ".*$")
    for campo, (_, patron) in BULLET_WIE.items()
}


def reescribe_bullets(item: dict, wijken: list[str]) -> bool:
    tocado = False
    for campo, (lang, patron) in BULLET_WIE.items():
        actual = (item.get(campo) or "").strip()
        if not actual or not PLANTILLAS[campo].match(actual):
            continue
        nuevo = patron.format(", ".join(wijk_label(w, lang) for w in wijken))
        if nuevo != actual:
            item[campo] = nuevo
            tocado = True
    return tocado


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    items = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    cambios = []
    reescritas = 0

    for item in items:
        actuales = [w for w in (item.get("wijken") or []) if w != "Overig"]
        detectados = detect_wijken_heuristics("", texto_de(item))
        detectados = [w for w in detectados if w != "Overig"]

        nuevos = [w for w in detectados if w not in actuales]
        if nuevos:
            item["wijken"] = actuales + nuevos
            cambios.append(f"{item.get('doc_id')}: {actuales or ['Overig']} -> {item['wijken']}")

        # La línea visible se rehace siempre desde la lista final, o las 45
        # entradas con barrio nuevo seguirían diciendo "Overig" al lector.
        if reescribe_bullets(item, item.get("wijken") or ["Overig"]):
            reescritas += 1

    for linea in cambios:
        logger.info(linea)
    logger.info(
        "%d entradas con barrio nuevo y %d con la línea de 'a quién afecta' rehecha, de %d",
        len(cambios), reescritas, len(items),
    )

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
