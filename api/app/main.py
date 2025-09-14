# api/app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Import routers (keep if these files exist) ---
try:
    from .routers.intelligence import router as intelligence_router
except Exception as e:
    intelligence_router = None
    print("[warn] intelligence router not loaded:", e)

app = FastAPI(title="Signal & Scale API", version="1.0.0")

# --- CORS (allow your Render frontend) ---
frontend_origin = os.getenv("FRONTEND_ORIGIN", "https://signal-scale-frontend.onrender.com")
allowed_origins = [
    frontend_origin,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {
        "name": "Signal & Scale",
        "status": "ok",
        "env": os.getenv("ENV", "development"),
    }

# Mount routers if available
if intelligence_router:
    app.include_router(intelligence_router, prefix="/api")

# Root
@app.get("/")
def root():
    return {"message": "Signal & Scale API is running."}
