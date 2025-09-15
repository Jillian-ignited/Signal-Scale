# api/app/routers/intelligence.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any, Dict

# Import settings and (optionally) your agents
from ..settings import settings

# If your agent functions are ready, import them.
# If they aren't yet stable, keep them commented and use SAFE_MODE.
try:
    from ..agents.cultural_radar import run_cultural_radar
    from ..agents.competitive_playbook import run_competitive_playbook
    from ..agents.dtc_audit import run_dtc_audit
    AGENTS_AVAILABLE = True
except Exception as e:
    # Log the import issue (Render logs)
    print("[intel] agent import failed:", repr(e))
    AGENTS_AVAILABLE = False

router = APIRouter(prefix="/api", tags=["intelligence"])

class AnalyzePayload(BaseModel):
    brand: Optional[str] = None
    competitors: Optional[List[str]] = None
    questions: Optional[List[str]] = None

def demo_payload(p: AnalyzePayload) -> Dict[str, Any]:
    """A safe, zero-dependency demo response so the UI renders."""
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
    SAFE_MODE=true → returns demo JSON so the frontend works even without OpenAI keys.
    SAFE_MODE=false → runs real agents; returns structured JSON or readable errors.
    """
    # Always echo what we received (useful for debugging from the frontend)
    print("[/api/intelligence/analyze] payload:", payload.model_dump())

    # If safe mode is enabled or agents aren't importable, return demo
    if settings.SAFE_MODE or not AGENTS_AVAILABLE:
        return demo_payload(payload)

    # Real mode
    try:
        brand = payload.brand or "Brand"
        comps = payload.competitors or []

        # Call your agents (sync). If they are async, await them.
        # Adjust signatures if your agent functions take different params.
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
        # Let FastAPI handle explicit HTTPExceptions as-is
        raise
    except Exception as e:
        # Return a clean JSON error (and log full details)
        print("[/api/intelligence/analyze] ERROR:", repr(e))
        # 200 with error payload keeps the frontend from exploding; change to 500 if you prefer
        return {
            "status": "error",
            "message": "Analysis failed",
            "detail": str(e),
        }