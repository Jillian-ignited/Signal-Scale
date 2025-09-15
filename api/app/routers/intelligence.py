# api/app/routers/intelligence.py
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

from ..settings import settings

try:
    from ..agents.cultural_radar import run_cultural_radar
    from ..agents.competitive_playbook import run_competitive_playbook
    from ..agents.dtc_audit import run_dtc_audit
    AGENTS_AVAILABLE = True
except Exception as e:
    print("[intel] agent import failed:", repr(e))
    AGENTS_AVAILABLE = False

router = APIRouter(prefix="/api", tags=["intelligence"])

class AnalyzePayload(BaseModel):
    brand: Optional[str] = None
    competitors: Optional[List[str]] = None
    questions: Optional[List[str]] = None

def demo_payload(p: AnalyzePayload) -> Dict[str, Any]:
    return {
        "status": "ok",
        "mode": "SAFE_MODE",
        "brand": p.brand or "Demo Brand",
        "competitors": p.competitors or ["Competitor A", "Competitor B"],
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

def coerce_payload(raw: Dict[str, Any]) -> AnalyzePayload:
    """Coerce any dict into AnalyzePayload without throwing 422."""
    if raw is None:
        raw = {}
    return AnalyzePayload(
        brand=raw.get("brand"),
        competitors=raw.get("competitors"),
        questions=raw.get("questions"),
    )

@router.post("/intelligence/analyze")
async def analyze(raw: Dict[str, Any] = Body(default={})):
    """
    Accepts any JSON (even {}), coerces to AnalyzePayload, and runs analysis.
    This avoids 422 errors if the frontend sends an empty or slightly different shape.
    """
    print("[/api/intelligence/analyze] raw:", raw)
    payload = coerce_payload(raw)
    print("[/api/intelligence/analyze] coerced:", payload.model_dump())

    if settings.SAFE_MODE or not AGENTS_AVAILABLE:
        return demo_payload(payload)

    try:
        brand = payload.brand or "Brand"
        comps = payload.competitors or []
        radar = run_cultural_radar(brand=brand, competitors=comps)
        playbook = run_competitive_playbook(brand=brand, competitors=comps)
        audit = run_dtc_audit(brand=brand, competitors=comps)

        return {
            "status": "ok",
            "mode": "REAL",
            "brand": brand,
            "competitors": comps,
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
        return {"status": "error", "message": "Analysis failed", "detail": str(e)}

# sanity check
@router.get("/intelligence/ping")
async def ping():
    return {"ok": True}
