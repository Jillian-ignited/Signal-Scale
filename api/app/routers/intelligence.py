# api/app/routers/intelligence.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ..settings import settings

router = APIRouter(tags=["intelligence"])

class AnalyzePayload(BaseModel):
    brand: Optional[str] = None
    competitors: Optional[List[str]] = None
    questions: Optional[List[str]] = None

def demo_result(p: AnalyzePayload) -> Dict[str, Any]:
    return {
        "status": "ok",
        "mode": "SAFE_MODE",
        "input_echo": p.model_dump(),
        "summary": {
            "top_trends": [
                {"name": "Ralphcore", "momentum": "+68.4%", "state": "Scaling"},
                {"name": "Wide Leg Trousers", "momentum": "+46.7%", "state": "Scaling"},
                {"name": "Sustainable Streetwear", "momentum": "+27.6%", "state": "Emerging"},
            ],
            "quick_wins": [
                "Lower free shipping threshold to $150",
                "Launch #CrooksLife UGC",
                "Add PDP stock/urgency indicators",
            ],
        },
        "confidence": {"level": "Low (demo)", "variance": 0.0, "sources": []},
    }

@router.post("/intelligence/analyze")
async def analyze(payload: AnalyzePayload) -> Dict[str, Any]:
    """
    Frontend posts here.
    SAFE_MODE=True returns a stable demo so the UI always works.
    """
    print("[analyze] payload:", payload.model_dump())

    if settings.SAFE_MODE:
        return demo_result(payload)

    # --- REAL mode (wire your agents here later) ---
    try:
        brand = payload.brand or "Brand"
        comps = payload.competitors or []
        # from ..agents.cultural_radar import run_cultural_radar
        # from ..agents.competitive_playbook import run_competitive_playbook
        # from ..agents.dtc_audit import run_dtc_audit
        # radar = run_cultural_radar(brand=brand, competitors=comps)
        # playbook = run_competitive_playbook(brand=brand, competitors=comps)
        # audit = run_dtc_audit(brand=brand, competitors=comps)
        return {
            "status": "ok",
            "mode": "REAL",
            "brand": brand,
            "competitors": comps,
            "outputs": {
                # "cultural_radar": radar,
                # "competitive_playbook": playbook,
                # "dtc_audit": audit,
            },
            "confidence": {"level": "Medium", "variance": 0.12, "sources": []},
        }
    except HTTPException:
        raise
    except Exception as e:
        print("[analyze] ERROR:", repr(e))
        return {"status": "error", "message": "Analysis failed", "detail": str(e)}
