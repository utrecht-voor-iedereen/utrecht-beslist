# 🥇 Utrecht Beslist

> Resumen en lenguaje llano (B1 Neerlandés + Inglés) de los documentos y decisiones del concejo municipal van **Gemeente Utrecht**.
> Open source, 0 €/mes, 100% estático y automatizado.

---

## 🇳🇱 Nederlands

**Utrecht Beslist** is een open-source platform dat raadsvoorstellen, besluiten en documenten van de Utrechtse gemeenteraad automatisch samenvat in begrijpelijke taal.

- **Databron:** [Open Raadsinformatie API](https://openraadsinformatie.nl/) (ElasticSearch API endpoint)
- **AI-keten:** Groq (`llama-3.3-70b`) ➔ Google Gemini Flash ➔ OpenRouter ➔ Degradatiemodus (fallback)
- **Directe transparantie:** Elk artikel bevat een rechtstreekse link naar het originele PDF-document van de gemeente Utrecht.
- **Privacy & Kosten:** 0 €/maand, 0 cookies, 100% statisch via GitHub Pages (`docs/`).

## 🇬🇧 English

**Utrecht Beslist** is an open-source platform providing plain-language summaries (B1 Dutch & English) of Utrecht city council decisions and official proposals.

- **Data Source:** Open Raadsinformatie ElasticSearch API
- **AI Resiliency:** Multi-provider fallback chain (Groq ➔ Gemini ➔ OpenRouter ➔ Degraded Mode)
- **100% Open Data:** Every summary directly links to the official municipal PDF source document.

---

## 🛠️ Repository Structure

```
utrecht-beslist/
├── .github/workflows/
│   └── daily.yml          # GitHub Actions cronrunner (07:47 Amsterdam time)
├── scripts/
│   ├── pipeline.py        # Master pipeline orchestrator
│   ├── source_ori.py      # Open Raadsinformatie ElasticSearch client
│   ├── ai_chain.py        # Groq -> Gemini -> OpenRouter -> Degraded AI chain
│   ├── build_site.py      # Jinja2 static HTML renderer
│   └── themes.py          # Themes & Utrecht neighborhood taxonomy
├── templates/
│   ├── base.html          # Layout shell with theme & language toggle
│   ├── index.html         # Main overview with instant search & chips
│   └── over.html          # Transparency, methodology & disclaimer page
├── static/
│   ├── css/styles.css     # CSS variable design system
│   └── js/app.js          # Client-side filtering & search engine
├── state/
│   └── processed.json     # Document deduplication & database record
├── docs/                  # Generated GitHub Pages production site
├── requirements.txt
├── LICENSE                # EUPL-1.2
└── README.md
```

---

## 🚀 Running Locally

1. **Clone & Install Dependencies:**
   ```bash
   cd utrecht-beslist
   pip install -r requirements.txt
   ```

2. **Execute Pipeline:**
   ```bash
   # Run in degraded mode (offline without AI keys)
   python -m scripts.pipeline

   # Or run with AI summarization keys enabled:
   export GROQ_API_KEY="your-groq-key"
   python -m scripts.pipeline
   ```

3. **Preview Generated Site:**
   ```bash
   python -m http.server 8000 --directory docs
   # Open http://localhost:8000 in your browser
   ```

---

## 📜 License

Licensed under the **European Union Public Licence v1.2 (EUPL-1.2)**.
