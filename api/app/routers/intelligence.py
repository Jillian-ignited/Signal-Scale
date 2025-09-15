# api/app/routers/intelligence.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(
    prefix="/intelligence",   # <-- NOTE: NO leading /api here
    tags=["intelligence"]
)

# ----- Models -----
class AnalyzePayload(BaseModel):
    brand: Optional[str] = None
    competitors: Optional[List[str]] = None
    questions: Optional[List[str]] = None

# ----- Routes -----
@router.post("/analyze")
async def analyze(payload: AnalyzePayload):
    """
    Simple placeholder that proves routing works.
    Your real analysis code can be injected here later.
    """
    # Minimal validation demo
    if not (payload.brand or payload.questions):
        raise HTTPException(status_code=400, detail="Provide 'brand' or 'questions'.")

    # Return something deterministic for now
    return {
        "ok": True,
        "received": payload.model_dump(),
        "meta": {
            "route": "/api/intelligence/analyze",
            "note": "Router prefix '/intelligence' + app.include_router(prefix='/api')"
        }
    }