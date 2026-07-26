"""
Unit tests for AI chain, chunking, and degraded fallback.
"""

from scripts.ai_chain import (
    chunk_text_by_words,
    generate_degraded_summary,
    validate_and_parse_llm_json,
)


def test_chunk_text_by_words():
    text = "word " * 15000
    chunks = chunk_text_by_words(text, max_words=10000)
    assert len(chunks) == 2
    assert len(chunks[0].split()) == 10000
    assert len(chunks[1].split()) == 5000

def test_generate_degraded_summary():
    doc = {
        "id": "doc_999",
        "title": "Raadsvoorstel Verkeer Binnenstad",
        "text": "Dit gaat over verkeer en auto's in de Binnenstad van Utrecht.",
        "pdf_url": "https://test.pdf"
    }
    summary = generate_degraded_summary(doc)
    assert summary["doc_id"] == "doc_999"
    assert summary["degraded"] is True
    assert "verkeer" in summary["thema"]
    assert "Binnenstad" in summary["wijken"]

def test_validate_and_parse_llm_json():
    json_str = """{
      "items": [
        {
          "doc_id": "test_1",
          "titel_kort_nl": "Korte titel NL",
          "title_short_en": "Short title EN",
          "samenvatting_nl": "Dit is de B1 samenvatting in het Nederlands.",
          "summary_en": "This is the plain English summary.",
          "thema": ["wonen"],
          "wijken": ["Overvecht"],
          "impact": "hoog"
        }
      ]
    }"""
    parsed = validate_and_parse_llm_json(json_str)
    assert len(parsed) == 1
    assert parsed[0]["doc_id"] == "test_1"
    assert parsed[0]["impact"] == "hoog"
