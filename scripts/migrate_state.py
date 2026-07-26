"""
Migration script to backfill existing state items with 3-bullet breakdown and English translations.
"""

import json

from scripts.ai_chain import generate_degraded_summary


def migrate():
    state_file = "state/processed.json"
    with open(state_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    updated_items = []
    for item in items:
        doc = {
            "id": item.get("doc_id"),
            "title": item.get("titel_kort_nl", ""),
            "text": "",
            "pdf_url": item.get("pdf_url", "")
        }
        deg = generate_degraded_summary(doc)
        deg["date"] = item.get("date", "")
        deg["pdf_url"] = item.get("pdf_url", "")
        updated_items.append(deg)

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(updated_items, f, indent=2, ensure_ascii=False)

    print(f"Migrated {len(updated_items)} items successfully.")

if __name__ == "__main__":
    migrate()
