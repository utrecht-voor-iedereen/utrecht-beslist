"""Tests for dossier consolidation in the static site build."""

from scripts.build_site import consolidate


def dossier(doc_id, title, date, state, attachments=None):
    return {
        "doc_id": doc_id,
        "official_title": title,
        "date": date,
        "state": state,
        "doc_type": "AgendaItem",
        "source_url": f"https://id.openraadsinformatie.nl/{doc_id}",
        "attachments": attachments or [],
    }


def test_records_of_one_dossier_become_a_single_article():
    """ORI files a proposal when tabled and again when decided; that is one story."""
    articles, redirects = consolidate([
        dossier("300", "Jaarstukken 2025", "2026-07-09", "passed"),
        dossier("100", "Jaarstukken 2025", "2026-06-18", "agenda"),
        dossier("200", "Jaarstukken 2025", "2026-06-21", "agenda"),
    ])

    assert len(articles) == 1
    article = articles[0]
    # The earliest record owns the address, so it survives the decision landing.
    assert article["doc_id"] == "100"
    # But the outcome is what the page reports.
    assert article["state"] == "passed"
    assert article["date"] == "2026-07-09"
    assert [step["doc_id"] for step in article["history"]] == ["100", "200", "300"]
    assert redirects == {"200": "100", "300": "100"}


def test_every_record_keeps_an_address():
    records = [
        dossier("100", "A", "2026-06-18", "agenda"),
        dossier("200", "A", "2026-07-09", "passed"),
        dossier("300", "B", "2026-06-20", "agenda"),
    ]
    articles, redirects = consolidate(records)

    canonical = {a["doc_id"] for a in articles}
    assert len(articles) + len(redirects) == len(records)
    assert set(redirects.values()) <= canonical


def test_attachments_are_merged_without_duplicates():
    shared = {"name": "Raadsvoorstel", "url": "https://example.org/a.pdf", "size": 1}
    extra = {"name": "Bijlage", "url": "https://example.org/b.pdf", "size": 2}
    articles, _ = consolidate([
        dossier("100", "A", "2026-06-18", "agenda", [shared]),
        dossier("200", "A", "2026-07-09", "passed", [shared, extra]),
    ])

    urls = [a["url"] for a in articles[0]["attachments"]]
    assert urls == ["https://example.org/a.pdf", "https://example.org/b.pdf"]


def test_untitled_records_do_not_collapse_into_one_dossier():
    """A missing official title must not make unrelated records the same story."""
    articles, redirects = consolidate([
        dossier("100", "", "2026-06-18", "agenda"),
        dossier("200", "", "2026-07-09", "agenda"),
    ])

    assert len(articles) == 2
    assert redirects == {}
