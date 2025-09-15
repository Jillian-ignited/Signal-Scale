import csv, io, os, json, time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field

# ---------- ⚙️ Auth ----------
def load_api_keys() -> List[str]:
    # Accept comma or newline separated keys
    raw = os.getenv("API_KEYS", "").strip()
    if not raw:
        return []
    parts = [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]
    return list(dict.fromkeys(parts))  # dedupe but keep order

API_KEYS = load_api_keys()

def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    if API_KEYS and (x_api_key not in API_KEYS):
        # If keys are configured, a valid one is required
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key

# ---------- Models ----------
class Brand(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    class Config: extra = "ignore"

class Competitor(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    class Config: extra = "ignore"

class AnalyzeRequest(BaseModel):
    brand: Brand = Field(default_factory=Brand)
    competitors: List[Competitor] = Field(default_factory=list)
    class Config: extra = "ignore"

# ---------- App ----------
app = FastAPI(title="Signal & Scale Intelligence API", version="1.1.0")

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
origins = [o.strip() for o in allowed_origins.split(",")] if allowed_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Error details ----------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    try:
        body = await request.json()
    except Exception:
        body = "<non-JSON or unreadable>"
    return JSONResponse(status_code=422, content={"detail": exc.errors(), "body_received": body})

# ---------- Health & schema ----------
@app.get("/api/health")
def health():
    return {"ok": True, "service": "signal-scale", "version": "1.1.0", "has_api_keys": bool(API_KEYS)}

@app.get("/api/intelligence/schema")
def schema():
    return {
        "expected": {
            "brand": {"name": "string", "url": "string", "meta": "object (optional)"},
            "competitors": "array of {name, url, meta}"
        }
    }

# ---------- ⚙️ Manus integration stub ----------
MANUS_API_KEY = os.getenv("MANUS_API_KEY", "").strip()
MANUS_AGENT_ID = os.getenv("MANUS_AGENT_ID", "").strip()  # your template/agent id, if applicable

def call_manus_agents(brand: Brand, competitors: List[Competitor]) -> List[Dict[str, Any]]:
    """
    Replace this stub with your real Manus agent call.
    Keep the return shape stable for export.
    """
    # Example: use MANUS_API_KEY/MANUS_AGENT_ID to query your workflow
    # Pseudocode:
    # client = Manus(api_key=MANUS_API_KEY)
    # resp = client.run(agent_id=MANUS_AGENT_ID, input={...})
    # return normalize(resp)

    rows: List[Dict[str, Any]] = []
    bname = (brand.name or "").strip() or "Unknown Brand"
    if not competitors:
        rows.append({"brand": bname, "competitor": "", "signal": "No competitors submitted", "score": 0, "note": "Add competitors."})
        return rows
    for c in competitors:
        cname = (c.name or "").strip() or "Unnamed Competitor"
        rows.append({
            "brand": bname, "competitor": cname,
            "signal": "Stub: Manus pipeline result",
            "score": 50, "note": f"URL: {c.url or 'n/a'}"
        })
    return rows

def analyze_core(req: AnalyzeRequest) -> Dict[str, Any]:
    signals = call_manus_agents(req.brand, req.competitors)
    return {"ok": True, "brand": req.brand.dict(), "competitors_count": len(req.competitors), "signals": signals}

# ---------- Routes (guarded) ----------
@app.post("/api/intelligence/analyze")
def analyze(req: AnalyzeRequest, _api_key=Depends(require_api_key)):
    return analyze_core(req)

@app.post("/api/intelligence/export")
def export_csv(req: AnalyzeRequest, _api_key=Depends(require_api_key)):
    result = analyze_core(req)
    rows = result.get("signals", [])
    output = io.StringIO()
    fieldnames = ["brand", "competitor", "signal", "score", "note"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow({k: r.get(k, "") for k in fieldnames})
    csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
    headers = {"Content-Disposition": 'attachment; filename="signal_scale_export.csv"'}
    return StreamingResponse(csv_bytes, media_type="text/csv", headers=headers)
