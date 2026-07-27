"""
Multi-provider LLM chain (Groq -> Gemini -> OpenRouter -> Degraded Mode) for Utrecht Beslist.
Summarizes council documents into structured JSON complying with SummaryBatchOutput schema.
Supports 8 languages: NL, EN, ES, TR, PT-BR, PT-PT, FR, DE.
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
Vertaal gemeentelijke raadsstukken naar helder Nederlands (B1-niveau), Engels, Spaans, Turks, Portugees (Brasil & Portugal), Frans en Duits.

Verplicht JSON formaat:
{
  "items": [
    {
      "doc_id": "string",
      "titel_kort_nl": "Korte heldere titel (max 8 woorden)",
      "title_short_en": "Short clear title in English (max 8 words)",
      "title_short_es": "Título corto en español (máx 8 palabras)",
      "title_short_tr": "Türkçe kısa başlık (maks 8 kelime)",
      "title_short_pt_br": "Título curto em português do Brasil (máx 8 palavras)",
      "title_short_pt_pt": "Título curto em português de Portugal (máx 8 palavras)",
      "title_short_fr": "Titre court en français (max 8 mots)",
      "title_short_de": "Kurzer Titel auf Deutsch (max. 8 Wörter)",
      "samenvatting_nl": "Samenvatting in B1 Nederlands (2-3 zinnen)",
      "summary_en": "Summary in plain English (2-3 sentences)",
      "summary_es": "Resumen en español claro (2-3 frases)",
      "summary_tr": "Sade Türkçe özet (2-3 cümle)",
      "summary_pt_br": "Resumo em português do Brasil (2-3 frases)",
      "summary_pt_pt": "Resumo em português de Portugal (2-3 frases)",
      "summary_fr": "Résumé en français simple (2-3 phrases)",
      "summary_de": "Zusammenfassung in einfachem Deutsch (2-3 Sätze)",
      "estado_besluit": "✅ Aangenomen | ⏳ In behandeling | ❌ Verworpen | ℹ️ Informatief",
      "status_en": "✅ Approved | ⏳ Under review | ❌ Rejected | ℹ️ Informational",
      "status_es": "✅ Aprobado | ⏳ En tramitación | ❌ Rechazado | ℹ️ Informativo",
      "status_tr": "✅ Kabul Edildi | ⏳ İncelemede | ❌ Reddedildi | ℹ️ Bilgilendirme",
      "status_pt_br": "✅ Aprovado | ⏳ Em análise | ❌ Rejeitado | ℹ️ Informativo",
      "status_pt_pt": "✅ Aprovado | ⏳ Em análise | ❌ Rejeitado | ℹ️ Informativo",
      "status_fr": "✅ Adopté | ⏳ En cours d'examen | ❌ Rejeté | ℹ️ Information",
      "status_de": "✅ Angenommen | ⏳ In Bearbeitung | ❌ Abgelehnt | ℹ️ Informativ",
      "cifra_clave_nl": "💶 Cijfer/Kosten (bv. 2,5M € of Geen extra kosten)",
      "key_figure_en": "💶 Figure/Cost (e.g. €2.5M or No extra cost)",
      "key_figure_es": "💶 Cifra/Coste (ej. 2,5M € o Sin costes extra)",
      "key_figure_tr": "💶 Rakam/Maliyet (örn. 2,5M € veya Ek maliyet yok)",
      "key_figure_pt_br": "💶 Valor/Custo (ex. 2,5M € ou Sem custo extra)",
      "key_figure_pt_pt": "💶 Valor/Custo (ex. 2,5M € ou Sem custo adicional)",
      "key_figure_fr": "💶 Chiffre/Coût (ex. 2,5M € ou Pas de coût supplémentaire)",
      "key_figure_de": "💶 Betrag/Kosten (z.B. 2,5M € oder Keine Zusatzkosten)",
      "frase_impacto_nl": "1 duidelijke zin wat er voor de Utrechtse inwoner verandert",
      "impact_sentence_en": "1 clear sentence explaining what changes for Utrecht residents",
      "impact_sentence_es": "1 frase clara que explique qué cambia para el vecino de Utrecht",
      "impact_sentence_tr": "Utrecht sakini için neyin değiştiğini açıklayan 1 net cümle",
      "impact_sentence_pt_br": "1 frase clara explicando o que muda para o morador de Utrecht",
      "impact_sentence_pt_pt": "1 frase clara explicando o que muda para o residente de Utrecht",
      "impact_sentence_fr": "1 phrase claire expliquant ce qui change pour l'habitant d'Utrecht",
      "impact_sentence_de": "1 klarer Satz dazu, was sich für Einwohner von Utrecht ändert",
      "punt_1_wat_nl": "📌 Wat: 1 zin beschrijving van de maatregel",
      "bullet_1_what_en": "📌 What: 1 sentence description of the measure",
      "bullet_1_what_es": "📌 Qué: Descripción en 1 frase de la medida",
      "bullet_1_what_tr": "📌 Ne: Önlemin 1 cümlelik açıklaması",
      "bullet_1_what_pt_br": "📌 O que: Descrição em 1 frase da medida",
      "bullet_1_what_pt_pt": "📌 O que: Descrição em 1 frase da medida",
      "bullet_1_what_fr": "📌 Quoi : Description en 1 phrase de la mesure",
      "bullet_1_what_de": "📌 Was: 1-Satz-Beschreibung der Maßnahme",
      "punt_2_wie_nl": "👥 Wie & Waar: Wie of welk gebied geraakt wordt",
      "bullet_2_who_en": "👥 Who & Where: Who or which area is affected",
      "bullet_2_who_es": "👥 Quién y dónde: Quién o qué zona se ve afectada",
      "bullet_2_who_tr": "👥 Kim ve Nerede: Kimi veya hangi bölgeyi etkilediği",
      "bullet_2_who_pt_br": "👥 Quem e Onde: Quem ou qual área é afetada",
      "bullet_2_who_pt_pt": "👥 Quem e Onde: Quem ou qual área é afetada",
      "bullet_2_who_fr": "👥 Qui & Où : Qui ou quelle zone est concernée",
      "bullet_2_who_de": "👥 Wer & Wo: Wer oder welcher Bereich betroffen ist",
      "punt_3_geld_nl": "💶 Impact & Kosten: Financieel effect of budget",
      "bullet_3_cost_en": "💶 Impact & Budget: Financial impact or budget",
      "bullet_3_cost_es": "💶 Impacto y presupuesto: Efecto financiero o presupuesto",
      "bullet_3_cost_tr": "💶 Etki ve Bütçe: Finansal etki veya bütçe",
      "bullet_3_cost_pt_br": "💶 Impacto e Orçamento: Efeito financeiro ou orçamento",
      "bullet_3_cost_pt_pt": "💶 Impacto e Orçamento: Efeito financeiro ou orçamento",
      "bullet_3_cost_fr": "💶 Impact & Budget : Effet financier ou budget",
      "bullet_3_cost_de": "💶 Wirkung & Budget: Finanzielle Auswirkung oder Budget",
      "contexto_nl": "🎯 Context: Waarom is dit voorstel ingediend?",
      "context_en": "🎯 Background: Why was this proposal submitted?",
      "context_es": "🎯 Contexto: ¿Por qué se presentó esta propuesta?",
      "context_tr": "🎯 Gerekçe: Bu teklif neden sunuldu?",
      "context_pt_br": "🎯 Contexto: Por que esta proposta foi apresentada?",
      "context_pt_pt": "🎯 Contexto: Por que esta proposta foi apresentada?",
      "context_fr": "🎯 Contexte : Pourquoi cette proposition a-t-elle été soumise ?",
      "context_de": "🎯 Kontext: Warum wurde dieser Antrag eingereicht?",
      "consecuencias_nl": "🏘️ Gevolgen: Wat verandert er concreet in de stad?",
      "consequences_en": "🏘️ Consequences: What concretely changes in the city?",
      "consequences_es": "🏘️ Consecuencias: ¿Qué cambia concretamente en la ciudad?",
      "consequences_tr": "🏘️ Sonuçlar: Şehirde somut olarak ne değişecek?",
      "consequences_pt_br": "🏘️ Consequências: O que muda concretamente na cidade?",
      "consequences_pt_pt": "🏘️ Consequências: O que muda concretamente na cidade?",
      "consequences_fr": "🏘️ Conséquences : Que change concrètement dans la ville ?",
      "consequences_de": "🏘️ Folgen: Was ändert sich konkret in der Stadt?",
      "plazo_nl": "📅 Uitvoering: Verwacht jaar/kwartaal van start",
      "timeline_en": "📅 Timeline: Expected start year/quarter",
      "timeline_es": "📅 Ejecución: Año/trimestre previsto de inicio",
      "timeline_tr": "📅 Takvim: Başlangıç için beklenen yıl/çeyrek",
      "timeline_pt_br": "📅 Cronograma: Ano/trimestre previsto de início",
      "timeline_pt_pt": "📅 Calendário: Ano/trimestre previsto de início",
      "timeline_fr": "📅 Calendrier : Année/trimestre prévu de début",
      "timeline_de": "📅 Zeitplan: Erwartetes Startjahr/-quartal",
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
        title_short_es=title_short_en,
        title_short_tr=title_short_en,
        title_short_pt_br=title_short_en,
        title_short_pt_pt=title_short_en,
        title_short_fr=title_short_en,
        title_short_de=title_short_en,
        samenvatting_nl=f"Officieel gemeentestuk: {title}. Dit document is rechtstreeks afkomstig van de gemeenteraad van Utrecht.",
        summary_en=f"Official council document: {title_short_en}. Official document available via the Municipality of Utrecht.",
        summary_es=f"Documento oficial del ayuntamiento: {title_short_en}.",
        summary_tr=f"Resmi belediye meclisi belgesi: {title_short_en}.",
        summary_pt_br=f"Documento oficial do conselho municipal: {title_short_en}.",
        summary_pt_pt=f"Documento oficial da câmara municipal: {title_short_en}.",
        summary_fr=f"Document officiel du conseil municipal : {title_short_en}.",
        summary_de=f"Offizielles Ratsdokument: {title_short_en}.",
        estado_besluit="✅ Aangenomen",
        status_en="✅ Approved",
        status_es="✅ Aprobado",
        status_tr="✅ Kabul Edildi",
        status_pt_br="✅ Aprovado",
        status_pt_pt="✅ Aprovado",
        status_fr="✅ Adopté",
        status_de="✅ Angenommen",
        cifra_clave_nl="💶 Zie raadsdocument",
        key_figure_en="💶 See council document",
        key_figure_es="💶 Ver documento municipal",
        key_figure_tr="💶 Meclis belgesine bakınız",
        key_figure_pt_br="💶 Ver documento do conselho",
        key_figure_pt_pt="💶 Ver documento da câmara",
        key_figure_fr="💶 Voir document municipal",
        key_figure_de="💶 Siehe Ratsdokument",
        frase_impacto_nl=f"Belangrijke raadsinformatie inzake {title_short_nl}.",
        impact_sentence_en=f"Important council decision concerning {title_short_en}.",
        impact_sentence_es=f"Decisión municipal importante sobre {title_short_en}.",
        impact_sentence_tr=f"{title_short_en} hakkında önemli meclis kararı.",
        impact_sentence_pt_br=f"Decisão municipal importante sobre {title_short_en}.",
        impact_sentence_pt_pt=f"Decisão municipal importante sobre {title_short_en}.",
        impact_sentence_fr=f"Décision municipale importante concernant {title_short_en}.",
        impact_sentence_de=f"Wichtige Ratsentscheidung zu {title_short_en}.",
        punt_1_wat_nl=f"📌 Wat: Officiële raadspublicatie over '{title_short_nl}'",
        bullet_1_what_en=f"📌 What: Official publication concerning '{title_short_en}'",
        bullet_1_what_es=f"📌 Qué: Publicación oficial sobre '{title_short_en}'",
        bullet_1_what_tr=f"📌 Ne: '{title_short_en}' hakkında resmi yayın",
        bullet_1_what_pt_br=f"📌 O que: Publicação oficial sobre '{title_short_en}'",
        bullet_1_what_pt_pt=f"📌 O que: Publicação oficial sobre '{title_short_en}'",
        bullet_1_what_fr=f"📌 Quoi : Publication officielle sur '{title_short_en}'",
        bullet_1_what_de=f"📌 Was: Offizielle Veröffentlichung zu '{title_short_en}'",
        punt_2_wie_nl=f"👥 Wie & Waar: Betreft {', '.join(wijken)}",
        bullet_2_who_en=f"👥 Who & Where: Concerns {', '.join(wijken)}",
        bullet_2_who_es=f"👥 Quién y dónde: Afecta a {', '.join(wijken)}",
        bullet_2_who_tr=f"👥 Kim ve Nerede: {', '.join(wijken)} bölgesini ilgilendiriyor",
        bullet_2_who_pt_br=f"👥 Quem e Onde: Refere-se a {', '.join(wijken)}",
        bullet_2_who_pt_pt=f"👥 Quem e Onde: Refere-se a {', '.join(wijken)}",
        bullet_2_who_fr=f"👥 Qui & Où : Concerne {', '.join(wijken)}",
        bullet_2_who_de=f"👥 Wer & Wo: Betrifft {', '.join(wijken)}",
        punt_3_geld_nl="💶 Impact & Kosten: Raadpleeg het originele stuk voor specifieke cijfers.",
        bullet_3_cost_en="💶 Impact & Cost: Consult the original council document for specific figures.",
        bullet_3_cost_es="💶 Impacto y presupuesto: Consulte el documento original para cifras específicas.",
        bullet_3_cost_tr="💶 Etki ve Bütçe: Belirli rakamlar için orijinal meclis belgesine bakınız.",
        bullet_3_cost_pt_br="💶 Impacto e Orçamento: Consulte o documento original para valores específicos.",
        bullet_3_cost_pt_pt="💶 Impacto e Orçamento: Consulte o documento original para valores específicos.",
        bullet_3_cost_fr="💶 Impact & Budget : Consultez le document original pour les chiffres précis.",
        bullet_3_cost_de="💶 Wirkung & Budget: Konsultieren Sie das Originaldokument für genaue Zahlen.",
        contexto_nl="Dit raadsvoorstel is ter besluitvorming voorgelegd aan de gemeenteraad van Utrecht.",
        context_en="This proposal was submitted for decision-making to the Utrecht city council.",
        context_es="Esta propuesta fue presentada para su adopción al ayuntamiento de Utrecht.",
        context_tr="Bu teklif karar alınmak üzere Utrecht belediye meclisine sunulmuştur.",
        context_pt_br="Esta proposta foi submetida para decisão ao conselho municipal de Utrecht.",
        context_pt_pt="Esta proposta foi submetida para decisão à câmara municipal de Utrecht.",
        context_fr="Cette proposition a été soumise au conseil municipal d'Utrecht.",
        context_de="Dieser Antrag wurde dem Stadtrat Utrecht zur Beschlussfassung vorgelegt.",
        consecuencias_nl="Het besluit treedt in werking volgens het vastgestelde raadsbesluit van de gemeente.",
        consequences_en="The decision takes effect according to the established municipal decree.",
        consequences_es="La decisión entra en vigor según el decreto municipal establecido.",
        consequences_tr="Karar, belirlenen belediye meclis kararına göre yürürlüğe girer.",
        consequences_pt_br="A decisão entra em vigor de acordo com o decreto municipal estabelecido.",
        consequences_pt_pt="A decisão entra em vigor de acordo com o decreto municipal estabelecido.",
        consequences_fr="La décision entre en vigueur conformément au décret municipal.",
        consequences_de="Der Beschluss tritt gemäß den städtischen Bestimmungen in Kraft.",
        plazo_nl="📅 Uitvoering: Lopend raadsjaar",
        timeline_en="📅 Timeline: Current council year",
        timeline_es="📅 Ejecución: Año municipal en curso",
        timeline_tr="📅 Takvim: Mevcut meclis yılı",
        timeline_pt_br="📅 Cronograma: Ano municipal atual",
        timeline_pt_pt="📅 Calendário: Ano municipal atual",
        timeline_fr="📅 Calendrier : Année municipale en cours",
        timeline_de="📅 Zeitplan: Laufendes Ratsjahr",
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
