# --- BEGIN: ultra-compatible analyze handler ---
from datetime import datetime
from typing import Any, Dict
from fastapi import Body
import sys
print("[startup] cwd:", os.getcwd())
print("[startup] sys.path:", sys.path[:5])  # first few entries

@app.post("/api/intelligence/analyze")
async def intelligence_analyze(payload: Dict[str, Any] = Body(...)):
    """
    UI-safe response that includes multiple legacy keys:
    - success/message (boolean/string)
    - report (object with title/summary/highlights/metrics/actions)
    - data/output/result (aliases for consumers expecting different names)
    - meta/confidence/sources (commonly used in your other agents)
    - blocks (array placeholder)
    """
    now = datetime.utcnow().isoformat() + "Z"
    received = payload or {}
    report = {
        "title": "Dynamic Cultural Intelligence (Stub)",
        "summary": "Wiring check successful. Replace this with real agent output.",
        "highlights": [
            "Pipeline connected end-to-end",
            "Frontend calling correct backend",
            "Response matches expected shape"
        ],
        "metrics": {
            "mentions_week": 18,
            "sentiment_positive_pct": 75,
            "top_trends": ["Ralphcore", "Wide Leg Trousers", "Sustainable Streetwear"]
        },
        "actions": [
            {"priority": "High", "label": "Seed 2 creators on trending tag"},
            {"priority": "Medium", "label": "Lower free-shipping threshold test"}
        ],
    }

    # Build a super-set response (covers most UI expectations)
    response = {
        "success": True,
        "message": "Analysis successful",
        "timestamp": now,
        "meta": {
            "brand": received.get("brand", "Unknown"),
            "environment": os.getenv("ENV", "development"),
            "endpoint": "/api/intelligence/analyze"
        },
        "confidence": {"score": 0.9, "range": "High", "variance": 0.05},
        "sources": [{"type": "internal", "name": "bootstrap-stub", "count": 0}],
        "report": report,     # <-- primary key most UIs use
        "data": report,       # <-- alias some UIs expect
        "output": report,     # <-- alias for other codepaths
        "result": report,     # <-- alias again (belt & suspenders)
        "blocks": [],         # <-- placeholder if UI renders blocks
        "raw": {"received_input": received}
    }
    return response

# Optional: quick GET to test in browser address bar
@app.get("/api/intelligence/analyze/test")
def intelligence_analyze_test():
    return {"ok": True, "hint": "POST to /api/intelligence/analyze with JSON body", "ts": datetime.utcnow().isoformat()+"Z"}
# --- END: ultra-compatible analyze handler ---
