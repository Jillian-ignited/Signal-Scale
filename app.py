# app.py
from fastapi import FastAPI, HTTPException, Body, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import io
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

# -----------------------
# Settings (simple version)
# -----------------------
ENV = os.getenv("ENV", "development")
SAFE_MODE = os.getenv("SAFE_MODE", "true").lower() in ("1", "true", "yes")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "https://signal-scale-frontend.onrender.com")

# Jinja2 environment for /templates
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html", "xml"])
)

app = FastAPI(title="Signal & Scale API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Health + Docs
# -----------------------
@app.get("/healthz")
def health():
    return {
        "name": "Signal & Scale",
        "version": "1.0.0",
        "status": "operational",
        "environment": ENV,
        "timestamp": datetime.utcnow().isoformat(),
        "docs_url": "/docs"
    }

# -----------------------
# Analyze (SAFE demo)
# -----------------------
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

@app.post("/api/intelligence/analyze")
def analyze(payload: AnalyzePayload):
    print("[/api/intelligence/analyze] payload:", payload.model_dump())
    # REAL agents can be wired later. For now, ensure the endpoint always works:
    if SAFE_MODE:
        return demo_payload(payload)

    # If you later wire real agents, wrap them in try/except and return JSON.
    return demo_payload(payload)

# -----------------------
# Export endpoint
# -----------------------
@app.post("/api/export/report")
def export_report(
    data: Dict[str, Any] = Body(...),
    format: str = "md"  # "md" | "html" | "pdf"
):
    """
    Expects JSON body like:
    {
      "brand": "...",
      "competitors": [...],
      "summary": {...},  # whatever your frontend shows
      "confidence": {...}
    }
    And query ?format=md|html|pdf  (or include "format" in body if you prefer)
    """
    # Allow body to override the query default
    fmt = (data.get("format") or format or "md").lower()
    brand_slug = (data.get("brand") or "report").replace(" ", "_")

    # Render Markdown
    if fmt == "md":
        tpl = jinja_env.get_template("report.md.j2")
        md = tpl.render(**data)
        return Response(
            content=md,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{brand_slug}_signal_scale.md"'}
        )

    # Render HTML (download)
    if fmt == "html":
        tpl = jinja_env.get_template("report.html")
        html = tpl.render(**data)
        return Response(
            content=html,
            media_type="text/html",
            headers={"Content-Disposition": f'attachment; filename="{brand_slug}_signal_scale.html"'}
        )

    # Optional PDF (pure-Python fallback using xhtml2pdf)
    if fmt == "pdf":
        try:
            from xhtml2pdf import pisa  # pure Python; no system deps
        except Exception:
            raise HTTPException(status_code=500, detail="PDF export not available on this server.")

        tpl = jinja_env.get_template("report.html")
        html = tpl.render(**data)
        pdf_io = io.BytesIO()
        result = pisa.CreatePDF(io.StringIO(html), dest=pdf_io)
        if result.err:
            raise HTTPException(status_code=500, detail="PDF generation failed.")
        pdf_io.seek(0)
        return StreamingResponse(
            pdf_io,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{brand_slug}_signal_scale.pdf"'}
        )

    raise HTTPException(status_code=400, detail="Unsupported format. Use md|html|pdf.")
