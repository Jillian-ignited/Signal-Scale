import csv
import io
import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

# ----------------------------
# Models (tolerant to extras)
# ----------------------------
class Brand(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        extra = "ignore"

class Competitor(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    class Config:
        extra = "ignore"

class AnalyzeRequest(BaseModel):
    brand: Brand = Field(default_factory=Brand)
    competitors: List[Competitor] = Field(default_factory=list)

    class Config:
        extra = "ignore"

# ----------------------------
# App
# ----------------------------
app = FastAPI(title="Signal & Scale Intelligence API", version="1.0.0")

# CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",")] if allowed_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Helpers
# ----------------------------
def compute_simple_signals(req: AnalyzeRequest) -> List[Dict[str, Any]]:
    """
    Placeholder 'analysis' that always succeeds.
    Replace with your real logic (scrapers, LLM calls, etc.).
    """
    rows: List[Dict[str, Any]] = []
    bname = (req.brand.name or "").strip() or "Unknown Brand"

    if not req.competitors:
        rows.append({
            "brand": bname,
            "competitor": "",
            "signal": "No competitors submitted",
            "score": 0,
            "note": "Submit at least one competitor to analyze."
        })
        return rows

    for c in req.competitors:
        cname = (c.name or "").strip() or "Unnamed Competitor"
        rows.append({
            "brand": bname,
            "competitor": cname,
            "signal": "Stub: baseline comparison",
            "score": 50,
            "note": f"URL seen: {c.url or 'n/a'}"
        })
    return rows

# Return structured JSON + echo for debugging
def analyze_core(req: AnalyzeRequest) -> Dict[str, Any]:
    signals = compute_simple_signals(req)
    return {
        "ok": True,
        "brand": req.brand.dict(),
        "competitors_count": len(req.competitors),
        "signals": signals
    }

# ----------------------------
# Error Handler
# ----------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.json()
    except Exception:
        body = "<non-JSON or unreadable>"
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body_received": body},
    )

# ----------------------------
# Routes
# ----------------------------
@app.get("/api/health")
def health():
    return {"ok": True, "service": "signal-scale", "version": "1.0.0"}

@app.get("/api/intelligence/schema")
def schema():
    return {
        "expected": {
            "brand": {"name": "string", "url": "string", "meta": "object (optional)"},
            "competitors": "array of {name, url, meta}"
        }
    }

@app.post("/api/intelligence/analyze")
def analyze(req: AnalyzeRequest):
    return analyze_core(req)

@app.post("/api/intelligence/export")
def export_csv(req: AnalyzeRequest):
    """
    Returns a CSV built from the same request body.
    """
    result = analyze_core(req)
    rows = result.get("signals", [])  # list of dicts

    output = io.StringIO()
    fieldnames = ["brand", "competitor", "signal", "score", "note"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in fieldnames})

    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    headers = {
        "Content-Disposition": 'attachment; filename="signal_scale_export.csv"'
    }
    return StreamingResponse(csv_bytes, media_type="text/csv", headers=headers)
