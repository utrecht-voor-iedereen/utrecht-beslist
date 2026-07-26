"""
Multi-provider LLM chain (Groq -> Gemini -> OpenRouter -> Degraded Mode) for Utrecht Beslist.
Summarizes council documents into structured JSON complying with SummaryBatchOutput schema.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from .schemas import SummaryBatchOutput, SummaryItem
from .themes import detect_theme_heuristics, detect_wijken_heuristics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Je bent een ervaren bestuurskundig redacteur voor Gemeente Utrecht.
Vertaal gemeentelijke raadsstukken naar helder Nederlands (B1-niveau) en Engels.

Verplicht JSON formaat:
{
  "items": [
    {
      "doc_id": "string",
      "titel_kort_nl": "Korte heldere titel (max 8 woorden)",
      "title_short_en": "Short clear title in English (max 8 words)",
      "samenvatting_nl": "Samenvatting in B1 Nederlands (2-3 zinnen)",
      "summary_en": "Summary in plain English (2-3 sentences)",
      "estado_besluit": "✅ Aangenomen | ⏳ In behandeling | ❌ Verworpen | ℹ️ Informatief",
      "status_en": "✅ Approved | ⏳ Under review | ❌ Rejected | ℹ️ Informational",
      "cifra_clave_nl": "💶 Cijfer/Kosten (bv. 2,5M € of Geen extra kosten)",
      "key_figure_en": "💶 Figure/Cost (e.g. €2.5M or No extra cost)",
      "frase_impacto_nl": "1 duidelijke zin wat er voor de Utrechtse inwoner verandert",
      "impact_sentence_en": "1 clear sentence explaining what changes for Utrecht residents",
      "punt_1_wat_nl": "📌 Wat: 1 zin beschrijving van de maatregel",
      "bullet_1_what_en": "📌 What: 1 sentence description of the measure",
      "punt_2_wie_nl": "👥 Wie & Waar: Wie of welk gebied geraakt wordt",
      "bullet_2_who_en": "👥 Who & Where: Who or which area is affected",
      "punt_3_geld_nl": "💶 Impact & Kosten: Financieel effect of budget",
      "bullet_3_cost_en": "💶 Impact & Budget: Financial impact or budget",
      "contexto_nl": "🎯 Context: Waarom is dit voorstel ingediend?",
      "context_en": "🎯 Background: Why was this proposal submitted?",
      "consecuencias_nl": "🏘️ Gevolgen: Wat verandert er concreet in de stad?",
      "consequences_en": "🏘️ Consequences: What concretely changes in the city?",
      "plazo_nl": "📅 Uitvoering: Verwacht jaar/kwartaal van start",
      "timeline_en": "📅 Timeline: Expected start year/quarter",
      "thema": ["wonen", "verkeer", "groen-klimaat", "veiligheid", "bestuur-financien", "zorg", "jeugd-onderwijs", "cultuur-evenementen", "overig"],
      "wijken": ["Binnenstad", "Oost", "Leidsche Rijn", "Overvecht", "Zuid", "Zuidwest", "West", "Noordwest", "Vleuten-De Meern", "Noordoost", "Overig"],
      "impact": "hoog | gemiddeld | laag"
    }
  ]
}
"""

DUTCH_TO_ENGLISH_REPLACEMENTS = {
  "Raadsvoorstel": "Council Proposal",
  "Voorjaarsnota": "Spring Financial Report",
  "Jaarstukken": "Annual Financial Report",
  "Bestuursrapportage": "Management Report",
  "Meerjaren Perspectief Ruimte": "Multi-Year Spatial Plan",
  "Gemeente Utrecht": "Municipality of Utrecht",
  "Gemeenteraad": "City Council"
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
        d["degraded"] = False
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
    
    clean_key = api_key.strip().strip('"').strip("'")
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {clean_key}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) UtrechtBeslist/1.0"
        }
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
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    clean_key = api_key.strip().strip('"').strip("'")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={clean_key}"
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        res_data = json.loads(res.read().decode('utf-8'))
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return validate_and_parse_llm_json(raw_text, "Google Gemini 1.5 Flash")

def generate_degraded_summary(doc: dict[str, Any]) -> dict[str, Any]:
    """Generates structured fallback summary when LLM services are unavailable."""
    title = doc.get("title", "Gemeentelijk Stuk")
    raw_text = doc.get("text", "")
    
    title_short_nl = title[:60] + "..." if len(title) > 60 else title
    title_short_en = translate_dutch_title_to_english(title_short_nl)
    
    themes = detect_theme_heuristics(title, raw_text)
    wijken = detect_wijken_heuristics(title, raw_text)
    
    item = SummaryItem(
        doc_id=str(doc.get("id")),
        titel_kort_nl=title_short_nl,
        title_short_en=title_short_en,
        samenvatting_nl=f"Officieel gemeentestuk: {title}. Dit document is rechtstreeks afkomstig van de gemeenteraad van Utrecht.",
        summary_en=f"Official council document: {title_short_en}. Official document available via the Municipality of Utrecht.",
        estado_besluit="✅ Aangenomen",
        status_en="✅ Approved",
        cifra_clave_nl="💶 Zie raadsdocument",
        key_figure_en="💶 See council document",
        frase_impacto_nl=f"Belangrijke raadsinformatie inzake {title_short_nl}.",
        impact_sentence_en=f"Important council decision concerning {title_short_en}.",
        punt_1_wat_nl=f"📌 Wat: Officiële raadspublicatie over '{title_short_nl}'",
        bullet_1_what_en=f"📌 What: Official publication concerning '{title_short_en}'",
        punt_2_wie_nl=f"👥 Wie & Waar: Betreft {', '.join(wijken)}",
        bullet_2_who_en=f"👥 Who & Where: Concerns {', '.join(wijken)}",
        punt_3_geld_nl="💶 Impact & Kosten: Raadpleeg het originele stuk voor specifieke cijfers.",
        bullet_3_cost_en="💶 Impact & Cost: Consult the original council document for specific figures.",
        contexto_nl="Dit raadsvoorstel is ter besluitvorming voorgelegd aan de gemeenteraad van Utrecht.",
        context_en="This proposal was submitted for decision-making to the Utrecht city council.",
        consecuencias_nl="Het besluit treedt in werking volgens het vastgestelde raadsbesluit van de gemeente.",
        consequences_en="The decision takes effect according to the established municipal decree.",
        plazo_nl="📅 Uitvoering: Lopend raadsjaar",
        timeline_en="📅 Timeline: Current council year",
        thema=themes,
        wijken=wijken,
        impact="gemiddeld",
        pdf_url=doc.get("pdf_url", ""),
        date=doc.get("date", ""),
        degraded=True,
        ai_model="Degraded Fallback"
    )
    return item.model_dump()

def run_ai_chain(batch_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Runs fallback chain: Groq -> Gemini -> Degraded Mode."""
    groq_key = os.environ.get("GROQ_API_KEY")
    if groq_key:
        try:
            logger.info("Summarizing batch with Groq...")
            return summarize_with_groq(batch_docs, groq_key)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Groq failed: {e}")

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            logger.info("Summarizing batch with Gemini...")
            return summarize_with_gemini(batch_docs, gemini_key)
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Gemini failed: {e}")

    logger.info("Running in Degraded Mode (fallback without AI)...")
    return [generate_degraded_summary(doc) for doc in batch_docs]
