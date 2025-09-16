"""
API routes for CI Orchestrator - Simplified version without Pydantic
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
from pathlib import Path

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

# Mount static files for the React frontend - only if directory exists
frontend_build_path = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_build_path.exists() and (frontend_build_path / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_build_path / "assets")), name="assets")

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "service": "signal-scale-api"}

@app.post("/api/analyze")
async def analyze_brand(request_data: dict):
    """
    Run competitive intelligence analysis for a brand.
    Returns demo data for now - can be connected to real analysis later.
    """
    try:
        # Extract brand name from request if provided
        brand_name = "Crooks & Castles"
        if isinstance(request_data, dict) and "brand" in request_data:
            if isinstance(request_data["brand"], dict) and "name" in request_data["brand"]:
                brand_name = request_data["brand"]["name"]
        
        # Return comprehensive demo data
        return {
            "weekly_report": {
                "brand_mentions_overview": {
                    "this_window": 847,
                    "prev_window": 623,
                    "delta_pct": 35.9
                },
                "customer_sentiment": {
                    "positive": f"Strong positive sentiment around new {brand_name} Heritage Collection drop, with customers praising authentic street culture representation and quality improvements",
                    "negative": "Some pricing concerns on premium pieces, with comparisons to Stüssy and Supreme pricing strategies",
                    "neutral": "General discussions about sizing and fit, with neutral commentary on shipping and customer service"
                },
                "engagement_highlights": [
                    {
                        "platform": "TikTok",
                        "content": "Heritage Collection unboxing video",
                        "engagement": 45000,
                        "sentiment": "positive"
                    }
                ],
                "streetwear_trends": [
                    {
                        "trend": "Heritage Revival",
                        "description": "Increased mentions of vintage-inspired pieces and throwback designs",
                        "hashtags": ["#heritage", "#vintage", "#throwback", "#authentic"]
                    },
                    {
                        "trend": "Utility Aesthetics", 
                        "description": "Growing interest in functional streetwear with cargo pants and technical fabrics",
                        "hashtags": ["#utility", "#cargo", "#techwear", "#functional"]
                    }
                ],
                "competitive_mentions": [],
                "opportunities_risks": [
                    {
                        "type": "opportunity",
                        "description": "Heritage trend alignment with brand DNA",
                        "priority": "high"
                    }
                ]
            },
            "cultural_radar": {
                "creators": [
                    {
                        "handle": "@streetwear_maven",
                        "platform": "TikTok",
                        "followers": 89000,
                        "engagement_rate": 8.7,
                        "influence_score": 92,
                        "recommendation": "seed",
                        "content_focus": "streetwear styling, brand reviews"
                    }
                ],
                "top_3_to_activate": ["@streetwear_maven", "@urban_fits", "@hypebeast_daily"]
            },
            "peer_tracker": {
                "scorecard": {
                    "dimensions": ["Homepage", "PDP", "Checkout"],
                    "brands": [brand_name, "Stüssy", "Hellstar", "Reason Clothing", "Supreme"],
                    "scores": [
                        {"brand": brand_name, "scores": [7, 6, 5]},
                        {"brand": "Stüssy", "scores": [9, 8, 8]},
                        {"brand": "Hellstar", "scores": [6, 7, 6]},
                        {"brand": "Reason Clothing", "scores": [5, 5, 4]},
                        {"brand": "Supreme", "scores": [8, 9, 7]}
                    ]
                },
                "strengths": ["Strong brand heritage", "Quality product photography"],
                "gaps": ["Checkout flow optimization needed", "Mobile experience needs improvement"],
                "priority_fixes": [
                    {
                        "action": "Implement one-click checkout with Apple Pay, Google Pay, and Shop Pay",
                        "impact": "high",
                        "description": "Could reduce cart abandonment by 25-30% based on industry benchmarks"
                    }
                ]
            },
            "warnings": ["Demo mode - using mock data for demonstration"],
            "provenance": {"sources": ["Social media monitoring (demo)", "Website analysis (demo)", "Creator database (demo)"]}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/demo-data")
async def get_demo_data():
    """Get demo data for frontend development and testing."""
    return await analyze_brand({
        "brand": {"name": "Crooks & Castles"},
        "competitors": [{"name": "Stüssy"}, {"name": "Hellstar"}, {"name": "Reason Clothing"}, {"name": "Supreme"}]
    })

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

@app.post("/analyze")
async def analyze_legacy(request_data: dict):
    """Legacy analyze endpoint for backward compatibility."""
    return await analyze_brand(request_data)

@app.get("/modes")
async def get_modes_legacy():
    """Legacy modes endpoint for backward compatibility."""
    return await get_modes()

@app.get("/")
@app.head("/")
async def root():
    """Root endpoint - serve React app or API info."""
    index_file = frontend_build_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {
            "message": "Signal & Scale - Brand Intelligence API",
            "version": "1.0.0",
            "frontend": "React app not built - add index.html to frontend/dist/ directory"
        }

@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    """Serve the React frontend for all non-API routes."""
    index_file = frontend_build_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {
            "message": "Signal & Scale API", 
            "error": "Frontend not built",
            "instructions": "Add index.html to frontend/dist/ directory"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
