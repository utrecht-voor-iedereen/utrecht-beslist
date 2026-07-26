"""
Resilient LLM summarization chain supporting Groq -> Gemini -> OpenRouter -> Degraded Mode.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any
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

def summarize_with_groq(batch_docs: List[Dict[str, Any]], api_key: str) -> List[Dict[str, Any]]:
    """Try summarization using Groq API."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    user_payload = {"documents": batch_docs}
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.loads(res.read().decode('utf-8'))
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return parsed.get("items", [])

def summarize_with_gemini(batch_docs: List[Dict[str, Any]], api_key: str) -> List[Dict[str, Any]]:
    """Try summarization using Gemini REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt_text = f"{SYSTEM_PROMPT}\n\nDOCUMENTEN:\n{json.dumps(batch_docs, ensure_ascii=False)}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        data = json.loads(res.read().decode('utf-8'))
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(content)
        return parsed.get("items", [])

def generate_degraded_summary(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Fallback generator when AI APIs are unavailable or fail."""
    title = doc.get("title", "Gemeenteraadstuk Utrecht")
    text = doc.get("text", "")
    
    themes = detect_theme_heuristics(title, text)
    wijken = detect_wijken_heuristics(title, text)
    
    excerpt = text[:250].replace("\n", " ").strip() if text else "Raadsdocument officieel beschikbaar bij gemeente Utrecht."
    
    return {
        "doc_id": doc.get("id", ""),
        "titel_kort_nl": title[:60],
        "title_short_en": title[:60],
        "samenvatting_nl": f"Officieel gemeentestuk: {title}. {excerpt}... Lees het volledige originele raadsstuk via de PDF bron.",
        "summary_en": f"Official council document: {title}. {excerpt}... Read the original full document via the PDF link.",
        "thema": themes,
        "wijken": wijken if wijken else ["Overig"],
        "impact": "gemiddeld",
        "degraded": True
    }

def summarize_batch(batch_docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Executes summarization chain: Groq -> Gemini -> OpenRouter -> Degraded Mode.
    """
    input_batch = [
        {
            "doc_id": d["id"],
            "title": d["title"],
            "text": d["text"][:2000] # Limit per document for token efficiency
        }
        for d in batch_docs
    ]

    groq_key = os.environ.get("GROQ_API_KEY")
    gemini_key = os.environ.get("GEMINI_API_KEY")

    if groq_key:
        try:
            logger.info("Summarizing batch with Groq...")
            return summarize_with_groq(input_batch, groq_key)
        except Exception as e:
            logger.warning(f"Groq failed: {e}")

    if gemini_key:
        try:
            logger.info("Summarizing batch with Gemini...")
            return summarize_with_gemini(input_batch, gemini_key)
        except Exception as e:
            logger.warning(f"Gemini failed: {e}")

    logger.info("Running in Degraded Mode (fallback without AI)...")
    return [generate_degraded_summary(d) for d in batch_docs]
