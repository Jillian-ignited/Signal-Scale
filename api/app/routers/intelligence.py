# api/app/routers/intelligence.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/intelligence", tags=["intelligence"])  # <- NO leading /api here

class AnalyzePayload(BaseModel):
    brand: str | None = None
    competitors: list[str] | None = None
    questions: list[str] | None = None

@router.post("/analyze")
async def analyze(payload: AnalyzePayload):
    # ... your logic ...
    return {"ok": True, "echo": payload.model_dump()}
