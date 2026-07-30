"""
Pydantic schemas for LLM summary outputs and state validation.
Supports 8 languages: NL, EN, ES, TR, PT-BR, PT-PT, FR, DE.
"""

from pydantic import BaseModel, Field


class SummaryItem(BaseModel):
    doc_id: str
    titel_kort_nl: str
    title_short_en: str
    samenvatting_nl: str
    summary_en: str

    # Dutch (nl) & English (en) fields
    # Overwritten from the ORI record in pipeline.py. Defaulting these to an
    # approval meant any field the model omitted claimed the council had
    # passed the proposal.
    estado_besluit: str = Field(default="")
    status_en: str = Field(default="")
    cifra_clave_nl: str = Field(default="💶 Geen extra kosten")
    key_figure_en: str = Field(default="💶 No extra costs")
    frase_impacto_nl: str = Field(default="Belangrijk besluit voor de ontwikkeling van Utrecht.")
    impact_sentence_en: str = Field(default="Important decision for the development of Utrecht.")

    punt_1_wat_nl: str = Field(default="Wat: Raadsbesluit of voorstel van de gemeente.")
    bullet_1_what_en: str = Field(default="What: Municipal decision or proposal.")
    punt_2_wie_nl: str = Field(default="Wie & Waar: Inwoners van Utrecht.")
    bullet_2_who_en: str = Field(default="Who & Where: Residents of Utrecht.")
    punt_3_geld_nl: str = Field(default="Impact & Kosten: Raadsinformatie disponible.")
    bullet_3_cost_en: str = Field(default="Impact & Budget: Council information available.")

    contexto_nl: str = Field(default="Dit besluit is ingediend en besproken in de Utrechtse gemeenteraad als onderdeel van de gemeentelijke cyclus.")
    context_en: str = Field(default="This decision was submitted and discussed in the Utrecht city council as part of the municipal planning cycle.")
    consecuencias_nl: str = Field(default="Het besluit geeft richting aan het gemeentelijk beleid en de uitvoering van projecten in de stad.")
    consequences_en: str = Field(default="The decision provides direction for municipal policy and execution of projects in the city.")
    plazo_nl: str = Field(default="📅 Uitvoering: 2026")
    timeline_en: str = Field(default="📅 Implementation: 2026")

    # Spanish (es)
    title_short_es: str = Field(default="")
    summary_es: str = Field(default="")
    status_es: str = Field(default="")
    key_figure_es: str = Field(default="💶 Sin costes extra")
    impact_sentence_es: str = Field(default="Decisión importante para el desarrollo de Utrecht.")
    bullet_1_what_es: str = Field(default="📌 Qué: Acuerdo o propuesta del ayuntamiento.")
    bullet_2_who_es: str = Field(default="👥 Quién y dónde: Vecinos de Utrecht.")
    bullet_3_cost_es: str = Field(default="💶 Impacto y presupuesto: Información municipal disponible.")
    context_es: str = Field(default="Esta propuesta fue presentada y debatida en el ayuntamiento de Utrecht.")
    consequences_es: str = Field(default="La decisión orienta la política municipal y la ejecución de proyectos.")
    timeline_es: str = Field(default="📅 Ejecución: 2026")

    # Turkish (tr)
    title_short_tr: str = Field(default="")
    summary_tr: str = Field(default="")
    status_tr: str = Field(default="")
    key_figure_tr: str = Field(default="💶 Ek maliyet yok")
    impact_sentence_tr: str = Field(default="Utrecht sakinleri için önemli karar.")
    bullet_1_what_tr: str = Field(default="📌 Ne: Belediye meclis kararı veya teklifi.")
    bullet_2_who_tr: str = Field(default="👥 Kim ve Nerede: Utrecht sakinleri.")
    bullet_3_cost_tr: str = Field(default="💶 Etki ve Bütçe: Meclis bilgisi mevcut.")
    context_tr: str = Field(default="Bu teklif Utrecht belediye meclisine sunulmuş ve görüşülmüştür.")
    consequences_tr: str = Field(default="Karar, şehirdeki belediye politikasına ve projelere yön vermektedir.")
    timeline_tr: str = Field(default="📅 Uygulama: 2026")

    # Brazilian Portuguese (pt-br)
    title_short_pt_br: str = Field(default="")
    summary_pt_br: str = Field(default="")
    status_pt_br: str = Field(default="")
    key_figure_pt_br: str = Field(default="💶 Sem custos extras")
    impact_sentence_pt_br: str = Field(default="Decisão importante para o desenvolvimento de Utrecht.")
    bullet_1_what_pt_br: str = Field(default="📌 O que: Decisão ou proposta municipal.")
    bullet_2_who_pt_br: str = Field(default="👥 Quem e Onde: Moradores de Utrecht.")
    bullet_3_cost_pt_br: str = Field(default="💶 Impacto e Orçamento: Informação municipal disponível.")
    context_pt_br: str = Field(default="Esta proposta foi apresentada e debatida no conselho municipal de Utrecht.")
    consequences_pt_br: str = Field(default="A decisão orienta a política municipal e a execução de projetos.")
    timeline_pt_br: str = Field(default="📅 Execução: 2026")

    # European Portuguese (pt-pt)
    title_short_pt_pt: str = Field(default="")
    summary_pt_pt: str = Field(default="")
    status_pt_pt: str = Field(default="")
    key_figure_pt_pt: str = Field(default="💶 Sem custos adicionais")
    impact_sentence_pt_pt: str = Field(default="Decisão importante para o desenvolvimento de Utrecht.")
    bullet_1_what_pt_pt: str = Field(default="📌 O que: Decisão ou proposta municipal.")
    bullet_2_who_pt_pt: str = Field(default="👥 Quem e Onde: Residentes de Utrecht.")
    bullet_3_cost_pt_pt: str = Field(default="💶 Impacto e Orçamento: Informação municipal disponível.")
    context_pt_pt: str = Field(default="Esta proposta foi apresentada e debatida na câmara municipal de Utrecht.")
    consequences_pt_pt: str = Field(default="A decisão orienta a política municipal e a execução de projetos.")
    timeline_pt_pt: str = Field(default="📅 Execução: 2026")

    # French (fr)
    title_short_fr: str = Field(default="")
    summary_fr: str = Field(default="")
    status_fr: str = Field(default="")
    key_figure_fr: str = Field(default="💶 Pas de coûts supplémentaires")
    impact_sentence_fr: str = Field(default="Décision importante pour le développement d'Utrecht.")
    bullet_1_what_fr: str = Field(default="📌 Quoi : Décision ou proposition municipale.")
    bullet_2_who_fr: str = Field(default="👥 Qui & Où : Habitants d'Utrecht.")
    bullet_3_cost_fr: str = Field(default="💶 Impact & Budget : Information municipale disponible.")
    context_fr: str = Field(default="Cette proposition a été soumise et débattue au conseil municipal d'Utrecht.")
    consequences_fr: str = Field(default="La décision oriente la politique municipale et l'exécution des projets.")
    timeline_fr: str = Field(default="📅 Exécution : 2026")

    # German (de)
    title_short_de: str = Field(default="")
    summary_de: str = Field(default="")
    status_de: str = Field(default="")
    key_figure_de: str = Field(default="💶 Keine Zusatzkosten")
    impact_sentence_de: str = Field(default="Wichtiger Beschluss für die Entwicklung von Utrecht.")
    bullet_1_what_de: str = Field(default="📌 Was: Stadtratsbeschluss oder Ratsantrag.")
    bullet_2_who_de: str = Field(default="👥 Wer & Wo: Einwohner von Utrecht.")
    bullet_3_cost_de: str = Field(default="💶 Wirkung & Budget: Ratsinformationen verfügbar.")
    context_de: str = Field(default="Dieser Antrag wurde im Stadtrat Utrecht eingereicht und diskutiert.")
    consequences_de: str = Field(default="Der Beschluss gibt die Richtung für die städtische Politik und Projekte vor.")
    timeline_de: str = Field(default="📅 Umsetzung: 2026")

    thema: list[str] = Field(default_factory=lambda: ["overig"])
    wijken: list[str] = Field(default_factory=lambda: ["Overig"])
    impact: str = Field(default="gemiddeld")
    pdf_url: str | None = ""
    date: str | None = ""
    degraded: bool | None = False
    ai_model: str | None = "Degraded Fallback"

    # Provenance, filled from the Open Raadsinformatie record rather than the
    # model, so the detail page can show where every claim comes from.
    state: str = Field(default="agenda")
    official_title: str = Field(default="")
    doc_type: str = Field(default="")
    classification: str = Field(default="")
    source_url: str = Field(default="")
    attachments: list[dict] = Field(default_factory=list)
    # doc_id whose papers this record shows, when ORI files the decision and
    # the proposal separately and only the proposal carries the PDFs.
    source_borrowed_from: str = Field(default="")


class SummaryBatchOutput(BaseModel):
    items: list[SummaryItem]
