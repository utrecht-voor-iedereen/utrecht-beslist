"""
Taxonomy definition for themes, neighborhoods (wijken), and heuristic classification for Utrecht Beslist.
Supports 8 languages: NL, EN, ES, TR, PT-BR, PT-PT, FR, DE.
"""

import re

THEMES = {
    "wonen": {
        "nl": "Wonen & Huisvesting",
        "en": "Housing & Living",
        "es": "Vivienda & Hábitat",
        "tr": "Konut & Barınma",
        "pt-br": "Habitação & Moradia",
        "pt-pt": "Habitação & Moradia",
        "fr": "Logement & Habitat",
        "de": "Wohnen & Wohnbau",
        "icon": "🏠",
        "keywords": ["wonen", "woning", "huur", "bouw", "huisvesting", "woonvisie", "bestemmingsplan", "erfpacht", "studentenwoningen", "woningbouw"]
    },
    "verkeer": {
        "nl": "Verkeer & Mobiliteit",
        "en": "Traffic & Mobility",
        "es": "Tráfico & Movilidad",
        "tr": "Trafik & Ulaşım",
        "pt-br": "Trânsito & Mobilidade",
        "pt-pt": "Trânsito & Mobilidade",
        "fr": "Transports & Mobilité",
        "de": "Verkehr & Mobilität",
        "icon": "🚲",
        "keywords": ["verkeer", "mobiliteit", "fiets", "parkeren", "ov", "bus", "tram", "wegen", "snelfietspad", "autoluw", "snelheid"]
    },
    "veiligheid": {
        "nl": "Veiligheid & Handhaving",
        "en": "Safety & Enforcement",
        "es": "Seguridad & Orden Público",
        "tr": "Güvenlik & Denetim",
        "pt-br": "Segurança & Fiscalização",
        "pt-pt": "Segurança & Fiscalização",
        "fr": "Sécurité & Maintien de l'Ordre",
        "de": "Sicherheit & Ordnung",
        "icon": "🛡️",
        "keywords": ["veiligheid", "politie", "handhaving", "overlast", "cameratoezicht", "boa", "noodverordening", "brandweer"]
    },
    "groen-klimaat": {
        "nl": "Groen & Klimaat",
        "en": "Green & Climate",
        "es": "Medio Ambiente & Clima",
        "tr": "Yeşil Alan & İklim",
        "pt-br": "Meio Ambiente & Clima",
        "pt-pt": "Espaços Verdes & Clima",
        "fr": "Espaces Verts & Climat",
        "de": "Grünflächen & Klima",
        "icon": "🌿",
        "keywords": ["groen", "klimaat", "duurzaam", "energie", "bomen", "park", "warmtenet", "zonnepanelen", "biodiversiteit", "afval"]
    },
    "jeugd-onderwijs": {
        "nl": "Jeugd & Onderwijs",
        "en": "Youth & Education",
        "es": "Juventud & Educación",
        "tr": "Gençlik & Eğitim",
        "pt-br": "Juventude & Educação",
        "pt-pt": "Juventude & Educação",
        "fr": "Jeunesse & Éducation",
        "de": "Jugend & Bildung",
        "icon": "🎓",
        "keywords": ["jeugd", "onderwijs", "school", "kinderopvang", "leerling", "student", "speeltuin", "jeugdzorg"]
    },
    "zorg": {
        "nl": "Zorg & Welzijn",
        "en": "Health & Welfare",
        "es": "Salud & Bienestar Social",
        "tr": "Sağlık & Sosyal Yardım",
        "pt-br": "Saúde & Bem-Estar Social",
        "pt-pt": "Saúde & Bem-Estar Social",
        "fr": "Santé & Action Sociale",
        "de": "Gesundheit & Soziales",
        "icon": "❤️",
        "keywords": ["zorg", "welzijn", "wmo", "gezondheid", "armoede", "bijstand", "inclusie", "ouderen", "vrijwilligers"]
    },
    "bestuur-financien": {
        "nl": "Bestuur & Financiën",
        "en": "Governance & Finance",
        "es": "Gobernanza & Finanzas",
        "tr": "Yönetim & Finans",
        "pt-br": "Governança & Finanças",
        "pt-pt": "Governação & Finanças",
        "fr": "Gouvernance & Finances",
        "de": "Verwaltung & Finanzen",
        "icon": "🏛️",
        "keywords": ["begroting", "financien", "belasting", "ozb", "voorjaarsnota", "najaarsnota", "jaarrekening", "verordening", "raadsvoorstel"]
    },
    "cultuur-evenementen": {
        "nl": "Cultuur & Sport",
        "en": "Culture & Sports",
        "es": "Cultura & Deportes",
        "tr": "Kültür & Spor",
        "pt-br": "Cultura & Esportes",
        "pt-pt": "Cultura & Desporto",
        "fr": "Culture & Sports",
        "de": "Kultur & Sport",
        "icon": "🎨",
        "keywords": ["cultuur", "sport", "evenement", "subsidie", "museum", "bibliotheek", "theater", "zwembad", "festival"]
    },
    "overig": {
        "nl": "Overig",
        "en": "Other",
        "es": "Otros",
        "tr": "Diğer",
        "pt-br": "Outros",
        "pt-pt": "Outros",
        "fr": "Autres",
        "de": "Sonstiges",
        "icon": "📋",
        "keywords": []
    }
}

WIJKEN = [
    "Binnenstad",
    "Oost",
    "Leidsche Rijn",
    "Overvecht",
    "Zuid",
    "Zuidwest",
    "West",
    "Noordwest",
    "Vleuten-De Meern",
    "Noordoost"
]

def detect_theme_heuristics(title: str, text: str) -> list[str]:
    """Detect theme based on keyword occurrence when AI classification is not available."""
    content = f"{title} {text}".lower()
    matches = []
    for key, data in THEMES.items():
        if key == "overig":
            continue
        for kw in data["keywords"]:
            if kw in content:
                matches.append(key)
                break
    return matches if matches else ["overig"]

def detect_wijken_heuristics(title: str, text: str) -> list[str]:
    """
    Detect Utrecht neighborhoods based on occurrences in text.

    Matching is on whole words: a plain substring test tagged every document
    mentioning Noordoost as Oost as well, and every Zuidwest document as Zuid.
    Longer names are tried first so Vleuten-De Meern is not shadowed.
    """
    content = f"{title} {text}".lower()
    found = []
    for wijk in sorted(WIJKEN, key=len, reverse=True):
        pattern = r"(?<![\w-])" + re.escape(wijk.lower()) + r"(?![\w-])"
        if re.search(pattern, content):
            found.append(wijk)

    # Keep the declared order so output does not depend on name length.
    ordered = [w for w in WIJKEN if w in found]
    return ordered if ordered else ["Overig"]
