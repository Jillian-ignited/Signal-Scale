"""
API routes for CI Orchestrator with React frontend integration
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
from pathlib import Path
import structlog

# Add the parent directory to the path so we can import from src
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root))

from src.models import CIOrchestratorInput, CIOrchestratorOutput, Brand, Competitor
from src.orchestrator import CIOrchestrator

logger = structlog.get_logger()

app = FastAPI(
    title="Signal & Scale - Brand Intelligence API",
    description="Competitive intelligence platform for fashion and consumer brands",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize orchestrator
orchestrator = CIOrchestrator()

# Mount static files for the React frontend
frontend_build_path = project_root / "frontend" / "dist"
if frontend_build_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_build_path / "assets")), name="assets")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "signal-scale-api"}

@app.post("/api/analyze", response_model=CIOrchestratorOutput)
async def analyze_brand(input_data: CIOrchestratorInput):
    """
    Run competitive intelligence analysis for a brand.
    
    This endpoint accepts brand information, competitors, and analysis parameters,
    then returns comprehensive insights across weekly reports, cultural radar,
    and peer tracking.
    """
    try:
        logger.info(f"Received analysis request for brand: {input_data.brand.name}")
        result = await orchestrator.run_analysis(input_data)
        return result
    except Exception as e:
        logger.error(f"Error in analysis endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/demo-data")
async def get_demo_data():
    """Get demo data for frontend development and testing."""
    
    demo_input = CIOrchestratorInput(
        brand=Brand(
            name="Crooks & Castles",
            url="https://crooksncastles.com",
            meta={
                "aliases": ["C&C", "Crooks"],
                "hashtags": ["#crooksncastles", "#crooks", "#streetwear"]
            }
        ),
        competitors=[
            Competitor(name="Stüssy", url="https://stussy.com"),
            Competitor(name="Hellstar", url="https://hellstar.com"),
            Competitor(name="Reason Clothing", url="https://reasonclothing.com"),
            Competitor(name="Supreme", url="https://supremenewyork.com"),
            Competitor(name="BAPE", url="https://bape.com")
        ],
        mode="all",
        window_days=7,
        max_results_per_section=5
    )
    
    try:
        result = await orchestrator.run_analysis(demo_input)
        return result
    except Exception as e:
        logger.warning(f"Demo data analysis failed, returning mock data: {str(e)}")
        # Return mock data if analysis fails
        return {
            "weekly_report": {
                "brand_mentions_overview": {"this_window": 847, "prev_window": 623, "delta_pct": 35.9},
                "customer_sentiment": {
                    "positive": "Strong positive sentiment around new Heritage Collection",
                    "negative": "Some pricing concerns on premium pieces",
                    "neutral": "General discussions about sizing and fit"
                },
                "engagement_highlights": [],
                "streetwear_trends": [],
                "competitive_mentions": [],
                "opportunities_risks": []
            },
            "cultural_radar": {
                "creators": [],
                "top_3_to_activate": []
            },
            "peer_tracker": {
                "scorecard": {
                    "dimensions": ["Homepage", "PDP", "Checkout"],
                    "brands": ["Crooks & Castles", "Stüssy", "Supreme"],
                    "scores": []
                },
                "strengths": [],
                "gaps": [],
                "priority_fixes": []
            },
            "warnings": ["Demo mode - using mock data"],
            "provenance": {"sources": []}
        }

@app.get("/api/modes")
async def get_modes():
    """Get available analysis modes and their descriptions."""
    return {
        "modes": ["weekly_report", "cultural_radar", "peer_tracker", "all"],
        "descriptions": {
            "weekly_report": "Track brand mentions, sentiment, engagement highlights, and competitive analysis",
            "cultural_radar": "Identify emerging creators and influencers in your target market",
            "peer_tracker": "Audit your DTC site against competitors across key dimensions",
            "all": "Combined analysis across all modes"
        }
    }

# Legacy endpoints for backward compatibility
@app.post("/analyze", response_model=CIOrchestratorOutput)
async def analyze_legacy(input_data: CIOrchestratorInput):
    """Legacy analyze endpoint for backward compatibility."""
    return await analyze_brand(input_data)

@app.get("/modes")
async def get_modes_legacy():
    """Legacy modes endpoint for backward compatibility."""
    return await get_modes()

@app.get("/")
async def root():
    """Root endpoint - serve React app or API info."""
    index_file = frontend_build_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {
            "message": "Signal & Scale - Brand Intelligence API",
            "version": "1.0.0",
            "frontend": "React app not built - run 'npm run build' in frontend directory"
        }

# Serve React app for all other routes
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve the React frontend for all non-API routes."""
    # Check if it's a static file request
    if full_path.startswith("assets/"):
        file_path = frontend_build_path / full_path
        if file_path.exists():
            return FileResponse(file_path)
    
    # For all other routes, serve the React app
    index_file = frontend_build_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        # Fallback if frontend not built
        return {
            "message": "Signal & Scale API", 
            "error": "Frontend not built",
            "instructions": "Run 'cd frontend && npm run build' to build the React app"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

