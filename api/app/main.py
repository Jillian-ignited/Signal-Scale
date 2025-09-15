# api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import intelligence
from .settings import settings

app = FastAPI(title="Signal & Scale API", version="1.0.0")

# --- CORS ---
# Allow your Render frontend and local dev
origins = set(settings.ALLOWED_ORIGINS)
origins.add("https://signal-scale-frontend.onrender.com")
origins.add("http://localhost:5173")
origins.add("http://127.0.0.1:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---
@app.get("/healthz")
def health():
    return {
        "name": "Signal & Scale",
        "status": "ok",
        "mode": "SAFE" if settings.SAFE_MODE else "REAL",
    }

# Mount /api/* routes (your frontend calls /api/intelligence/analyze)
app.include_router(intelligence.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Signal & Scale API root. See /docs"}
