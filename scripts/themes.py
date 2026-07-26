"""
Taxonomy definition for themes, neighborhoods (wijken), and heuristic classification for Utrecht Beslist.
"""

THEMES = {
    "wonen": {
        "nl": "Wonen & Huisvesting",
        "en": "Housing & Living",
        "icon": "🏠",
        "keywords": ["wonen", "woning", "huur", "bouw", "huisvesting", "woonvisie", "bestemmingsplan", "erfpacht", "studentenwoningen", "woningbouw"]
    },
    "verkeer": {
        "nl": "Verkeer & Mobiliteit",
        "en": "Traffic & Mobility",
        "icon": "🚲",
        "keywords": ["verkeer", "mobiliteit", "fiets", "parkeren", "ov", "bus", "tram", "wegen", "snelfietspad", "autoluw", "snelheid"]
    },
    "veiligheid": {
        "nl": "Veiligheid & Handhaving",
        "en": "Safety & Enforcement",
        "icon": "🛡️",
        "keywords": ["veiligheid", "politie", "handhaving", "overlast", "cameratoezicht", "boa", "noodverordening", "brandweer"]
    },
    "groen-klimaat": {
        "nl": "Groen & Klimaat",
        "en": "Green & Climate",
        "icon": "🌿",
        "keywords": ["groen", "klimaat", "duurzaam", "energie", "bomen", "park", "warmtenet", "zonnepanelen", "biodiversiteit", "afval"]
    },
    "jeugd-onderwijs": {
        "nl": "Jeugd & Onderwijs",
        "en": "Youth & Education",
        "icon": "🎓",
        "keywords": ["jeugd", "onderwijs", "school", "kinderopvang", "leerling", "student", "speeltuin", "jeugdzorg"]
    },
    "zorg": {
        "nl": "Zorg & Welzijn",
        "en": "Health & Welfare",
        "icon": "❤️",
        "keywords": ["zorg", "welzijn", "wmo", "gezondheid", "armoede", "bijstand", "inclusie", "ouderen", "vrijwilligers"]
    },
    "bestuur-financien": {
        "nl": "Bestuur & Financiën",
        "en": "Governance & Finance",
        "icon": "🏛️",
        "keywords": ["begroting", "financien", "belasting", "ozb", "voorjaarsnota", "najaarsnota", "jaarrekening", "verordening", "raadsvoorstel"]
    },
    "cultuur-evenementen": {
        "nl": "Cultuur & Sport",
        "en": "Culture & Sports",
        "icon": "🎨",
        "keywords": ["cultuur", "sport", "evenement", "subsidie", "museum", "bibliotheek", "theater", "zwembad", "festival"]
    },
    "overig": {
        "nl": "Overig",
        "en": "Other",
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
    """Detect Utrecht neighborhoods based on occurrences in text."""
    content = f"{title} {text}"
    found = []
    for wijk in WIJKEN:
        if wijk.lower() in content.lower():
            found.append(wijk)
    return found
