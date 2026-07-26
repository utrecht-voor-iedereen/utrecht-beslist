"""
Resilient LLM summarization chain supporting Groq -> Gemini -> OpenRouter -> Degraded Mode.
Includes 3-bullet breakdown (Wat/Wie/Geld), max 10,000-word text chunking, and Pydantic validation.
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
Verzin nooit bedragen, data of namen; als iets niet in het stuk staat, zeg dat expliciet.

Retourneer UITSLUITEND een JSON object volgens dit schema:
{
  "items": [
    {
      "doc_id": "string",
      "titel_kort_nl": "korte duidelijke titel max 10 woorden",
      "title_short_en": "short clear title max 10 words",
      "samenvatting_nl": "80-120 woorden op B1 niveau: wat is er besloten of voorgesteld, voor wie, en de impact.",
      "summary_en": "80-120 words plain English summary of the proposal or decision.",
      "punt_1_wat_nl": "Wat: 1 zinsamenvatting van het besluit",
      "bullet_1_what_en": "What: 1 sentence decision summary",
      "punt_2_wie_nl": "Wie: wie hierdoor geraakt worden of in welke wijk",
      "bullet_2_who_en": "Who: who is affected or which neighborhood",
      "punt_3_geld_nl": "Kosten/Impact: bedrag of verwachte impact",
      "bullet_3_cost_en": "Cost/Impact: amount or expected impact",
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

def validate_and_parse_llm_json(raw_json_str: str, model_name: str) -> list[dict[str, Any]]:
    """Validates raw LLM response using Pydantic and attaches model metadata."""
    data = json.loads(raw_json_str)
    validated = SummaryBatchOutput.model_validate(data)
    items = []
    for item in validated.items:
        d = item.model_dump()
        d["ai_model"] = model_name
        items.append(d)
    return items

def summarize_with_groq(batch_docs: list[dict[str, Any]], api_key: str) -> list[dict[str, Any]]:
    """Try summarization using Groq API."""
    model_name = os.environ.get("AI_MODEL", "llama-3.3-70b-versatile")
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": model_name,
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
        return validate_and_parse_llm_json(content, f"Groq ({model_name})")

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
        return validate_and_parse_llm_json(content, "Google Gemini 1.5 Flash")

def generate_degraded_summary(doc: dict[str, Any]) -> dict[str, Any]:
    """Fallback generator when AI APIs are unavailable, with English translation & 3-bullet breakdown."""
    title = doc.get("title", "Gemeenteraadstuk Utrecht")
    text = doc.get("text", "")
    
    english_title = translate_dutch_title_to_english(title)
    themes = detect_theme_heuristics(title, text)
    wijken = detect_wijken_heuristics(title, text)
    wijk_str = ", ".join(wijken) if wijken else "Gans Utrecht"
    excerpt = text[:250].replace("\n", " ").strip() if text else "Raadsdocument officieel beschikbaar bij gemeente Utrecht."
    
    item = SummaryItem(
        doc_id=doc.get("id", ""),
        titel_kort_nl=title[:70],
        title_short_en=english_title[:70],
        samenvatting_nl=f"Officieel gemeentestuk: {title}. {excerpt}... Lees het volledige originele raadsstuk via de PDF bron.",
        summary_en=f"Official council document: {english_title}. {excerpt}... Read the original full document via the PDF link.",
        punt_1_wat_nl=f"📌 Wat: Officiële publicatie over '{title[:45]}...'",
        bullet_1_what_en=f"📌 What: Official publication concerning '{english_title[:45]}...'",
        punt_2_wie_nl=f"👥 Wie & Waar: Betreft {wijk_str}",
        bullet_2_who_en=f"👥 Who & Where: Concerns {wijk_str}",
        punt_3_geld_nl="💶 Impact & Kosten: Raadpleeg het originele raadsstuk voor specifieke bedragen.",
        bullet_3_cost_en="💶 Impact & Cost: Consult the original council document for specific figures.",
        thema=themes,
        wijken=wijken if wijken else ["Overig"],
        impact="gemiddeld",
        degraded=True,
        ai_model="Degraded Mode (Fallback)"
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
