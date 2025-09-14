from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from datetime import datetime
import logging
import os
from .models import AnalysisRequest, ExportRequest
from .agents.cultural_radar import run_cultural_radar
from .agents.competitive_playbook import run_competitive_playbook
from .agents.dtc_audit import run_dtc_audit
from .services.exporter import export_html, export_markdown
from .db import ping, init_db
from .settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Signal & Scale API",
    description="AI-powered competitive intelligence platform",
    version="1.0.0",
    docs_url="/docs" if settings.ENV == "development" else None,
    redoc_url="/redoc" if settings.ENV == "development" else None,
)

# CORS middleware
origins = ["*"] if settings.ENV == "development" else [
    "https://signal-scale.onrender.com",
    "https://your-frontend-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "operational",
        "environment": settings.ENV,
        "timestamp": datetime.now().isoformat(),
        "docs_url": "/docs" if settings.ENV == "development" else "disabled"
    }

@app.get("/healthz")
async def health_check():
    try:
        ping()
        return {
            "status": "healthy",
            "database": "connected",
            "environment": settings.ENV,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@app.post("/api/run/cultural_radar")
async def cultural_radar_analysis(request: AnalysisRequest):
    try:
        brand_dict = request.brand.dict()
        competitors_list = [c.dict() for c in request.competitors]
        analysis = await run_cultural_radar(brand_dict, competitors_list)
        
        return {
            "agent": "Cultural Radar v3.0",
            "brand": brand_dict,
            "competitors": competitors_list,
            "generated_at": datetime.now().isoformat(),
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Cultural radar analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/run/competitive_playbook")
async def competitive_playbook_analysis(request: AnalysisRequest):
    try:
        brand_dict = request.brand.dict()
        competitors_list = [c.dict() for c in request.competitors]
        analysis = await run_competitive_playbook(brand_dict, competitors_list)
        
        return {
            "agent": "Competitive Playbook v3.2",
            "brand": brand_dict,
            "competitors": competitors_list,
            "generated_at": datetime.now().isoformat(),
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"Competitive playbook analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/run/dtc_audit")
async def dtc_audit_analysis(request: AnalysisRequest):
    try:
        brand_dict = request.brand.dict()
        competitors_list = [c.dict() for c in request.competitors]
        analysis = await run_dtc_audit(brand_dict, competitors_list)
        
        return {
            "agent": "DTC Audit v2.1",
            "brand": brand_dict,
            "competitors": competitors_list,
            "generated_at": datetime.now().isoformat(),
            "analysis": analysis
        }
    except Exception as e:
        logger.error(f"DTC audit analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/export")
async def export_report(request: ExportRequest):
    try:
        if request.format == "html":
            content = export_html(request.payload)
            return HTMLResponse(content=content)
        else:
            content = export_markdown(request.payload)
            return PlainTextResponse(content=content)
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@app.get("/ping")
async def ping_endpoint():
    return {"status": "pong"}
