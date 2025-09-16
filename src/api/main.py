"""
API routes for CI Orchestrator
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.models import CIOrchestratorInput, CIOrchestratorOutput
from src.orchestrator import CIOrchestrator
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="CI Orchestrator API",
    description="A competitive intelligence agent for fashion/streetwear brands.",
    version="1.0.0",
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

@app.post("/analyze", response_model=CIOrchestratorOutput)
async def analyze(input_data: CIOrchestratorInput):
    """
    Run the CI Orchestrator analysis based on the provided input.
    """
    try:
        logger.info(f"Received analysis request for brand: {input_data.brand.name}")
        result = await orchestrator.run_analysis(input_data)
        return result
    except Exception as e:
        logger.error(f"Error in analysis endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"message": "CI Orchestrator API is running."}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "CI Orchestrator API"}

@app.get("/modes")
async def get_modes():
    return {
        "modes": ["weekly_report", "cultural_radar", "peer_tracker", "all"],
        "descriptions": {
            "weekly_report": "Track brand mentions, sentiment, engagement highlights, and competitive analysis",
            "cultural_radar": "Identify emerging creators and influencers in your target market",
            "peer_tracker": "Audit your DTC site against competitors across key dimensions",
            "all": "Combined analysis across all modes"
        }
    }