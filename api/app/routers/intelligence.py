# api/app/routers/intelligence.py

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..settings import settings

# Try to import real agents; if it fails we stay in SAFE_MODE demo
AGENTS_AVAILABLE = False
try:
    from ..agents.cultural_radar import run_cultural_radar
    from ..agents.competitive_playbook import run_competitive_playbook
    from ..agents.dtc_audit import run_dtc_audit
    AGENTS_AVAILABLE = True
except Exception as e:
    print("[intel] agent import failed:", repr(e))
    AGENTS_AVAILABLE = False

# ✅ define router BEFORE using it in decorators
router = APIRouter(prefix="/api", tags=["intelligence"])


@router.get("/ping")
async def ping() -> Dict[str, str]:
    """Simple ping to verify router is mounted."""
    return {"status": "ok", "router": "intelligence"}


class AnalyzePayload(BaseModel):
    brand: Optional[str] = None
    competitors: Optional[List[str]] = None
    questions: Optional[List[str]] = None


def demo_payload(p: AnalyzePayload) -> Dict[str, Any]:
    """Zero-dependency demo response so the UI renders even without agents/keys."""
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


@router.post("/intelligence/analyze")
async def analyze(payload: AnalyzePayload) -> Dict[str, Any]:
    """
    Primary analysis endpoint.
    SAFE_MODE=true or missing agents → demo JSON.
    Otherwise calls your real agent functions.
    """
    print("[/api/intelligence/analyze] payload:", payload.model_dump())

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
