"""
Pydantic data schemas for validating LLM output and document states.
"""


from pydantic import BaseModel, Field


class SummaryItem(BaseModel):
    doc_id: str
    titel_kort_nl: str = Field(..., max_length=150)
    title_short_en: str = Field(..., max_length=150)
    samenvatting_nl: str
    summary_en: str
    
    # 3 Bullet Points Breakdown
    punt_1_wat_nl: str | None = "Wat: Raadsbesluit of voorstel"
    bullet_1_what_en: str | None = "What: Council decision or proposal"
    punt_2_wie_nl: str | None = "Wie: Inwoners van Utrecht"
    bullet_2_who_en: str | None = "Who: Residents of Utrecht"
    punt_3_geld_nl: str | None = "Impact & Kosten: Raadsinformatie"
    bullet_3_cost_en: str | None = "Impact & Budget: Council information"
    
    thema: list[str] = Field(default_factory=lambda: ["overig"])
    wijken: list[str] = Field(default_factory=lambda: ["Overig"])
    impact: str = Field(default="gemiddeld")
    pdf_url: str | None = ""
    date: str | None = ""
    degraded: bool | None = False
    ai_model: str | None = "Degraded Fallback"

class SummaryBatchOutput(BaseModel):
    items: list[SummaryItem]
