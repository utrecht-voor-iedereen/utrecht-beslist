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
    thema: list[str] = Field(default_factory=lambda: ["overig"])
    wijken: list[str] = Field(default_factory=lambda: ["Overig"])
    impact: str = Field(default="gemiddeld")
    pdf_url: str | None = ""
    date: str | None = ""
    degraded: bool | None = False

class SummaryBatchOutput(BaseModel):
    items: list[SummaryItem]
