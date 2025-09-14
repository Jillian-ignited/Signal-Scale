# api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.app.agents.cultural_radar import run_cultural_radar
from api.app.agents.competitive_playbook import run_competitive_playbook

app = FastAPI(title="Signal & Scale API", version="1.0")

# ✅ Add CORS so frontend requests aren’t blocked
origins = [
    "https://signal-scale-frontend.onrender.com",  # your frontend
    "http://localhost:5173",  # dev mode
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/api/intelligence/analyze")
def analyze(payload: dict):
    return {"message": "Analysis successful", "input": payload}

@app.post("/api/run/cultural_radar")
def cultural_radar(payload: dict):
    return run_cultural_radar(payload)

@app.post("/api/run/competitive_playbook")
def competitive_playbook(payload: dict):
    return run_competitive_playbook(payload)
