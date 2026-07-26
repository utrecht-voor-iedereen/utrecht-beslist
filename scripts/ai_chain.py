"""
Resilient LLM summarization chain supporting Groq -> Gemini -> OpenRouter -> Degraded Mode.
Includes max 10,000-word text chunking, English title translation for fallback mode, and Pydantic validation.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from .schemas import SummaryBatchOutput, SummaryItem
from .themes import detect_theme_heuristics, detect_wijken_heuristics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Je bent een neutrale redacteur die raadsstukken van gemeente Utrecht uitlegt aan inwoners.
Schrijf in mensentaal (B1-niveau voor NL, plain English voor EN), kort en feitelijk. Geen juridisch advies.
Verzin nooit bedragen, data of namen; als iets niet in het stuk staat, zeg dat niet.

Retourneer UITSLUITEND een JSON object volgens dit schema:
{
  "items": [
    {
      "doc_id": "string",
      "titel_kort_nl": "korte duidelijke titel max 10 woorden",
      "title_short_en": "short clear title max 10 words",
      "samenvatting_nl": "80-120 woorden op B1 niveau: wat is er besloten of voorgesteld, voor wie, en de impact.",
      "summary_en": "80-120 words plain English summary of the proposal or decision.",
      "thema": ["kies uit: wonen, verkeer, veiligheid, groen-klimaat, jeugd-onderwijs, zorg, bestuur-financien, cultuur-evenementen, overig"],
      "wijken": ["kies uit: Binnenstad, Oost, Leidsche Rijn, Overvecht, Zuid, Zuidwest, West, Noordwest, Vleuten-De Meern, Noordoost"],
      "impact": "hoog | gemiddeld | laag"
    }
  ]
}
"""

DUTCH_TO_ENGLISH_REPLACEMENTS = {
    "Raadsvoorstel": "Council Proposal",
    "Eerste bestuursrapportage": "First Management Report",
    "Tweede bestuursrapportage": "Second Management Report",
    "Voorjaarsnota": "Spring Financial Report",
    "Najaarsnota": "Autumn Financial Report",
    "Meerjaren Perspectief Ruimte": "Multi-Year Spatial Plan",
    "Jaarstukken": "Annual Financial Statements",
    "Resultaatbestemming": "Appropriation of Result",
    "Vergadering": "Meeting",
    "Gemeenteraad": "City Council",
    "Gemeente": "Municipality of",
    "Besluitenlijst": "Decision List",
    "Gewijzigd": "Amended",
    "Verordening": "Ordinance",
    "Bestemmingsplan": "Zoning Plan"
}

def translate_dutch_title_to_english(dutch_title: str) -> str:
    """Translates key Dutch municipal administrative terms into clear English."""
    eng_title = dutch_title
    for nl_term, en_term in DUTCH_TO_ENGLISH_REPLACEMENTS.items():
        eng_title = eng_title.replace(nl_term, en_term)
    return eng_title

def chunk_text_by_words(text: str, max_words: int = 10000) -> list[str]:
    """Divides text into chunks of at most max_words."""
    words = text.split()
    if len(words) <= max_words:
        return [text]
    
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    return chunks

def validate_and_parse_llm_json(raw_json_str: str) -> list[dict[str, Any]]:
    """Validates raw LLM response using Pydantic."""
    data = json.loads(raw_json_str)
    validated = SummaryBatchOutput.model_validate(data)
    return [item.model_dump() for item in validated.items]

def summarize_with_groq(batch_docs: list[dict[str, Any]], api_key: str) -> list[dict[str, Any]]:
    """Try summarization using Groq API."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": os.environ.get("AI_MODEL", "llama-3.3-70b-versatile"),
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"documents": batch_docs}, ensure_ascii=False)}
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        content = json.loads(res.read().decode('utf-8'))["choices"][0]["message"]["content"]
        return validate_and_parse_llm_json(content)

def summarize_with_gemini(batch_docs: list[dict[str, Any]], api_key: str) -> list[dict[str, Any]]:
    """Try summarization using Gemini API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt_text = f"{SYSTEM_PROMPT}\n\nDOCUMENTEN:\n{json.dumps(batch_docs, ensure_ascii=False)}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        content = json.loads(res.read().decode('utf-8'))["candidates"][0]["content"]["parts"][0]["text"]
        return validate_and_parse_llm_json(content)

def generate_degraded_summary(doc: dict[str, Any]) -> dict[str, Any]:
    """Fallback generator when AI APIs are unavailable, with English translation helper."""
    title = doc.get("title", "Gemeenteraadstuk Utrecht")
    text = doc.get("text", "")
    
    english_title = translate_dutch_title_to_english(title)
    
    themes = detect_theme_heuristics(title, text)
    wijken = detect_wijken_heuristics(title, text)
    excerpt = text[:250].replace("\n", " ").strip() if text else "Raadsdocument officieel beschikbaar bij gemeente Utrecht."
    
    item = SummaryItem(
        doc_id=doc.get("id", ""),
        titel_kort_nl=title[:70],
        title_short_en=english_title[:70],
        samenvatting_nl=f"Officieel gemeentestuk: {title}. {excerpt}... Lees het volledige originele raadsstuk via de PDF bron.",
        summary_en=f"Official council document: {english_title}. {excerpt}... Read the original full document via the PDF link.",
        thema=themes,
        wijken=wijken if wijken else ["Overig"],
        impact="gemiddeld",
        degraded=True
    )
    return item.model_dump()

def summarize_batch(batch_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Executes summarization chain: Groq -> Gemini -> OpenRouter -> Degraded Mode.
    Handles text chunking for documents over 10,000 words.
    """
    prepared_batch = []
    for d in batch_docs:
        full_text = d.get("text", "")
        chunks = chunk_text_by_words(full_text, max_words=10000)
        prepared_batch.append({
            "doc_id": d["id"],
            "title": d["title"],
            "text": chunks[0]
        })

    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if groq_key:
        try:
            logger.info("Summarizing batch with Groq...")
            return summarize_with_groq(prepared_batch, groq_key)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Groq failed: {e}")

    if gemini_key:
        try:
            logger.info("Summarizing batch with Gemini...")
            return summarize_with_gemini(prepared_batch, gemini_key)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Gemini failed: {e}")

    logger.info("Running in Degraded Mode (fallback without AI)...")
    return [generate_degraded_summary(d) for d in batch_docs]
