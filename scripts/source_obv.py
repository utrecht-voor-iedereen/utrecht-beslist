"""
Client for OpenBesluitvorming, the successor of Open Raadsinformatie.

ORI Classic stopped harvesting the iBabs councils, Utrecht among them, in the
first week of July 2026, and the maintainers will not fix it: the Elastic
endpoint is deprecated and switches off on 1 November 2026
(openstate/open-raadsinformatie#555). OpenBesluitvorming carries the same
registers, current, behind a REST API: https://openbesluitvorming.nl/docs/api

It has no free query language, and its search endpoint is not a harvesting
route: browsing a date window returns `hasMore` with pages that skip results,
even for a single day. The supported route is the export feed — one snapshot,
then a change log read with a cursor — so this module keeps a small local
mirror of Utrecht's recent council meetings in state/openbesluitvorming.json
and brings it up to date on every run.

A meeting carries its whole agenda, and each agenda item its documents. That
is all the pipeline needs to know which proposals were tabled and which were
decided; the text of a document is fetched separately, only for what is about
to be summarized.
"""

import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Any

from .source_ori import (
    DECISION_TITLE_PREFIXES,
    EXCLUDE_TITLE_KEYWORDS,
    MAX_DOC_TEXT_CHARS,
)

logger = logging.getLogger(__name__)

API_BASE = "https://openbesluitvorming.nl/api"
SOURCE_KEY = "utrecht"
# The API asks for a project name and a way to reach whoever runs it.
USER_AGENT = "UtrechtBeslistBot/2.0 (+https://utrecht-voor-iedereen.github.io/utrecht-beslist/)"
PERMALINK = "https://openbesluitvorming.nl/?organization=" + SOURCE_KEY + "&view={entity_id}"

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SYNC_FILE = os.path.join(PROJECT_ROOT, "state", "openbesluitvorming.json")

# How far back the mirror keeps meetings. It is the equivalent of the window of
# 150 hits the ORI query used to return: long enough to cover a recess and the
# backlog MAX_NEW_PER_RUN drains a few documents a day, short enough that the
# committed file stays small.
LOOKBACK_DAYS = int(os.environ.get("OBV_LOOKBACK_DAYS", "120"))

# Rebuild the mirror from a fresh snapshot this often. The change log should
# carry every edit to a meeting, but nothing here can prove it does, and a
# raadsbesluit that never arrives leaves a decision shown as tabled for good.
# A snapshot of Utrecht's meetings is three requests.
RESNAPSHOT_DAYS = int(os.environ.get("OBV_RESNAPSHOT_DAYS", "7"))

# Meetings whose agenda is a list of proposals. The weekly overview is where a
# proposal first appears; the council meeting is where it is decided, and where
# the raadsbesluit is attached afterwards. Committee meetings discuss the same
# proposals in between and would only add a third record per dossier.
MEETING_PREFIXES = ("gemeenteraad", "raadsvergadering", "raadsvoorstellen weekoverzicht")

# The signed decision iBabs attaches to the agenda item once the council has
# voted, e.g. "Raadsbesluit Voorjaarsnota 2026 (gepubliceerd op 10 juli 2026)".
DECISION_DOCUMENT_PREFIX = "raadsbesluit"

PREFERRED_DOCUMENT_TERMS = ("raadsbesluit", "raadsvoorstel", "initiatiefvoorstel", "voorstel")
DEPRIORITIZED_DOCUMENT_TERMS = ("voorblad", "presentielijst", "bijlage")

# The pipeline reads at most this many documents per agenda item. The proposal
# and the decision come first, so the rest is rarely reached before the text
# budget is spent.
MAX_DOCUMENTS_PER_ITEM = 3


class ExportCursorInvalid(Exception):
    """The stored change-log cursor is no longer accepted."""


def _get(path: str, params: dict[str, Any], timeout: int = 60, attempts: int = 4) -> tuple[bytes, Any]:
    """GET against the API, waiting out 429s as the API asks."""
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}" if params else f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read(), response.headers
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt + 1 < attempts:
                wait = float(e.headers.get("Retry-After") or 5)
                logger.info("OpenBesluitvorming asked to slow down; waiting %.0fs.", wait)
                time.sleep(min(wait, 60))
                continue
            if e.code == 400:
                try:
                    code = json.loads(e.read().decode("utf-8")).get("code")
                except (ValueError, AttributeError):
                    code = None
                if code == "invalid_export_cursor":
                    raise ExportCursorInvalid() from e
            raise
    raise RuntimeError(f"gave up on {url} after {attempts} attempts")


def _ndjson(body: bytes) -> list[dict[str, Any]]:
    # Split on newlines only. str.splitlines() also breaks on U+2028 and U+0085,
    # which agenda texts pasted from Word do contain, inside JSON strings.
    return [json.loads(line) for line in body.split(b"\n") if line.strip()]


def entity_suffix(entity_id: str) -> str:
    """The supplier's own id, the last part of an entity id. Safe in a URL path."""
    return entity_id.rsplit(":", 1)[-1]


def permalink(entity_id: str) -> str:
    return PERMALINK.format(entity_id=urllib.parse.quote(entity_id, safe=""))


# --- the mirror ---------------------------------------------------------------


def is_council_meeting(payload: dict[str, Any]) -> bool:
    name = str(payload.get("name") or "").strip().lower()
    return name.startswith(MEETING_PREFIXES)


def compact_meeting(payload: dict[str, Any]) -> dict[str, Any]:
    """Keeps what the pipeline reads from a meeting, and drops the rest."""

    def items(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for node in nodes or []:
            out.append({
                "id": node.get("id") or "",
                "title": node.get("title") or "",
                "is_heading": bool(node.get("is_heading")),
                "documents": [
                    {
                        "id": doc.get("id") or "",
                        "name": doc.get("name") or doc.get("file_name") or "",
                        "url": doc.get("original_url") or "",
                    }
                    for doc in node.get("documents") or []
                    if doc.get("id")
                ],
                "agenda_items": items(node.get("agenda_items") or []),
            })
        return out

    return {
        "name": payload.get("name") or "",
        "start_date": payload.get("start_date") or "",
        "agenda": items(payload.get("agenda") or []),
    }


def _within_window(meeting: dict[str, Any], today: date) -> bool:
    raw = str(meeting.get("start_date") or "")[:10]
    try:
        return date.fromisoformat(raw) >= today - timedelta(days=LOOKBACK_DAYS)
    except ValueError:
        return False


def load_mirror(path: str = SYNC_FILE) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            mirror = json.load(f)
        if isinstance(mirror, dict) and isinstance(mirror.get("meetings"), dict):
            return mirror
    except FileNotFoundError:
        pass
    except (OSError, ValueError) as e:
        logger.warning("Could not read %s, rebuilding it: %s", path, e)
    return {"cursor": "", "snapshot_at": "", "meetings": {}}


def save_mirror(mirror: dict[str, Any], path: str = SYNC_FILE) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mirror, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def apply_records(mirror: dict[str, Any], records: list[dict[str, Any]]) -> int:
    """Folds export records into the mirror. Returns how many meetings changed."""
    changed = 0
    for record in records:
        if record.get("entity_type") != "Meeting":
            continue
        entity_id = record.get("entity_id") or ""
        payload = record.get("payload") or {}
        if record.get("op") == "delete" or not is_council_meeting(payload):
            # A meeting renamed away from the council, or withdrawn, leaves.
            if mirror["meetings"].pop(entity_id, None) is not None:
                changed += 1
            continue
        mirror["meetings"][entity_id] = compact_meeting(payload)
        changed += 1
    return changed


def prune(mirror: dict[str, Any], today: date) -> None:
    mirror["meetings"] = {
        mid: meeting for mid, meeting in mirror["meetings"].items() if _within_window(meeting, today)
    }


def _snapshot_meetings() -> tuple[list[dict[str, Any]], str]:
    """
    Every Utrecht meeting, from the export snapshot.

    Entity ids sort alphabetically, so starting the cursor at "meeting" skips
    the documents, and the first id that is not a meeting ends the run.
    """
    records: list[dict[str, Any]] = []
    cursor, changes_cursor = "meeting", ""
    for _page in range(20):
        body, headers = _get(
            "/export/snapshot", {"source": SOURCE_KEY, "cursor": cursor, "limit": 1000}, timeout=180,
        )
        changes_cursor = changes_cursor or headers.get("X-Changes-Cursor") or ""
        page = _ndjson(body)
        meetings = [r for r in page if str(r.get("entity_id", "")).startswith("meeting:")]
        records.extend(meetings)
        cursor = headers.get("X-Next-Cursor") or ""
        if len(meetings) < len(page) or headers.get("X-Has-More") != "true" or not cursor.startswith("meeting:"):
            break
    return records, changes_cursor


def _read_changes(cursor: str) -> tuple[list[dict[str, Any]], str]:
    records: list[dict[str, Any]] = []
    for _page in range(100):
        body, headers = _get("/export/changes", {"source": SOURCE_KEY, "cursor": cursor, "limit": 1000})
        records.extend(_ndjson(body))
        cursor = headers.get("X-Next-Cursor") or cursor
        if headers.get("X-Has-More") != "true":
            break
    return records, cursor


def _snapshot_is_due(mirror: dict[str, Any], now: datetime) -> bool:
    if not mirror.get("cursor") or not mirror.get("snapshot_at"):
        return True
    try:
        taken = datetime.fromisoformat(mirror["snapshot_at"])
    except ValueError:
        return True
    return now - taken >= timedelta(days=RESNAPSHOT_DAYS)


def sync_meetings(path: str = SYNC_FILE, now: datetime | None = None) -> dict[str, dict[str, Any]]:
    """
    Brings the mirror up to date and returns its meetings, keyed by entity id.

    A failed request leaves the mirror as it was, so a bad night at the API
    costs one day's news rather than the window.
    """
    now = now or datetime.now(timezone.utc)
    mirror = load_mirror(path)

    try:
        if not _snapshot_is_due(mirror, now):
            try:
                records, cursor = _read_changes(mirror["cursor"])
                changed = apply_records(mirror, records)
                mirror["cursor"] = cursor
                logger.info("OpenBesluitvorming: %d change(s) read, %d council meeting(s) updated.", len(records), changed)
            except ExportCursorInvalid:
                logger.warning("OpenBesluitvorming no longer accepts the stored cursor; taking a new snapshot.")
                mirror["snapshot_at"] = ""

        if _snapshot_is_due(mirror, now):
            records, cursor = _snapshot_meetings()
            fresh = {"cursor": cursor, "snapshot_at": now.isoformat(), "meetings": {}}
            apply_records(fresh, records)
            mirror = fresh
            logger.info("OpenBesluitvorming: snapshot of %d meeting(s) taken.", len(records))
    except Exception as e:  # noqa: BLE001
        logger.error("Could not update from OpenBesluitvorming, using the mirror as it was: %s", e)

    prune(mirror, now.date())
    save_mirror(mirror, path)
    return mirror["meetings"]


# --- from meetings to documents ----------------------------------------------


def _walk(items: list[dict[str, Any]]):
    for item in items:
        yield item
        yield from _walk(item.get("agenda_items") or [])


def _document_rank(document: dict[str, Any]) -> tuple:
    """Orders an item's documents so the proposal and decision beat the cover sheet."""
    name = (document.get("name") or "").lower()
    preferred = next((i for i, term in enumerate(PREFERRED_DOCUMENT_TERMS) if name.startswith(term)), None)
    deprioritized = any(term in name for term in DEPRIORITIZED_DOCUMENT_TERMS)
    # A cover sheet is a title and a dossier number; even an appendix says more.
    cover = "voorblad" in name
    return (preferred is None, cover, deprioritized, preferred or 0)


def is_proposal(title: str) -> bool:
    """Whether an agenda item is something the council decides on."""
    lowered = title.lower().lstrip("'\"“‘ ")
    if not lowered.startswith(DECISION_TITLE_PREFIXES):
        return False
    return not any(keyword in lowered for keyword in EXCLUDE_TITLE_KEYWORDS)


def documents_from_meetings(meetings: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """
    One document per proposal per meeting, in the shape the pipeline expects.

    Tabled in the weekly overview and decided in the council, a dossier yields
    two records, as it did at ORI with an AgendaItem and a Raadsbesluit report.
    build_site.consolidate() joins them into one article with its history.
    """
    docs = []
    for meeting_id, meeting in meetings.items():
        for item in _walk(meeting.get("agenda") or []):
            title = (item.get("title") or "").strip()
            if item.get("is_heading") or not is_proposal(title):
                continue
            documents = sorted(item.get("documents") or [], key=_document_rank)
            if not documents:
                continue
            decided = any(
                (d.get("name") or "").lower().startswith(DECISION_DOCUMENT_PREFIX) for d in documents
            )
            docs.append({
                "id": entity_suffix(item.get("id") or ""),
                "title": title,
                "date": meeting.get("start_date") or "",
                "pdf_url": next((d["url"] for d in documents if d.get("url")), ""),
                "text": "",
                "state": "passed" if decided else "agenda",
                "doc_type": "AgendaItem",
                "classification": "Raadsbesluit" if decided else "",
                "source_url": permalink(meeting_id),
                "meeting_id": meeting_id,
                "document_ids": [d["id"] for d in documents],
                "attachments": [
                    {"name": d.get("name") or "", "url": d["url"], "size": 0}
                    for d in documents if d.get("url")
                ],
            })
    docs.sort(key=lambda d: (d["date"], d["id"]), reverse=True)
    return docs


def fetch_utrecht_documents() -> list[dict[str, Any]]:
    """The proposals of Utrecht's recent council meetings, without their text."""
    return documents_from_meetings(sync_meetings())


def fetch_text(document_id: str) -> str:
    try:
        body, _ = _get(f"/entities/{urllib.parse.quote(document_id, safe='')}", {})
        return str(json.loads(body.decode("utf-8")).get("markdownText") or "").strip()
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not read %s from OpenBesluitvorming: %s", document_id, e)
        return ""


def enrich_with_text(docs: list[dict[str, Any]], max_text_chars: int = MAX_DOC_TEXT_CHARS) -> list[dict[str, Any]]:
    """
    Fills in each document's text from its papers, best first.

    Search results no longer carry the body, so this costs one request per
    paper; it is done only for what is about to be summarized.
    """
    for doc in docs:
        if doc.get("text"):
            continue
        parts: list[str] = []
        for document_id in doc.get("document_ids", [])[:MAX_DOCUMENTS_PER_ITEM]:
            text = fetch_text(document_id)
            if text:
                parts.append(text)
            if sum(len(p) for p in parts) >= max_text_chars:
                break
        doc["text"] = "\n\n".join(parts)[:max_text_chars]
    return docs


# --- is the register current? ------------------------------------------------


def source_status() -> dict[str, Any] | None:
    """
    OpenBesluitvorming's own account of how current Utrecht is.

    It says whether last night's import from iBabs succeeded. That is the
    question the peer councils used to be asked to answer indirectly, and the
    one that went unanswered for three months when ORI stopped importing.
    """
    try:
        body, _ = _get("/status", {})
        for source in json.loads(body.decode("utf-8")).get("sources", []):
            if source.get("sourceKey") == SOURCE_KEY:
                return source
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not read OpenBesluitvorming's status: %s", e)
    return None
