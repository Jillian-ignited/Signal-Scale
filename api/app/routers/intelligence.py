# api/app/routers/intelligence.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Any, Dict, List, Optional

# If you have settings, keep this import. If not, stub SAFE_MODE = True below.
try:
    from ..settings import settings  # must provide settings.SAFE_MODE (bool)
    SAFE_MODE = getattr(settings, "SAFE_MODE", True)
except Exception:
    SAFE_MODE = True

# Try to import agents; if they fail we’ll gracefully fall back.
try:
    from ..agents.cultural_radar import run_cultural_radar
    from ..agents.competitive_playbook import run_competitive_playbook
    from ..agents.dtc_audit import run_dtc_audit
    AGENTS_AVAILABLE = True
except Exception as e:
    print("[intel] agent import failed:", repr(e))
    AGENTS_AVAILABLE = False

router = APIRouter(tags=["intelligence"])

class AnalyzePayload(BaseModel):
    brand: Optional[str] = None
    competitors: Optional[List[str]] = None
    questions: Optional[List[str]] = None

    # Accept both CSV strings and arrays, and coerce to list[str]
    @field_validator("competitors", mode="before")
    @classmethod
    def _coerce_competitors(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if isinstance(v, list):
            return [str(s) for s in v]
        return None

    @field_validator("questions", mode="before")
    @classmethod
    def _coerce_questions(cls, v):
        if v is None or v == "":
            return None
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        if isinstance(v, list):
            return [str(s) for s in v]
        return None

def demo_payload(p: AnalyzePayload) -> Dict[str, Any]:
    return {
        "status": "ok",
        "mode": "SAFE_MODE",
        "echo": {
            "brand": p.brand or "Demo Brand",
            "competitors": p.competitors or ["Competitor A", "Competitor B"],
            "questions": p.questions or [],
        },
        "summary": {
            "top_trends": [
                {"name": "Ralphcore", "momentum": "+68.4%", "state": "Scaling"},
                {"name": "Wide Leg Trousers", "momentum": "+46.7%", "state": "Scaling"},
                {"name": "Sustainable Streetwear", "momentum": "+27.6%", "state": "Emerging"},
            ],
            "quick_wins": [
                "Lower free shipping threshold to $150",
                "Launch #UGC campaign",
                "Add urgency + stock indicators on PDPs",
            ],
        },
        "confidence": {"level": "Low (demo)", "variance": 0.0, "sources": []},
    }

@router.post("/intelligence/analyze")
async def analyze(payload: Optional[AnalyzePayload] = None) -> Dict[str, Any]:
    """
    Accepts super-flexible JSON. Works with {}, or with brand/competitors/questions
    provided as strings or arrays. Falls back to demo in SAFE_MODE or when agents are unavailable.
    """
    payload = payload or AnalyzePayload()  # allow empty body {}
    print("[/api/intelligence/analyze] payload:", payload.model_dump())

    # Demo mode (no OpenAI key, or agents not wired yet)
    if SAFE_MODE or not AGENTS_AVAILABLE:
        return demo_payload(payload)

    # Real mode: call your agents
    try:
        brand = payload.brand or "Brand"
        comps = payload.competitors or []
        qs = payload.questions or []

        radar = run_cultural_radar(brand=brand, competitors=comps, questions=qs)  # adapt if signatures differ
        playbook = run_competitive_playbook(brand=brand, competitors=comps, questions=qs)
        audit = run_dtc_audit(brand=brand, competitors=comps, questions=qs)

        return {
            "status": "ok",
            "mode": "REAL",
            "brand": brand,
            "competitors": comps,
            "questions": qs,
            "outputs": {
                "cultural_radar": radar,
                "competitive_playbook": playbook,
                "dtc_audit": audit,
            },
            "confidence": {
                "level": "Medium",
                "variance": 0.12,
                "sources": ["Site audits", "Social signals", "Price scans"],
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        print("[/api/intelligence/analyze] ERROR:", repr(e))
        # Return JSON error (keeps the UI from white-screening)
        return {"status": "error", "message": "Analysis failed", "detail": str(e)}
