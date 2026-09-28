"""
Unit tests for the OpenBesluitvorming mirror and the documents read from it.
"""

from datetime import date, datetime, timezone

from scripts import source_obv
from scripts.source_obv import (
    apply_records,
    documents_from_meetings,
    load_mirror,
    prune,
    sync_meetings,
)

UTRECHT = "gemeente:utrecht"


def _doc(uuid, name):
    return {
        "id": f"document:ibabs:{UTRECHT}:{uuid}",
        "name": name,
        "original_url": f"https://api1.ibabs.eu/publicdownload.aspx?site=Utrecht&id={uuid}",
    }


def _meeting(name="Gemeenteraad", start="2026-07-09T08:00:00Z", agenda=None):
    return {"type": "Meeting", "name": name, "start_date": start, "agenda": agenda or []}


def _record(entity_id, payload, op="upsert"):
    return {"op": op, "entity_type": "Meeting", "entity_id": entity_id, "payload": payload}


VOORJAARSNOTA = {
    "id": f"agenda_item:ibabs:{UTRECHT}:item-1",
    "title": "Raadsvoorstel Voorjaarsnota 2026",
    "documents": [
        _doc("aaaa", "Dossier 5245 voorblad.pdf"),
        _doc("bbbb", "Bijlage Subsidiestaat 2026"),
        _doc("cccc", "Raadsvoorstel Voorjaarsnota 2026"),
    ],
}


def _mirror(*records):
    mirror = {"cursor": "", "snapshot_at": "", "meetings": {}}
    apply_records(mirror, list(records))
    return mirror


def test_only_council_meetings_enter_the_mirror():
    mirror = _mirror(
        _record("meeting:a", _meeting()),
        _record("meeting:b", _meeting(name="Raadsvoorstellen weekoverzicht")),
        _record("meeting:c", _meeting(name="Commissie Ruimte")),
    )
    assert set(mirror["meetings"]) == {"meeting:a", "meeting:b"}


def test_a_deleted_meeting_leaves_the_mirror():
    mirror = _mirror(_record("meeting:a", _meeting()))
    apply_records(mirror, [{"op": "delete", "entity_type": "Meeting", "entity_id": "meeting:a"}])
    assert mirror["meetings"] == {}


def test_prune_drops_meetings_outside_the_window():
    mirror = _mirror(
        _record("meeting:old", _meeting(start="2025-01-09T08:00:00Z")),
        _record("meeting:new", _meeting(start="2026-09-24T08:00:00Z")),
    )
    prune(mirror, date(2026, 9, 28))
    assert set(mirror["meetings"]) == {"meeting:new"}


def test_proposal_becomes_a_document_with_its_papers_best_first():
    mirror = _mirror(_record("meeting:ibabs:x", _meeting(agenda=[VOORJAARSNOTA])))
    (doc,) = documents_from_meetings(mirror["meetings"])
    assert doc["id"] == "item-1"
    assert doc["title"] == "Raadsvoorstel Voorjaarsnota 2026"
    assert doc["state"] == "agenda"
    assert doc["pdf_url"].endswith("id=cccc")
    assert doc["document_ids"][-1].endswith(":aaaa")  # the cover sheet goes last
    assert "view=meeting%3Aibabs%3Ax" in doc["source_url"]


def test_attached_raadsbesluit_marks_the_decision():
    decided = dict(VOORJAARSNOTA)
    decided["documents"] = VOORJAARSNOTA["documents"] + [
        _doc("dddd", "Raadsbesluit Voorjaarsnota 2026 (gepubliceerd op 10 juli 2026)")
    ]
    mirror = _mirror(_record("meeting:x", _meeting(agenda=[decided])))
    (doc,) = documents_from_meetings(mirror["meetings"])
    assert doc["state"] == "passed"
    assert doc["classification"] == "Raadsbesluit"
    assert doc["pdf_url"].endswith("id=dddd")


def test_letters_and_procedure_are_not_published():
    agenda = [
        {"id": "i:1", "title": "Opening", "documents": []},
        {"id": "i:2", "title": "Raadsbrief Collegereactie", "documents": [_doc("eeee", "Raadsbrief")]},
        {"id": "i:3", "title": "Raadsvoorstel zonder stukken", "documents": []},
        {"id": "i:4", "title": "Initiatiefvoorstel Groen", "documents": [_doc("ffff", "Initiatiefvoorstel Groen")],
         "agenda_items": [{"id": "i:5", "title": "Raadsvoorstel Genest", "documents": [_doc("gggg", "Raadsvoorstel Genest")]}]},
    ]
    mirror = _mirror(_record("meeting:x", _meeting(agenda=agenda)))
    assert sorted(d["id"] for d in documents_from_meetings(mirror["meetings"])) == ["4", "5"]


def test_sync_keeps_the_mirror_when_the_api_fails(tmp_path, monkeypatch):
    path = str(tmp_path / "obv.json")
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    kept = _mirror(_record("meeting:x", _meeting(start="2026-09-24T08:00:00Z")))
    kept.update(cursor="100", snapshot_at=now.isoformat())
    source_obv.save_mirror(kept, path)

    def broken(*_args, **_kwargs):
        raise OSError("network down")

    monkeypatch.setattr(source_obv, "_get", broken)
    assert set(sync_meetings(path, now=now)) == {"meeting:x"}
    assert load_mirror(path)["cursor"] == "100"


def test_sync_reads_changes_after_the_snapshot(tmp_path, monkeypatch):
    path = str(tmp_path / "obv.json")
    now = datetime(2026, 9, 28, tzinfo=timezone.utc)
    mirror = {"cursor": "100", "snapshot_at": now.isoformat(), "meetings": {}}
    source_obv.save_mirror(mirror, path)

    import json

    def fake_get(path_, params, **_kwargs):
        assert path_ == "/export/changes" and params["cursor"] == "100"
        body = json.dumps(_record("meeting:new", _meeting(start="2026-09-24T08:00:00Z"))).encode()
        return body, {"X-Next-Cursor": "101", "X-Has-More": "false"}

    monkeypatch.setattr(source_obv, "_get", fake_get)
    assert set(sync_meetings(path, now=now)) == {"meeting:new"}
    assert load_mirror(path)["cursor"] == "101"
