"""
Pydantic schemas for LLM summary outputs and state validation.
"""

from pydantic import BaseModel, Field


class SummaryItem(BaseModel):
    doc_id: str
    titel_kort_nl: str
    title_short_en: str
    samenvatting_nl: str
    summary_en: str

    # Decision Status & Key Metrics
    estado_besluit: str = Field(default="✅ Aangenomen")
    status_en: str = Field(default="✅ Approved")
    cifra_clave_nl: str = Field(default="💶 Geen extra kosten")
    key_figure_en: str = Field(default="💶 No extra costs")
    frase_impacto_nl: str = Field(default="Belangrijk besluit voor de ontwikkeling van Utrecht.")
    impact_sentence_en: str = Field(default="Important decision for the development of Utrecht.")

    # 3 Bullet Points Breakdown (Front Card Summary)
    punt_1_wat_nl: str = Field(default="Wat: Raadsbesluit of voorstel van de gemeente.")
    bullet_1_what_en: str = Field(default="What: Municipal decision or proposal.")
    punt_2_wie_nl: str = Field(default="Wie & Waar: Inwoners van Utrecht.")
    bullet_2_who_en: str = Field(default="Who & Where: Residents of Utrecht.")
    punt_3_geld_nl: str = Field(default="Impact & Kosten: Raadsinformatie disponible.")
    bullet_3_cost_en: str = Field(default="Impact & Budget: Council information available.")

    # Extended Details (For Detail Page / besluit/<doc_id>/)
    contexto_nl: str = Field(default="Dit besluit is ingediend en besproken in de Utrechtse gemeenteraad als onderdeel van de gemeentelijke cyclus.")
    context_en: str = Field(default="This decision was submitted and discussed in the Utrecht city council as part of the municipal planning cycle.")
    consecuencias_nl: str = Field(default="Het besluit geeft richting aan het gemeentelijk beleid en de uitvoering van projecten in de stad.")
    consequences_en: str = Field(default="The decision provides direction for municipal policy and execution of projects in the city.")
    plazo_nl: str = Field(default="📅 Uitvoering: 2026")
    timeline_en: str = Field(default="📅 Implementation: 2026")

    thema: list[str] = Field(default_factory=lambda: ["overig"])
    wijken: list[str] = Field(default_factory=lambda: ["Overig"])
    impact: str = Field(default="gemiddeld")
    pdf_url: str | None = ""
    date: str | None = ""
    degraded: bool | None = False
    ai_model: str | None = "Degraded Fallback"

class SummaryBatchOutput(BaseModel):
    items: list[SummaryItem]
