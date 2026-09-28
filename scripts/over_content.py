"""
The "About" page: what the site is, where the data comes from, what the AI does
and does not decide, and how a mistake gets corrected.

This is what the municipality, a councillor or a journalist reads before
trusting a summary, so every claim here has to match what the code does. When
the pipeline changes — the source, the model, what is read from the register —
this page changes with it.

The strings are trusted HTML (links only) written here, not user content.
"""

from .i18n import status_text, t

REPO_URL = "https://github.com/utrecht-voor-iedereen/utrecht-beslist"
PORTAL_URL = "https://utrecht.bestuurlijkeinformatie.nl/"
OBV_URL = "https://openbesluitvorming.nl/"


def _a(url: str, label: str) -> str:
    return f'<a href="{url}" target="_blank" rel="noopener">{label}</a>'


OVER_HERO = {
    "nl": ("Over Utrecht Beslist", "Hoe de samenvattingen ontstaan, wat uit het officiële register komt en wat niet, en hoe u een fout meldt."),
    "en": ("About Utrecht Beslist", "How the summaries are made, what comes from the official record and what does not, and how to report a mistake."),
    "es": ("Sobre Utrecht Beslist", "Cómo se hacen los resúmenes, qué sale del registro oficial y qué no, y cómo avisar de un error."),
    "tr": ("Utrecht Beslist hakkında", "Özetler nasıl hazırlanıyor, neler resmi kayıttan geliyor, neler gelmiyor ve bir hatayı nasıl bildirirsiniz."),
    "pt-br": ("Sobre o Utrecht Beslist", "Como os resumos são feitos, o que vem do registro oficial e o que não vem, e como avisar de um erro."),
    "pt-pt": ("Sobre o Utrecht Beslist", "Como os resumos são feitos, o que vem do registo oficial e o que não vem, e como comunicar um erro."),
    "fr": ("À propos d'Utrecht Beslist", "Comment les résumés sont rédigés, ce qui vient du registre officiel et ce qui n'en vient pas, et comment signaler une erreur."),
    "de": ("Über Utrecht Beslist", "Wie die Zusammenfassungen entstehen, was aus dem offiziellen Register stammt und was nicht, und wie Sie einen Fehler melden."),
}

# Each section: (icon, heading, [paragraphs]).
OVER_SECTIONS: dict[str, list[tuple[str, str, list[str]]]] = {
    "nl": [
        ("🏛️", "Wat is Utrecht Beslist?", [
            "Utrecht Beslist vat de voorstellen en besluiten van de Utrechtse gemeenteraad samen in begrijpelijke taal (B1), in acht talen.",
            "Het is een <strong>onafhankelijk burgerinitiatief</strong>, geen website van de gemeente Utrecht. De officiële stukken staan in het " + _a(PORTAL_URL, "Raadsportaal") + ".",
            "De site is gratis, zonder reclame, cookies of tracking. De broncode is open (EUPL-1.2) en staat op " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📥", "Waar komen de gegevens vandaan?", [
            "Alle stukken komen van " + _a(OBV_URL, "OpenBesluitvorming") + ", de openbare bron voor raadsinformatie van gemeenten (opvolger van Open Raadsinformatie). Stukken tot en met 9 juli 2026 komen nog uit Open Raadsinformatie.",
            "Elke ochtend, van maandag tot en met zaterdag, halen we de nieuwe vergaderingen van de gemeenteraad op. We publiceren raadsvoorstellen en initiatiefvoorstellen; brieven, notulen en andere stukken niet.",
        ]),
        ("🔒", "Wat komt uit het officiële register, niet van AI", [
            "De <strong>status</strong>, de <strong>datum</strong>, de <strong>officiële titel</strong> en de <strong>links naar de pdf's</strong> nemen we over uit het register. De AI bepaalt die niet.",
            "Een voorstel staat op <em>{agenda}</em> tot de gemeente het raadsbesluit publiceert; dan wordt het <em>{passed}</em>.",
            "De datum is de datum van de vergadering waarin het stuk wordt besproken. Agenda's verschijnen een of twee weken vooraf, dus een datum kan in de toekomst liggen.",
        ]),
        ("🤖", "Wat schrijft de AI?", [
            "De samenvatting, de kernpunten en de vertalingen schrijft een taalmodel (nu het open model gpt-oss-120b, via Groq), op basis van de tekst van het raadsvoorstel zelf. Sommige samenvattingen zijn met de hand gemaakt.",
            "Het model krijgt vaste regels: niets verzinnen, bedragen en datums alleen zoals ze in het stuk staan, en niets zeggen over de uitslag van een stemming.",
            "Een AI kan zich vergissen. Een samenvatting is <strong>geen juridisch advies</strong>: lees bij twijfel altijd het officiële stuk. Sommige oudere stukken hebben nog een voorlopige tekst; die vervangen we stap voor stap.",
        ]),
        ("✏️", "Een fout gezien?", [
            "Gebruik de knop <em>{report}</em> op de pagina van het besluit, of het formulier onderaan elke pagina. Het opent een e-mail; we lezen elk bericht.",
            "We corrigeren de fout zo snel mogelijk. Elke wijziging is openbaar te volgen in de geschiedenis van de code op " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📜", "Bewaren", [
            "We verwijderen geen besluiten van deze site. Het officiële archief van de raad beheert de gemeente Utrecht; deze site is een samenvatting in gewone taal, geen archief.",
        ]),
    ],
    "en": [
        ("🏛️", "What is Utrecht Beslist?", [
            "Utrecht Beslist summarises the proposals and decisions of Utrecht city council in plain language (B1), in eight languages.",
            "It is an <strong>independent civic project</strong>, not a City of Utrecht website. The official documents are in the " + _a(PORTAL_URL, "council portal") + ".",
            "The site is free, with no ads, cookies or tracking. The code is open source (EUPL-1.2) and on " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📥", "Where does the data come from?", [
            "All documents come from " + _a(OBV_URL, "OpenBesluitvorming") + ", the public source of council information for Dutch municipalities (successor to Open Raadsinformatie). Documents up to 9 July 2026 still come from Open Raadsinformatie.",
            "Every morning, Monday to Saturday, we fetch the new city council meetings. We publish council proposals and initiative proposals; not letters, minutes or other papers.",
        ]),
        ("🔒", "What comes from the official record, not from AI", [
            "The <strong>status</strong>, the <strong>date</strong>, the <strong>official title</strong> and the <strong>links to the PDFs</strong> are taken from the register. The AI does not decide them.",
            "A proposal shows <em>{agenda}</em> until the municipality publishes the council decision; then it becomes <em>{passed}</em>.",
            "The date is the date of the meeting where the item is discussed. Agendas appear one or two weeks ahead, so a date can be in the future.",
        ]),
        ("🤖", "What does the AI write?", [
            "The summary, key points and translations are written by a language model (currently the open model gpt-oss-120b, via Groq), from the text of the proposal itself. Some summaries were written by hand.",
            "The model follows fixed rules: invent nothing, give amounts and dates only as the document states them, and say nothing about the outcome of a vote.",
            "AI can make mistakes. A summary is <strong>not legal advice</strong>: when in doubt, read the official document. Some older items still have a provisional text; we are replacing those step by step.",
        ]),
        ("✏️", "Spotted a mistake?", [
            "Use the <em>{report}</em> button on the decision page, or the form at the bottom of every page. It opens an email; we read every message.",
            "We fix mistakes as soon as we can. Every change can be followed publicly in the code history on " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📜", "Keeping records", [
            "We do not delete decisions from this site. The council's official archive is kept by the City of Utrecht; this site is a plain-language summary, not an archive.",
        ]),
    ],
    "es": [
        ("🏛️", "¿Qué es Utrecht Beslist?", [
            "Utrecht Beslist resume las propuestas y decisiones del ayuntamiento de Utrecht en lenguaje claro (nivel B1), en ocho idiomas.",
            "Es una <strong>iniciativa ciudadana independiente</strong>, no una web del Ayuntamiento de Utrecht. Los documentos oficiales están en el " + _a(PORTAL_URL, "portal del consejo") + ".",
            "La web es gratuita, sin anuncios, cookies ni seguimiento. El código es abierto (EUPL-1.2) y está en " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📥", "¿De dónde salen los datos?", [
            "Todos los documentos vienen de " + _a(OBV_URL, "OpenBesluitvorming") + ", la fuente pública de información de los consejos municipales neerlandeses (sucesora de Open Raadsinformatie). Los documentos hasta el 9 de julio de 2026 vienen aún de Open Raadsinformatie.",
            "Cada mañana, de lunes a sábado, recogemos las nuevas sesiones del ayuntamiento. Publicamos propuestas del gobierno local y propuestas de iniciativa; no cartas, actas ni otros documentos.",
        ]),
        ("🔒", "Qué sale del registro oficial y no de la IA", [
            "El <strong>estado</strong>, la <strong>fecha</strong>, el <strong>título oficial</strong> y los <strong>enlaces a los PDF</strong> se copian del registro. La IA no los decide.",
            "Una propuesta aparece como <em>{agenda}</em> hasta que el ayuntamiento publica el acuerdo; entonces pasa a <em>{passed}</em>.",
            "La fecha es la de la sesión en que se trata el punto. Los órdenes del día se publican una o dos semanas antes, así que una fecha puede estar en el futuro.",
        ]),
        ("🤖", "¿Qué escribe la IA?", [
            "El resumen, los puntos clave y las traducciones los escribe un modelo de lenguaje (ahora el modelo abierto gpt-oss-120b, a través de Groq), a partir del texto de la propia propuesta. Algunos resúmenes se han escrito a mano.",
            "El modelo sigue reglas fijas: no inventar nada, dar importes y fechas solo como aparecen en el documento y no decir nada sobre el resultado de una votación.",
            "La IA puede equivocarse. Un resumen <strong>no es asesoramiento jurídico</strong>: ante la duda, lee el documento oficial. Algunos documentos antiguos tienen aún un texto provisional; los vamos sustituyendo poco a poco.",
        ]),
        ("✏️", "¿Has visto un error?", [
            "Usa el botón <em>{report}</em> en la página de la decisión o el formulario al final de cada página. Se abre un correo; leemos todos los mensajes.",
            "Corregimos los errores lo antes posible. Cada cambio puede seguirse públicamente en el historial del código en " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📜", "Conservación", [
            "No borramos decisiones de esta web. El archivo oficial del consejo lo gestiona el Ayuntamiento de Utrecht; esta web es un resumen en lenguaje claro, no un archivo.",
        ]),
    ],
    "tr": [
        ("🏛️", "Utrecht Beslist nedir?", [
            "Utrecht Beslist, Utrecht belediye meclisinin önerilerini ve kararlarını sekiz dilde, anlaşılır bir dille (B1) özetler.",
            "Bu <strong>bağımsız bir yurttaş girişimidir</strong>, Utrecht Belediyesi'nin sitesi değildir. Resmi belgeler " + _a(PORTAL_URL, "meclis portalında") + " yer alır.",
            "Site ücretsizdir; reklam, çerez ve izleme yoktur. Kaynak kodu açıktır (EUPL-1.2) ve " + _a(REPO_URL, "GitHub") + " üzerindedir.",
        ]),
        ("📥", "Veriler nereden geliyor?", [
            "Tüm belgeler, Hollanda belediyelerinin meclis bilgileri için kamuya açık kaynak olan " + _a(OBV_URL, "OpenBesluitvorming") + "'dan gelir (Open Raadsinformatie'nin devamı). 9 Temmuz 2026'ya kadarki belgeler hâlâ Open Raadsinformatie'den gelir.",
            "Pazartesiden cumartesiye her sabah belediye meclisinin yeni toplantılarını alıyoruz. Meclis önerilerini ve girişim önerilerini yayımlıyoruz; mektupları, tutanakları ve diğer belgeleri yayımlamıyoruz.",
        ]),
        ("🔒", "Neler resmi kayıttan gelir, yapay zekâdan değil", [
            "<strong>Durum</strong>, <strong>tarih</strong>, <strong>resmi başlık</strong> ve <strong>PDF bağlantıları</strong> kayıttan alınır. Bunlara yapay zekâ karar vermez.",
            "Bir öneri, belediye meclis kararını yayımlayana kadar <em>{agenda}</em> görünür; sonra <em>{passed}</em> olur.",
            "Tarih, konunun görüşüleceği toplantının tarihidir. Gündemler bir iki hafta önceden yayımlanır; bu yüzden tarih gelecekte olabilir.",
        ]),
        ("🤖", "Yapay zekâ ne yazıyor?", [
            "Özeti, ana noktaları ve çevirileri, önerinin kendi metnine dayanarak bir dil modeli yazar (şu anda Groq üzerinden açık model gpt-oss-120b). Bazı özetler elle yazılmıştır.",
            "Model sabit kurallara uyar: hiçbir şey uydurmaz, tutarları ve tarihleri yalnızca belgede yazdığı gibi verir ve oylama sonucu hakkında bir şey söylemez.",
            "Yapay zekâ hata yapabilir. Özet <strong>hukuki tavsiye değildir</strong>: emin değilseniz resmi belgeyi okuyun. Bazı eski belgelerde hâlâ geçici bir metin var; bunları adım adım değiştiriyoruz.",
        ]),
        ("✏️", "Bir hata mı gördünüz?", [
            "Karar sayfasındaki <em>{report}</em> düğmesini veya her sayfanın altındaki formu kullanın. Bir e-posta açılır; her mesajı okuyoruz.",
            "Hataları en kısa sürede düzeltiyoruz. Her değişiklik " + _a(REPO_URL, "GitHub") + "'daki kod geçmişinde herkese açık olarak izlenebilir.",
        ]),
        ("📜", "Saklama", [
            "Bu siteden karar silmiyoruz. Meclisin resmi arşivini Utrecht Belediyesi tutar; bu site bir arşiv değil, anlaşılır dilde bir özettir.",
        ]),
    ],
    "pt-br": [
        ("🏛️", "O que é o Utrecht Beslist?", [
            "O Utrecht Beslist resume as propostas e decisões da câmara municipal de Utrecht em linguagem simples (nível B1), em oito idiomas.",
            "É uma <strong>iniciativa cidadã independente</strong>, não um site da Prefeitura de Utrecht. Os documentos oficiais estão no " + _a(PORTAL_URL, "portal da câmara") + ".",
            "O site é gratuito, sem anúncios, cookies ou rastreamento. O código é aberto (EUPL-1.2) e está no " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📥", "De onde vêm os dados?", [
            "Todos os documentos vêm do " + _a(OBV_URL, "OpenBesluitvorming") + ", a fonte pública de informação das câmaras municipais holandesas (sucessor do Open Raadsinformatie). Os documentos até 9 de julho de 2026 ainda vêm do Open Raadsinformatie.",
            "Toda manhã, de segunda a sábado, buscamos as novas sessões da câmara. Publicamos propostas do executivo e propostas de iniciativa; não cartas, atas ou outros documentos.",
        ]),
        ("🔒", "O que vem do registro oficial, não da IA", [
            "O <strong>status</strong>, a <strong>data</strong>, o <strong>título oficial</strong> e os <strong>links para os PDFs</strong> são copiados do registro. A IA não decide isso.",
            "Uma proposta aparece como <em>{agenda}</em> até a prefeitura publicar a decisão da câmara; então passa a <em>{passed}</em>.",
            "A data é a da sessão em que o item é discutido. As pautas saem uma ou duas semanas antes, então uma data pode estar no futuro.",
        ]),
        ("🤖", "O que a IA escreve?", [
            "O resumo, os pontos principais e as traduções são escritos por um modelo de linguagem (hoje o modelo aberto gpt-oss-120b, via Groq), a partir do texto da própria proposta. Alguns resumos foram escritos à mão.",
            "O modelo segue regras fixas: não inventar nada, dar valores e datas só como estão no documento e não dizer nada sobre o resultado de uma votação.",
            "A IA pode errar. Um resumo <strong>não é aconselhamento jurídico</strong>: na dúvida, leia o documento oficial. Alguns documentos antigos ainda têm um texto provisório; estamos substituindo aos poucos.",
        ]),
        ("✏️", "Viu um erro?", [
            "Use o botão <em>{report}</em> na página da decisão ou o formulário no fim de cada página. Ele abre um e-mail; lemos todas as mensagens.",
            "Corrigimos os erros o quanto antes. Cada mudança pode ser acompanhada publicamente no histórico do código no " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📜", "Guarda", [
            "Não apagamos decisões deste site. O arquivo oficial da câmara é mantido pela Prefeitura de Utrecht; este site é um resumo em linguagem simples, não um arquivo.",
        ]),
    ],
    "pt-pt": [
        ("🏛️", "O que é o Utrecht Beslist?", [
            "O Utrecht Beslist resume as propostas e decisões da assembleia municipal de Utrecht em linguagem simples (nível B1), em oito línguas.",
            "É uma <strong>iniciativa cidadã independente</strong>, não um site do Município de Utrecht. Os documentos oficiais estão no " + _a(PORTAL_URL, "portal da assembleia") + ".",
            "O site é gratuito, sem publicidade, cookies ou rastreio. O código é aberto (EUPL-1.2) e está no " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📥", "De onde vêm os dados?", [
            "Todos os documentos vêm do " + _a(OBV_URL, "OpenBesluitvorming") + ", a fonte pública de informação das assembleias municipais neerlandesas (sucessor do Open Raadsinformatie). Os documentos até 9 de julho de 2026 ainda vêm do Open Raadsinformatie.",
            "Todas as manhãs, de segunda a sábado, recolhemos as novas sessões da assembleia. Publicamos propostas do executivo e propostas de iniciativa; não cartas, atas ou outros documentos.",
        ]),
        ("🔒", "O que vem do registo oficial, não da IA", [
            "O <strong>estado</strong>, a <strong>data</strong>, o <strong>título oficial</strong> e as <strong>ligações para os PDF</strong> são copiados do registo. A IA não os decide.",
            "Uma proposta aparece como <em>{agenda}</em> até o município publicar a deliberação; depois passa a <em>{passed}</em>.",
            "A data é a da sessão em que o ponto é discutido. As ordens de trabalhos saem uma ou duas semanas antes, por isso uma data pode estar no futuro.",
        ]),
        ("🤖", "O que escreve a IA?", [
            "O resumo, os pontos principais e as traduções são escritos por um modelo de linguagem (agora o modelo aberto gpt-oss-120b, através da Groq), a partir do texto da própria proposta. Alguns resumos foram escritos à mão.",
            "O modelo segue regras fixas: não inventar nada, dar montantes e datas só como constam do documento e não dizer nada sobre o resultado de uma votação.",
            "A IA pode enganar-se. Um resumo <strong>não é aconselhamento jurídico</strong>: em caso de dúvida, leia o documento oficial. Alguns documentos antigos ainda têm um texto provisório; estamos a substituí-los aos poucos.",
        ]),
        ("✏️", "Viu um erro?", [
            "Use o botão <em>{report}</em> na página da decisão ou o formulário no fim de cada página. Abre um e-mail; lemos todas as mensagens.",
            "Corrigimos os erros o mais depressa possível. Cada alteração pode ser acompanhada publicamente no histórico do código no " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📜", "Conservação", [
            "Não apagamos decisões deste site. O arquivo oficial da assembleia é mantido pelo Município de Utrecht; este site é um resumo em linguagem simples, não um arquivo.",
        ]),
    ],
    "fr": [
        ("🏛️", "Qu'est-ce qu'Utrecht Beslist ?", [
            "Utrecht Beslist résume les propositions et décisions du conseil municipal d'Utrecht en langage clair (niveau B1), en huit langues.",
            "C'est une <strong>initiative citoyenne indépendante</strong>, pas un site de la Ville d'Utrecht. Les documents officiels se trouvent sur le " + _a(PORTAL_URL, "portail du conseil") + ".",
            "Le site est gratuit, sans publicité, cookies ni pistage. Le code est libre (EUPL-1.2) et se trouve sur " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📥", "D'où viennent les données ?", [
            "Tous les documents proviennent d'" + _a(OBV_URL, "OpenBesluitvorming") + ", la source publique d'information des conseils municipaux néerlandais (successeur d'Open Raadsinformatie). Les documents jusqu'au 9 juillet 2026 proviennent encore d'Open Raadsinformatie.",
            "Chaque matin, du lundi au samedi, nous récupérons les nouvelles séances du conseil. Nous publions les propositions de l'exécutif et les propositions d'initiative ; pas les lettres, procès-verbaux ni autres documents.",
        ]),
        ("🔒", "Ce qui vient du registre officiel, pas de l'IA", [
            "Le <strong>statut</strong>, la <strong>date</strong>, le <strong>titre officiel</strong> et les <strong>liens vers les PDF</strong> sont repris du registre. L'IA ne les décide pas.",
            "Une proposition affiche <em>{agenda}</em> jusqu'à ce que la ville publie la délibération ; elle passe alors à <em>{passed}</em>.",
            "La date est celle de la séance où le point est discuté. Les ordres du jour paraissent une ou deux semaines avant, une date peut donc être dans le futur.",
        ]),
        ("🤖", "Qu'écrit l'IA ?", [
            "Le résumé, les points clés et les traductions sont rédigés par un modèle de langage (actuellement le modèle ouvert gpt-oss-120b, via Groq), à partir du texte même de la proposition. Certains résumés ont été écrits à la main.",
            "Le modèle suit des règles fixes : ne rien inventer, ne donner montants et dates que tels qu'ils figurent dans le document, et ne rien dire du résultat d'un vote.",
            "L'IA peut se tromper. Un résumé <strong>n'est pas un conseil juridique</strong> : en cas de doute, lisez le document officiel. Certains documents anciens ont encore un texte provisoire ; nous les remplaçons peu à peu.",
        ]),
        ("✏️", "Vous avez vu une erreur ?", [
            "Utilisez le bouton <em>{report}</em> sur la page de la décision, ou le formulaire en bas de chaque page. Il ouvre un e-mail ; nous lisons chaque message.",
            "Nous corrigeons les erreurs au plus vite. Chaque modification peut être suivie publiquement dans l'historique du code sur " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📜", "Conservation", [
            "Nous ne supprimons aucune décision de ce site. Les archives officielles du conseil sont tenues par la Ville d'Utrecht ; ce site est un résumé en langage clair, pas une archive.",
        ]),
    ],
    "de": [
        ("🏛️", "Was ist Utrecht Beslist?", [
            "Utrecht Beslist fasst die Vorlagen und Beschlüsse des Utrechter Gemeinderats in einfacher Sprache (B1) zusammen, in acht Sprachen.",
            "Es ist eine <strong>unabhängige Bürgerinitiative</strong>, keine Website der Stadt Utrecht. Die offiziellen Dokumente finden Sie im " + _a(PORTAL_URL, "Ratsportal") + ".",
            "Die Website ist kostenlos, ohne Werbung, Cookies oder Tracking. Der Code ist offen (EUPL-1.2) und liegt auf " + _a(REPO_URL, "GitHub") + ".",
        ]),
        ("📥", "Woher kommen die Daten?", [
            "Alle Dokumente stammen von " + _a(OBV_URL, "OpenBesluitvorming") + ", der öffentlichen Quelle für Ratsinformationen niederländischer Gemeinden (Nachfolger von Open Raadsinformatie). Dokumente bis zum 9. Juli 2026 stammen noch aus Open Raadsinformatie.",
            "Jeden Morgen von Montag bis Samstag holen wir die neuen Sitzungen des Gemeinderats ab. Wir veröffentlichen Ratsvorlagen und Initiativvorlagen; keine Briefe, Protokolle oder anderen Unterlagen.",
        ]),
        ("🔒", "Was aus dem offiziellen Register stammt, nicht von der KI", [
            "<strong>Status</strong>, <strong>Datum</strong>, <strong>offizieller Titel</strong> und <strong>Links zu den PDFs</strong> werden aus dem Register übernommen. Die KI entscheidet darüber nicht.",
            "Eine Vorlage steht auf <em>{agenda}</em>, bis die Stadt den Ratsbeschluss veröffentlicht; dann wird sie <em>{passed}</em>.",
            "Das Datum ist das der Sitzung, in der der Punkt beraten wird. Tagesordnungen erscheinen ein bis zwei Wochen vorher, daher kann ein Datum in der Zukunft liegen.",
        ]),
        ("🤖", "Was schreibt die KI?", [
            "Zusammenfassung, Kernpunkte und Übersetzungen schreibt ein Sprachmodell (derzeit das offene Modell gpt-oss-120b über Groq), auf Grundlage des Textes der Vorlage selbst. Einige Zusammenfassungen wurden von Hand geschrieben.",
            "Das Modell folgt festen Regeln: nichts erfinden, Beträge und Daten nur so angeben, wie sie im Dokument stehen, und nichts über den Ausgang einer Abstimmung sagen.",
            "KI kann sich irren. Eine Zusammenfassung ist <strong>keine Rechtsberatung</strong>: Lesen Sie im Zweifel das offizielle Dokument. Einige ältere Einträge haben noch einen vorläufigen Text; diese ersetzen wir Schritt für Schritt.",
        ]),
        ("✏️", "Einen Fehler gefunden?", [
            "Nutzen Sie die Schaltfläche <em>{report}</em> auf der Seite des Beschlusses oder das Formular unten auf jeder Seite. Es öffnet eine E-Mail; wir lesen jede Nachricht.",
            "Wir korrigieren Fehler so schnell wie möglich. Jede Änderung ist öffentlich in der Code-Historie auf " + _a(REPO_URL, "GitHub") + " nachvollziehbar.",
        ]),
        ("📜", "Aufbewahrung", [
            "Wir löschen keine Beschlüsse von dieser Website. Das offizielle Archiv des Rates führt die Stadt Utrecht; diese Website ist eine Zusammenfassung in einfacher Sprache, kein Archiv.",
        ]),
    ],
}


def over_hero(lang: str) -> tuple[str, str]:
    return OVER_HERO.get(lang, OVER_HERO["en"])


def over_sections(lang: str) -> list[tuple[str, str, list[str]]]:
    """
    The sections in one language, with the labels the site actually shows.

    The status names and the report button are filled in from i18n rather
    than typed here, so the page cannot describe a button by a name it does
    not carry.
    """
    labels = {
        "agenda": status_text("agenda", lang),
        "passed": status_text("passed", lang),
        "report": t("report_error", lang),
    }
    sections = OVER_SECTIONS.get(lang, OVER_SECTIONS["en"])
    return [(icon, title, [p.format(**labels) for p in paragraphs]) for icon, title, paragraphs in sections]
