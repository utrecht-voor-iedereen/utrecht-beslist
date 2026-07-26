"""
Unit tests for Open Raadsinformatie source parsing and filtering.
"""

from scripts.source_ori import filter_documents, normalize_document


def test_normalize_document():
    raw_hit = {
        "_id": "utrecht_doc_123",
        "_source": {
            "name": "Raadsvoorstel Woningbouw Leidsche Rijn",
            "start_date": "2026-07-26T10:00:00+02:00",
            "original_url": "https://api1.ibabs.eu/test.pdf",
            "md_text": ["Dit is de tekst van het raadsvoorstel voor woningbouw."]
        }
    }
    doc = normalize_document(raw_hit)
    assert doc["id"] == "utrecht_doc_123"
    assert doc["title"] == "Raadsvoorstel Woningbouw Leidsche Rijn"
    assert doc["date"] == "2026-07-26T10:00:00+02:00"
    assert doc["pdf_url"] == "https://api1.ibabs.eu/test.pdf"
    assert "woningbouw" in doc["text"]

def test_filter_documents_exclusions():
    raw_hits = [
        {
            "_id": "1",
            "_source": {"name": "Presentielijst Vergadering", "md_text": ["Jan, Piet, Klaas"]}
        },
        {
            "_id": "2",
            "_source": {
                "name": "Raadsvoorstel Klimaatplan 2026",
                "start_date": "2026-07-25T00:00:00+02:00",
                "md_text": ["Lang raadsvoorstel om klimaatneutraal te worden in 2030."]
            }
        }
    ]
    filtered = filter_documents(raw_hits)
    assert len(filtered) == 1
    assert filtered[0]["id"] == "2"
