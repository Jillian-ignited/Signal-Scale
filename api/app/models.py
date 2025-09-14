from pydantic import BaseModel, HttpUrl
from typing import List, Literal

class BrandInput(BaseModel):
    name: str
    url: HttpUrl
    category: str = "apparel"
    target_audience: str = "18-34"

class CompetitorInput(BaseModel):
    name: str
    url: HttpUrl

class AnalysisRequest(BaseModel):
    brand: BrandInput
    competitors: List[CompetitorInput]

class ExportRequest(BaseModel):
    payload: dict
    format: Literal["html", "markdown"] = "html"
