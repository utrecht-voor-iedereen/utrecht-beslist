"""
Client module for Open Raadsinformatie (ORI) ElasticSearch API for Utrecht municipal documents.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORI_ELASTIC_ENDPOINT = "https://api.openraadsinformatie.nl/v1/elastic/ori_utrecht*/_search"

EXCLUDE_TITLE_KEYWORDS = [
    "presentielijst",
    "besluitenlijst ter vaststelling",
    "actielijst",
    "incomende stukken",
    "opening en mededelingen",
    "sluiting",
    "vaststelling agenda"
]

def fetch_utrecht_documents(size: int = 150) -> list[dict[str, Any]]:
    """
    Fetch latest documents from Open Raadsinformatie for Utrecht.
    """
    query_payload = {
        "size": size,
        "sort": [
            {
                "start_date": {
                    "order": "desc",
                    "unmapped_type": "keyword"
                }
            }
        ]
    }

    req = urllib.request.Request(
        ORI_ELASTIC_ENDPOINT,
        data=json.dumps(query_payload).encode('utf-8'),
        headers={"Content-Type": "application/json", "User-Agent": "UtrechtBeslistBot/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.loads(response.read().decode('utf-8'))
            hits = data.get("hits", {}).get("hits", [])
            logger.info(f"Fetched {len(hits)} raw documents from Open Raadsinformatie.")
            return hits
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error fetching from Open Raadsinformatie: {e}")
        return []

ORI_PERMALINK = "https://id.openraadsinformatie.nl/{doc_id}"

# ORI records the outcome of a vote with these opengov URIs.
RESULT_STATES = {
    "http://www.w3.org/ns/opengov#ResultPassed": "passed",
    "http://www.w3.org/ns/opengov#ResultFailed": "failed",
}

# Cover sheets and appendices carry no decision text; prefer the proposal.
PREFERRED_ATTACHMENT_TERMS = ("raadsvoorstel", "raadsbrief", "raadsbesluit", "voorstel")
DEPRIORITIZED_ATTACHMENT_TERMS = ("voorblad", "presentielijst", "bijlage")


def extract_text(source: dict[str, Any]) -> str:
    """Pulls the document body out of md_text, falling back to plain text."""
    for field in ("md_text", "text"):
        raw = source.get(field)
        if isinstance(raw, list):
            joined = "\n".join(str(part) for part in raw if part and str(part).strip() != "\f")
        elif isinstance(raw, str):
            joined = raw
        else:
            continue
        if joined.strip():
            return joined.strip()
    return ""


def derive_state(source: dict[str, Any]) -> str:
    """
    The decision state, taken from ORI instead of guessed by the summarizer.

    A Report classified Raadsbesluit is a recorded decision; an AgendaItem is
    an item tabled for a meeting, which is not the same thing and must not be
    presented as approved.
    """
    result = RESULT_STATES.get(str(source.get("result") or ""))
    if result:
        return result

    doc_type = str(source.get("@type") or "")
    classification = str(source.get("classification") or "")
    if doc_type == "AgendaItem":
        return "agenda"
    if classification == "Raadsbesluit":
        return "passed"
    return "informational"


def normalize_document(raw_hit: dict[str, Any]) -> dict[str, Any]:
    """
    Normalizes Elastic raw hit into standard document dict.

    Agenda items carry neither a body nor a PDF of their own — both live in the
    MediaObjects listed under `attachment`. Reading only the hit itself is why
    every entry shipped with an empty pdf_url and a summary written from the
    title alone.
    """
    doc_id = raw_hit.get("_id", "")
    source = raw_hit.get("_source", {})

    title = source.get("name") or source.get("title") or "Gemeentestuk Utrecht"
    date_str = source.get("start_date") or source.get("last_discussed_at") or ""
    pdf_url = source.get("original_url") or source.get("url") or ""

    # ORI returns a bare string when a record has exactly one attachment, and a
    # list when it has several. Treating only the list case as valid dropped
    # the single-attachment documents, which is why two entries appeared to
    # have no source at all.
    raw_attachments = source.get("attachment")
    if isinstance(raw_attachments, str):
        attachment_ids = [raw_attachments] if raw_attachments.strip() else []
    elif isinstance(raw_attachments, list):
        attachment_ids = [str(a) for a in raw_attachments if a]
    else:
        attachment_ids = []

    return {
        "id": doc_id,
        "title": title.strip(),
        "date": date_str,
        "pdf_url": pdf_url,
        "text": extract_text(source),
        "state": derive_state(source),
        "doc_type": str(source.get("@type") or ""),
        "classification": str(source.get("classification") or ""),
        "source_url": ORI_PERMALINK.format(doc_id=doc_id),
        "attachment_ids": attachment_ids,
        "attachments": [],
    }


def _attachment_rank(attachment: dict[str, Any]) -> tuple:
    """Orders attachments so the actual proposal wins over the cover sheet."""
    name = (attachment.get("name") or "").lower()
    preferred = any(term in name for term in PREFERRED_ATTACHMENT_TERMS)
    deprioritized = any(term in name for term in DEPRIORITIZED_ATTACHMENT_TERMS)
    # Sorted descending, so higher tuples come first.
    return (preferred, not deprioritized, attachment.get("size", 0))


def fetch_attachments(ids: list[str]) -> dict[str, dict[str, Any]]:
    """Looks up MediaObject records by id, in one request per 100 ids."""
    found: dict[str, dict[str, Any]] = {}
    unique = [i for i in dict.fromkeys(ids) if i]

    for start in range(0, len(unique), 100):
        chunk = unique[start:start + 100]
        payload = {"size": len(chunk), "query": {"ids": {"values": chunk}}}
        req = urllib.request.Request(
            ORI_ELASTIC_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "UtrechtBeslistBot/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error fetching attachments from Open Raadsinformatie: {e}")
            continue

        for hit in data.get("hits", {}).get("hits", []):
            src = hit.get("_source", {})
            found[hit.get("_id", "")] = {
                "id": hit.get("_id", ""),
                "name": src.get("name") or src.get("file_name") or "",
                "url": src.get("original_url") or src.get("url") or "",
                "size": src.get("size_in_bytes") or 0,
                "text": extract_text(src),
            }
    return found


# Groq's free tier allows 12,000 tokens per minute and the summarization system
# prompt already costs about 2,000, so a document body has to stay well under
# that. 6,000 characters is roughly 1,800 tokens and still covers the proposal
# itself, which is what the summary is written from.
MAX_DOC_TEXT_CHARS = 6000


def enrich_with_attachments(docs: list[dict[str, Any]], max_text_chars: int = MAX_DOC_TEXT_CHARS) -> list[dict[str, Any]]:
    """
    Attaches each document's PDFs and their text.

    Without this the summarizer only ever saw a title, which is why thirty
    summaries came back as variations of "this proposal concerns X".
    """
    all_ids = [aid for doc in docs for aid in doc.get("attachment_ids", [])]
    if not all_ids:
        return docs

    lookup = fetch_attachments(all_ids)
    logger.info(f"Resolved {len(lookup)} of {len(set(all_ids))} referenced attachments.")

    for doc in docs:
        resolved = [lookup[aid] for aid in doc.get("attachment_ids", []) if aid in lookup]
        resolved.sort(key=_attachment_rank, reverse=True)

        doc["attachments"] = [
            {"name": a["name"], "url": a["url"], "size": a["size"]}
            for a in resolved if a["url"]
        ]

        if not doc.get("pdf_url") and doc["attachments"]:
            doc["pdf_url"] = doc["attachments"][0]["url"]

        if not doc.get("text"):
            body = "\n\n".join(a["text"] for a in resolved if a["text"])
            doc["text"] = body[:max_text_chars]

    return share_text_between_siblings(docs)


def share_text_between_siblings(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Lets a decision record read the documents of the proposal it decided.

    ORI publishes a dossier twice: once as the AgendaItem for the meeting,
    which carries the PDFs, and once as a Report classified Raadsbesluit that
    records the outcome and carries nothing at all. Both share an official
    `name`. Without this the decision — the more important of the two — was
    summarized from its title, which is how five council decisions ended up
    described as "this proposal concerns the multi-year spatial perspective".

    Only the source material is shared. The state, date and register link of
    each record stay its own, because they are what differs between them.
    """
    donors: dict[str, dict[str, Any]] = {}
    for doc in docs:
        name = (doc.get("title") or "").strip()
        if not name or not doc.get("text"):
            continue
        # Prefer the donor with the most attachments: dossiers are sometimes
        # tabled twice and the later agenda has the fuller set.
        current = donors.get(name)
        if current is None or len(doc.get("attachments", [])) > len(current.get("attachments", [])):
            donors[name] = doc

    borrowed = 0
    for doc in docs:
        if doc.get("text"):
            continue
        donor = donors.get((doc.get("title") or "").strip())
        if not donor or donor is doc:
            continue

        doc["text"] = donor["text"]
        doc["attachments"] = list(donor.get("attachments", []))
        if not doc.get("pdf_url"):
            doc["pdf_url"] = donor.get("pdf_url", "")
        # Recorded so the page can say whose documents these are.
        doc["source_borrowed_from"] = donor["id"]
        borrowed += 1

    if borrowed:
        logger.info("%d record(s) took their source documents from a matching dossier.", borrowed)
    return docs

# Titles that introduce something the council decides on. Everything else the
# register carries — Raadsbrief, memos, B&W minutes, commitment lists — is the
# material around a decision rather than a decision.
DECISION_TITLE_PREFIXES = (
    "raadsvoorstel",
    "initiatiefvoorstel",
    "motie",
    "amendement",
)

# Publish only what the council decides on. The site is called Utrecht Beslist
# and asks "what did the council decide"; of the 93 unpublished documents in
# ORI's window, 40 were letters from the executive and not one was a proposal.
# Set UTRECHT_BESLIST_ALL_DOCS=1 to widen it back to everything the register
# carries.
DECISIONS_ONLY = os.environ.get("UTRECHT_BESLIST_ALL_DOCS", "") not in ("1", "true", "yes")


def is_decision(doc: dict[str, Any]) -> bool:
    """Whether a document is something the council decides, not reports on."""
    title = doc.get("title", "").lower().lstrip("'\"“‘ ")
    if title.startswith(DECISION_TITLE_PREFIXES):
        return True
    return doc.get("classification") == "Raadsbesluit"


def filter_documents(raw_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Filters raw document hits to keep relevant, non-trivial documents.
    """
    filtered = []
    for hit in raw_hits:
        doc = normalize_document(hit)
        title_lower = doc["title"].lower()

        # Check keyword exclusions
        if any(kw in title_lower for kw in EXCLUDE_TITLE_KEYWORDS):
            continue

        # A meeting is a container for agenda items, not a decision; publishing
        # one produced an article titled "Raadsvoorstellen weekoverzicht" with
        # nothing behind it.
        if doc["doc_type"] == "Meeting":
            continue

        if DECISIONS_ONLY and not is_decision(doc):
            continue

        # Keep anything that either has text of its own or points at documents
        # we can read; enrich_with_attachments() fills the text in afterwards.
        has_source = len(doc["text"]) >= 100 or doc["attachment_ids"]
        if not has_source and not ("raadsvoorstel" in title_lower or "nota" in title_lower):
            continue

        filtered.append(doc)

    return enrich_with_attachments(filtered)
