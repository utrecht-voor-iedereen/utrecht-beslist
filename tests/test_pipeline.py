"""
Unit tests for the pipeline's staleness diagnosis.
"""

import logging
from datetime import datetime, timezone

from scripts.pipeline import diagnose_staleness, drop_already_published


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def test_quiet_council_with_a_working_import_is_a_recess():
    # The summer recess, which the bare threshold used to report as a fault
    # every day for six weeks.
    status = {"state": "ok", "lastSuccessAt": "2026-08-04T00:44:19Z"}
    level, message = diagnose_staleness(27, status)
    assert level == logging.INFO
    assert "recess" in message


def test_register_current_but_site_behind_is_not_a_recess():
    status = {"state": "ok", "lastSuccessAt": "2026-09-28T00:44:19Z", "latestContentDate": _today()}
    level, message = diagnose_staleness(81, status)
    assert level == logging.WARNING
    assert "recess" not in message


def test_failing_import_is_critical():
    # What happened at ORI from July 2026: the council kept meeting and nothing
    # arrived.
    status = {
        "state": "failing",
        "lastSuccessAt": "2026-07-09T00:00:00Z",
        "lastErrorMessage": "iBabs blocks requests from this host (403)",
    }
    level, message = diagnose_staleness(40, status)
    assert level == logging.CRITICAL
    assert "403" in message
    assert "2026-07-09" in message


def test_stale_import_is_not_called_a_recess():
    level, _ = diagnose_staleness(25, {"state": "stale", "lastSuccessAt": "2026-08-01T00:00:00Z"})
    assert level == logging.CRITICAL


def test_unreachable_status_does_not_claim_a_verdict():
    level, message = diagnose_staleness(30, {})
    assert level == logging.ERROR
    assert "cannot tell" in message


IBABS = "https://api1.ibabs.eu/publicdownload.aspx?site=Utrecht&id="
PAPER = "7929a332-17e5-4837-a552-2d0d1e2d63a5"


def _new(date):
    return {"id": "6d04a31b-263e-4cee-ab6d-21bb54adb9d3", "date": date, "pdf_url": IBABS + PAPER}


def test_items_published_under_an_ori_id_are_not_summarized_again():
    existing = [{
        "doc_id": "7961870",
        "date": "2026-07-09T00:00:00+02:00",
        "pdf_url": "",
        "attachments": [{"url": IBABS + PAPER.upper()}],
    }]
    assert drop_already_published([_new("2026-07-09T08:00:00Z")], existing) == []


def test_a_decided_item_is_matched_by_its_proposal_not_its_new_raadsbesluit():
    existing = [{"doc_id": "7961871", "date": "2026-07-09T00:00:00+02:00", "pdf_url": IBABS + PAPER}]
    decided = {
        "id": "x",
        "date": "2026-07-09T08:00:00Z",
        "pdf_url": IBABS + "cf7cc2ce-7a68-4131-a37b-b97651bd7171",
        "attachments": [{"url": IBABS + "cf7cc2ce-7a68-4131-a37b-b97651bd7171"}, {"url": IBABS + PAPER}],
    }
    assert drop_already_published([decided], existing) == []


def test_a_dossier_back_at_a_later_meeting_is_new():
    existing = [{"doc_id": "7961870", "date": "2026-07-09T00:00:00+02:00", "pdf_url": IBABS + PAPER}]
    assert len(drop_already_published([_new("2026-09-24T08:00:00Z")], existing)) == 1


def test_entries_from_openbesluitvorming_do_not_hide_themselves():
    # Only ORI-era entries are matched; a new entry is found again by its own id.
    existing = [{"doc_id": "6d04a31b-263e-4cee-ab6d-21bb54adb9d3", "date": "2026-07-09T08:00:00Z", "pdf_url": IBABS + PAPER}]
    assert len(drop_already_published([_new("2026-07-09T08:00:00Z")], existing)) == 1


def test_ori_permalinks_move_to_the_same_paper_in_openbesluitvorming():
    from scripts.pipeline import relink_ori_entries

    proposal = {
        "doc_id": "7947071",
        "official_title": "Raadsvoorstel Voorjaarsnota 2026",
        "source_url": "https://id.openraadsinformatie.nl/7947071",
        "pdf_url": IBABS + PAPER,
    }
    # ORI filed the decision without papers; it borrows the proposal's.
    decision = {
        "doc_id": "7961871",
        "official_title": "Raadsvoorstel Voorjaarsnota 2026",
        "source_url": "https://id.openraadsinformatie.nl/7961871",
        "pdf_url": "",
    }
    orphan = {"doc_id": "1", "official_title": "Geheim", "source_url": "https://id.openraadsinformatie.nl/1"}
    current = {"doc_id": "x", "source_url": "https://openbesluitvorming.nl/?organization=utrecht&view=m"}

    assert relink_ori_entries([proposal, decision, orphan, current]) == 3
    expected = "https://openbesluitvorming.nl/?organization=utrecht&view=document%3Aibabs%3Agemeente%3Autrecht%3A" + PAPER
    assert proposal["source_url"] == expected
    assert decision["source_url"] == expected
    assert orphan["source_url"] == "https://openbesluitvorming.nl/?query=Geheim&organization=utrecht"
    assert current["source_url"].endswith("view=m")
    assert relink_ori_entries([proposal, decision, orphan, current]) == 0
