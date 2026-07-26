"""
Utility to mark items as degraded to force pipeline re-summarization.
"""

import json


def main():
    state_file = "state/processed.json"
    with open(state_file, "r", encoding="utf-8") as f:
        items = json.load(f)

    for item in items:
        item["degraded"] = True

    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    print(f"Marked {len(items)} items for re-summarization.")

if __name__ == "__main__":
    main()
