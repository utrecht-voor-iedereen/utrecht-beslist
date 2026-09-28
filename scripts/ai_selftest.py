"""
Checks that every configured AI model still answers, without touching the site.

Providers retire models without much notice — Groq dropped llama-3.3-70b from
its free tier and the pipeline summarized nothing for weeks before anyone
noticed. This sends one tiny document to each model in the chain and reports
which answer with a valid summary, so a retirement shows up here first.

    python -m scripts.ai_selftest
"""
from __future__ import annotations

import logging
import os
import sys
import time
from collections.abc import Callable
from typing import Any

from .ai_chain import (
    GEMINI_DEFAULT_MODEL,
    groq_models,
    summarize_with_gemini,
    summarize_with_groq_model,
    summarize_with_openrouter,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

SAMPLE = {
    "id": "selftest",
    "title": "Raadsvoorstel Vaststellen subsidieregeling buurtmoestuinen 2027",
    "date": "2026-10-01",
    "pdf_url": "",
    "text": (
        "Voorstel aan de gemeenteraad. Het college stelt de raad voor de subsidieregeling "
        "buurtmoestuinen 2027 vast te stellen. Bewonersgroepen kunnen maximaal 2.500 euro per "
        "moestuin aanvragen voor aanleg en onderhoud. Het totale budget is 120.000 euro per jaar "
        "en komt uit het programma Groen. De regeling geldt voor de hele stad en start op "
        "1 januari 2027."
    ),
}


def check(name: str, call: Callable[[], list[dict[str, Any]]]) -> bool:
    start = time.monotonic()
    try:
        items = call()
    except Exception as e:  # noqa: BLE001
        logger.info("FAIL  %-40s %s", name, str(e)[:200])
        return False
    ok = bool(items) and not items[0].get("degraded") and items[0].get("summary_es")
    seconds = time.monotonic() - start
    if ok:
        logger.info("OK    %-40s %.1fs  «%s»", name, seconds, items[0].get("titel_kort_nl", "")[:60])
    else:
        logger.info("FAIL  %-40s answered without a usable summary", name)
    return bool(ok)


def main() -> int:
    results: list[bool] = []
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        for model in groq_models():
            def call(m: str = model) -> list[dict[str, Any]]:
                return summarize_with_groq_model([SAMPLE], groq_key, m)
            results.append(check(f"groq/{model}", call))
            time.sleep(10)  # stay inside each model's per-minute budget
    else:
        logger.info("SKIP  groq (no GROQ_API_KEY)")

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key:
        model = os.environ.get("GEMINI_MODEL", GEMINI_DEFAULT_MODEL)
        results.append(check(f"gemini/{model}", lambda: summarize_with_gemini([SAMPLE], gemini_key)))
    else:
        logger.info("SKIP  gemini (no GEMINI_API_KEY)")

    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    if openrouter_key:
        results.append(check("openrouter", lambda: summarize_with_openrouter([SAMPLE], openrouter_key)))
    else:
        logger.info("SKIP  openrouter (no OPENROUTER_API_KEY)")

    working = sum(results)
    logger.info("%d of %d configured models answered.", working, len(results))
    # Fails the workflow when nothing works, which is when the site stops.
    return 0 if working else 1


if __name__ == "__main__":
    sys.exit(main())
